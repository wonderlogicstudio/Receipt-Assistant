from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import AppConfig
from app.db.repository import JobHistoryRepository
from app.history.job_service import JobHistoryService
from app.ui.history_utils import (
    CARD_DETAIL_COLUMNS,
    EXPORT_FILE_COLUMNS,
    RECEIPT_DETAIL_COLUMNS,
    build_safe_download_path,
    card_transactions_to_history_detail_dataframe,
    export_files_to_display_dataframe,
    job_detail_to_summary_dict,
    read_export_file_bytes,
    receipt_records_to_history_detail_dataframe,
    select_latest_export_file,
)


def sample_job_detail():
    return {
        "job": {
            "id": "job-123456789",
            "created_at": "2026-05-10T13:20:30",
            "status": "completed",
            "receipt_count": 1,
            "card_transaction_count": 1,
            "needs_review_count": 1,
            "excluded_count": 0,
            "total_amount": 141420,
            "export_file_name": "result.xlsx",
            "export_relative_path": "data/outputs/job/result.xlsx",
        },
        "receipt_records": [
            {
                "transaction_date": "2026-05-10",
                "merchant_name": "테스트상호",
                "total_amount": 141420,
                "supply_amount": 128563,
                "vat_amount": 12857,
                "expense_category": "사무용품비",
                "recommended_expense_category": "사무용품비",
                "review_status": "needs_review",
                "review_reasons_json": '["사용자 확인 필요"]',
                "card_match_status": "matched",
                "card_match_reason": "금액/날짜 후보",
                "duplicate_suspected": 0,
                "source_file_name": r"C:\private\receipt.jpg",
                "stored_relative_path": r"C:\private\receipt.jpg",
                "raw_text": "hidden raw text",
                "raw_json": "hidden raw json",
            }
        ],
        "card_transactions": [
            {
                "transaction_date": "2026-05-10",
                "merchant_name": "테스트상호",
                "total_amount": 141420,
                "card_name": "테스트카드",
                "approval_number": "1234567890123456",
                "parse_status": "parsed",
                "source_file_name": r"C:\private\card.csv",
                "stored_relative_path": r"C:\private\card.csv",
            }
        ],
        "export_files": [
            {
                "export_file_name": r"C:\private\result.xlsx",
                "export_relative_path": r"C:\private\result.xlsx",
                "file_size_bytes": 2048,
                "created_at": "2026-05-10T13:20:30",
            }
        ],
    }


def test_job_detail_to_summary_dict_converts_display_values():
    summary = job_detail_to_summary_dict(sample_job_detail())

    assert summary["작업ID"] == "job-123456789"
    assert summary["처리일시"] == "2026-05-10 13:20"
    assert summary["상태"] == "completed"
    assert summary["총금액"] == "141,420"
    assert summary["엑셀파일명"] == "result.xlsx"
    assert "export_relative_path" not in summary


def test_receipt_records_to_history_detail_dataframe_hides_internal_fields():
    dataframe = receipt_records_to_history_detail_dataframe(sample_job_detail()["receipt_records"])

    assert list(dataframe.columns) == RECEIPT_DETAIL_COLUMNS
    assert dataframe.loc[0, "원본파일명"] == "receipt.jpg"
    serialized = dataframe.to_string()
    assert "C:" not in serialized
    assert "private" not in serialized
    assert "stored_relative_path" not in serialized
    assert "raw_text" not in serialized
    assert "raw_json" not in serialized


def test_card_transactions_to_history_detail_dataframe_hides_internal_fields():
    dataframe = card_transactions_to_history_detail_dataframe(sample_job_detail()["card_transactions"])

    assert list(dataframe.columns) == CARD_DETAIL_COLUMNS
    assert dataframe.loc[0, "원본파일명"] == "card.csv"
    assert dataframe.loc[0, "승인번호"] == "***3456"
    serialized = dataframe.to_string()
    assert "1234567890123456" not in serialized
    assert "C:" not in serialized
    assert "stored_relative_path" not in serialized


def test_export_files_to_display_dataframe_hides_relative_paths():
    dataframe = export_files_to_display_dataframe(sample_job_detail()["export_files"])

    assert list(dataframe.columns) == EXPORT_FILE_COLUMNS
    assert dataframe.loc[0, "엑셀파일명"] == "result.xlsx"
    assert dataframe.loc[0, "파일크기"] == "2.0 KB"
    serialized = dataframe.to_string()
    assert "export_relative_path" not in serialized
    assert "C:" not in serialized


def test_select_latest_export_file_uses_created_at():
    latest = select_latest_export_file(
        [
            {"id": "old", "created_at": "2026-05-10T10:00:00"},
            {"id": "new", "created_at": "2026-05-10T11:00:00"},
        ]
    )

    assert latest["id"] == "new"
    assert select_latest_export_file([]) is None


def test_build_safe_download_path_allows_output_dir_child(tmp_path):
    output_root = tmp_path / "data" / "outputs"
    path = build_safe_download_path(output_root, "data/outputs/job/result.xlsx")

    assert path == (output_root / "job" / "result.xlsx").resolve()


@pytest.mark.parametrize("unsafe_path", ["../secret.xlsx", "job/../secret.xlsx", r"C:\private\secret.xlsx"])
def test_build_safe_download_path_rejects_unsafe_paths(tmp_path, unsafe_path):
    with pytest.raises(ValueError):
        build_safe_download_path(tmp_path / "data" / "outputs", unsafe_path)


def test_read_export_file_bytes_reads_existing_file(tmp_path):
    output_root = tmp_path / "data" / "outputs"
    target = output_root / "job" / "result.xlsx"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"xlsx")

    assert read_export_file_bytes(output_root, "data/outputs/job/result.xlsx") == b"xlsx"


def test_read_export_file_bytes_returns_none_for_missing_file(tmp_path):
    assert read_export_file_bytes(tmp_path / "data" / "outputs", "data/outputs/job/missing.xlsx") is None


def test_service_detail_and_latest_export_file(tmp_path):
    config = AppConfig(app_db_path=tmp_path / "history.db", output_root=tmp_path / "data" / "outputs")
    service = JobHistoryService(repository=JobHistoryRepository(config=config), config=config)
    job = service.save_job_result(
        session_id="session-a",
        receipt_records=[sample_job_detail()["receipt_records"][0]],
        card_transactions=[sample_job_detail()["card_transactions"][0]],
        export_file={
            "session_id": "session-a",
            "export_file_name": "result.xlsx",
            "export_relative_path": "data/outputs/job/result.xlsx",
            "file_size_bytes": 4,
        },
    )

    detail = service.get_processing_job_detail(str(job["id"]))
    latest = service.get_latest_export_file(str(job["id"]))

    assert detail["job"]["id"] == job["id"]
    assert len(detail["receipt_records"]) == 1
    assert len(detail["card_transactions"]) == 1
    assert len(detail["export_files"]) == 1
    assert latest["export_file_name"] == "result.xlsx"
    assert service.get_processing_job_detail("missing") is None
    assert service.get_latest_export_file("missing") is None

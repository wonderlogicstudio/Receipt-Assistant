from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from app.core.card_models import CardTransaction
from app.core.config import AppConfig
from app.core.enums import CardMatchStatus, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.db.repository import JobHistoryRepository
from app.history.job_service import JobHistoryService
from app.storage.file_store import StoredFileMetadata


def make_service(tmp_path: Path) -> JobHistoryService:
    config = AppConfig(
        app_db_path=tmp_path / "history.db",
        output_root=tmp_path / "data" / "outputs",
    )
    repository = JobHistoryRepository(config=config)
    return JobHistoryService(repository=repository, config=config)


def make_receipt(*, review_status: str = ReviewStatus.NEEDS_REVIEW.value, amount: int = 12000) -> ReceiptRecord:
    return ReceiptRecord.create(
        session_id="session-a",
        source_file_id="source-a",
        ocr_result_id="ocr-a",
        source_file_name=r"C:\private\receipt.jpg",
        stored_relative_path=r"C:\private\data\uploads\receipt.jpg",
        evidence_type="receipt_image",
        transaction_date=date(2026, 5, 10),
        merchant_name="테스트상호",
        business_number="123-45-67890",
        total_amount=amount,
        supply_amount=10909,
        vat_amount=1091,
        payment_method="카드",
        expense_category=None,
        review_status=review_status,
        review_reason="사용자 확인 필요",
        confidence=0.9,
        card_match_status=CardMatchStatus.UNMATCHED.value,
        parser_warnings=["상호 확인"],
        review_reasons=["사용자 확인 필요"],
        recommended_expense_category="사무용품비",
        validation_warnings=["금액 확인"],
    )


def make_card() -> CardTransaction:
    return CardTransaction.create(
        session_id="session-a",
        source_file_id="card-source",
        source_file_name=r"C:\private\card.csv",
        stored_relative_path=r"C:\private\data\uploads\card.csv",
        row_number=1,
        transaction_date=date(2026, 5, 10),
        merchant_name="테스트상호",
        total_amount=12000,
        card_name="테스트카드",
        approval_number="1234567890123456",
    )


def make_upload() -> StoredFileMetadata:
    return StoredFileMetadata(
        original_file_name=r"C:\private\receipt.jpg",
        stored_file_name="receipt_safe.jpg",
        stored_relative_path=r"C:\private\data\uploads\receipt.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session-a",
    )


def test_service_creates_job_and_saves_result_summary(tmp_path):
    service = make_service(tmp_path)
    job = service.create_processing_job("session-a")

    updated = service.save_job_result(
        job_id=str(job["id"]),
        session_id="session-a",
        uploaded_files=[make_upload()],
        receipt_records=[
            make_receipt(review_status=ReviewStatus.NEEDS_REVIEW.value, amount=12000),
            make_receipt(review_status=ReviewStatus.EXCLUDED.value, amount=5000),
        ],
        card_transactions=[make_card()],
        export_file={
            "session_id": "session-a",
            "export_file_name": "result.xlsx",
            "export_relative_path": "data/outputs/job/result.xlsx",
            "file_size_bytes": 100,
        },
    )

    assert updated["receipt_count"] == 2
    assert updated["card_transaction_count"] == 1
    assert updated["needs_review_count"] == 1
    assert updated["excluded_count"] == 1
    assert updated["total_amount"] == 12000
    assert updated["export_file_name"] == "result.xlsx"


def test_service_lists_jobs_and_returns_detail(tmp_path):
    service = make_service(tmp_path)
    job = service.save_job_result(
        session_id="session-a",
        uploaded_files=[make_upload()],
        receipt_records=[make_receipt()],
        card_transactions=[make_card()],
    )

    listed = service.list_processing_jobs()
    detail = service.get_processing_job_detail(str(job["id"]))

    assert listed[0]["id"] == job["id"]
    assert detail["job"]["id"] == job["id"]
    assert len(detail["uploaded_files"]) == 1
    assert len(detail["receipt_records"]) == 1
    assert len(detail["card_transactions"]) == 1
    assert detail["export_files"] == []
    assert service.get_processing_job_detail("missing") is None


def test_service_saves_export_bytes_to_file_and_relative_path_only(tmp_path):
    service = make_service(tmp_path)
    job = service.create_processing_job("session-a")

    export = service.save_export_file_info(
        job_id=str(job["id"]),
        session_id="session-a",
        export_file_name="result.xlsx",
        export_bytes=b"excel-bytes",
    )

    assert export["export_relative_path"] == f"data/outputs/{job['id']}/result.xlsx"
    assert (tmp_path / "data" / "outputs" / str(job["id"]) / "result.xlsx").read_bytes() == b"excel-bytes"


def test_service_save_job_result_can_store_export_bytes(tmp_path):
    service = make_service(tmp_path)

    job = service.save_job_result(
        session_id="session-a",
        receipt_records=[make_receipt()],
        card_transactions=[make_card()],
        export_file={
            "session_id": "session-a",
            "export_file_name": "result.xlsx",
            "export_bytes": b"excel-bytes",
        },
    )
    detail = service.get_processing_job_detail(str(job["id"]))
    export_file = detail["export_files"][0]

    assert job["export_file_name"] == "result.xlsx"
    assert export_file["export_relative_path"] == f"data/outputs/{job['id']}/result.xlsx"
    assert (tmp_path / "data" / "outputs" / str(job["id"]) / "result.xlsx").read_bytes() == b"excel-bytes"


def test_service_does_not_store_raw_ocr_json_card_source_or_absolute_paths(tmp_path):
    service = make_service(tmp_path)
    raw_ocr_text = "OCR 원문 전체가 들어가면 안 됩니다"
    raw_json_marker = "raw_json_secret"
    card_source_marker = "card_source_full_row"

    job = service.save_job_result(
        session_id="session-a",
        uploaded_files=[make_upload()],
        receipt_records=[
            {
                **make_receipt().to_dict(),
                "ocr_raw_text": raw_ocr_text,
                "raw_json": {"secret": raw_json_marker},
            }
        ],
        card_transactions=[
            {
                **make_card().__dict__,
                "source_raw_row": card_source_marker,
                "approval_number": "1234567890123456",
            }
        ],
    )

    with sqlite3.connect(tmp_path / "history.db") as connection:
        serialized = "\n".join(
            str(value)
            for table in ("uploaded_files", "receipt_records", "card_transactions", "processing_jobs")
            for row in connection.execute(f"SELECT * FROM {table}").fetchall()
            for value in row
            if value is not None
        )

    assert str(tmp_path) not in serialized
    assert "C:" not in serialized
    assert raw_ocr_text not in serialized
    assert raw_json_marker not in serialized
    assert card_source_marker not in serialized
    assert "1234567890123456" not in serialized

    detail = service.get_processing_job_detail(str(job["id"]))
    receipt = detail["receipt_records"][0]
    card = detail["card_transactions"][0]

    assert json.loads(receipt["parser_warnings_json"]) == ["상호 확인"]
    assert card["approval_number"] == "***3456"

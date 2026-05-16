from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.core.config import AppConfig
from app.db.repository import JobHistoryRepository
from app.history.job_service import JobHistoryService
from tests.standard_parser_regression_helpers import (
    assert_no_forbidden_text,
    parse_azure_adapter_fixture,
    parse_standard_fixture,
)


def _service(tmp_path) -> JobHistoryService:
    config = AppConfig(
        upload_root=tmp_path / "data" / "uploads",
        upload_relative_root=Path("data/uploads"),
        output_root=tmp_path / "data" / "outputs",
        app_db_path=tmp_path / "history.db",
    )
    return JobHistoryService(repository=JobHistoryRepository(config=config), config=config)


def test_standard_parser_records_save_to_processing_history_without_schema_change(tmp_path) -> None:
    service = _service(tmp_path)
    records = [
        parse_standard_fixture("mock_receipt_standard.json"),
        parse_standard_fixture("azure_like_receipt_standard.json"),
        parse_standard_fixture("edge_case_receipt_standard.json"),
        parse_azure_adapter_fixture("azure_receipt_sanitized_response.json"),
    ]

    job = service.save_job_result(
        session_id="session-standard-regression",
        receipt_records=records,
        export_file={
            "session_id": "session-standard-regression",
            "export_file_name": "standard_parser_regression.xlsx",
            "export_bytes": b"sample-xlsx-bytes",
        },
        status="completed",
    )
    detail = service.get_processing_job_detail(str(job["id"]))

    assert detail is not None
    assert detail["job"]["receipt_count"] == len(records)
    assert detail["job"]["total_amount"] == sum(record.total_amount or 0 for record in records)
    assert len(detail["receipt_records"]) == len(records)
    assert len(detail["export_files"]) == 1
    assert detail["export_files"][0]["export_file_name"] == "standard_parser_regression.xlsx"
    assert_no_forbidden_text(detail)


def test_processing_history_receipt_rows_keep_standard_parser_warning_fields_safely(tmp_path) -> None:
    service = _service(tmp_path)
    record = parse_standard_fixture("azure_like_receipt_standard.json")

    job = service.save_job_result(session_id="session-warning-regression", receipt_records=[record])
    detail = service.get_processing_job_detail(str(job["id"]))
    row = detail["receipt_records"][0]

    assert row["source_file_name"] == "sample_azure_receipt_001.pdf"
    assert row["vat_review_required"] == 1
    assert json.loads(row["vat_warnings_json"])
    assert json.loads(row["sensitive_text_categories_json"]) == ["wifi_credential"]
    assert "provider_fields" not in json.dumps(row, ensure_ascii=False, default=str)
    assert_no_forbidden_text(row)


def test_processing_history_masks_or_omits_raw_provider_metadata_and_absolute_paths(tmp_path) -> None:
    service = _service(tmp_path)
    record = parse_azure_adapter_fixture("azure_receipt_edge_sanitized_response.json")

    job = service.save_job_result(
        session_id="session-safe-regression",
        receipt_records=[record],
        export_file={
            "session_id": "session-safe-regression",
            "export_file_name": r"C:\private\standard_parser.xlsx",
            "export_relative_path": r"C:\private\standard_parser.xlsx",
            "file_size_bytes": 42,
        },
    )
    detail = service.get_processing_job_detail(str(job["id"]))
    serialized = json.dumps(detail, ensure_ascii=False, default=str)

    assert detail["export_files"][0]["export_file_name"] == "standard_parser.xlsx"
    assert detail["export_files"][0]["export_relative_path"] == "standard_parser.xlsx"
    assert "C:" not in serialized
    assert "private" not in serialized
    assert_no_forbidden_text(detail)


def test_processing_history_schema_does_not_add_standard_ocr_or_provider_fields_columns(tmp_path) -> None:
    service = _service(tmp_path)
    service.create_processing_job(session_id="session-schema-regression")

    with sqlite3.connect(tmp_path / "history.db") as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(receipt_records)").fetchall()}

    assert "standard_ocr_result" not in columns
    assert "provider_fields" not in columns
    assert "provider_raw_response" not in columns
    assert "raw_json" not in columns
    assert "raw_text" not in columns

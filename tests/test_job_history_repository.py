from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.db.database import init_db
from app.db.repository import JobHistoryRepository


def test_init_db_creates_job_history_tables(tmp_path):
    db_path = tmp_path / "history.db"

    init_db(db_path=db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {
        "processing_jobs",
        "uploaded_files",
        "receipt_records",
        "card_transactions",
        "export_files",
        "merchant_master",
        "merchant_alias",
        "merchant_source_log",
    }.issubset(table_names)

    with sqlite3.connect(db_path) as connection:
        merchant_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(merchant_master)").fetchall()
        }
        source_log_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(merchant_source_log)").fetchall()
        }

    assert {
        "road_name",
        "building_main_number",
        "building_sub_number",
        "building_name",
        "road_address",
        "normalized_road_address",
    }.issubset(merchant_columns)
    assert {"source_file_hash", "duplicate_file"}.issubset(source_log_columns)


def test_repository_creates_gets_and_lists_jobs_latest_first(tmp_path):
    repository = JobHistoryRepository(db_path=tmp_path / "history.db")
    first = repository.create_job(session_id="session-a", job_id="job-a")
    second = repository.create_job(session_id="session-b", job_id="job-b")

    assert repository.get_job(first["id"])["session_id"] == "session-a"
    assert repository.get_job("missing") is None

    jobs = repository.list_jobs(limit=1, offset=0)

    assert jobs[0]["id"] == second["id"]
    assert repository.list_jobs(limit=1, offset=1)[0]["id"] == first["id"]


def test_repository_saves_and_reads_related_rows_without_absolute_paths(tmp_path):
    repository = JobHistoryRepository(db_path=tmp_path / "history.db")
    job = repository.create_job(session_id="session-a")
    job_id = str(job["id"])

    repository.save_uploaded_files(
        job_id,
        [
            {
                "session_id": "session-a",
                "original_file_name": r"C:\private\receipt.jpg",
                "stored_file_name": "receipt_safe.jpg",
                "stored_relative_path": r"C:\private\data\uploads\receipt.jpg",
                "file_extension": ".jpg",
                "file_size_bytes": 10,
                "file_role": "receipt",
            }
        ],
    )
    repository.save_receipt_records(
        job_id,
        [
            {
                "id": "receipt-a",
                "session_id": "session-a",
                "source_file_id": "source-a",
                "ocr_result_id": "ocr-a",
                "source_file_name": r"C:\private\receipt.jpg",
                "transaction_date": "2026-05-10",
                "merchant_name": "테스트상호",
                "business_number": "123-45-67890",
                "total_amount": 12000,
                "gross_amount": 13000,
                "discount_amount": 1000,
                "final_amount": 12000,
                "paid_amount": 12000,
                "amount_source": "paid_amount",
                "amount_warnings": ["discount_detected"],
                "supply_amount": 10909,
                "vat_amount": 1091,
                "estimated_supply_amount": None,
                "estimated_vat_amount": None,
                "vat_source": "explicit",
                "vat_note": "영수증에 부가세가 명시되어 있음",
                "vat_warnings": [],
                "vat_review_required": False,
                "sensitive_text_detected": True,
                "sensitive_text_categories": ["wifi_password"],
                "sensitive_warnings": ["wifi_password_detected"],
                "payment_method": "카드",
                "recommended_expense_category": "사무용품비",
                "expense_category": None,
                "review_status": "needs_review",
                "review_reasons": ["확인 필요"],
                "validation_warnings": ["금액 확인"],
                "parser_warnings": ["상호 확인"],
                "card_match_status": "unmatched",
                "card_match_reason": None,
                "card_match_score": None,
                "duplicate_suspected": False,
                "memo": None,
            }
        ],
    )
    repository.save_card_transactions(
        job_id,
        [
            {
                "id": "card-a",
                "session_id": "session-a",
                "source_file_id": "card-source",
                "source_file_name": r"C:\private\card.csv",
                "transaction_date": "2026-05-10",
                "merchant_name": "테스트상호",
                "total_amount": 12000,
                "card_name": "테스트카드",
                "approval_number": "1234567890123456",
                "currency": "KRW",
                "parse_status": "parsed",
                "warning_messages": ["확인"],
            }
        ],
    )
    export = repository.save_export_file(
        job_id,
        {
            "session_id": "session-a",
            "export_file_name": r"C:\private\result.xlsx",
            "export_relative_path": r"C:\private\result.xlsx",
            "file_size_bytes": 100,
        },
    )

    uploaded = repository.get_uploaded_files_by_job(job_id)[0]
    receipt = repository.get_receipt_records_by_job(job_id)[0]
    card = repository.get_card_transactions_by_job(job_id)[0]
    exports = repository.get_export_files_by_job(job_id)

    assert uploaded["original_file_name"] == "receipt.jpg"
    assert uploaded["stored_relative_path"] == "receipt.jpg"
    assert receipt["source_file_name"] == "receipt.jpg"
    assert receipt["gross_amount"] == 13000
    assert receipt["discount_amount"] == 1000
    assert receipt["final_amount"] == 12000
    assert receipt["paid_amount"] == 12000
    assert receipt["amount_source"] == "paid_amount"
    assert json.loads(receipt["amount_warnings_json"]) == ["discount_detected"]
    assert receipt["vat_source"] == "explicit"
    assert receipt["vat_note"] == "영수증에 부가세가 명시되어 있음"
    assert json.loads(receipt["vat_warnings_json"]) == []
    assert receipt["vat_review_required"] == 0
    assert receipt["sensitive_text_detected"] == 1
    assert json.loads(receipt["sensitive_text_categories_json"]) == ["wifi_password"]
    assert json.loads(receipt["sensitive_warnings_json"]) == ["wifi_password_detected"]
    assert json.loads(receipt["parser_warnings_json"]) == ["상호 확인"]
    assert card["source_file_name"] == "card.csv"
    assert card["approval_number"] == "***3456"
    assert exports[0]["export_file_name"] == "result.xlsx"
    assert export["export_relative_path"] == "result.xlsx"

    serialized_rows = "\n".join(
        str(value)
        for row in [uploaded, receipt, card, exports[0]]
        for value in row.values()
        if value is not None
    )
    assert str(tmp_path) not in serialized_rows
    assert "C:" not in serialized_rows
    assert "raw_text" not in serialized_rows
    assert "raw_json" not in serialized_rows


def test_repository_updates_job_summary(tmp_path):
    repository = JobHistoryRepository(db_path=tmp_path / "history.db")
    job = repository.create_job(session_id="session-a")

    updated = repository.update_job_summary(
        str(job["id"]),
        status="completed",
        receipt_count=2,
        card_transaction_count=3,
        needs_review_count=1,
        excluded_count=1,
        total_amount=12000,
        export_file_name="result.xlsx",
        export_relative_path="data/outputs/job/result.xlsx",
    )

    assert updated["status"] == "completed"
    assert updated["receipt_count"] == 2
    assert updated["card_transaction_count"] == 3
    assert updated["needs_review_count"] == 1
    assert updated["excluded_count"] == 1
    assert updated["total_amount"] == 12000
    assert updated["export_relative_path"] == "data/outputs/job/result.xlsx"

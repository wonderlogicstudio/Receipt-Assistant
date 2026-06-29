from __future__ import annotations

from datetime import date

from app.core.config import AppConfig
from app.db.database import get_connection, init_db
from app.db.repository import JobHistoryRepository
from app.history.job_service import JobHistoryService
from app.history.safe_diagnostics import build_processing_history_safety_diagnostic


def test_processing_history_safety_diagnostic_uses_counts_only(tmp_path):
    config = AppConfig(app_db_path=tmp_path / "history.db")
    service = JobHistoryService(repository=JobHistoryRepository(config=config), config=config)
    service.save_job_result(
        session_id="session-safe",
        receipt_records=[
            {
                "id": "receipt-safe",
                "session_id": "session-safe",
                "source_file_name": "receipt.jpg",
                "transaction_date": date(2026, 5, 19),
                "merchant_name": "Safe Store",
                "business_number": "123-45-67890",
                "total_amount": 5600,
                "payment_method": "card",
                "review_status": "needs_review",
            }
        ],
        uploaded_files=[
            {
                "session_id": "session-safe",
                "original_file_name": "receipt.jpg",
                "stored_file_name": "receipt.jpg",
                "stored_relative_path": "data/uploads/session-safe/receipt.jpg",
                "file_extension": ".jpg",
                "file_size_bytes": 10,
            }
        ],
        export_file={"export_file_name": "result.xlsx", "export_bytes": b"excel"},
    )

    diagnostic = build_processing_history_safety_diagnostic(config=config)
    serialized = str(diagnostic.as_display_dict())

    assert diagnostic.is_safe is True
    assert diagnostic.forbidden_column_count == 0
    assert diagnostic.absolute_path_value_count == 0
    assert diagnostic.receipt_record_count == 1
    assert "Safe Store" not in serialized
    assert "receipt.jpg" not in serialized
    assert "data/uploads" not in serialized


def test_processing_history_safety_diagnostic_counts_unsafe_schema_or_values(tmp_path):
    db_path = tmp_path / "history.db"
    init_db(db_path=db_path)
    with get_connection(db_path=db_path) as connection:
        connection.execute("ALTER TABLE receipt_records ADD COLUMN raw_text TEXT")
        connection.execute(
            """
            INSERT INTO processing_jobs (
                id, session_id, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "job-unsafe",
                "session-unsafe",
                "completed",
                "2026-06-19T00:00:00",
                "2026-06-19T00:00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO receipt_records (
                id, job_id, source_file_name, merchant_name, raw_text, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "receipt-unsafe",
                "job-unsafe",
                r"C:\private\receipt.jpg",
                "Unsafe Store",
                "synthetic raw ocr text",
                "2026-06-19T00:00:00",
                "2026-06-19T00:00:00",
            ),
        )

    diagnostic = build_processing_history_safety_diagnostic(db_path=db_path)
    serialized = str(diagnostic.as_display_dict())

    assert diagnostic.is_safe is False
    assert diagnostic.forbidden_column_count >= 1
    assert diagnostic.absolute_path_value_count >= 1
    assert "synthetic raw ocr text" not in serialized
    assert "C:\\private" not in serialized

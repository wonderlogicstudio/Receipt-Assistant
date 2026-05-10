from __future__ import annotations

from app.ui.history_utils import (
    HISTORY_COLUMNS,
    build_history_summary,
    format_amount,
    format_history_datetime,
    jobs_to_history_dataframe,
    sanitize_history_display_row,
)


def test_jobs_to_history_dataframe_uses_expected_display_columns():
    dataframe = jobs_to_history_dataframe(
        [
            {
                "id": "job-abcdef123456",
                "created_at": "2026-05-10T13:20:30",
                "status": "completed",
                "receipt_count": 2,
                "card_transaction_count": 3,
                "needs_review_count": 1,
                "excluded_count": 0,
                "total_amount": 141420,
                "export_file_name": "result.xlsx",
                "export_relative_path": "data/outputs/job/result.xlsx",
                "stored_relative_path": "data/uploads/session/file.jpg",
                "raw_text": "hidden",
                "raw_json": {"hidden": True},
            }
        ]
    )

    assert list(dataframe.columns) == HISTORY_COLUMNS
    assert dataframe.loc[0, "처리일시"] == "2026-05-10 13:20"
    assert dataframe.loc[0, "총금액"] == "141,420"
    assert dataframe.loc[0, "엑셀파일명"] == "result.xlsx"
    assert dataframe.loc[0, "작업ID"] == "job-abcd"
    serialized = dataframe.to_string()
    assert "export_relative_path" not in serialized
    assert "stored_relative_path" not in serialized
    assert "raw_text" not in serialized
    assert "raw_json" not in serialized
    assert "data/outputs" not in serialized
    assert "data/uploads" not in serialized


def test_format_amount_handles_numbers_and_empty_values():
    assert format_amount(141420) == "141,420"
    assert format_amount("12000") == "12,000"
    assert format_amount(None) == "-"
    assert format_amount("not-a-number") == "-"


def test_format_history_datetime_handles_valid_and_invalid_values():
    assert format_history_datetime("2026-05-10T13:20:30") == "2026-05-10 13:20"
    assert format_history_datetime(None) == "-"
    assert format_history_datetime("bad-date") == "-"


def test_build_history_summary_calculates_current_rows_only():
    summary = build_history_summary(
        [
            {
                "receipt_count": 2,
                "card_transaction_count": 3,
                "needs_review_count": 1,
                "total_amount": 10000,
            },
            {
                "receipt_count": 1,
                "card_transaction_count": 0,
                "needs_review_count": 1,
                "total_amount": 5000,
            },
        ]
    )

    assert summary == {
        "total_jobs": 2,
        "total_receipts": 3,
        "total_card_transactions": 3,
        "total_needs_review": 2,
        "total_amount": 15000,
    }


def test_empty_jobs_return_empty_dataframe_and_zero_summary():
    dataframe = jobs_to_history_dataframe([])
    summary = build_history_summary([])

    assert list(dataframe.columns) == HISTORY_COLUMNS
    assert dataframe.empty
    assert summary == {
        "total_jobs": 0,
        "total_receipts": 0,
        "total_card_transactions": 0,
        "total_needs_review": 0,
        "total_amount": 0,
    }


def test_sanitize_history_display_row_does_not_leave_paths_or_internal_fields():
    row = sanitize_history_display_row(
        {
            "id": "job-123456789",
            "created_at": "2026-05-10T13:20:30",
            "status": "",
            "receipt_count": None,
            "card_transaction_count": None,
            "needs_review_count": None,
            "excluded_count": None,
            "total_amount": None,
            "export_file_name": r"C:\private\result.xlsx",
            "export_relative_path": r"C:\private\result.xlsx",
            "stored_relative_path": r"C:\private\receipt.jpg",
            "raw_text": "hidden",
            "raw_json": "hidden",
        }
    )

    assert set(row) == set(HISTORY_COLUMNS)
    assert row["상태"] == "-"
    assert row["엑셀파일명"] == "result.xlsx"
    serialized = " ".join(str(value) for value in row.values())
    assert "C:" not in serialized
    assert "private" not in serialized
    assert "hidden" not in serialized

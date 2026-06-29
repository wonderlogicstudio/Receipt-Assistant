from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from app.core.config import AppConfig
from app.db.database import get_connection, init_db


FORBIDDEN_HISTORY_COLUMN_TOKENS = (
    "raw_text",
    "raw_json",
    "provider_raw",
    "full_ocr_text",
    "operation_location",
    "endpoint",
    "api_key",
    "secret",
    "token",
)
HISTORY_TABLES = (
    "processing_jobs",
    "uploaded_files",
    "receipt_records",
    "card_transactions",
    "export_files",
)
ABSOLUTE_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\|/Users/|/home/|/var/|/tmp/)")


@dataclass(frozen=True)
class ProcessingHistorySafetyDiagnostic:
    table_count: int
    checked_table_count: int
    forbidden_column_count: int
    absolute_path_value_count: int
    checked_text_value_count: int
    receipt_record_count: int
    uploaded_file_count: int
    export_file_count: int

    @property
    def is_safe(self) -> bool:
        return self.forbidden_column_count == 0 and self.absolute_path_value_count == 0

    def as_display_dict(self) -> dict[str, object]:
        return {
            "checked_table_count": self.checked_table_count,
            "forbidden_column_count": self.forbidden_column_count,
            "absolute_path_value_count": self.absolute_path_value_count,
            "checked_text_value_count": self.checked_text_value_count,
            "receipt_record_count": self.receipt_record_count,
            "uploaded_file_count": self.uploaded_file_count,
            "export_file_count": self.export_file_count,
            "is_safe": self.is_safe,
        }


def build_processing_history_safety_diagnostic(
    *,
    config: AppConfig | None = None,
    db_path: Path | str | None = None,
    value_scan_limit: int = 500,
) -> ProcessingHistorySafetyDiagnostic:
    init_db(config=config, db_path=db_path)
    checked_text_value_count = 0
    absolute_path_value_count = 0
    forbidden_column_count = 0
    checked_table_count = 0
    safe_scan_limit = max(1, min(int(value_scan_limit), 5000))

    with get_connection(config=config, db_path=db_path) as connection:
        existing_tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        for table_name in HISTORY_TABLES:
            if table_name not in existing_tables:
                continue
            checked_table_count += 1
            columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            text_columns: list[str] = []
            for column in columns:
                column_name = str(column["name"])
                column_type = str(column["type"] or "").upper()
                normalized = column_name.lower()
                if any(token in normalized for token in FORBIDDEN_HISTORY_COLUMN_TOKENS):
                    forbidden_column_count += 1
                if "TEXT" in column_type or not column_type:
                    text_columns.append(column_name)
            if text_columns:
                selected_columns = ", ".join(f'"{column}"' for column in text_columns)
                rows = connection.execute(
                    f"SELECT {selected_columns} FROM {table_name} LIMIT ?",
                    (safe_scan_limit,),
                ).fetchall()
                for row in rows:
                    for column in text_columns:
                        value = row[column]
                        if value in {None, ""}:
                            continue
                        checked_text_value_count += 1
                        if ABSOLUTE_PATH_PATTERN.search(str(value)):
                            absolute_path_value_count += 1

        receipt_record_count = _table_count(connection, "receipt_records")
        uploaded_file_count = _table_count(connection, "uploaded_files")
        export_file_count = _table_count(connection, "export_files")

    return ProcessingHistorySafetyDiagnostic(
        table_count=len(HISTORY_TABLES),
        checked_table_count=checked_table_count,
        forbidden_column_count=forbidden_column_count,
        absolute_path_value_count=absolute_path_value_count,
        checked_text_value_count=checked_text_value_count,
        receipt_record_count=receipt_record_count,
        uploaded_file_count=uploaded_file_count,
        export_file_count=export_file_count,
    )


def _table_count(connection, table_name: str) -> int:
    try:
        row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    except Exception:
        return 0
    return int(row["count"] or 0)

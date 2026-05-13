from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import AppConfig, get_config
from app.db.schema import SCHEMA_SQL


RECEIPT_RECORD_COLUMN_MIGRATIONS = {
    "gross_amount": "INTEGER",
    "discount_amount": "INTEGER",
    "final_amount": "INTEGER",
    "paid_amount": "INTEGER",
    "amount_source": "TEXT",
    "amount_warnings_json": "TEXT",
    "estimated_supply_amount": "INTEGER",
    "estimated_vat_amount": "INTEGER",
    "vat_source": "TEXT",
    "vat_note": "TEXT",
    "vat_warnings_json": "TEXT",
    "vat_review_required": "INTEGER",
    "sensitive_text_detected": "INTEGER",
    "sensitive_text_categories_json": "TEXT",
    "sensitive_warnings_json": "TEXT",
}


def _db_path(config: AppConfig | None = None, db_path: Path | str | None = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return (config or get_config()).app_db_path


@contextmanager
def get_connection(
    config: AppConfig | None = None,
    db_path: Path | str | None = None,
) -> Iterator[sqlite3.Connection]:
    path = _db_path(config, db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(config: AppConfig | None = None, db_path: Path | str | None = None) -> None:
    with get_connection(config=config, db_path=db_path) as connection:
        for statement in SCHEMA_SQL:
            connection.execute(statement)
        _ensure_columns(connection, "receipt_records", RECEIPT_RECORD_COLUMN_MIGRATIONS)


def _ensure_columns(connection: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
    for column_name, column_type in columns.items():
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

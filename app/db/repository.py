from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from app.core.config import AppConfig
from app.core.exceptions import ReceiptAssistantError
from app.db.database import get_connection, init_db


class JobHistoryRepositoryError(ReceiptAssistantError):
    """Raised when job history persistence fails."""


class JobHistoryRepository:
    def __init__(self, db_path: Path | str | None = None, config: AppConfig | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else None
        self.config = config
        init_db(config=config, db_path=self.db_path)

    def create_job(
        self,
        *,
        session_id: str | None = None,
        status: str = "created",
        note: str | None = None,
        job_id: str | None = None,
    ) -> dict[str, object]:
        now = _utc_now()
        row = {
            "id": job_id or str(uuid4()),
            "session_id": session_id,
            "status": status,
            "created_at": now,
            "updated_at": now,
            "receipt_count": 0,
            "card_transaction_count": 0,
            "needs_review_count": 0,
            "excluded_count": 0,
            "total_amount": 0,
            "export_file_name": None,
            "export_relative_path": None,
            "note": note,
        }
        self._execute(
            """
            INSERT INTO processing_jobs (
                id, session_id, status, created_at, updated_at, receipt_count,
                card_transaction_count, needs_review_count, excluded_count,
                total_amount, export_file_name, export_relative_path, note
            ) VALUES (
                :id, :session_id, :status, :created_at, :updated_at, :receipt_count,
                :card_transaction_count, :needs_review_count, :excluded_count,
                :total_amount, :export_file_name, :export_relative_path, :note
            )
            """,
            row,
        )
        return row

    def update_job_summary(self, job_id: str, **summary: object) -> dict[str, object] | None:
        allowed = {
            "status",
            "receipt_count",
            "card_transaction_count",
            "needs_review_count",
            "excluded_count",
            "total_amount",
            "export_file_name",
            "export_relative_path",
            "note",
        }
        values = {key: value for key, value in summary.items() if key in allowed}
        if "export_relative_path" in values:
            values["export_relative_path"] = _safe_relative_path(values["export_relative_path"])
        values["updated_at"] = _utc_now()
        assignments = ", ".join(f"{key} = :{key}" for key in values)
        values["id"] = job_id
        self._execute(f"UPDATE processing_jobs SET {assignments} WHERE id = :id", values)
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, object] | None:
        rows = self._fetch_all("SELECT * FROM processing_jobs WHERE id = ?", (job_id,))
        return rows[0] if rows else None

    def list_jobs(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, object]]:
        safe_limit = max(min(int(limit), 200), 1)
        safe_offset = max(int(offset), 0)
        return self._fetch_all(
            "SELECT * FROM processing_jobs ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (safe_limit, safe_offset),
        )

    def save_uploaded_files(self, job_id: str, uploaded_files: Iterable[dict[str, object]]) -> None:
        rows = []
        for item in uploaded_files:
            rows.append(
                {
                    "id": str(item.get("id") or uuid4()),
                    "job_id": job_id,
                    "session_id": item.get("session_id"),
                    "original_file_name": _display_file_name(item.get("original_file_name")),
                    "stored_file_name": _display_file_name(item.get("stored_file_name")),
                    "stored_relative_path": _safe_relative_path(item.get("stored_relative_path")),
                    "file_extension": item.get("file_extension"),
                    "file_size_bytes": item.get("file_size_bytes"),
                    "file_role": item.get("file_role"),
                    "created_at": str(item.get("created_at") or _utc_now()),
                }
            )
        self._executemany(
            """
            INSERT INTO uploaded_files (
                id, job_id, session_id, original_file_name, stored_file_name,
                stored_relative_path, file_extension, file_size_bytes, file_role, created_at
            ) VALUES (
                :id, :job_id, :session_id, :original_file_name, :stored_file_name,
                :stored_relative_path, :file_extension, :file_size_bytes, :file_role, :created_at
            )
            """,
            rows,
        )

    def save_receipt_records(self, job_id: str, receipt_records: Iterable[dict[str, object]]) -> None:
        rows = []
        now = _utc_now()
        for item in receipt_records:
            rows.append(
                {
                    "id": str(item.get("id") or uuid4()),
                    "job_id": job_id,
                    "session_id": item.get("session_id"),
                    "source_file_id": item.get("source_file_id"),
                    "ocr_result_id": item.get("ocr_result_id"),
                    "source_file_name": _display_file_name(item.get("source_file_name")),
                    "transaction_date": item.get("transaction_date"),
                    "merchant_name": item.get("merchant_name"),
                    "business_number": item.get("business_number"),
                    "total_amount": item.get("total_amount"),
                    "gross_amount": item.get("gross_amount"),
                    "discount_amount": item.get("discount_amount"),
                    "final_amount": item.get("final_amount"),
                    "paid_amount": item.get("paid_amount"),
                    "amount_source": item.get("amount_source"),
                    "amount_warnings_json": _json_text(item.get("amount_warnings")),
                    "supply_amount": item.get("supply_amount"),
                    "vat_amount": item.get("vat_amount"),
                    "estimated_supply_amount": item.get("estimated_supply_amount"),
                    "estimated_vat_amount": item.get("estimated_vat_amount"),
                    "vat_source": item.get("vat_source"),
                    "vat_note": item.get("vat_note"),
                    "vat_warnings_json": _json_text(item.get("vat_warnings")),
                    "vat_review_required": 1 if item.get("vat_review_required") else 0,
                    "sensitive_text_detected": 1 if item.get("sensitive_text_detected") else 0,
                    "sensitive_text_categories_json": _json_text(item.get("sensitive_text_categories")),
                    "sensitive_warnings_json": _json_text(item.get("sensitive_warnings")),
                    "payment_method": item.get("payment_method"),
                    "recommended_expense_category": item.get("recommended_expense_category"),
                    "expense_category": item.get("expense_category"),
                    "review_status": item.get("review_status"),
                    "review_reasons_json": _json_text(item.get("review_reasons")),
                    "validation_warnings_json": _json_text(item.get("validation_warnings")),
                    "parser_warnings_json": _json_text(item.get("parser_warnings")),
                    "card_match_status": item.get("card_match_status"),
                    "card_match_reason": item.get("card_match_reason"),
                    "card_match_score": item.get("card_match_score"),
                    "duplicate_suspected": 1 if item.get("duplicate_suspected") else 0,
                    "memo": item.get("memo"),
                    "created_at": str(item.get("created_at") or now),
                    "updated_at": str(item.get("updated_at") or now),
                }
            )
        self._executemany(
            """
            INSERT INTO receipt_records (
                id, job_id, session_id, source_file_id, ocr_result_id, source_file_name,
                transaction_date, merchant_name, business_number, total_amount, gross_amount,
                discount_amount, final_amount, paid_amount, amount_source, amount_warnings_json,
                supply_amount, vat_amount, estimated_supply_amount, estimated_vat_amount, vat_source,
                vat_note, vat_warnings_json, vat_review_required, sensitive_text_detected,
                sensitive_text_categories_json, sensitive_warnings_json, payment_method, recommended_expense_category, expense_category,
                review_status, review_reasons_json, validation_warnings_json, parser_warnings_json,
                card_match_status, card_match_reason, card_match_score, duplicate_suspected,
                memo, created_at, updated_at
            ) VALUES (
                :id, :job_id, :session_id, :source_file_id, :ocr_result_id, :source_file_name,
                :transaction_date, :merchant_name, :business_number, :total_amount, :gross_amount,
                :discount_amount, :final_amount, :paid_amount, :amount_source, :amount_warnings_json,
                :supply_amount, :vat_amount, :estimated_supply_amount, :estimated_vat_amount, :vat_source,
                :vat_note, :vat_warnings_json, :vat_review_required, :sensitive_text_detected,
                :sensitive_text_categories_json, :sensitive_warnings_json, :payment_method, :recommended_expense_category, :expense_category,
                :review_status, :review_reasons_json, :validation_warnings_json, :parser_warnings_json,
                :card_match_status, :card_match_reason, :card_match_score, :duplicate_suspected,
                :memo, :created_at, :updated_at
            )
            """,
            rows,
        )

    def save_card_transactions(self, job_id: str, card_transactions: Iterable[dict[str, object]]) -> None:
        rows = []
        for item in card_transactions:
            rows.append(
                {
                    "id": str(item.get("id") or uuid4()),
                    "job_id": job_id,
                    "session_id": item.get("session_id"),
                    "source_file_id": item.get("source_file_id"),
                    "source_file_name": _display_file_name(item.get("source_file_name")),
                    "transaction_date": item.get("transaction_date"),
                    "merchant_name": item.get("merchant_name"),
                    "total_amount": item.get("total_amount"),
                    "card_name": item.get("card_name"),
                    "approval_number": _safe_approval_number(item.get("approval_number")),
                    "currency": item.get("currency") or "KRW",
                    "parse_status": item.get("parse_status"),
                    "warning_messages_json": _json_text(item.get("warning_messages")),
                    "created_at": str(item.get("created_at") or _utc_now()),
                }
            )
        self._executemany(
            """
            INSERT INTO card_transactions (
                id, job_id, session_id, source_file_id, source_file_name, transaction_date,
                merchant_name, total_amount, card_name, approval_number, currency, parse_status,
                warning_messages_json, created_at
            ) VALUES (
                :id, :job_id, :session_id, :source_file_id, :source_file_name, :transaction_date,
                :merchant_name, :total_amount, :card_name, :approval_number, :currency, :parse_status,
                :warning_messages_json, :created_at
            )
            """,
            rows,
        )

    def save_export_file(self, job_id: str, export_file: dict[str, object]) -> dict[str, object]:
        row = {
            "id": str(export_file.get("id") or uuid4()),
            "job_id": job_id,
            "session_id": export_file.get("session_id"),
            "export_file_name": _display_file_name(export_file.get("export_file_name")),
            "export_relative_path": _safe_relative_path(export_file.get("export_relative_path")),
            "file_size_bytes": export_file.get("file_size_bytes"),
            "created_at": str(export_file.get("created_at") or _utc_now()),
        }
        self._execute(
            """
            INSERT INTO export_files (
                id, job_id, session_id, export_file_name, export_relative_path, file_size_bytes, created_at
            ) VALUES (
                :id, :job_id, :session_id, :export_file_name, :export_relative_path, :file_size_bytes, :created_at
            )
            """,
            row,
        )
        self.update_job_summary(
            job_id,
            export_file_name=row["export_file_name"],
            export_relative_path=row["export_relative_path"],
        )
        return row

    def get_uploaded_files_by_job(self, job_id: str) -> list[dict[str, object]]:
        return self._fetch_all("SELECT * FROM uploaded_files WHERE job_id = ? ORDER BY created_at ASC", (job_id,))

    def get_receipt_records_by_job(self, job_id: str) -> list[dict[str, object]]:
        return self._fetch_all("SELECT * FROM receipt_records WHERE job_id = ? ORDER BY created_at ASC", (job_id,))

    def get_card_transactions_by_job(self, job_id: str) -> list[dict[str, object]]:
        return self._fetch_all("SELECT * FROM card_transactions WHERE job_id = ? ORDER BY created_at ASC", (job_id,))

    def get_export_files_by_job(self, job_id: str) -> list[dict[str, object]]:
        return self._fetch_all("SELECT * FROM export_files WHERE job_id = ? ORDER BY created_at ASC", (job_id,))

    def _execute(self, sql: str, parameters: dict[str, object] | tuple[object, ...]) -> None:
        try:
            with get_connection(config=self.config, db_path=self.db_path) as connection:
                connection.execute(sql, parameters)
        except sqlite3.Error as exc:
            raise JobHistoryRepositoryError("job history database operation failed") from exc

    def _executemany(self, sql: str, rows: list[dict[str, object]]) -> None:
        if not rows:
            return
        try:
            with get_connection(config=self.config, db_path=self.db_path) as connection:
                connection.executemany(sql, rows)
        except sqlite3.Error as exc:
            raise JobHistoryRepositoryError("job history database operation failed") from exc

    def _fetch_all(self, sql: str, parameters: tuple[object, ...]) -> list[dict[str, object]]:
        try:
            with get_connection(config=self.config, db_path=self.db_path) as connection:
                cursor = connection.execute(sql, parameters)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            raise JobHistoryRepositoryError("job history database operation failed") from exc


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def _json_text(value: object) -> str:
    if value is None:
        value = []
    if not isinstance(value, (list, tuple)):
        value = [str(value)]
    return json.dumps(list(value), ensure_ascii=False)


def _display_file_name(value: object) -> str | None:
    if value in {None, ""}:
        return None
    return Path(str(value).replace("\\", "/")).name


def _safe_relative_path(value: object) -> str | None:
    if value in {None, ""}:
        return None
    text = str(value).replace("\\", "/").strip()
    if not text:
        return None
    if Path(text).is_absolute() or ":" in text.split("/")[0]:
        return Path(text).name
    return text.lstrip("/")


def _safe_approval_number(value: object) -> str | None:
    if value in {None, ""}:
        return None
    text = str(value).strip()
    digits = "".join(character for character in text if character.isdigit())
    if len(digits) >= 12:
        return f"***{digits[-4:]}"
    return text

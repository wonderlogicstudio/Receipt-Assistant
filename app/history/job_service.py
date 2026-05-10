from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from app.core.config import AppConfig, get_config
from app.core.enums import ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.core.card_models import CardTransaction
from app.db.repository import JobHistoryRepository
from app.storage.file_store import StoredFileMetadata


class JobHistoryService:
    def __init__(
        self,
        repository: JobHistoryRepository | None = None,
        *,
        config: AppConfig | None = None,
    ) -> None:
        self.config = config or get_config()
        self.repository = repository or JobHistoryRepository(config=self.config)

    def create_processing_job(self, session_id: str | None = None) -> dict[str, object]:
        return self.repository.create_job(session_id=session_id, status="created")

    def save_job_result(
        self,
        *,
        job_id: str | None = None,
        session_id: str | None = None,
        uploaded_files: Iterable[StoredFileMetadata | dict[str, object]] | None = None,
        receipt_records: Iterable[ReceiptRecord | dict[str, object]] | None = None,
        card_transactions: Iterable[CardTransaction | dict[str, object]] | None = None,
        export_file: dict[str, object] | None = None,
        status: str = "completed",
        note: str | None = None,
    ) -> dict[str, object]:
        job = self.repository.get_job(job_id) if job_id else None
        if job is None:
            job = self.repository.create_job(session_id=session_id, status="created", job_id=job_id)
        safe_job_id = str(job["id"])

        uploaded_rows = [_uploaded_file_to_row(item) for item in (uploaded_files or [])]
        receipt_rows = [_receipt_record_to_row(item) for item in (receipt_records or [])]
        card_rows = [_card_transaction_to_row(item) for item in (card_transactions or [])]

        self.repository.save_uploaded_files(safe_job_id, uploaded_rows)
        self.repository.save_receipt_records(safe_job_id, receipt_rows)
        self.repository.save_card_transactions(safe_job_id, card_rows)

        export_row = None
        if export_file is not None:
            export_row = self.repository.save_export_file(
                safe_job_id,
                self._prepare_export_file_row(safe_job_id, session_id, export_file),
            )

        summary = _build_summary(receipt_rows, card_rows)
        summary["status"] = status
        summary["note"] = note
        if export_row is not None:
            summary["export_file_name"] = export_row["export_file_name"]
            summary["export_relative_path"] = export_row["export_relative_path"]
        updated_job = self.repository.update_job_summary(safe_job_id, **summary)
        return updated_job or self.repository.get_job(safe_job_id) or job

    def list_processing_jobs(self, limit: int = 50, offset: int = 0) -> list[dict[str, object]]:
        return self.repository.list_jobs(limit=limit, offset=offset)

    def get_processing_job_detail(self, job_id: str) -> dict[str, object] | None:
        job = self.repository.get_job(job_id)
        if job is None:
            return None
        return {
            "job": job,
            "uploaded_files": self.repository.get_uploaded_files_by_job(job_id),
            "receipt_records": self.repository.get_receipt_records_by_job(job_id),
            "card_transactions": self.repository.get_card_transactions_by_job(job_id),
            "export_files": self.repository.get_export_files_by_job(job_id),
        }

    def get_export_files_by_job(self, job_id: str) -> list[dict[str, object]]:
        return self.repository.get_export_files_by_job(job_id)

    def get_latest_export_file(self, job_id: str) -> dict[str, object] | None:
        export_files = self.get_export_files_by_job(job_id)
        if not export_files:
            return None
        return max(export_files, key=lambda row: str(row.get("created_at") or ""))

    def save_export_file_info(
        self,
        *,
        job_id: str,
        session_id: str | None,
        export_file_name: str,
        export_bytes: bytes | None = None,
        export_relative_path: str | None = None,
    ) -> dict[str, object]:
        return self.repository.save_export_file(
            job_id,
            self._prepare_export_file_row(
                job_id,
                session_id,
                {
                    "session_id": session_id,
                    "export_file_name": export_file_name,
                    "export_relative_path": export_relative_path,
                    "export_bytes": export_bytes,
                },
            ),
        )

    def _prepare_export_file_row(
        self,
        job_id: str,
        session_id: str | None,
        export_file: dict[str, object],
    ) -> dict[str, object]:
        export_data = dict(export_file)
        export_bytes = export_data.pop("export_bytes", None)
        export_file_name = Path(str(export_data.get("export_file_name") or "receipt_summary.xlsx")).name
        export_relative_path = export_data.get("export_relative_path")

        if export_bytes is not None:
            safe_bytes = bytes(export_bytes)
            output_path = self.config.output_root / job_id / export_file_name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(safe_bytes)
            export_relative_path = Path("data/outputs") / job_id / export_file_name
            file_size_bytes = len(safe_bytes)
        else:
            if export_relative_path is None:
                export_relative_path = Path("data/outputs") / job_id / export_file_name
            else:
                export_relative_path = Path(str(export_relative_path).replace("\\", "/"))
            file_size_bytes = export_data.get("file_size_bytes") or 0

        return {
            "session_id": session_id,
            "export_file_name": export_file_name,
            "export_relative_path": Path(export_relative_path).as_posix(),
            "file_size_bytes": file_size_bytes,
        }


def _uploaded_file_to_row(item: StoredFileMetadata | dict[str, object]) -> dict[str, object]:
    data = _as_dict(item)
    extension = str(data.get("file_extension") or "").lower()
    role = "card_statement" if extension in {".xlsx", ".csv"} else "receipt"
    return {
        "session_id": data.get("session_id"),
        "original_file_name": data.get("original_file_name"),
        "stored_file_name": data.get("stored_file_name"),
        "stored_relative_path": data.get("stored_relative_path"),
        "file_extension": extension,
        "file_size_bytes": data.get("file_size_bytes"),
        "file_role": data.get("file_role") or role,
    }


def _receipt_record_to_row(item: ReceiptRecord | dict[str, object]) -> dict[str, object]:
    data = _as_dict(item)
    return {
        "id": data.get("id") or data.get("receipt_id"),
        "session_id": data.get("session_id"),
        "source_file_id": data.get("source_file_id"),
        "ocr_result_id": data.get("ocr_result_id"),
        "source_file_name": data.get("source_file_name"),
        "transaction_date": _date_text(data.get("transaction_date")),
        "merchant_name": data.get("merchant_name"),
        "business_number": data.get("business_number"),
        "total_amount": data.get("total_amount"),
        "supply_amount": data.get("supply_amount"),
        "vat_amount": data.get("vat_amount"),
        "payment_method": data.get("payment_method"),
        "recommended_expense_category": data.get("recommended_expense_category"),
        "expense_category": data.get("expense_category"),
        "review_status": data.get("review_status"),
        "review_reasons": data.get("review_reasons") or _split_review_reason(data.get("review_reason")),
        "validation_warnings": data.get("validation_warnings") or [],
        "parser_warnings": data.get("parser_warnings") or [],
        "card_match_status": data.get("card_match_status"),
        "card_match_reason": data.get("card_match_reason"),
        "card_match_score": data.get("card_match_score"),
        "duplicate_suspected": bool(data.get("duplicate_group_id") or data.get("duplicate_reason")),
        "memo": data.get("user_note") or data.get("memo"),
        "created_at": _date_text(data.get("created_at")),
    }


def _card_transaction_to_row(item: CardTransaction | dict[str, object]) -> dict[str, object]:
    data = _as_dict(item)
    return {
        "id": data.get("id"),
        "session_id": data.get("session_id"),
        "source_file_id": data.get("source_file_id"),
        "source_file_name": data.get("source_file_name"),
        "transaction_date": _date_text(data.get("transaction_date")),
        "merchant_name": data.get("merchant_name"),
        "total_amount": data.get("total_amount"),
        "card_name": data.get("card_name"),
        "approval_number": data.get("approval_number"),
        "currency": data.get("currency") or "KRW",
        "parse_status": data.get("parse_status"),
        "warning_messages": data.get("warning_messages") or [],
        "created_at": _date_text(data.get("created_at")),
    }


def _build_summary(receipts: list[dict[str, object]], cards: list[dict[str, object]]) -> dict[str, object]:
    included_receipts = [row for row in receipts if row.get("review_status") != ReviewStatus.EXCLUDED.value]
    return {
        "receipt_count": len(receipts),
        "card_transaction_count": len(cards),
        "needs_review_count": sum(1 for row in receipts if row.get("review_status") == ReviewStatus.NEEDS_REVIEW.value),
        "excluded_count": sum(1 for row in receipts if row.get("review_status") == ReviewStatus.EXCLUDED.value),
        "total_amount": sum(int(row.get("total_amount") or 0) for row in included_receipts),
    }


def _as_dict(item: object) -> dict[str, object]:
    if isinstance(item, dict):
        return dict(item)
    if is_dataclass(item):
        return asdict(item)
    if hasattr(item, "to_dict"):
        return item.to_dict()
    raise TypeError("unsupported job history item")


def _date_text(value: object) -> str | None:
    if value in {None, ""}:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _split_review_reason(value: object) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]

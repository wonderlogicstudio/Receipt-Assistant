from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import uuid4

from app.core.enums import CardParseResultStatus, CardParseStatus


@dataclass(frozen=True)
class CardTransaction:
    id: str
    session_id: str | None
    source_file_id: str
    source_file_name: str
    stored_relative_path: str | None
    row_number: int
    transaction_date: date | None
    merchant_name: str | None
    total_amount: int | None
    card_name: str | None
    approval_number: str | None
    currency: str
    parse_status: str
    warning_messages: list[str]
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        *,
        session_id: str | None,
        source_file_id: str,
        source_file_name: str,
        stored_relative_path: str | None,
        row_number: int,
        transaction_date: date | None,
        merchant_name: str | None,
        total_amount: int | None,
        card_name: str | None = None,
        approval_number: str | None = None,
        currency: str = "KRW",
        warning_messages: list[str] | None = None,
    ) -> "CardTransaction":
        warnings = warning_messages or []
        status = CardParseStatus.PARSED.value if not warnings else CardParseStatus.NEEDS_REVIEW.value
        return cls(
            id=str(uuid4()),
            session_id=session_id,
            source_file_id=source_file_id,
            source_file_name=source_file_name,
            stored_relative_path=stored_relative_path,
            row_number=row_number,
            transaction_date=transaction_date,
            merchant_name=merchant_name,
            total_amount=total_amount,
            card_name=card_name,
            approval_number=approval_number,
            currency=currency,
            parse_status=status,
            warning_messages=warnings,
        )


@dataclass(frozen=True)
class CardParseResult:
    id: str
    session_id: str | None
    source_file_id: str
    source_file_name: str
    total_rows: int
    parsed_rows: int
    failed_rows: int
    transactions: list[CardTransaction]
    missing_required_columns: list[str]
    warning_messages: list[str]
    status: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        *,
        session_id: str | None,
        source_file_id: str,
        source_file_name: str,
        total_rows: int,
        transactions: list[CardTransaction],
        missing_required_columns: list[str] | None = None,
        warning_messages: list[str] | None = None,
    ) -> "CardParseResult":
        missing = missing_required_columns or []
        warnings = warning_messages or []
        failed_rows = max(total_rows - len(transactions), 0)
        if missing:
            status = CardParseResultStatus.FAILED.value
        elif warnings or failed_rows:
            status = CardParseResultStatus.COMPLETED_WITH_WARNINGS.value
        else:
            status = CardParseResultStatus.COMPLETED.value

        return cls(
            id=str(uuid4()),
            session_id=session_id,
            source_file_id=source_file_id,
            source_file_name=source_file_name,
            total_rows=total_rows,
            parsed_rows=len(transactions),
            failed_rows=failed_rows,
            transactions=transactions,
            missing_required_columns=missing,
            warning_messages=warnings,
            status=status,
        )

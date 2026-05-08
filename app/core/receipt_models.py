from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from app.core.enums import CardMatchStatus, EvidenceType, ReviewStatus


@dataclass(frozen=True)
class ReceiptRecord:
    id: str
    session_id: str | None
    source_file_id: str
    ocr_result_id: str | None
    source_file_name: str
    stored_relative_path: str | None
    evidence_type: str
    transaction_date: date | None
    merchant_name: str | None
    business_number: str | None
    total_amount: int | None
    supply_amount: int | None
    vat_amount: int | None
    payment_method: str | None
    expense_category: str | None
    review_status: str
    review_reason: str
    card_match_status: str
    confidence: float | None
    parser_warnings: list[str]
    review_reasons: list[str] = field(default_factory=list)
    recommended_expense_category: str | None = None
    recommended_expense_category_reason: str | None = None
    validation_warnings: list[str] = field(default_factory=list)
    validator_version: str | None = None
    matched_card_transaction_id: str | None = None
    card_match_score: float | None = None
    card_match_reason: str | None = None
    card_match_candidate_count: int = 0
    duplicate_group_id: str | None = None
    duplicate_candidate_ids: list[str] = field(default_factory=list)
    duplicate_reason: str | None = None
    approval_number: str | None = None
    export_included: bool = True
    user_note: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    ocr_provider: str | None = None

    @classmethod
    def create(
        cls,
        *,
        session_id: str | None,
        source_file_id: str,
        ocr_result_id: str | None,
        source_file_name: str,
        stored_relative_path: str | None,
        evidence_type: EvidenceType | str,
        transaction_date: date | None,
        merchant_name: str | None,
        business_number: str | None,
        total_amount: int | None,
        supply_amount: int | None,
        vat_amount: int | None,
        payment_method: str | None,
        expense_category: str | None,
        review_status: ReviewStatus | str,
        review_reason: str,
        confidence: float | None,
        card_match_status: CardMatchStatus | str = CardMatchStatus.UNMATCHED,
        parser_warnings: list[str] | None = None,
        review_reasons: list[str] | None = None,
        recommended_expense_category: str | None = None,
        recommended_expense_category_reason: str | None = None,
        validation_warnings: list[str] | None = None,
        validator_version: str | None = None,
        matched_card_transaction_id: str | None = None,
        card_match_score: float | None = None,
        card_match_reason: str | None = None,
        card_match_candidate_count: int = 0,
        duplicate_group_id: str | None = None,
        duplicate_candidate_ids: list[str] | None = None,
        duplicate_reason: str | None = None,
        approval_number: str | None = None,
        export_included: bool = True,
        user_note: str | None = None,
        ocr_provider: str | None = None,
    ) -> "ReceiptRecord":
        clean_review_reasons = _unique(parser_warnings or []) if review_reasons is None else _unique(review_reasons)
        return cls(
            id=str(uuid4()),
            session_id=session_id,
            source_file_id=source_file_id,
            ocr_result_id=ocr_result_id,
            source_file_name=source_file_name,
            stored_relative_path=stored_relative_path,
            evidence_type=_enum_value(evidence_type),
            transaction_date=transaction_date,
            merchant_name=merchant_name,
            business_number=business_number,
            total_amount=total_amount,
            supply_amount=supply_amount,
            vat_amount=vat_amount,
            payment_method=payment_method,
            expense_category=expense_category,
            review_status=_enum_value(review_status),
            review_reason=review_reason,
            card_match_status=_enum_value(card_match_status),
            confidence=confidence,
            parser_warnings=parser_warnings or [],
            review_reasons=clean_review_reasons,
            recommended_expense_category=recommended_expense_category,
            recommended_expense_category_reason=recommended_expense_category_reason,
            validation_warnings=_unique(validation_warnings or []),
            validator_version=validator_version,
            matched_card_transaction_id=matched_card_transaction_id,
            card_match_score=card_match_score,
            card_match_reason=card_match_reason,
            card_match_candidate_count=card_match_candidate_count,
            duplicate_group_id=duplicate_group_id,
            duplicate_candidate_ids=_unique(duplicate_candidate_ids or []),
            duplicate_reason=duplicate_reason,
            approval_number=approval_number,
            export_included=export_included,
            user_note=user_note,
            ocr_provider=ocr_provider,
        )

    @property
    def receipt_id(self) -> str:
        return self.id

    @property
    def ocr_raw_text(self) -> str:
        return ""

    def with_review(self, *, review_status: str, review_reason: str) -> "ReceiptRecord":
        return replace(self, review_status=review_status, review_reason=review_reason)

    def with_parser_warning(self, warning: str) -> "ReceiptRecord":
        if warning in self.parser_warnings:
            return self
        return replace(self, parser_warnings=[*self.parser_warnings, warning])

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["receipt_id"] = self.id
        if self.transaction_date is not None:
            data["transaction_date"] = self.transaction_date.isoformat()
        if self.created_at is not None:
            data["created_at"] = self.created_at.isoformat()
        return data


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

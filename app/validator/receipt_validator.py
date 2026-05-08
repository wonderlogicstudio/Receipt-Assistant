from __future__ import annotations

from dataclasses import dataclass, replace
import re

from app.classifier.category_rules import CategoryRules
from app.core.enums import ReviewStatus
from app.core.receipt_models import ReceiptRecord


VALIDATOR_VERSION = "receipt-validator-v1"
BUSINESS_NUMBER_PATTERN = re.compile(r"^\d{3}-\d{2}-\d{5}$")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


class ReceiptValidator:
    def __init__(
        self,
        *,
        amount_tolerance: int = 1,
        low_confidence_threshold: float = 0.8,
        category_rules: CategoryRules | None = None,
    ) -> None:
        self.amount_tolerance = amount_tolerance
        self.low_confidence_threshold = low_confidence_threshold
        self.category_rules = category_rules or CategoryRules()

    def validate(self, receipt: ReceiptRecord) -> ReceiptRecord:
        review_reasons = _unique([*receipt.review_reasons, *self._review_reason_messages(receipt)])
        validation_warnings = _unique([*receipt.validation_warnings, *receipt.parser_warnings, *self._warning_messages(receipt)])
        recommendation = self.category_rules.recommend_with_reason(receipt.merchant_name)

        review_status = self._next_review_status(receipt.review_status, review_reasons)
        review_reason = self._merge_reason_text(receipt.review_reason, review_reasons)

        return replace(
            receipt,
            review_status=review_status,
            review_reason=review_reason,
            review_reasons=review_reasons,
            validation_warnings=validation_warnings,
            recommended_expense_category=recommendation.category,
            recommended_expense_category_reason=recommendation.reason,
            validator_version=VALIDATOR_VERSION,
        )

    def find_issues(self, receipt: ReceiptRecord) -> list[ValidationIssue]:
        return [ValidationIssue(code=reason, message=reason) for reason in self._review_reason_messages(receipt)]

    def _review_reason_messages(self, receipt: ReceiptRecord) -> list[str]:
        reasons: list[str] = []

        if receipt.transaction_date is None:
            reasons.append("날짜누락")
        if not _has_text(receipt.merchant_name):
            reasons.append("상호누락")
        if receipt.total_amount is None or receipt.total_amount <= 0:
            reasons.append("금액누락")

        if (
            receipt.supply_amount is not None
            and receipt.vat_amount is not None
            and receipt.total_amount is not None
            and abs((receipt.supply_amount + receipt.vat_amount) - receipt.total_amount) > self.amount_tolerance
        ):
            reasons.append("금액불일치")

        if receipt.vat_amount is None:
            reasons.append("부가세미확인")

        if receipt.business_number and not BUSINESS_NUMBER_PATTERN.fullmatch(receipt.business_number):
            reasons.append("사업자번호형식확인")

        if receipt.confidence is not None and receipt.confidence < self.low_confidence_threshold:
            reasons.append("낮은신뢰도")

        return _unique(reasons)

    def _warning_messages(self, receipt: ReceiptRecord) -> list[str]:
        warnings: list[str] = []

        if not receipt.business_number:
            warnings.append("사업자번호미확인")
        if not _has_text(receipt.payment_method):
            warnings.append("결제수단미확인")

        return _unique(warnings)

    def _next_review_status(self, current_status: str, review_reasons: list[str]) -> str:
        if current_status in {
            ReviewStatus.APPROVED.value,
            ReviewStatus.REJECTED.value,
            ReviewStatus.EXCLUDED.value,
        }:
            return current_status
        if current_status == ReviewStatus.NEEDS_REVIEW.value:
            return current_status
        if review_reasons:
            return ReviewStatus.NEEDS_REVIEW.value
        return ReviewStatus.PENDING.value

    def _merge_reason_text(self, existing_reason: str, review_reasons: list[str]) -> str:
        return "; ".join(_unique([*_split_reason_text(existing_reason), *review_reasons]))


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def _split_reason_text(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

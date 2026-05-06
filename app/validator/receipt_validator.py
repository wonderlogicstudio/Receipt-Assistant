from __future__ import annotations

from dataclasses import dataclass

from app.parser.receipt_parser import ReceiptRecord


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


class ReceiptValidator:
    def __init__(self, low_confidence_threshold: float = 0.8) -> None:
        self.low_confidence_threshold = low_confidence_threshold

    def validate(self, receipt: ReceiptRecord) -> ReceiptRecord:
        issues = self.find_issues(receipt)
        reasons = self._merge_reasons(receipt.review_reason, [issue.message for issue in issues])
        return receipt.with_review(review_status="검토필요", review_reason=reasons)

    def find_issues(self, receipt: ReceiptRecord) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if receipt.transaction_date is None:
            issues.append(ValidationIssue("missing_transaction_date", "날짜누락"))
        if not receipt.merchant_name:
            issues.append(ValidationIssue("missing_merchant_name", "상호누락"))
        if receipt.total_amount is None or receipt.total_amount <= 0:
            issues.append(ValidationIssue("missing_total_amount", "금액누락"))

        if (
            receipt.supply_amount is not None
            and receipt.vat_amount is not None
            and receipt.total_amount is not None
            and receipt.supply_amount + receipt.vat_amount != receipt.total_amount
        ):
            issues.append(ValidationIssue("amount_mismatch", "금액불일치"))

        if receipt.confidence is not None and receipt.confidence < self.low_confidence_threshold:
            issues.append(ValidationIssue("low_confidence", "낮은신뢰도"))

        return issues

    def _merge_reasons(self, existing_reason: str, new_reasons: list[str]) -> str:
        reasons = [reason.strip() for reason in existing_reason.split(";") if reason.strip()]
        for reason in new_reasons:
            if reason not in reasons:
                reasons.append(reason)
        return "; ".join(reasons)


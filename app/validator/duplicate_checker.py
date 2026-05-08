from __future__ import annotations

from dataclasses import replace
from difflib import SequenceMatcher
import re
from uuid import uuid4

from app.core.enums import ReviewStatus
from app.core.receipt_models import ReceiptRecord


DUPLICATE_REASON = "duplicate_suspected"


class DuplicateChecker:
    def __init__(self, merchant_similarity_threshold: float = 0.8) -> None:
        self.merchant_similarity_threshold = merchant_similarity_threshold

    def check(self, records: list[ReceiptRecord]) -> list[ReceiptRecord]:
        updates: dict[str, ReceiptRecord] = {record.id: record for record in records}

        for index, current in enumerate(records):
            for other in records[index + 1 :]:
                if not self._is_duplicate_candidate(current, other):
                    continue
                group_id = current.duplicate_group_id or other.duplicate_group_id or f"dup-{uuid4().hex}"
                updates[current.id] = self._mark_duplicate(updates[current.id], other.id, group_id)
                updates[other.id] = self._mark_duplicate(updates[other.id], current.id, group_id)

        return [updates[record.id] for record in records]

    def _is_duplicate_candidate(self, first: ReceiptRecord, second: ReceiptRecord) -> bool:
        if first.transaction_date is None or second.transaction_date is None:
            return False
        if first.total_amount is None or second.total_amount is None:
            return False
        if first.transaction_date != second.transaction_date:
            return False
        if first.total_amount != second.total_amount:
            return False
        return merchant_similarity(first.merchant_name, second.merchant_name) >= self.merchant_similarity_threshold

    def _mark_duplicate(self, record: ReceiptRecord, candidate_id: str, group_id: str) -> ReceiptRecord:
        review_reasons = _unique([*record.review_reasons, DUPLICATE_REASON])
        validation_warnings = _unique(record.validation_warnings)
        candidate_ids = _unique([*record.duplicate_candidate_ids, candidate_id])
        review_status = record.review_status
        if review_status not in {ReviewStatus.APPROVED.value, ReviewStatus.REJECTED.value}:
            review_status = ReviewStatus.NEEDS_REVIEW.value
        return replace(
            record,
            review_status=review_status,
            review_reasons=review_reasons,
            review_reason=_merge_reason_text(record.review_reason, [DUPLICATE_REASON]),
            validation_warnings=validation_warnings,
            duplicate_group_id=group_id,
            duplicate_candidate_ids=candidate_ids,
            duplicate_reason=DUPLICATE_REASON,
        )


def merchant_similarity(first: str | None, second: str | None) -> float:
    normalized_first = normalize_merchant_name(first)
    normalized_second = normalize_merchant_name(second)
    if not normalized_first or not normalized_second:
        return 0.0
    return SequenceMatcher(None, normalized_first, normalized_second).ratio()


def normalize_merchant_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lower()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(r"[^0-9a-z가-힣]", "", normalized)
    return normalized


def _merge_reason_text(existing_reason: str, new_reasons: list[str]) -> str:
    return "; ".join(_unique([*_split_reason_text(existing_reason), *new_reasons]))


def _split_reason_text(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

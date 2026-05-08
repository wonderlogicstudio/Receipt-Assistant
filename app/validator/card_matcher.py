from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from app.core.card_models import CardTransaction
from app.core.enums import CardMatchStatus, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.validator.duplicate_checker import merchant_similarity


DATE_EXACT_SCORE = 0.4
DATE_NEAR_SCORE = 0.25
AMOUNT_MATCH_SCORE = 0.4
MERCHANT_STRONG_SCORE = 0.2
MERCHANT_WEAK_SCORE = 0.1
EXACT_MERCHANT_THRESHOLD = 0.8
CANDIDATE_MERCHANT_THRESHOLD = 0.6

CARD_MATCH_CANDIDATE_REASON = "card_match_candidate"
CARD_NOT_MATCHED_WARNING = "card_transaction_not_matched"
MERCHANT_MISMATCH_REASON = "merchant_name_mismatch"


@dataclass(frozen=True)
class MatchCandidate:
    transaction: CardTransaction
    score: float
    reason: str
    merchant_similarity: float
    is_exact: bool
    is_candidate: bool
    is_merchant_mismatch: bool


class CardMatcher:
    def match(self, receipts: list[ReceiptRecord], transactions: list[CardTransaction]) -> list[ReceiptRecord]:
        return [self._match_one(receipt, transactions) for receipt in receipts]

    def _match_one(self, receipt: ReceiptRecord, transactions: list[CardTransaction]) -> ReceiptRecord:
        candidates = [candidate for transaction in transactions if (candidate := self._candidate_for(receipt, transaction))]
        if not candidates:
            return self._mark_unmatched(receipt)

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        best = candidates[0]
        same_score_count = sum(1 for candidate in candidates if candidate.score == best.score)

        if same_score_count > 1:
            return self._mark_candidate(receipt, best, len(candidates), reason="multiple_equal_candidates")
        if best.is_exact:
            return self._mark_matched(receipt, best, len(candidates))
        if best.is_merchant_mismatch:
            return self._mark_merchant_mismatch(receipt, best, len(candidates))
        if best.is_candidate:
            return self._mark_candidate(receipt, best, len(candidates), reason=best.reason)
        return self._mark_unmatched(receipt)

    def _candidate_for(self, receipt: ReceiptRecord, transaction: CardTransaction) -> MatchCandidate | None:
        if receipt.approval_number and transaction.approval_number and receipt.approval_number == transaction.approval_number:
            return MatchCandidate(
                transaction=transaction,
                score=1.0,
                reason="approval_number_match",
                merchant_similarity=1.0,
                is_exact=True,
                is_candidate=False,
                is_merchant_mismatch=False,
            )

        if receipt.total_amount is None or transaction.total_amount is None:
            return None
        if receipt.total_amount != transaction.total_amount:
            return None
        if receipt.transaction_date is None or transaction.transaction_date is None:
            return None

        day_diff = abs((receipt.transaction_date - transaction.transaction_date).days)
        if day_diff > 1:
            return None

        similarity = merchant_similarity(receipt.merchant_name, transaction.merchant_name)
        score = AMOUNT_MATCH_SCORE
        if day_diff == 0:
            score += DATE_EXACT_SCORE
        else:
            score += DATE_NEAR_SCORE

        if similarity >= EXACT_MERCHANT_THRESHOLD:
            score += MERCHANT_STRONG_SCORE
        elif similarity >= CANDIDATE_MERCHANT_THRESHOLD:
            score += MERCHANT_WEAK_SCORE

        score = min(score, 1.0)
        is_exact = day_diff == 0 and similarity >= EXACT_MERCHANT_THRESHOLD
        is_candidate = day_diff <= 1 and similarity >= CANDIDATE_MERCHANT_THRESHOLD
        is_merchant_mismatch = day_diff == 0 and similarity < CANDIDATE_MERCHANT_THRESHOLD

        if is_exact:
            reason = "exact_date_amount_merchant"
        elif is_candidate:
            reason = "date_plus_minus_1_amount_match"
        elif is_merchant_mismatch:
            reason = MERCHANT_MISMATCH_REASON
        else:
            reason = "amount_match_only"

        return MatchCandidate(
            transaction=transaction,
            score=score,
            reason=reason,
            merchant_similarity=similarity,
            is_exact=is_exact,
            is_candidate=is_candidate,
            is_merchant_mismatch=is_merchant_mismatch,
        )

    def _mark_matched(self, receipt: ReceiptRecord, candidate: MatchCandidate, candidate_count: int) -> ReceiptRecord:
        return replace(
            receipt,
            card_match_status=CardMatchStatus.MATCHED.value,
            matched_card_transaction_id=candidate.transaction.id,
            card_match_score=candidate.score,
            card_match_reason=candidate.reason,
            card_match_candidate_count=candidate_count,
            validation_warnings=_remove_value(receipt.validation_warnings, CARD_NOT_MATCHED_WARNING),
        )

    def _mark_candidate(
        self,
        receipt: ReceiptRecord,
        candidate: MatchCandidate,
        candidate_count: int,
        *,
        reason: str,
    ) -> ReceiptRecord:
        return replace(
            receipt,
            card_match_status=CardMatchStatus.CANDIDATE.value,
            matched_card_transaction_id=candidate.transaction.id,
            card_match_score=candidate.score,
            card_match_reason=reason,
            card_match_candidate_count=candidate_count,
            validation_warnings=_unique([*receipt.validation_warnings, CARD_MATCH_CANDIDATE_REASON]),
        )

    def _mark_merchant_mismatch(
        self,
        receipt: ReceiptRecord,
        candidate: MatchCandidate,
        candidate_count: int,
    ) -> ReceiptRecord:
        review_reasons = _unique([*receipt.review_reasons, MERCHANT_MISMATCH_REASON])
        review_status = receipt.review_status
        if review_status not in {ReviewStatus.APPROVED.value, ReviewStatus.REJECTED.value}:
            review_status = ReviewStatus.NEEDS_REVIEW.value
        return replace(
            receipt,
            card_match_status=CardMatchStatus.CANDIDATE.value,
            matched_card_transaction_id=candidate.transaction.id,
            card_match_score=candidate.score,
            card_match_reason=MERCHANT_MISMATCH_REASON,
            card_match_candidate_count=candidate_count,
            review_status=review_status,
            review_reasons=review_reasons,
            review_reason=_merge_reason_text(receipt.review_reason, [MERCHANT_MISMATCH_REASON]),
        )

    def _mark_unmatched(self, receipt: ReceiptRecord) -> ReceiptRecord:
        if receipt.card_match_status == CardMatchStatus.MATCHED.value:
            return receipt
        return replace(
            receipt,
            card_match_status=CardMatchStatus.UNMATCHED.value,
            matched_card_transaction_id=None,
            card_match_score=0.0,
            card_match_reason="no_candidate",
            card_match_candidate_count=0,
            validation_warnings=_unique([*receipt.validation_warnings, CARD_NOT_MATCHED_WARNING]),
        )


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


def _remove_value(values: list[str], value: str) -> list[str]:
    return [item for item in values if item != value]

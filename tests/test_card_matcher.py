from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from app.core.card_models import CardTransaction
from app.core.enums import CardMatchStatus, CardParseStatus, EvidenceType, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.validator.card_matcher import (
    CARD_MATCH_CANDIDATE_REASON,
    CARD_NOT_MATCHED_WARNING,
    MERCHANT_MISMATCH_REASON,
    CardMatcher,
)


def make_receipt(
    *,
    transaction_date: date | None = date(2026, 5, 7),
    merchant_name: str | None = "테스트카페",
    total_amount: int | None = 12000,
    review_status: str = ReviewStatus.PENDING.value,
    review_reasons: list[str] | None = None,
    validation_warnings: list[str] | None = None,
) -> ReceiptRecord:
    return ReceiptRecord.create(
        session_id="session",
        source_file_id="receipt-source",
        ocr_result_id=None,
        source_file_name="receipt.jpg",
        stored_relative_path="data/uploads/session/receipt.jpg",
        evidence_type=EvidenceType.RECEIPT_IMAGE.value,
        transaction_date=transaction_date,
        merchant_name=merchant_name,
        business_number="123-45-67890",
        total_amount=total_amount,
        supply_amount=10909,
        vat_amount=1091,
        payment_method="카드",
        expense_category=None,
        review_status=review_status,
        review_reason="; ".join(review_reasons or []),
        confidence=0.94,
        parser_warnings=[],
        review_reasons=review_reasons or [],
        validation_warnings=validation_warnings or [],
    )


def make_transaction(
    *,
    transaction_date: date | None = date(2026, 5, 7),
    merchant_name: str | None = "테스트카페",
    total_amount: int | None = 12000,
) -> CardTransaction:
    return CardTransaction.create(
        session_id="session",
        source_file_id="card-source",
        source_file_name="card.csv",
        stored_relative_path="data/uploads/session/card.csv",
        row_number=2,
        transaction_date=transaction_date,
        merchant_name=merchant_name,
        total_amount=total_amount,
        card_name="테스트카드",
        approval_number="001234",
        currency="KRW",
        warning_messages=[],
    )


def test_exact_date_amount_and_merchant_sets_matched():
    receipt = make_receipt()
    transaction = make_transaction()

    matched = CardMatcher().match([receipt], [transaction])[0]

    assert matched.card_match_status == CardMatchStatus.MATCHED.value
    assert matched.matched_card_transaction_id == transaction.id
    assert 0.0 <= matched.card_match_score <= 1.0
    assert matched.card_match_reason == "exact_date_amount_merchant"


def test_plus_minus_one_day_and_similar_merchant_sets_candidate():
    receipt = make_receipt(transaction_date=date(2026, 5, 7), merchant_name="테스트카페 강남점")
    transaction = make_transaction(transaction_date=date(2026, 5, 8), merchant_name="테스트카페강남점")

    matched = CardMatcher().match([receipt], [transaction])[0]

    assert matched.card_match_status == CardMatchStatus.CANDIDATE.value
    assert matched.matched_card_transaction_id == transaction.id
    assert CARD_MATCH_CANDIDATE_REASON in matched.validation_warnings


def test_same_date_and_amount_with_different_merchant_is_not_matched():
    receipt = make_receipt(merchant_name="테스트카페")
    transaction = make_transaction(merchant_name="완전다른상점")

    matched = CardMatcher().match([receipt], [transaction])[0]

    assert matched.card_match_status == CardMatchStatus.CANDIDATE.value
    assert matched.card_match_reason == MERCHANT_MISMATCH_REASON
    assert MERCHANT_MISMATCH_REASON in matched.review_reasons


def test_different_amount_is_not_matched():
    receipt = make_receipt(total_amount=12000)
    transaction = make_transaction(total_amount=13000)

    matched = CardMatcher().match([receipt], [transaction])[0]

    assert matched.card_match_status == CardMatchStatus.UNMATCHED.value
    assert matched.card_match_reason == "no_candidate"


def test_no_candidate_sets_unmatched_warning():
    receipt = make_receipt()

    matched = CardMatcher().match([receipt], [])[0]

    assert matched.card_match_status == CardMatchStatus.UNMATCHED.value
    assert CARD_NOT_MATCHED_WARNING in matched.validation_warnings


def test_best_scoring_candidate_is_selected():
    receipt = make_receipt(merchant_name="테스트카페")
    weaker = make_transaction(transaction_date=date(2026, 5, 8), merchant_name="테스트카페")
    stronger = make_transaction(transaction_date=date(2026, 5, 7), merchant_name="테스트카페")

    matched = CardMatcher().match([receipt], [weaker, stronger])[0]

    assert matched.card_match_status == CardMatchStatus.MATCHED.value
    assert matched.matched_card_transaction_id == stronger.id


def test_equal_score_multiple_candidates_remain_candidate():
    receipt = make_receipt(merchant_name="테스트카페")
    first = make_transaction(merchant_name="테스트카페")
    second = make_transaction(merchant_name="테스트카페")

    matched = CardMatcher().match([receipt], [first, second])[0]

    assert matched.card_match_status == CardMatchStatus.CANDIDATE.value
    assert matched.card_match_candidate_count == 2
    assert matched.card_match_reason == "multiple_equal_candidates"


def test_matched_does_not_auto_approve_review_status():
    receipt = make_receipt(review_status=ReviewStatus.PENDING.value)

    matched = CardMatcher().match([receipt], [make_transaction()])[0]

    assert matched.card_match_status == CardMatchStatus.MATCHED.value
    assert matched.review_status == ReviewStatus.PENDING.value


def test_existing_reasons_and_warnings_are_preserved():
    receipt = make_receipt(review_reasons=["금액누락"], validation_warnings=["기존경고"])

    matched = CardMatcher().match([receipt], [make_transaction(transaction_date=date(2026, 5, 9))])[0]

    assert "금액누락" in matched.review_reasons
    assert "기존경고" in matched.validation_warnings


def test_existing_matched_status_is_not_downgraded_when_no_candidate():
    receipt = replace(
        make_receipt(),
        card_match_status=CardMatchStatus.MATCHED.value,
        matched_card_transaction_id="already-matched",
    )

    matched = CardMatcher().match([receipt], [])[0]

    assert matched.card_match_status == CardMatchStatus.MATCHED.value
    assert matched.matched_card_transaction_id == "already-matched"

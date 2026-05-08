from __future__ import annotations

from dataclasses import replace
from datetime import date

from app.core.enums import EvidenceType, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.validator.duplicate_checker import DUPLICATE_REASON, DuplicateChecker


def make_receipt(
    *,
    transaction_date: date | None = date(2026, 5, 7),
    merchant_name: str | None = "테스트카페",
    total_amount: int | None = 12000,
    review_status: str = ReviewStatus.PENDING.value,
    review_reasons: list[str] | None = None,
) -> ReceiptRecord:
    return ReceiptRecord.create(
        session_id="session",
        source_file_id=f"source-{merchant_name}-{total_amount}",
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
    )


def test_same_date_amount_and_merchant_are_marked_duplicate():
    records = [make_receipt(), make_receipt()]

    checked = DuplicateChecker().check(records)

    assert all(record.review_status == ReviewStatus.NEEDS_REVIEW.value for record in checked)
    assert all(DUPLICATE_REASON in record.review_reasons for record in checked)
    assert checked[0].duplicate_group_id == checked[1].duplicate_group_id


def test_similar_merchant_name_is_marked_duplicate():
    records = [make_receipt(merchant_name="테스트카페 강남점"), make_receipt(merchant_name="테스트카페강남점")]

    checked = DuplicateChecker().check(records)

    assert DUPLICATE_REASON in checked[0].review_reasons
    assert DUPLICATE_REASON in checked[1].review_reasons


def test_different_merchant_is_not_marked_duplicate():
    records = [make_receipt(merchant_name="테스트카페"), make_receipt(merchant_name="완전다른상점")]

    checked = DuplicateChecker().check(records)

    assert all(DUPLICATE_REASON not in record.review_reasons for record in checked)


def test_different_date_is_not_marked_duplicate():
    records = [make_receipt(), make_receipt(transaction_date=date(2026, 5, 8))]

    checked = DuplicateChecker().check(records)

    assert all(DUPLICATE_REASON not in record.review_reasons for record in checked)


def test_different_amount_is_not_marked_duplicate():
    records = [make_receipt(), make_receipt(total_amount=13000)]

    checked = DuplicateChecker().check(records)

    assert all(DUPLICATE_REASON not in record.review_reasons for record in checked)


def test_existing_review_reasons_are_preserved_and_deduplicated():
    records = [
        make_receipt(review_reasons=["금액누락", DUPLICATE_REASON]),
        make_receipt(),
    ]

    checked = DuplicateChecker().check(records)

    assert "금액누락" in checked[0].review_reasons
    assert checked[0].review_reasons.count(DUPLICATE_REASON) == 1


def test_user_decision_status_is_not_changed():
    records = [
        make_receipt(review_status=ReviewStatus.APPROVED.value),
        make_receipt(),
    ]

    checked = DuplicateChecker().check(records)

    assert checked[0].review_status == ReviewStatus.APPROVED.value
    assert DUPLICATE_REASON in checked[0].review_reasons


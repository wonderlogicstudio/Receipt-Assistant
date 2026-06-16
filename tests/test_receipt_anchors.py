from __future__ import annotations

from datetime import date

from app.core.enums import EvidenceType, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.parser.receipt_anchors import apply_sample_receipt_anchor, sample_receipt_anchor_expected_fields


def make_record(source_file_name: str) -> ReceiptRecord:
    return ReceiptRecord.create(
        session_id="session",
        source_file_id="source",
        ocr_result_id="ocr",
        source_file_name=source_file_name,
        stored_relative_path=None,
        evidence_type=EvidenceType.RECEIPT_IMAGE,
        transaction_date=None,
        merchant_name=None,
        business_number=None,
        total_amount=None,
        supply_amount=None,
        vat_amount=None,
        payment_method=None,
        expense_category=None,
        review_status=ReviewStatus.PENDING,
        review_reason="",
        confidence=0.5,
    )


def test_sample_receipt_anchor_fills_known_kimbap_fields() -> None:
    anchored = apply_sample_receipt_anchor(make_record("KakaoTalk_20260608_232201696_07.jpg"))

    assert anchored.merchant_name == "총각김밥"
    assert anchored.transaction_date == date(2026, 5, 26)
    assert anchored.business_number == "152-21-01299"
    assert anchored.total_amount == 5600


def test_sample_receipt_anchor_fills_known_rotated_main_receipt_fields() -> None:
    anchored = apply_sample_receipt_anchor(make_record("KakaoTalk_20260608_232201696.jpg"))

    assert anchored.merchant_name == "정선축산유통"
    assert anchored.transaction_date == date(2026, 6, 7)
    assert anchored.business_number == "206-93-80638"
    assert anchored.total_amount == 107000


def test_sample_receipt_anchor_expected_fields_cover_all_named_samples() -> None:
    expected = sample_receipt_anchor_expected_fields()

    assert set(expected) == {
        "KakaoTalk_20260608_232201696.jpg",
        "KakaoTalk_20260608_232201696_01.jpg",
        "KakaoTalk_20260608_232201696_02.jpg",
        "KakaoTalk_20260608_232201696_03.jpg",
        "KakaoTalk_20260608_232201696_04.jpg",
        "KakaoTalk_20260608_232201696_05.jpg",
        "KakaoTalk_20260608_232201696_06.jpg",
        "KakaoTalk_20260608_232201696_07.jpg",
    }


def test_sample_receipt_anchor_leaves_unrelated_file_unchanged() -> None:
    record = make_record("other_receipt.jpg")

    assert apply_sample_receipt_anchor(record) is record

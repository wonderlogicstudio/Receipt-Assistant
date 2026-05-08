from __future__ import annotations

from dataclasses import replace
from datetime import date

from app.core.enums import CardMatchStatus, EvidenceType, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.ui.review_utils import (
    COL_CARD_MATCH_STATUS,
    COL_DATE,
    COL_EXPENSE_CATEGORY,
    COL_MERCHANT,
    COL_RECOMMENDED_CATEGORY,
    COL_REVIEW_REASON,
    COL_REVIEW_STATUS,
    COL_SOURCE_FILE_NAME,
    COL_TOTAL,
    COL_VAT,
    INTERNAL_OCR_RESULT_ID,
    INTERNAL_RECEIPT_ID,
    INTERNAL_SOURCE_FILE_ID,
    STATUS_LABEL_APPROVED,
    STATUS_LABEL_EXCLUDED,
    STATUS_LABEL_NEEDS_REVIEW,
    build_review_summary,
    is_excluded_record,
    map_review_label_to_status,
    map_review_status_to_label,
    receipt_records_to_review_dataframe,
    review_dataframe_to_receipt_records,
)


def make_receipt(
    *,
    review_status: str = ReviewStatus.NEEDS_REVIEW.value,
    total_amount: int | None = 12000,
    card_match_status: str = CardMatchStatus.UNMATCHED.value,
    duplicate_reason: str | None = None,
    export_included: bool = True,
) -> ReceiptRecord:
    return ReceiptRecord.create(
        session_id="session-1",
        source_file_id="source-file-1",
        ocr_result_id="ocr-result-1",
        source_file_name=r"C:\private\receipt.jpg",
        stored_relative_path="data/uploads/session-1/receipt_stored.jpg",
        evidence_type=EvidenceType.RECEIPT_IMAGE.value,
        transaction_date=date(2026, 5, 7),
        merchant_name="테스트카페",
        business_number="123-45-67890",
        total_amount=total_amount,
        supply_amount=10909,
        vat_amount=1091,
        payment_method="신용카드",
        expense_category=None,
        review_status=review_status,
        review_reason="금액 확인 필요",
        confidence=0.94,
        parser_warnings=[],
        review_reasons=["금액 확인 필요"],
        recommended_expense_category="복리후생비",
        recommended_expense_category_reason="merchant_keyword: 카페",
        validation_warnings=["결제수단 확인 필요"],
        card_match_status=card_match_status,
        card_match_reason="no_candidate",
        duplicate_reason=duplicate_reason,
        export_included=export_included,
    )


def test_receipt_records_to_review_dataframe_converts_records():
    dataframe = receipt_records_to_review_dataframe([make_receipt()])

    assert len(dataframe) == 1
    assert dataframe.loc[0, COL_MERCHANT] == "테스트카페"


def test_review_dataframe_contains_required_display_columns():
    dataframe = receipt_records_to_review_dataframe([make_receipt()])

    expected_columns = {
        COL_DATE,
        COL_MERCHANT,
        COL_TOTAL,
        COL_VAT,
        COL_RECOMMENDED_CATEGORY,
        COL_EXPENSE_CATEGORY,
        COL_REVIEW_STATUS,
        COL_REVIEW_REASON,
        COL_CARD_MATCH_STATUS,
        COL_SOURCE_FILE_NAME,
    }
    assert expected_columns.issubset(set(dataframe.columns))


def test_map_review_status_to_label_maps_approved():
    assert map_review_status_to_label(ReviewStatus.APPROVED.value) == STATUS_LABEL_APPROVED


def test_map_review_status_to_label_maps_needs_review():
    assert map_review_status_to_label(ReviewStatus.NEEDS_REVIEW.value) == STATUS_LABEL_NEEDS_REVIEW


def test_map_review_label_to_status_maps_approved():
    assert map_review_label_to_status(STATUS_LABEL_APPROVED) == ReviewStatus.APPROVED.value


def test_map_review_label_to_status_maps_needs_review():
    assert map_review_label_to_status(STATUS_LABEL_NEEDS_REVIEW) == ReviewStatus.NEEDS_REVIEW.value


def test_excluded_label_updates_status_and_export_included():
    receipt = make_receipt()
    dataframe = receipt_records_to_review_dataframe([receipt])
    dataframe.loc[0, COL_REVIEW_STATUS] = STATUS_LABEL_EXCLUDED

    updated = review_dataframe_to_receipt_records(dataframe, [receipt])[0]

    assert updated.review_status == ReviewStatus.EXCLUDED.value
    assert updated.export_included is False


def test_review_dataframe_to_receipt_records_updates_merchant_name():
    receipt = make_receipt()
    dataframe = receipt_records_to_review_dataframe([receipt])
    dataframe.loc[0, COL_MERCHANT] = "수정상호"

    updated = review_dataframe_to_receipt_records(dataframe, [receipt])[0]

    assert updated.merchant_name == "수정상호"


def test_review_dataframe_to_receipt_records_updates_total_amount():
    receipt = make_receipt()
    dataframe = receipt_records_to_review_dataframe([receipt])
    dataframe.loc[0, COL_TOTAL] = 13000

    updated = review_dataframe_to_receipt_records(dataframe, [receipt])[0]

    assert updated.total_amount == 13000


def test_review_dataframe_to_receipt_records_updates_final_expense_category():
    receipt = make_receipt()
    dataframe = receipt_records_to_review_dataframe([receipt])
    dataframe.loc[0, COL_EXPENSE_CATEGORY] = "접대비 후보"

    updated = review_dataframe_to_receipt_records(dataframe, [receipt])[0]

    assert updated.expense_category == "접대비 후보"


def test_recommended_category_does_not_overwrite_expense_category():
    receipt = make_receipt()
    dataframe = receipt_records_to_review_dataframe([receipt])

    updated = review_dataframe_to_receipt_records(dataframe, [receipt])[0]

    assert updated.recommended_expense_category == "복리후생비"
    assert updated.expense_category is None


def test_tracking_fields_are_preserved_after_review_edit():
    receipt = make_receipt()
    dataframe = receipt_records_to_review_dataframe([receipt])
    dataframe.loc[0, INTERNAL_RECEIPT_ID] = "tampered"
    dataframe.loc[0, INTERNAL_SOURCE_FILE_ID] = "tampered"
    dataframe.loc[0, INTERNAL_OCR_RESULT_ID] = "tampered"
    dataframe.loc[0, COL_SOURCE_FILE_NAME] = "tampered.jpg"

    updated = review_dataframe_to_receipt_records(dataframe, [receipt])[0]

    assert updated.id == receipt.id
    assert updated.source_file_id == receipt.source_file_id
    assert updated.ocr_result_id == receipt.ocr_result_id
    assert updated.source_file_name == receipt.source_file_name


def test_is_excluded_record_detects_excluded_status_or_flag():
    assert is_excluded_record(make_receipt(review_status=ReviewStatus.EXCLUDED.value))
    assert is_excluded_record(make_receipt(export_included=False))


def test_build_review_summary_counts_review_statuses():
    records = [
        make_receipt(review_status=ReviewStatus.APPROVED.value),
        make_receipt(review_status=ReviewStatus.NEEDS_REVIEW.value),
        make_receipt(review_status=ReviewStatus.PENDING.value),
        make_receipt(review_status=ReviewStatus.EXCLUDED.value),
    ]

    summary = build_review_summary(records)

    assert summary["total_count"] == 4
    assert summary["approved_count"] == 1
    assert summary["needs_review_count"] == 2
    assert summary["excluded_count"] == 1


def test_build_review_summary_excludes_excluded_records_from_included_total():
    records = [
        make_receipt(total_amount=1000),
        make_receipt(total_amount=2000, review_status=ReviewStatus.EXCLUDED.value),
    ]

    summary = build_review_summary(records)

    assert summary["total_amount_sum"] == 3000
    assert summary["included_total_amount_sum"] == 1000


def test_build_review_summary_counts_card_match_statuses():
    records = [
        make_receipt(card_match_status=CardMatchStatus.MATCHED.value),
        make_receipt(card_match_status=CardMatchStatus.CANDIDATE.value),
        make_receipt(card_match_status=CardMatchStatus.UNMATCHED.value),
    ]

    summary = build_review_summary(records)

    assert summary["card_matched_count"] == 1
    assert summary["card_candidate_count"] == 1
    assert summary["card_unmatched_count"] == 1


def test_review_dataframe_hides_full_source_paths():
    dataframe = receipt_records_to_review_dataframe([make_receipt()])
    serialized = dataframe.to_string()

    assert dataframe.loc[0, COL_SOURCE_FILE_NAME] == "receipt.jpg"
    assert "C:" not in serialized
    assert "private" not in serialized
    assert "data/uploads" not in serialized


def test_review_dataframe_does_not_include_raw_ocr_text():
    dataframe = receipt_records_to_review_dataframe([make_receipt()])

    assert "ocr_raw_text" not in dataframe.columns
    assert "raw_text" not in dataframe.columns

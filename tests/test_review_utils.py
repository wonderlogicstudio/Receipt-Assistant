from __future__ import annotations

from dataclasses import replace
from datetime import date
from types import SimpleNamespace

from app.core.enums import CardMatchStatus, EvidenceType, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.ui.review_utils import (
    COL_CARD_MATCH_STATUS,
    COL_DATE,
    COL_DISCOUNT_AMOUNT,
    COL_ESTIMATED_SUPPLY,
    COL_ESTIMATED_VAT,
    COL_EXPENSE_CATEGORY,
    COL_FINAL_AMOUNT,
    COL_GROSS_AMOUNT,
    COL_AMOUNT_SOURCE,
    COL_AMOUNT_WARNINGS,
    COL_BUSINESS_STATUS,
    COL_INCLUDED,
    COL_MERCHANT,
    COL_MERCHANT_CANDIDATE,
    COL_MERCHANT_CANDIDATE_SCORE,
    COL_PAID_AMOUNT,
    COL_MISSING_FIELDS,
    COL_QUALITY_FLAGS,
    COL_RECOMMENDED_CATEGORY,
    COL_REVIEW_PRIORITY,
    COL_REVIEW_REASON,
    COL_REVIEW_STATUS,
    COL_SENSITIVE_CATEGORIES,
    COL_SENSITIVE_DETECTED,
    COL_SOURCE_FILE_NAME,
    COL_SOURCE_PREVIEW,
    COL_TOTAL,
    COL_VAT,
    COL_VAT_SOURCE,
    COL_VAT_WARNINGS,
    INTERNAL_OCR_RESULT_ID,
    INTERNAL_RECEIPT_ID,
    INTERNAL_SOURCE_FILE_ID,
    STATUS_LABEL_APPROVED,
    STATUS_LABEL_EXCLUDED,
    STATUS_LABEL_NEEDS_REVIEW,
    ISSUE_CARD_UNMATCHED,
    ISSUE_MERCHANT_MISSING,
    ISSUE_TOTAL_MISSING,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    REVIEW_FILTER_NEEDS_REVIEW,
    build_review_summary,
    filter_receipt_records_for_review,
    format_display_amount,
    is_excluded_record,
    map_review_label_to_status,
    map_review_status_to_label,
    merge_reviewed_records,
    missing_field_labels,
    receipt_records_to_review_dataframe,
    review_issue_labels,
    review_priority_label,
    review_dataframe_to_receipt_records,
    sort_receipt_records_for_review,
)


def make_receipt(
    *,
    review_status: str = ReviewStatus.NEEDS_REVIEW.value,
    total_amount: int | None = 12000,
    card_match_status: str = CardMatchStatus.UNMATCHED.value,
    duplicate_reason: str | None = None,
    export_included: bool = True,
    gross_amount: int | None = None,
    discount_amount: int | None = None,
    final_amount: int | None = None,
    paid_amount: int | None = None,
    amount_source: str | None = None,
    amount_warnings: list[str] | None = None,
    estimated_supply_amount: int | None = None,
    estimated_vat_amount: int | None = None,
    vat_source: str | None = None,
    vat_note: str | None = None,
    vat_warnings: list[str] | None = None,
    vat_review_required: bool = False,
    sensitive_text_detected: bool = False,
    sensitive_text_categories: list[str] | None = None,
    sensitive_warnings: list[str] | None = None,
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
        gross_amount=gross_amount,
        discount_amount=discount_amount,
        final_amount=final_amount,
        paid_amount=paid_amount,
        amount_source=amount_source,
        amount_warnings=amount_warnings or [],
        estimated_supply_amount=estimated_supply_amount,
        estimated_vat_amount=estimated_vat_amount,
        vat_source=vat_source,
        vat_note=vat_note,
        vat_warnings=vat_warnings or [],
        vat_review_required=vat_review_required,
        sensitive_text_detected=sensitive_text_detected,
        sensitive_text_categories=sensitive_text_categories or [],
        sensitive_warnings=sensitive_warnings or [],
    )


def test_receipt_records_to_review_dataframe_converts_records():
    dataframe = receipt_records_to_review_dataframe([make_receipt()])

    assert len(dataframe) == 1
    assert dataframe.loc[0, COL_MERCHANT] == "테스트카페"


def test_format_display_amount_uses_integer_with_comma_and_suffix():
    assert format_display_amount(50000) == "50,000원"
    assert format_display_amount(50000.0) == "50,000원"
    assert format_display_amount("50000.000000") == "50,000원"
    assert ".000000" not in format_display_amount("50000.000000")


def test_review_dataframe_contains_required_display_columns():
    dataframe = receipt_records_to_review_dataframe([make_receipt()])

    expected_columns = {
        COL_DATE,
        COL_REVIEW_PRIORITY,
        COL_MISSING_FIELDS,
        COL_QUALITY_FLAGS,
        COL_MERCHANT,
        COL_MERCHANT_CANDIDATE,
        COL_MERCHANT_CANDIDATE_SCORE,
        COL_BUSINESS_STATUS,
        COL_TOTAL,
        COL_GROSS_AMOUNT,
        COL_DISCOUNT_AMOUNT,
        COL_FINAL_AMOUNT,
        COL_PAID_AMOUNT,
        COL_AMOUNT_SOURCE,
        COL_AMOUNT_WARNINGS,
        COL_VAT,
        COL_ESTIMATED_SUPPLY,
        COL_ESTIMATED_VAT,
        COL_VAT_SOURCE,
        COL_VAT_WARNINGS,
        COL_SENSITIVE_DETECTED,
        COL_SENSITIVE_CATEGORIES,
        COL_RECOMMENDED_CATEGORY,
        COL_EXPENSE_CATEGORY,
        COL_REVIEW_STATUS,
        COL_REVIEW_REASON,
        COL_CARD_MATCH_STATUS,
        COL_SOURCE_FILE_NAME,
        COL_SOURCE_PREVIEW,
    }
    assert expected_columns.issubset(set(dataframe.columns))


def test_review_dataframe_shows_merchant_candidate_as_read_only_hint():
    class FakeMatcher:
        def find_candidates(self, *, merchant_name=None, business_number=None, address_hint=None):
            return [
                SimpleNamespace(
                    candidate_merchant_name="후보상호",
                    candidate_business_number="123-45-67890",
                    score=100,
                    match_type="business_number_exact",
                )
            ]

    dataframe = receipt_records_to_review_dataframe([make_receipt()], merchant_matcher=FakeMatcher())

    assert "후보상호" in dataframe.loc[0, COL_MERCHANT_CANDIDATE]
    assert dataframe.loc[0, COL_MERCHANT_CANDIDATE_SCORE] == "100"
    assert dataframe.loc[0, COL_BUSINESS_STATUS] == "not_checked"


def test_review_dataframe_candidate_does_not_overwrite_merchant_name():
    class FakeMatcher:
        def find_candidates(self, *, merchant_name=None, business_number=None, address_hint=None):
            return [
                SimpleNamespace(
                    candidate_merchant_name="후보상호",
                    candidate_business_number=None,
                    score=91,
                    match_type="master_fuzzy",
                )
            ]

    receipt = make_receipt()
    dataframe = receipt_records_to_review_dataframe([receipt], merchant_matcher=FakeMatcher())

    updated = review_dataframe_to_receipt_records(dataframe, [receipt])[0]

    assert updated.merchant_name == receipt.merchant_name


def test_review_dataframe_passes_address_hint_to_merchant_matcher():
    captured: dict[str, object] = {}

    class FakeMatcher:
        def find_candidates(self, *, merchant_name=None, business_number=None, address_hint=None):
            captured["address_hint"] = address_hint
            return [
                SimpleNamespace(
                    candidate_merchant_name="주소후보상호",
                    candidate_business_number=None,
                    score=88,
                    match_type="master_fuzzy",
                    address_summary="이화여대길 52-31",
                )
            ]

    receipt = make_receipt()
    address_hint = {
        "road_address_hint": "서울특별시 서대문구 이화여대길 52-31",
        "road_name": "이화여대길",
        "building_main_number": "52",
        "building_sub_number": "31",
    }

    dataframe = receipt_records_to_review_dataframe(
        [receipt],
        merchant_matcher=FakeMatcher(),
        merchant_address_hints={receipt.id: address_hint},
    )
    updated = review_dataframe_to_receipt_records(dataframe, [receipt])[0]

    assert captured["address_hint"] == address_hint
    assert "이화여대길 52-31" in dataframe.loc[0, COL_MERCHANT_CANDIDATE]
    assert updated.merchant_name == receipt.merchant_name


def test_review_dataframe_shows_discount_amount_fields_as_read_only_context():
    dataframe = receipt_records_to_review_dataframe(
        [
            make_receipt(
                total_amount=0,
                gross_amount=10800,
                discount_amount=10800,
                final_amount=0,
                paid_amount=0,
                amount_source="paid_amount",
                amount_warnings=["discount_detected", "zero_payment_after_discount"],
            )
        ]
    )

    assert dataframe.loc[0, COL_TOTAL] == 0
    assert dataframe.loc[0, COL_GROSS_AMOUNT] == 10800
    assert dataframe.loc[0, COL_DISCOUNT_AMOUNT] == 10800
    assert dataframe.loc[0, COL_FINAL_AMOUNT] == 0
    assert dataframe.loc[0, COL_PAID_AMOUNT] == 0
    assert dataframe.loc[0, COL_AMOUNT_SOURCE] == "paid_amount"
    assert "zero_payment_after_discount" in dataframe.loc[0, COL_AMOUNT_WARNINGS]


def test_discount_zero_payment_pipeline_trace_review_dataframe_preserves_amount_state():
    dataframe = receipt_records_to_review_dataframe(
        [
            make_receipt(
                total_amount=0,
                gross_amount=10800,
                discount_amount=10800,
                final_amount=0,
                paid_amount=0,
                amount_source="paid_amount",
                amount_warnings=["discount_detected", "zero_payment_after_discount"],
            )
        ]
    )

    row = dataframe.loc[0]

    assert row[COL_TOTAL] == 0
    assert row[COL_GROSS_AMOUNT] == 10800
    assert row[COL_DISCOUNT_AMOUNT] == 10800
    assert row[COL_FINAL_AMOUNT] == 0
    assert row[COL_PAID_AMOUNT] == 0
    assert row[COL_AMOUNT_SOURCE] == "paid_amount"
    assert "discount_detected" in row[COL_AMOUNT_WARNINGS]
    assert "zero_payment_after_discount" in row[COL_AMOUNT_WARNINGS]


def test_review_dataframe_shows_estimated_vat_fields_as_read_only_context():
    dataframe = receipt_records_to_review_dataframe(
        [
            make_receipt(
                total_amount=5100,
                estimated_supply_amount=4636,
                estimated_vat_amount=464,
                vat_source="estimated_reference",
                vat_note="부가세 미표기, 참고용 역산값",
                vat_warnings=["vat_not_explicit", "vat_estimated_reference_only"],
                vat_review_required=True,
            )
        ]
    )

    assert dataframe.loc[0, COL_ESTIMATED_SUPPLY] == 4636
    assert dataframe.loc[0, COL_ESTIMATED_VAT] == 464
    assert dataframe.loc[0, COL_VAT_SOURCE] == "estimated_reference"
    assert "vat_estimated_reference_only" in dataframe.loc[0, COL_VAT_WARNINGS]


def test_review_dataframe_shows_sensitive_categories_without_values():
    dataframe = receipt_records_to_review_dataframe(
        [
            make_receipt(
                sensitive_text_detected=True,
                sensitive_text_categories=["wifi_password"],
                sensitive_warnings=["wifi_password_detected"],
            )
        ]
    )

    assert bool(dataframe.loc[0, COL_SENSITIVE_DETECTED]) is True
    assert dataframe.loc[0, COL_SENSITIVE_CATEGORIES] == "wifi_password"


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


def test_review_dataframe_shows_quality_flags_for_missing_fields():
    receipt = replace(make_receipt(), merchant_name=None, total_amount=None)

    dataframe = receipt_records_to_review_dataframe([receipt])

    assert dataframe.loc[0, COL_REVIEW_PRIORITY] == PRIORITY_HIGH
    assert "merchant_name" in dataframe.loc[0, COL_MISSING_FIELDS]
    assert "total_amount" in dataframe.loc[0, COL_MISSING_FIELDS]
    assert ISSUE_MERCHANT_MISSING in dataframe.loc[0, COL_QUALITY_FLAGS]
    assert ISSUE_TOTAL_MISSING in dataframe.loc[0, COL_QUALITY_FLAGS]


def test_missing_field_labels_use_core_field_names():
    receipt = replace(
        make_receipt(),
        transaction_date=None,
        merchant_name=None,
        total_amount=None,
        expense_category=None,
    )

    assert missing_field_labels(receipt) == [
        "transaction_date",
        "merchant_name",
        "total_amount",
        "expense_category",
    ]


def test_review_priority_label_marks_missing_core_fields_high():
    receipt = replace(make_receipt(), transaction_date=None)

    assert review_priority_label(receipt) == PRIORITY_HIGH


def test_review_priority_label_marks_amount_or_vat_review_high():
    assert review_priority_label(make_receipt(amount_warnings=["amount_review"])) == PRIORITY_HIGH
    assert review_priority_label(make_receipt(vat_warnings=["vat_review"])) == PRIORITY_HIGH
    assert review_priority_label(make_receipt(vat_review_required=True)) == PRIORITY_HIGH


def test_review_priority_label_marks_sensitive_or_card_review_high():
    assert review_priority_label(make_receipt(sensitive_text_detected=True)) == PRIORITY_HIGH
    assert review_priority_label(make_receipt(card_match_status=CardMatchStatus.NEEDS_REVIEW.value)) == PRIORITY_HIGH
    assert review_priority_label(make_receipt(card_match_status=CardMatchStatus.CANDIDATE.value)) == PRIORITY_HIGH
    assert review_priority_label(make_receipt(card_match_status=CardMatchStatus.MISMATCH.value)) == PRIORITY_HIGH


def test_review_priority_label_marks_uncategorized_or_pending_medium():
    uncategorized = replace(
        make_receipt(card_match_status=CardMatchStatus.MATCHED.value),
        recommended_expense_category=None,
        validation_warnings=[],
    )
    pending = replace(
        make_receipt(review_status=ReviewStatus.PENDING.value, card_match_status=CardMatchStatus.MATCHED.value),
        validation_warnings=[],
    )

    assert review_priority_label(uncategorized) == PRIORITY_MEDIUM
    assert review_priority_label(pending) == PRIORITY_MEDIUM


def test_review_dataframe_sorts_high_medium_low_by_default():
    low = replace(
        make_receipt(review_status=ReviewStatus.APPROVED.value, card_match_status=CardMatchStatus.MATCHED.value),
        review_reason="",
        review_reasons=[],
        validation_warnings=[],
        expense_category="복리후생비",
    )
    medium = replace(
        make_receipt(review_status=ReviewStatus.PENDING.value, card_match_status=CardMatchStatus.MATCHED.value),
        review_reason="",
        review_reasons=[],
        validation_warnings=[],
        expense_category="복리후생비",
    )
    high = replace(make_receipt(), merchant_name=None)

    dataframe = receipt_records_to_review_dataframe([low, medium, high])

    assert list(dataframe[COL_REVIEW_PRIORITY]) == [PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW]


def test_review_dataframe_to_records_updates_sorted_row_without_tracking_columns():
    low = replace(
        make_receipt(review_status=ReviewStatus.APPROVED.value, card_match_status=CardMatchStatus.MATCHED.value),
        source_file_id="low-source",
        review_reason="",
        review_reasons=[],
        validation_warnings=[],
        expense_category="복리후생비",
    )
    high = replace(make_receipt(), source_file_id="high-source", merchant_name=None)
    sorted_records = sort_receipt_records_for_review([low, high])
    dataframe = receipt_records_to_review_dataframe(sorted_records).drop(
        columns=[INTERNAL_RECEIPT_ID, INTERNAL_SOURCE_FILE_ID, INTERNAL_OCR_RESULT_ID]
    )
    dataframe.loc[0, COL_INCLUDED] = False

    updated = review_dataframe_to_receipt_records(dataframe, sorted_records)

    assert updated[0].source_file_id == "high-source"
    assert updated[0].export_included is False
    assert updated[1].source_file_id == "low-source"
    assert updated[1].export_included is True


def test_review_issue_labels_include_card_unmatched_without_sensitive_values():
    receipt = make_receipt(card_match_status=CardMatchStatus.UNMATCHED.value)

    labels = review_issue_labels(receipt)

    assert ISSUE_CARD_UNMATCHED in labels
    assert "raw_text" not in " ".join(labels)


def test_filter_receipt_records_for_review_filters_by_status_and_issue():
    clean = make_receipt(review_status=ReviewStatus.APPROVED.value, card_match_status=CardMatchStatus.MATCHED.value)
    missing = replace(make_receipt(), merchant_name=None)
    excluded = make_receipt(review_status=ReviewStatus.EXCLUDED.value)

    filtered = filter_receipt_records_for_review(
        [clean, missing, excluded],
        status_filter=REVIEW_FILTER_NEEDS_REVIEW,
        issue_filters=[ISSUE_MERCHANT_MISSING],
    )

    assert filtered == [missing]


def test_merge_reviewed_records_preserves_hidden_filter_rows():
    first = make_receipt()
    second = replace(make_receipt(), source_file_id="source-file-2")
    reviewed_second = replace(second, merchant_name="수정상호")

    merged = merge_reviewed_records([first, second], [reviewed_second])

    assert merged[0] == first
    assert merged[1].merchant_name == "수정상호"


def test_review_priority_label_marks_complete_approved_record_done():
    receipt = make_receipt(
        review_status=ReviewStatus.APPROVED.value,
        card_match_status=CardMatchStatus.MATCHED.value,
    )
    receipt = replace(
        receipt,
        review_reason="",
        review_reasons=[],
        validation_warnings=[],
        expense_category="복리후생비",
    )

    assert review_priority_label(receipt) == PRIORITY_LOW

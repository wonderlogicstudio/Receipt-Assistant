from __future__ import annotations

from dataclasses import replace

from app.classifier.category_rules import CategoryRules
from app.core.enums import ReviewStatus
from app.validator.card_matcher import CardMatcher
from app.validator.receipt_validator import ReceiptValidator
from tests.standard_parser_regression_helpers import (
    assert_downstream_receipt_shape,
    assert_no_forbidden_text,
    assert_non_amount_values_not_in_amount_fields,
    matching_card_transaction,
    paddleocr_candidate_record,
    parse_azure_adapter_fixture,
    parse_standard_fixture,
    standard_parser_records,
)


def test_standard_parser_records_pass_receipt_validator_without_provider_payloads() -> None:
    validator = ReceiptValidator()

    for receipt in standard_parser_records():
        validated = validator.validate(receipt)

        assert_downstream_receipt_shape(validated)
        assert validated.validator_version == "receipt-validator-v1"
        assert validated.review_status in {
            ReviewStatus.PENDING.value,
            ReviewStatus.NEEDS_REVIEW.value,
            ReviewStatus.APPROVED.value,
            ReviewStatus.REJECTED.value,
            ReviewStatus.EXCLUDED.value,
        }
        assert_no_forbidden_text(validated)
        assert_non_amount_values_not_in_amount_fields(validated)


def test_validator_preserves_missing_required_field_review_reasons_for_standard_records() -> None:
    validator = ReceiptValidator()
    base = parse_azure_adapter_fixture("azure_receipt_sanitized_response.json")

    missing_merchant = validator.validate(replace(base, merchant_name=None))
    missing_date = validator.validate(replace(base, transaction_date=None))
    missing_amount = validator.validate(replace(base, total_amount=None))

    assert missing_merchant.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert missing_date.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert missing_amount.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert any("상호" in reason or "곹샇" in reason for reason in missing_merchant.review_reasons)
    assert any("날짜" in reason or "좎쭨" in reason for reason in missing_date.review_reasons)
    assert any("금액" in reason or "湲덉븸" in reason for reason in missing_amount.review_reasons)


def test_validator_keeps_vat_and_sensitive_review_signals_from_standard_records() -> None:
    validator = ReceiptValidator()
    receipt = parse_standard_fixture("azure_like_receipt_standard.json")

    validated = validator.validate(receipt)

    assert validated.vat_amount is None
    assert validated.vat_review_required is True
    assert "vat_review_hint" in validated.validation_warnings
    assert validated.sensitive_text_detected is True
    assert validated.sensitive_text_categories == ["wifi_credential"]
    assert "wifi_credential" in str(validated.sensitive_text_categories)
    assert_no_forbidden_text(validated)


def test_validator_does_not_exclude_zero_payment_after_discount_standard_record() -> None:
    validator = ReceiptValidator()
    receipt = parse_standard_fixture("edge_case_receipt_standard.json")

    validated = validator.validate(receipt)

    assert validated.total_amount == 0
    assert validated.export_included is True
    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "zero_paid_amount_requires_review" in validated.validation_warnings
    assert "paid_amount_mismatch" in validated.review_reasons


def test_category_rules_use_receipt_record_merchant_without_standard_ocr_input() -> None:
    rules = CategoryRules()

    categorized = rules.recommend_with_reason(parse_standard_fixture("mock_receipt_standard.json").merchant_name)
    uncategorized = rules.recommend_with_reason(parse_standard_fixture("azure_like_receipt_standard.json").merchant_name)

    assert categorized.category == "복리후생비"
    assert categorized.reason and categorized.reason.startswith("merchant_keyword:")
    assert uncategorized.category == "미분류"


def test_category_recommendation_stays_separate_from_final_expense_category() -> None:
    validated = ReceiptValidator().validate(parse_standard_fixture("mock_receipt_standard.json"))

    assert validated.recommended_expense_category == "복리후생비"
    assert validated.expense_category is None
    assert_no_forbidden_text(validated)


def test_card_matcher_matches_standard_parser_record_by_receipt_and_card_models() -> None:
    receipt = parse_azure_adapter_fixture("azure_receipt_sanitized_response.json")
    transaction = matching_card_transaction(receipt)

    matched = CardMatcher().match([receipt], [transaction])[0]

    assert matched.matched_card_transaction_id == transaction.id
    assert matched.card_match_status == "matched"
    assert matched.card_match_reason in {"approval_number_match", "exact_date_amount_merchant"}
    assert_no_forbidden_text(matched)


def test_card_matcher_does_not_force_match_zero_payment_edge_record() -> None:
    receipt = parse_standard_fixture("edge_case_receipt_standard.json")
    transaction = matching_card_transaction(replace(receipt, total_amount=5000))

    matched = CardMatcher().match([receipt], [transaction])[0]

    assert matched.total_amount == 0
    assert matched.card_match_status in {"unmatched", "matched"}
    if matched.card_match_status == "matched":
        assert matched.card_match_reason == "approval_number_match"
    assert_non_amount_values_not_in_amount_fields(matched)


def test_downstream_accepts_paddleocr_candidate_provider_without_special_case() -> None:
    receipt = paddleocr_candidate_record()
    validated = ReceiptValidator().validate(receipt)
    transaction = matching_card_transaction(validated)
    matched = CardMatcher().match([validated], [transaction])[0]

    assert validated.ocr_provider == "paddleocr"
    assert matched.ocr_provider == "paddleocr"
    assert matched.card_match_status == "matched"
    assert_no_forbidden_text(matched)

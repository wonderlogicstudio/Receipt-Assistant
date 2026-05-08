from dataclasses import replace

from app.core.enums import ReviewStatus
from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.validator.receipt_validator import ReceiptValidator


def make_receipt(tmp_path):
    receipt_path = tmp_path / "sample_receipt.jpg"
    receipt_path.write_bytes(b"sample")
    return ReceiptParser().parse(MockOCRProvider().extract(receipt_path))


def test_missing_transaction_date_needs_review(tmp_path):
    validated = ReceiptValidator().validate(replace(make_receipt(tmp_path), transaction_date=None))

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "날짜누락" in validated.review_reasons


def test_missing_merchant_name_needs_review(tmp_path):
    validated = ReceiptValidator().validate(replace(make_receipt(tmp_path), merchant_name=None))

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "상호누락" in validated.review_reasons


def test_missing_total_amount_needs_review(tmp_path):
    validated = ReceiptValidator().validate(replace(make_receipt(tmp_path), total_amount=None))

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "금액누락" in validated.review_reasons


def test_zero_total_amount_needs_review(tmp_path):
    validated = ReceiptValidator().validate(replace(make_receipt(tmp_path), total_amount=0))

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "금액누락" in validated.review_reasons


def test_matching_amounts_do_not_add_mismatch_reason(tmp_path):
    receipt = replace(make_receipt(tmp_path), supply_amount=10909, vat_amount=1091, total_amount=12000)

    validated = ReceiptValidator().validate(receipt)

    assert "금액불일치" not in validated.review_reasons


def test_amount_mismatch_over_tolerance_adds_review_reason(tmp_path):
    receipt = replace(make_receipt(tmp_path), supply_amount=10000, vat_amount=1000, total_amount=12000)

    validated = ReceiptValidator(amount_tolerance=1).validate(receipt)

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "금액불일치" in validated.review_reasons


def test_amount_difference_within_tolerance_is_not_mismatch(tmp_path):
    receipt = replace(make_receipt(tmp_path), supply_amount=10000, vat_amount=1999, total_amount=12000)

    validated = ReceiptValidator(amount_tolerance=1).validate(receipt)

    assert "금액불일치" not in validated.review_reasons


def test_missing_vat_amount_adds_review_reason(tmp_path):
    validated = ReceiptValidator().validate(replace(make_receipt(tmp_path), vat_amount=None))

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "부가세미확인" in validated.review_reasons


def test_valid_business_number_does_not_add_format_reason(tmp_path):
    validated = ReceiptValidator().validate(replace(make_receipt(tmp_path), business_number="123-45-67890"))

    assert "사업자번호형식확인" not in validated.review_reasons


def test_invalid_business_number_adds_review_reason(tmp_path):
    validated = ReceiptValidator().validate(replace(make_receipt(tmp_path), business_number="123456"))

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "사업자번호형식확인" in validated.review_reasons


def test_missing_business_number_adds_warning_without_review_reason(tmp_path):
    validated = ReceiptValidator().validate(replace(make_receipt(tmp_path), business_number=None))

    assert "사업자번호미확인" in validated.validation_warnings
    assert "사업자번호형식확인" not in validated.review_reasons


def test_missing_payment_method_adds_validation_warning(tmp_path):
    validated = ReceiptValidator().validate(replace(make_receipt(tmp_path), payment_method=None))

    assert "결제수단미확인" in validated.validation_warnings


def test_parser_warnings_are_preserved_in_validation_warnings(tmp_path):
    receipt = replace(make_receipt(tmp_path), parser_warnings=["날짜누락"])

    validated = ReceiptValidator().validate(receipt)

    assert "날짜누락" in validated.parser_warnings
    assert "날짜누락" in validated.validation_warnings


def test_duplicate_review_reasons_are_removed(tmp_path):
    receipt = replace(make_receipt(tmp_path), transaction_date=None, review_reasons=["날짜누락"], review_reason="날짜누락")

    validated = ReceiptValidator().validate(receipt)

    assert validated.review_reasons.count("날짜누락") == 1
    assert validated.review_reason.split(";").count("날짜누락") == 1


def test_normal_receipt_keeps_pending_status(tmp_path):
    receipt = replace(make_receipt(tmp_path), review_status=ReviewStatus.PENDING.value)

    validated = ReceiptValidator().validate(receipt)

    assert validated.review_status == ReviewStatus.PENDING.value


def test_existing_needs_review_does_not_return_to_pending(tmp_path):
    receipt = replace(make_receipt(tmp_path), review_status=ReviewStatus.NEEDS_REVIEW.value)

    validated = ReceiptValidator().validate(receipt)

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value


def test_existing_user_decision_status_is_not_changed(tmp_path):
    receipt = replace(make_receipt(tmp_path), review_status=ReviewStatus.APPROVED.value, transaction_date=None)

    validated = ReceiptValidator().validate(receipt)

    assert validated.review_status == ReviewStatus.APPROVED.value
    assert "날짜누락" in validated.review_reasons


def test_recommendation_is_stored_separately_from_expense_category(tmp_path):
    receipt = replace(make_receipt(tmp_path), merchant_name="스타벅스 강남점", expense_category=None)

    validated = ReceiptValidator().validate(receipt)

    assert validated.recommended_expense_category == "복리후생비"
    assert validated.expense_category is None

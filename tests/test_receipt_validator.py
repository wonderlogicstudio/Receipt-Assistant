from dataclasses import replace

from app.core.enums import ReviewStatus
from app.core.ocr_models import OCRResult
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

    assert "금액누락" not in validated.review_reasons


def test_zero_total_amount_after_discount_needs_review_without_missing_amount(tmp_path):
    validated = ReceiptValidator().validate(
        replace(
            make_receipt(tmp_path),
            total_amount=0,
            gross_amount=10800,
            discount_amount=10800,
            final_amount=0,
            paid_amount=0,
            amount_warnings=["discount_detected", "zero_payment_after_discount"],
        )
    )

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "금액누락" not in validated.review_reasons
    assert "zero_payment_after_discount" in validated.review_reasons
    assert "zero_payment_after_discount" in validated.validation_warnings


def test_inferred_discount_warning_is_preserved(tmp_path):
    validated = ReceiptValidator().validate(
        replace(
            make_receipt(tmp_path),
            total_amount=0,
            gross_amount=10800,
            discount_amount=10800,
            final_amount=0,
            paid_amount=0,
            amount_warnings=[
                "discount_inferred_from_zero_payment",
                "zero_payment_after_discount",
            ],
        )
    )

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "discount_inferred_from_zero_payment" in validated.validation_warnings
    assert "zero_payment_after_discount" in validated.review_reasons


def test_discount_zero_payment_pipeline_trace_validator_preserves_amount_state():
    raw_text = "\n".join(
        [
            "제품명",
            "(할인내역)        수량        금액",
            "                  (할인금액)",
            "레디팩(아몬드봉봉)          10,800",
            "KT 멤버십 VVIP 초이스      -10,800",
            ">>드라이아이스(분) 10       0",
            "총매출액                  10,800",
            "할인금액                  10,800",
            "합계금액                  0",
            "받은금액                  0",
        ]
    )
    ocr_result = OCRResult.completed(
        source_file_id="source-file-1",
        source_file_name="sample_receipt.jpg",
        stored_relative_path="data/uploads/session-1/sample_receipt.jpg",
        provider="mock",
        raw_text=raw_text,
        raw_json={},
        confidence=0.94,
    )

    parsed = ReceiptParser().parse(ocr_result)
    validated = ReceiptValidator().validate(parsed)

    assert validated.gross_amount == 10800
    assert validated.discount_amount == 10800
    assert validated.final_amount == 0
    assert validated.paid_amount == 0
    assert validated.total_amount == 0
    assert validated.amount_source in {"paid_amount", "final_amount"}
    assert "discount_detected" in validated.amount_warnings
    assert "zero_payment_after_discount" in validated.amount_warnings
    assert "zero_payment_after_discount" in validated.review_reasons
    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value


def test_discount_amount_match_does_not_add_mismatch_reason(tmp_path):
    receipt = replace(make_receipt(tmp_path), gross_amount=10800, discount_amount=10800, final_amount=0)

    validated = ReceiptValidator().validate(receipt)

    assert "amount_mismatch_after_discount" not in validated.review_reasons


def test_discount_amount_mismatch_adds_review_reason(tmp_path):
    receipt = replace(make_receipt(tmp_path), gross_amount=10800, discount_amount=1000, final_amount=0)

    validated = ReceiptValidator().validate(receipt)

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "amount_mismatch_after_discount" in validated.review_reasons


def test_discount_amount_larger_than_gross_adds_suspicious_reason(tmp_path):
    receipt = replace(make_receipt(tmp_path), gross_amount=10800, discount_amount=21600, final_amount=0)

    validated = ReceiptValidator().validate(receipt)

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "discount_amount_suspicious" in validated.review_reasons
    assert "discount_amount_suspicious" in validated.validation_warnings


def test_paid_amount_mismatch_adds_review_reason(tmp_path):
    receipt = replace(make_receipt(tmp_path), paid_amount=10000, final_amount=9000)

    validated = ReceiptValidator().validate(receipt)

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "paid_amount_mismatch" in validated.review_reasons


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


def test_estimated_reference_vat_adds_review_reason_without_filling_explicit_vat(tmp_path):
    validated = ReceiptValidator().validate(
        replace(
            make_receipt(tmp_path),
            supply_amount=None,
            vat_amount=None,
            estimated_supply_amount=4636,
            estimated_vat_amount=464,
            vat_source="estimated_reference",
            vat_warnings=["vat_not_explicit", "vat_estimated_reference_only"],
            vat_review_required=True,
        )
    )

    assert validated.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert validated.vat_amount is None
    assert validated.supply_amount is None
    assert "vat_estimated_reference_only" in validated.review_reasons
    assert "vat_estimated_reference_only" in validated.validation_warnings


def test_explicit_vat_does_not_add_missing_vat_reason(tmp_path):
    validated = ReceiptValidator().validate(
        replace(make_receipt(tmp_path), supply_amount=10000, vat_amount=1000, total_amount=11000, vat_source="explicit")
    )

    assert "부가세미확인" not in validated.review_reasons


def test_zero_amount_vat_source_does_not_add_missing_vat_reason(tmp_path):
    validated = ReceiptValidator().validate(
        replace(
            make_receipt(tmp_path),
            total_amount=0,
            supply_amount=None,
            vat_amount=None,
            estimated_supply_amount=None,
            estimated_vat_amount=None,
            vat_source="zero_amount",
            vat_warnings=["vat_not_explicit", "vat_estimate_skipped_zero_amount"],
            vat_review_required=False,
        )
    )

    assert "부가세미확인" not in validated.review_reasons


def test_estimated_vat_amounts_must_match_total_amount(tmp_path):
    validated = ReceiptValidator().validate(
        replace(
            make_receipt(tmp_path),
            total_amount=5100,
            supply_amount=None,
            vat_amount=None,
            estimated_supply_amount=4600,
            estimated_vat_amount=400,
            vat_source="estimated_reference",
            vat_review_required=True,
        )
    )

    assert "vat_amount_mismatch" in validated.validation_warnings


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

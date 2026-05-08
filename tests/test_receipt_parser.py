from __future__ import annotations

from app.core.enums import CardMatchStatus, EvidenceType, OCRProviderName, OCRStatus, ReviewStatus
from app.core.ocr_models import OCRResult
from app.parser.normalizers import normalize_amount, normalize_business_number, normalize_date
from app.parser.receipt_parser import ReceiptParser


SAMPLE_OCR_TEXT = "\n".join(
    [
        "상호명: 테스트카페",
        "사업자번호: 123-45-67890",
        "거래일자: 2026.05.07",
        "공급가액: 10,909원",
        "부가세: 1,091원",
        "합계: 12,000원",
        "결제수단: 신용카드",
    ]
)


def make_ocr_result(raw_text: str = SAMPLE_OCR_TEXT, status: str = OCRStatus.COMPLETED.value) -> OCRResult:
    if status == OCRStatus.COMPLETED.value:
        return OCRResult.completed(
            source_file_id="source-file-1",
            source_file_name="sample_receipt.jpg",
            stored_relative_path="data/uploads/session-1/sample_receipt.jpg",
            provider=OCRProviderName.MOCK.value,
            raw_text=raw_text,
            raw_json={},
            confidence=0.94,
        )
    return OCRResult.failed(
        source_file_id="source-file-1",
        source_file_name="sample_receipt.jpg",
        stored_relative_path="data/uploads/session-1/sample_receipt.jpg",
        provider=OCRProviderName.MOCK.value,
        error_message="mock failure",
    )


def test_sample_ocr_raw_text_is_converted_to_receipt_record():
    receipt = ReceiptParser().parse(make_ocr_result())

    assert receipt.transaction_date.isoformat() == "2026-05-07"
    assert receipt.merchant_name == "테스트카페"
    assert receipt.business_number == "123-45-67890"
    assert receipt.supply_amount == 10909
    assert receipt.vat_amount == 1091
    assert receipt.total_amount == 12000
    assert receipt.payment_method == "신용카드"
    assert receipt.review_status == ReviewStatus.PENDING.value


def test_ocr_result_metadata_is_reflected_in_receipt_record():
    ocr_result = make_ocr_result()

    receipt = ReceiptParser().parse(ocr_result)

    assert receipt.ocr_result_id == ocr_result.id
    assert receipt.source_file_id == "source-file-1"
    assert receipt.source_file_name == "sample_receipt.jpg"
    assert receipt.stored_relative_path == "data/uploads/session-1/sample_receipt.jpg"
    assert receipt.session_id == "session-1"
    assert receipt.confidence == 0.94


def test_receipt_normalizers_handle_supported_formats():
    assert normalize_date("2026.05.07").isoformat() == "2026-05-07"
    assert normalize_date("20260507").isoformat() == "2026-05-07"
    assert normalize_amount("12,000원") == 12000
    assert normalize_amount("₩12,000") == 12000
    assert normalize_business_number("1234567890") == "123-45-67890"
    assert normalize_business_number("123-45-67890") == "123-45-67890"


def test_missing_total_amount_needs_review_with_warning():
    raw_text = "\n".join(["테스트카페", "거래일자: 2026.05.07", "사업자번호: 123-45-67890"])

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "금액누락" in receipt.parser_warnings
    assert "금액누락" in receipt.review_reason


def test_missing_merchant_name_needs_review_with_warning():
    raw_text = "\n".join(["거래일자: 2026.05.07", "합계: 12,000원", "사업자번호: 123-45-67890"])

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "상호누락" in receipt.parser_warnings


def test_missing_transaction_date_needs_review_with_warning():
    raw_text = "\n".join(["테스트카페", "합계: 12,000원", "사업자번호: 123-45-67890"])

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "날짜누락" in receipt.parser_warnings


def test_complete_required_fields_stay_pending_and_unmatched():
    receipt = ReceiptParser().parse(make_ocr_result())

    assert receipt.review_status == ReviewStatus.PENDING.value
    assert receipt.card_match_status == CardMatchStatus.UNMATCHED.value
    assert receipt.expense_category is None
    assert receipt.evidence_type == EvidenceType.RECEIPT_IMAGE.value


def test_failed_ocr_result_becomes_needs_review():
    receipt = ReceiptParser().parse(make_ocr_result(status=OCRStatus.FAILED.value))

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert any("OCR 상태 확인 필요" in warning for warning in receipt.parser_warnings)


def test_unclear_business_number_adds_parser_warning():
    raw_text = "\n".join(["테스트카페", "사업자번호: 123-45-678", "거래일자: 2026.05.07", "합계: 12,000원"])

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.business_number is None
    assert "사업자번호 형식 확인 필요" in receipt.parser_warnings


def test_receipt_record_does_not_store_raw_ocr_text():
    receipt = ReceiptParser().parse(make_ocr_result())
    data = receipt.to_dict()

    assert "raw_text" not in data
    assert "raw_json" not in data
    assert receipt.ocr_raw_text == ""

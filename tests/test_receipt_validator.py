from dataclasses import replace

from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.validator.receipt_validator import ReceiptValidator


def test_receipt_validator_detects_missing_required_values():
    receipt = ReceiptParser().parse(MockOCRProvider().extract("sample_receipt.jpg"))
    invalid = replace(receipt, transaction_date=None, merchant_name=None, total_amount=None)

    validated = ReceiptValidator().validate(invalid)

    assert validated.review_status == "검토필요"
    assert "날짜누락" in validated.review_reason
    assert "상호누락" in validated.review_reason
    assert "금액누락" in validated.review_reason


def test_receipt_validator_detects_amount_mismatch_and_low_confidence():
    receipt = ReceiptParser().parse(MockOCRProvider().extract("sample_receipt.jpg"))
    invalid = replace(receipt, total_amount=32000, confidence=0.5)

    validated = ReceiptValidator().validate(invalid)

    assert "금액불일치" in validated.review_reason
    assert "낮은신뢰도" in validated.review_reason


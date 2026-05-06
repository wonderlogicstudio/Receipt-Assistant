from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser, parse_amount, parse_date


def test_receipt_parser_maps_ocr_result_to_standard_fields():
    ocr_result = MockOCRProvider().extract("sample_receipt.png")
    receipt = ReceiptParser().parse(ocr_result)

    assert receipt.receipt_id
    assert receipt.source_file_name == "sample_receipt.png"
    assert receipt.transaction_date.isoformat() == "2026-05-06"
    assert receipt.merchant_name == "샘플문구 강남점"
    assert receipt.business_number == "123-45-67890"
    assert receipt.total_amount == 33000
    assert receipt.supply_amount == 30000
    assert receipt.vat_amount == 3000
    assert receipt.payment_method == "카드"
    assert receipt.expense_category == "소모품비"
    assert receipt.confidence == 0.94
    assert receipt.review_status == "검토필요"
    assert "검수 필요" in receipt.review_reason


def test_receipt_parser_normalizers_handle_common_formats():
    assert parse_amount("33,000원") == 33000
    assert parse_date("2026.05.06").isoformat() == "2026-05-06"


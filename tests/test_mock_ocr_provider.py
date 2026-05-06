from app.ocr.mock_provider import MockOCRProvider


def test_mock_ocr_provider_returns_standard_sample_result():
    result = MockOCRProvider().extract("sample_receipt.jpg")

    assert result.status == "success"
    assert result.provider == "mock"
    assert result.source_file_name == "sample_receipt.jpg"
    assert result.confidence == 0.94
    assert result.raw_json["merchant_name"] == "샘플문구 강남점"
    assert result.raw_json["total_amount"] == 33000
    assert "사업자번호" in result.raw_text


def test_mock_ocr_provider_rejects_unsupported_receipt_file_type():
    result = MockOCRProvider().extract("card_statement.xlsx")

    assert result.status == "failed"
    assert result.error_message


from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.ui.streamlit_app import PREVIEW_COLUMNS, receipts_to_preview_dataframe


def test_receipts_to_preview_dataframe_hides_raw_ocr_fields():
    receipt = ReceiptParser().parse(MockOCRProvider().extract("sample_receipt.jpg"))

    dataframe = receipts_to_preview_dataframe([receipt])

    assert list(dataframe.columns) == PREVIEW_COLUMNS
    assert "ocr_raw_text" not in dataframe.columns
    assert "raw_json" not in dataframe.columns
    assert dataframe.loc[0, "merchant_name"] == "샘플문구 강남점"

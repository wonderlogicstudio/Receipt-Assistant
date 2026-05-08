from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.storage.file_store import StoredFileMetadata
from app.ui.streamlit_app import PREVIEW_COLUMNS, receipts_to_preview_dataframe, stored_files_to_dataframe


def test_receipts_to_preview_dataframe_hides_raw_ocr_fields(tmp_path):
    receipt_path = tmp_path / "sample_receipt.jpg"
    receipt_path.write_bytes(b"sample")
    receipt = ReceiptParser().parse(MockOCRProvider().extract(receipt_path))

    dataframe = receipts_to_preview_dataframe([receipt])

    assert list(dataframe.columns) == PREVIEW_COLUMNS
    assert "ocr_raw_text" not in dataframe.columns
    assert "raw_json" not in dataframe.columns
    assert dataframe.loc[0, "merchant_name"] == "샘플문구 강남점"


def test_stored_files_to_dataframe_hides_original_path_parts():
    metadata = StoredFileMetadata(
        original_file_name=r"C:\private\receipt.pdf",
        stored_file_name="receipt_abc.pdf",
        stored_relative_path="data/uploads/session/receipt_abc.pdf",
        file_extension=".pdf",
        file_size_bytes=10,
        session_id="session",
    )

    dataframe = stored_files_to_dataframe([metadata])

    assert dataframe.loc[0, "original_file_name"] == "receipt.pdf"
    assert "C:" not in dataframe.loc[0, "original_file_name"]

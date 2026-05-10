from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.storage.file_store import StoredFileMetadata
from app.core.ocr_models import OCRResult
from app.ui.streamlit_app import (
    PREVIEW_COLUMNS,
    format_ocr_diagnostic,
    receipts_to_preview_dataframe,
    should_disable_process_button,
    stored_files_to_dataframe,
)


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


def test_format_ocr_diagnostic_uses_safe_tokens_only():
    result = OCRResult.failed(
        source_file_id="id",
        source_file_name="receipt.jpg",
        stored_relative_path=r"C:\private\receipt.jpg",
        provider="azure",
        error_message="do not show this",
        diagnostic_code="proxy_error",
    )

    diagnostic = format_ocr_diagnostic(result)

    assert diagnostic == "status=failed, provider=azure, reason=proxy_error"
    assert "receipt.jpg" not in diagnostic
    assert "private" not in diagnostic
    assert "do not show this" not in diagnostic


def test_should_disable_process_button_when_empty_or_processing():
    assert should_disable_process_button([], is_processing=False) is True
    assert should_disable_process_button(None, is_processing=False) is True
    assert should_disable_process_button([object()], is_processing=True) is True
    assert should_disable_process_button([object()], is_processing=False) is False

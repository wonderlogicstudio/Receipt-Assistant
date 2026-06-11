from datetime import datetime

from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.storage.file_store import StoredFileMetadata
from app.core.ocr_models import OCRResult
from app.core.standard_ocr import StandardOCRKeyValueCandidate, StandardOCRResult, StandardOCRTextBlock
from app.ui.streamlit_app import (
    PREVIEW_COLUMNS,
    build_runtime_ocr_config,
    format_ocr_diagnostic,
    process_receipt_files_with_mock_ocr,
    receipts_to_preview_dataframe,
    resolve_runtime_ocr_provider_name,
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


def test_runtime_ocr_provider_selection_resolves_current_or_safe_override(monkeypatch):
    assert resolve_runtime_ocr_provider_name("__current__", "azure") == "azure"
    assert resolve_runtime_ocr_provider_name("mock", "azure") == "mock"
    assert resolve_runtime_ocr_provider_name("azure", "mock") == "azure"
    assert resolve_runtime_ocr_provider_name("paddle", "azure") == "paddle"
    assert resolve_runtime_ocr_provider_name("paddleocr", "azure") == "paddleocr"
    assert resolve_runtime_ocr_provider_name("unknown", "azure") == "azure"

    monkeypatch.setenv("OCR_PROVIDER", "azure")
    config = build_runtime_ocr_config("mock")

    assert config.ocr_provider == "mock"


def test_process_receipt_files_accepts_standard_ocr_provider_result():
    metadata = StoredFileMetadata(
        original_file_name=r"C:\private\paddle_receipt.jpg",
        stored_file_name="paddle_receipt.jpg",
        stored_relative_path="data/uploads/session/paddle_receipt.jpg",
        file_extension=".jpg",
        file_size_bytes=10,
        session_id="session",
    )

    result = process_receipt_files_with_mock_ocr(
        [metadata],
        ocr_provider=FakeStandardOCRProvider(),
    )

    assert not result.errors
    assert len(result.receipt_records) == 1
    receipt = result.receipt_records[0]
    assert receipt.ocr_provider == "paddleocr"
    assert receipt.source_file_name == "paddle_receipt.jpg"
    assert receipt.merchant_name == "테스트카페"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-06-10"
    assert receipt.total_amount == 12000
    assert "private" not in receipt.source_file_name
    assert isinstance(result.ocr_results[0], StandardOCRResult)


class FakeStandardOCRProvider:
    provider_name = "paddleocr"

    def extract(self, _source: object) -> StandardOCRResult:
        return StandardOCRResult(
            id="standard-test",
            provider="paddleocr",
            provider_version="test",
            engine_runtime="pc_local",
            status="completed",
            text_blocks=[
                StandardOCRTextBlock(
                    page_index=0,
                    block_id="line-1",
                    text="상호명 테스트카페",
                    normalized_text="상호명 테스트카페",
                    confidence=0.98,
                    line_order=0,
                )
            ],
            key_value_candidates=[
                StandardOCRKeyValueCandidate(
                    key="merchant_name",
                    candidate_type="merchant_name",
                    value="테스트카페",
                    normalized_value="테스트카페",
                ),
                StandardOCRKeyValueCandidate(
                    key="transaction_date",
                    candidate_type="transaction_date",
                    value="2026-06-10",
                    normalized_value="2026-06-10",
                ),
                StandardOCRKeyValueCandidate(
                    key="total_amount",
                    candidate_type="total_amount",
                    value="12,000",
                    normalized_value="12000",
                ),
                StandardOCRKeyValueCandidate(
                    key="payment_method",
                    candidate_type="payment_method",
                    value="카드",
                    normalized_value="카드",
                ),
            ],
            confidence=0.98,
            created_at=datetime(2026, 6, 10, 12, 0, 0),
        )

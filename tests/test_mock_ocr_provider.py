from __future__ import annotations

from pathlib import Path

from app.core.enums import OCRProviderName, OCRStatus
from app.ocr.mock_provider import MockOCRProvider


def make_file(tmp_path: Path, file_name: str) -> Path:
    path = tmp_path / file_name
    path.write_bytes(b"sample")
    return path


def test_mock_ocr_provider_returns_completed_result_for_jpg(tmp_path):
    result = MockOCRProvider().extract(make_file(tmp_path, "sample_receipt.jpg"))

    assert result.status == OCRStatus.COMPLETED.value
    assert result.provider == OCRProviderName.MOCK.value
    assert result.source_file_name == "sample_receipt.jpg"
    assert result.source_file_id
    assert result.stored_relative_path == "sample_receipt.jpg"
    assert result.confidence == 0.94
    assert 0 <= result.confidence <= 1
    assert result.raw_text
    assert result.raw_json
    assert result.raw_json["merchant_name"] == "샘플문구 강남점"
    assert result.raw_json["total_amount"] == 33000
    assert "사업자번호" in result.raw_text


def test_mock_ocr_provider_returns_completed_result_for_pdf(tmp_path):
    result = MockOCRProvider().extract(make_file(tmp_path, "sample_receipt.pdf"))

    assert result.status == OCRStatus.COMPLETED.value
    assert result.source_file_name == "sample_receipt.pdf"
    assert result.source_file_id


def test_mock_ocr_provider_skips_xlsx_card_statement(tmp_path):
    result = MockOCRProvider().extract(make_file(tmp_path, "card_statement.xlsx"))

    assert result.status == OCRStatus.SKIPPED.value
    assert result.provider == OCRProviderName.MOCK.value
    assert result.raw_text == ""
    assert result.raw_json is None
    assert result.error_message


def test_mock_ocr_provider_skips_csv_card_statement(tmp_path):
    result = MockOCRProvider().extract(make_file(tmp_path, "card_statement.csv"))

    assert result.status == OCRStatus.SKIPPED.value
    assert result.error_message


def test_mock_ocr_provider_fails_for_unsupported_extension(tmp_path):
    result = MockOCRProvider().extract(make_file(tmp_path, "receipt.txt"))

    assert result.status == OCRStatus.FAILED.value
    assert result.error_message


def test_mock_ocr_provider_fails_for_missing_file(tmp_path):
    result = MockOCRProvider().extract(tmp_path / "missing_receipt.jpg")

    assert result.status == OCRStatus.FAILED.value
    assert result.error_message


def test_mock_ocr_provider_uses_stored_file_metadata_from_file_store():
    from io import BytesIO
    import shutil
    from uuid import uuid4

    from app.storage.file_store import FileStore

    class UploadedFile(BytesIO):
        def __init__(self, name: str, content: bytes) -> None:
            super().__init__(content)
            self.name = name

    session_id = f"ocr-{uuid4().hex}"
    metadata = FileStore().save_uploaded_file(UploadedFile("stored_receipt.png", b"sample"), session_id=session_id)

    try:
        result = MockOCRProvider().extract(metadata)
    finally:
        shutil.rmtree(Path("data/uploads") / session_id, ignore_errors=True)

    assert result.status == OCRStatus.COMPLETED.value
    assert result.source_file_name == "stored_receipt.png"
    assert result.stored_relative_path == metadata.stored_relative_path
    assert result.source_file_id

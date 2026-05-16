from __future__ import annotations

import inspect
from pathlib import Path

from app.core.config import AppConfig, get_config
from app.core.ocr_models import OCRResult
from app.core.standard_ocr import StandardOCRResult
from app.ocr.azure_provider import AzureDocumentIntelligenceProvider
from app.ocr.base import OCRProvider
from app.ocr.mock_provider import MockOCRProvider
from app.ocr.provider_factory import get_ocr_provider


class NoNetworkSession:
    def __init__(self) -> None:
        self.post_calls: list[object] = []
        self.get_calls: list[object] = []

    def post(self, *args, **kwargs):  # pragma: no cover - should never be reached
        self.post_calls.append((args, kwargs))
        raise AssertionError("Azure regression tests must not call network")

    def get(self, *args, **kwargs):  # pragma: no cover - should never be reached
        self.get_calls.append((args, kwargs))
        raise AssertionError("Azure regression tests must not call network")


def make_config() -> AppConfig:
    return AppConfig(
        ocr_provider="azure",
        azure_document_intelligence_endpoint="azure-endpoint-placeholder",
        azure_document_intelligence_key="test-credential",
        ocr_request_timeout_seconds=5,
    )


def make_provider(session: NoNetworkSession | None = None) -> AzureDocumentIntelligenceProvider:
    return AzureDocumentIntelligenceProvider(
        make_config(),
        session=session or NoNetworkSession(),
        poll_interval_seconds=1,
        max_poll_attempts=1,
        max_retries=0,
        sleep_func=lambda seconds: None,
    )


def test_azure_provider_is_importable_and_still_implements_ocr_provider() -> None:
    provider = make_provider()

    assert isinstance(provider, AzureDocumentIntelligenceProvider)
    assert isinstance(provider, OCRProvider)
    assert provider.provider_name == "azure"


def test_azure_provider_extract_public_interface_still_returns_ocr_result() -> None:
    signature = inspect.signature(AzureDocumentIntelligenceProvider.extract)

    assert list(signature.parameters) == ["self", "source"]
    assert signature.return_annotation in {OCRResult, "OCRResult"}


def test_azure_provider_extract_does_not_return_standard_ocr_result_for_skipped_file(
    tmp_path: Path,
) -> None:
    session = NoNetworkSession()
    provider = make_provider(session)
    statement = tmp_path / "statement.xlsx"
    statement.write_bytes(b"dummy")

    result = provider.extract(statement)

    assert isinstance(result, OCRResult)
    assert not isinstance(result, StandardOCRResult)
    assert result.status == "skipped"
    assert result.provider == "azure"
    assert session.post_calls == []
    assert session.get_calls == []


def test_azure_provider_missing_file_still_returns_ocr_result_without_network(
    tmp_path: Path,
) -> None:
    session = NoNetworkSession()
    provider = make_provider(session)

    result = provider.extract(tmp_path / "missing.jpg")

    assert isinstance(result, OCRResult)
    assert not isinstance(result, StandardOCRResult)
    assert result.status == "failed"
    assert result.diagnostic_code == "source_not_accessible"
    assert session.post_calls == []
    assert session.get_calls == []


def test_default_provider_factory_does_not_require_azure_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    monkeypatch.delenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", raising=False)

    provider = get_ocr_provider(get_config())

    assert isinstance(provider, MockOCRProvider)


def test_azure_provider_default_extract_path_is_not_forced_through_standard_adapter() -> None:
    provider_source = inspect.getsource(AzureDocumentIntelligenceProvider)

    assert "AzureStandardOCRAdapter" not in provider_source
    assert "build_standard_ocr_from_azure_summary" not in provider_source

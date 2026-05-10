import pytest

from app.core.config import AppConfig, get_config
from app.core.exceptions import ConfigurationError
from app.ocr.azure_provider import AzureDocumentIntelligenceProvider
from app.ocr.mock_provider import MockOCRProvider
from app.ocr.provider_factory import get_ocr_provider


def test_default_config_returns_mock_provider(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OCR_PROVIDER", raising=False)

    provider = get_ocr_provider(get_config())

    assert isinstance(provider, MockOCRProvider)


def test_mock_provider_config_returns_mock_provider():
    provider = get_ocr_provider(AppConfig(ocr_provider="mock"))

    assert isinstance(provider, MockOCRProvider)


def test_azure_provider_config_creates_azure_provider():
    provider = get_ocr_provider(
        AppConfig(
            ocr_provider="azure",
            azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com/",
            azure_document_intelligence_key="not-a-real-credential",
        )
    )

    assert isinstance(provider, AzureDocumentIntelligenceProvider)


def test_azure_provider_config_without_key_raises_configuration_error():
    with pytest.raises(ConfigurationError):
        get_ocr_provider(
            AppConfig(
                ocr_provider="azure",
                azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com/",
                azure_document_intelligence_key=None,
            )
        )


def test_unknown_provider_raises_configuration_error():
    with pytest.raises(ConfigurationError):
        get_ocr_provider(AppConfig(ocr_provider="unknown"))

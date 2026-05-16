from __future__ import annotations

from app.core.config import AppConfig, get_config
from app.ocr.azure_provider import AzureDocumentIntelligenceProvider
from app.ocr.mock_provider import MockOCRProvider
from app.ocr.paddle_provider import PaddleOCRProvider
from app.ocr.provider_factory import get_ocr_provider


def test_provider_factory_creates_paddle_provider_candidate() -> None:
    provider = get_ocr_provider(AppConfig(ocr_provider="paddle"))

    assert isinstance(provider, PaddleOCRProvider)
    assert provider.provider_name == "paddleocr"


def test_provider_factory_accepts_paddleocr_alias() -> None:
    provider = get_ocr_provider(AppConfig(ocr_provider="paddleocr"))

    assert isinstance(provider, PaddleOCRProvider)


def test_provider_factory_default_still_returns_mock(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OCR_PROVIDER", raising=False)

    provider = get_ocr_provider(get_config())

    assert isinstance(provider, MockOCRProvider)


def test_provider_factory_mock_flow_is_unchanged() -> None:
    provider = get_ocr_provider(AppConfig(ocr_provider="mock"))

    assert isinstance(provider, MockOCRProvider)


def test_provider_factory_azure_flow_is_unchanged() -> None:
    provider = get_ocr_provider(
        AppConfig(
            ocr_provider="azure",
            azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com/",
            azure_document_intelligence_key="not-a-real-credential",
        )
    )

    assert isinstance(provider, AzureDocumentIntelligenceProvider)


def test_provider_factory_env_paddle_candidate_does_not_require_paddleocr(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OCR_PROVIDER", "paddle")

    provider = get_ocr_provider(get_config())

    assert isinstance(provider, PaddleOCRProvider)


def test_provider_factory_tests_do_not_add_paddleocr_dependency() -> None:
    requirements = __import__("pathlib").Path("requirements.txt").read_text(encoding="utf-8").lower()

    assert "paddleocr" not in requirements

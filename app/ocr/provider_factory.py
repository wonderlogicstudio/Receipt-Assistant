from __future__ import annotations

from app.core.config import AppConfig, get_config
from app.core.enums import OCRProviderName
from app.core.exceptions import ConfigurationError
from app.ocr.azure_provider import AzureDocumentIntelligenceProvider
from app.ocr.base import OCRProvider
from app.ocr.mock_provider import MockOCRProvider


def get_ocr_provider(config: AppConfig | None = None) -> OCRProvider:
    safe_config = config or get_config()
    provider_name = (safe_config.ocr_provider or OCRProviderName.MOCK.value).strip().lower()

    if provider_name == OCRProviderName.MOCK.value:
        return MockOCRProvider()
    if provider_name == OCRProviderName.AZURE.value:
        return AzureDocumentIntelligenceProvider(safe_config)
    raise ConfigurationError(f"지원하지 않는 OCR provider입니다: {provider_name}")

from __future__ import annotations

from app.core.config import AppConfig, get_config
from app.core.enums import OCRProviderName
from app.core.exceptions import ConfigurationError
from app.ocr.azure_provider import AzureDocumentIntelligenceProvider
from app.ocr.base import OCRProvider
from app.ocr.mock_provider import MockOCRProvider
from app.ocr.paddle_provider import PaddleOCRProvider


def get_ocr_provider(config: AppConfig | None = None) -> OCRProvider | PaddleOCRProvider:
    safe_config = config or get_config()
    provider_name = (safe_config.ocr_provider or OCRProviderName.MOCK.value).strip().lower()

    if provider_name == OCRProviderName.MOCK.value:
        return MockOCRProvider()
    if provider_name == OCRProviderName.AZURE.value:
        return AzureDocumentIntelligenceProvider(safe_config)
    if provider_name in {OCRProviderName.PADDLE.value, OCRProviderName.PADDLEOCR.value}:
        return PaddleOCRProvider(
            lang=safe_config.paddle_lang,
            use_angle_cls=safe_config.paddle_use_angle_cls,
            use_gpu=safe_config.paddle_use_gpu,
            show_log=safe_config.paddle_show_log,
        )
    raise ConfigurationError(f"지원하지 않는 OCR provider입니다: {provider_name}")

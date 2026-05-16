from app.ocr.adapters.azure_standard_adapter import (
    AzureStandardOCRAdapter,
    convert_azure_response_to_standard_ocr,
)
from app.ocr.adapters.azure_adapter_bridge import build_standard_ocr_from_azure_summary
from app.ocr.adapters.paddle_standard_adapter import (
    PaddleStandardOCRAdapter,
    convert_paddle_result_to_standard_ocr,
)

__all__ = [
    "AzureStandardOCRAdapter",
    "build_standard_ocr_from_azure_summary",
    "convert_azure_response_to_standard_ocr",
    "PaddleStandardOCRAdapter",
    "convert_paddle_result_to_standard_ocr",
]

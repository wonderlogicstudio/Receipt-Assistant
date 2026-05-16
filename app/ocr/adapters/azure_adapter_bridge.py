from __future__ import annotations

from typing import Any, Mapping

from app.core.standard_ocr import StandardOCRResult
from app.ocr.adapters.azure_standard_adapter import AzureStandardOCRAdapter


def build_standard_ocr_from_azure_summary(
    azure_summary: Mapping[str, Any],
    *,
    source_file_id: str | None = None,
    source_file_name: str | None = None,
    provider_version: str | None = None,
    diagnostic_code: str | None = None,
    warnings: list[str] | None = None,
) -> StandardOCRResult:
    """Prepare a StandardOCRResult from a sanitized Azure-like summary.

    This bridge is intentionally not wired into AzureProvider.extract(). It is
    a narrow 7-week-C handoff point for future Provider connection work.
    """

    return AzureStandardOCRAdapter().convert(
        azure_summary,
        source_file_id=source_file_id,
        source_file_name=source_file_name,
        provider_version=provider_version,
        diagnostic_code=diagnostic_code,
        warnings=warnings,
    )

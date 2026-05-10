from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.enums import OCRProviderName, OCRStatus


@dataclass(frozen=True)
class OCRResult:
    id: str
    source_file_id: str
    source_file_name: str
    stored_relative_path: str | None
    provider: str
    raw_text: str
    raw_json: dict[str, Any] | None = None
    confidence: float | None = None
    status: str = OCRStatus.COMPLETED.value
    error_message: str | None = None
    diagnostic_code: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def completed(
        cls,
        *,
        source_file_id: str,
        source_file_name: str,
        stored_relative_path: str | None,
        provider: OCRProviderName | str,
        raw_text: str,
        raw_json: dict[str, Any],
        confidence: float,
    ) -> "OCRResult":
        return cls(
            id=str(uuid4()),
            source_file_id=source_file_id,
            source_file_name=source_file_name,
            stored_relative_path=stored_relative_path,
            provider=str(provider),
            raw_text=raw_text,
            raw_json=raw_json,
            confidence=confidence,
            status=OCRStatus.COMPLETED.value,
        )

    @classmethod
    def skipped(
        cls,
        *,
        source_file_id: str,
        source_file_name: str,
        stored_relative_path: str | None,
        provider: OCRProviderName | str,
        error_message: str,
        diagnostic_code: str | None = None,
    ) -> "OCRResult":
        return cls(
            id=str(uuid4()),
            source_file_id=source_file_id,
            source_file_name=source_file_name,
            stored_relative_path=stored_relative_path,
            provider=str(provider),
            raw_text="",
            raw_json=None,
            confidence=None,
            status=OCRStatus.SKIPPED.value,
            error_message=error_message,
            diagnostic_code=diagnostic_code or "skipped",
        )

    @classmethod
    def failed(
        cls,
        *,
        source_file_id: str,
        source_file_name: str,
        stored_relative_path: str | None,
        provider: OCRProviderName | str,
        error_message: str,
        diagnostic_code: str | None = None,
    ) -> "OCRResult":
        return cls(
            id=str(uuid4()),
            source_file_id=source_file_id,
            source_file_name=source_file_name,
            stored_relative_path=stored_relative_path,
            provider=str(provider),
            raw_text="",
            raw_json=None,
            confidence=None,
            status=OCRStatus.FAILED.value,
            error_message=error_message,
            diagnostic_code=diagnostic_code or "ocr_failed",
        )

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class OCRResult:
    id: str
    source_file_id: str
    source_file_name: str
    provider: str
    raw_text: str
    raw_json: dict[str, Any] | None = None
    confidence: float | None = None
    status: str = "success"
    error_message: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def success(
        cls,
        *,
        source_file_name: str,
        provider: str,
        raw_text: str,
        raw_json: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> "OCRResult":
        return cls(
            id=str(uuid4()),
            source_file_id=str(uuid4()),
            source_file_name=source_file_name,
            provider=provider,
            raw_text=raw_text,
            raw_json=raw_json,
            confidence=confidence,
            status="success",
        )

    @classmethod
    def failed(
        cls,
        *,
        source_file_name: str,
        provider: str,
        error_message: str,
    ) -> "OCRResult":
        return cls(
            id=str(uuid4()),
            source_file_id=str(uuid4()),
            source_file_name=source_file_name,
            provider=provider,
            raw_text="",
            raw_json=None,
            confidence=None,
            status="failed",
            error_message=error_message,
        )


class OCRProvider(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> OCRResult:
        """Extract OCR text from a file path without exposing file contents."""


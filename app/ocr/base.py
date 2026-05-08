from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from app.core.ocr_models import OCRResult
from app.storage.file_store import StoredFileMetadata


OCRInput = Union[str, Path, StoredFileMetadata]


class OCRProvider(ABC):
    @abstractmethod
    def extract(self, source: OCRInput) -> OCRResult:
        """Extract OCR text from a file path without exposing file contents."""

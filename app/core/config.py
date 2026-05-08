from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_ALLOWED_UPLOAD_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".pdf", ".xlsx", ".csv"})
DEFAULT_MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True)
class AppConfig:
    upload_root: Path = Path("data/uploads")
    upload_relative_root: Path = Path("data/uploads")
    max_upload_size_bytes: int = DEFAULT_MAX_UPLOAD_SIZE_BYTES
    allowed_upload_extensions: frozenset[str] = field(default_factory=lambda: DEFAULT_ALLOWED_UPLOAD_EXTENSIONS)


def get_config() -> AppConfig:
    upload_root = Path(os.getenv("RECEIPT_ASSISTANT_UPLOAD_ROOT", "data/uploads"))
    max_upload_size_bytes = int(
        os.getenv("RECEIPT_ASSISTANT_MAX_UPLOAD_SIZE_BYTES", str(DEFAULT_MAX_UPLOAD_SIZE_BYTES))
    )
    return AppConfig(upload_root=upload_root, max_upload_size_bytes=max_upload_size_bytes)

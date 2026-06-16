from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_ALLOWED_UPLOAD_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".pdf", ".xlsx", ".csv"})
DEFAULT_MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024
DEFAULT_OCR_PROVIDER = "mock"
DEFAULT_AZURE_MODEL_ID = "prebuilt-receipt"
DEFAULT_AZURE_API_VERSION = "2024-11-30"
DEFAULT_OCR_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_AZURE_OCR_DEFAULT_POLL_INTERVAL_SECONDS = 1
DEFAULT_AZURE_OCR_MAX_POLL_INTERVAL_SECONDS = 10
DEFAULT_AZURE_OCR_MAX_POLL_ATTEMPTS = 30
DEFAULT_AZURE_OCR_MAX_RETRIES = 3
DEFAULT_AZURE_OCR_IGNORE_ENV_PROXY = False
DEFAULT_APP_DB_PATH = Path("data/app.db")
DEFAULT_OUTPUT_ROOT = Path("data/outputs")
DEFAULT_UPLOAD_RETENTION_DAYS = 7
DEFAULT_OUTPUT_RETENTION_DAYS = 7
DEFAULT_CLEANUP_DRY_RUN = True
DEFAULT_PADDLE_USE_GPU = False
DEFAULT_PADDLE_USE_ANGLE_CLS = False
DEFAULT_PADDLE_LANG = "korean"
DEFAULT_PADDLE_SHOW_LOG = False


@dataclass(frozen=True)
class AppConfig:
    upload_root: Path = Path("data/uploads")
    upload_relative_root: Path = Path("data/uploads")
    output_root: Path = DEFAULT_OUTPUT_ROOT
    app_db_path: Path = DEFAULT_APP_DB_PATH
    max_upload_size_bytes: int = DEFAULT_MAX_UPLOAD_SIZE_BYTES
    allowed_upload_extensions: frozenset[str] = field(default_factory=lambda: DEFAULT_ALLOWED_UPLOAD_EXTENSIONS)
    upload_retention_days: int = DEFAULT_UPLOAD_RETENTION_DAYS
    output_retention_days: int = DEFAULT_OUTPUT_RETENTION_DAYS
    cleanup_dry_run_default: bool = DEFAULT_CLEANUP_DRY_RUN
    ocr_provider: str = DEFAULT_OCR_PROVIDER
    azure_document_intelligence_endpoint: str | None = None
    azure_document_intelligence_key: str | None = None
    azure_document_intelligence_model_id: str = DEFAULT_AZURE_MODEL_ID
    azure_document_intelligence_api_version: str = DEFAULT_AZURE_API_VERSION
    ocr_request_timeout_seconds: int = DEFAULT_OCR_REQUEST_TIMEOUT_SECONDS
    azure_ocr_default_poll_interval_seconds: int = DEFAULT_AZURE_OCR_DEFAULT_POLL_INTERVAL_SECONDS
    azure_ocr_max_poll_interval_seconds: int = DEFAULT_AZURE_OCR_MAX_POLL_INTERVAL_SECONDS
    azure_ocr_max_poll_attempts: int = DEFAULT_AZURE_OCR_MAX_POLL_ATTEMPTS
    azure_ocr_max_retries: int = DEFAULT_AZURE_OCR_MAX_RETRIES
    azure_ocr_ignore_env_proxy: bool = DEFAULT_AZURE_OCR_IGNORE_ENV_PROXY
    paddle_use_gpu: bool = DEFAULT_PADDLE_USE_GPU
    paddle_use_angle_cls: bool = DEFAULT_PADDLE_USE_ANGLE_CLS
    paddle_lang: str = DEFAULT_PADDLE_LANG
    paddle_show_log: bool = DEFAULT_PADDLE_SHOW_LOG


def get_config() -> AppConfig:
    load_dotenv(dotenv_path=Path.cwd() / ".env")
    upload_root = Path(os.getenv("UPLOAD_DIR") or os.getenv("RECEIPT_ASSISTANT_UPLOAD_ROOT", "data/uploads"))
    output_root = Path(os.getenv("OUTPUT_DIR", str(DEFAULT_OUTPUT_ROOT)))
    app_db_path = Path(os.getenv("APP_DB_PATH", str(DEFAULT_APP_DB_PATH)))
    max_upload_size_bytes = int(
        os.getenv("RECEIPT_ASSISTANT_MAX_UPLOAD_SIZE_BYTES", str(DEFAULT_MAX_UPLOAD_SIZE_BYTES))
    )
    timeout_seconds = int(os.getenv("OCR_REQUEST_TIMEOUT_SECONDS", str(DEFAULT_OCR_REQUEST_TIMEOUT_SECONDS)))
    timeout_seconds = min(max(timeout_seconds, 1), DEFAULT_OCR_REQUEST_TIMEOUT_SECONDS)
    return AppConfig(
        upload_root=upload_root,
        upload_relative_root=Path("data/uploads"),
        output_root=output_root,
        app_db_path=app_db_path,
        max_upload_size_bytes=max_upload_size_bytes,
        upload_retention_days=_positive_int_env("UPLOAD_RETENTION_DAYS", DEFAULT_UPLOAD_RETENTION_DAYS),
        output_retention_days=_positive_int_env("OUTPUT_RETENTION_DAYS", DEFAULT_OUTPUT_RETENTION_DAYS),
        cleanup_dry_run_default=_bool_env("CLEANUP_DRY_RUN_DEFAULT", DEFAULT_CLEANUP_DRY_RUN),
        ocr_provider=os.getenv("OCR_PROVIDER", DEFAULT_OCR_PROVIDER).strip().lower() or DEFAULT_OCR_PROVIDER,
        azure_document_intelligence_endpoint=_optional_env("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
        azure_document_intelligence_key=_optional_env("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
        azure_document_intelligence_model_id=os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID",
            DEFAULT_AZURE_MODEL_ID,
        ).strip()
        or DEFAULT_AZURE_MODEL_ID,
        azure_document_intelligence_api_version=os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_API_VERSION",
            DEFAULT_AZURE_API_VERSION,
        ).strip()
        or DEFAULT_AZURE_API_VERSION,
        ocr_request_timeout_seconds=timeout_seconds,
        azure_ocr_default_poll_interval_seconds=_positive_int_env(
            "AZURE_OCR_DEFAULT_POLL_INTERVAL_SECONDS",
            DEFAULT_AZURE_OCR_DEFAULT_POLL_INTERVAL_SECONDS,
        ),
        azure_ocr_max_poll_interval_seconds=_positive_int_env(
            "AZURE_OCR_MAX_POLL_INTERVAL_SECONDS",
            DEFAULT_AZURE_OCR_MAX_POLL_INTERVAL_SECONDS,
        ),
        azure_ocr_max_poll_attempts=_positive_int_env(
            "AZURE_OCR_MAX_POLL_ATTEMPTS",
            DEFAULT_AZURE_OCR_MAX_POLL_ATTEMPTS,
        ),
        azure_ocr_max_retries=_positive_int_env(
            "AZURE_OCR_MAX_RETRIES",
            DEFAULT_AZURE_OCR_MAX_RETRIES,
        ),
        azure_ocr_ignore_env_proxy=_bool_env(
            "AZURE_OCR_IGNORE_ENV_PROXY",
            DEFAULT_AZURE_OCR_IGNORE_ENV_PROXY,
        ),
        paddle_use_gpu=_bool_env("PADDLE_USE_GPU", DEFAULT_PADDLE_USE_GPU),
        paddle_use_angle_cls=_bool_env("PADDLE_USE_ANGLE_CLS", DEFAULT_PADDLE_USE_ANGLE_CLS),
        paddle_lang=os.getenv("PADDLE_LANG", DEFAULT_PADDLE_LANG).strip() or DEFAULT_PADDLE_LANG,
        paddle_show_log=_bool_env("PADDLE_SHOW_LOG", DEFAULT_PADDLE_SHOW_LOG),
    )


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value.strip())
    except ValueError:
        return default
    return value if value > 0 else default


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default

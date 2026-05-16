from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


FORBIDDEN_PAYLOAD_KEYS = {
    "analyze_result",
    "headers",
    "operation_location",
    "raw_json",
    "raw_response",
    "raw_text",
    "provider_raw_json",
    "provider_raw_response",
    "read_result",
    "full_ocr_text",
}
FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "secret",
    "token",
    "password",
    "endpoint",
}
ABSOLUTE_PATH_PATTERNS = (
    r"[A-Za-z]:\\",
    "/Users/",
    "/home/",
    "/var/",
    "/tmp/",
)


class StandardOCRTextBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_index: int
    block_id: str
    text: str
    normalized_text: str | None = None
    confidence: float | None = None
    bbox: list[float] | None = None
    line_order: int | None = None
    block_type: str | None = None
    sensitive_category: str | None = None

    @field_validator("page_index")
    @classmethod
    def validate_page_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("page_index must be greater than or equal to 0")
        return value

    @field_validator("block_id")
    @classmethod
    def validate_block_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("block_id must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float | None) -> float | None:
        return _validate_confidence(value)

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, value: list[float] | None) -> list[float] | None:
        if value is None:
            return value
        if len(value) not in {4, 8}:
            raise ValueError("bbox must contain 4 or 8 numeric values")
        return value

    @field_validator("line_order")
    @classmethod
    def validate_line_order(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("line_order must be greater than or equal to 0")
        return value


class StandardOCRKeyValueCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    value: str | None = None
    normalized_value: str | None = None
    confidence: float | None = None
    source_block_ids: list[str] = Field(default_factory=list)
    candidate_type: str | None = None

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("key must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float | None) -> float | None:
        return _validate_confidence(value)


class StandardOCRTableCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_index: int
    table_id: str
    rows: list[list[str]] = Field(default_factory=list)
    confidence: float | None = None
    source_block_ids: list[str] = Field(default_factory=list)

    @field_validator("page_index")
    @classmethod
    def validate_page_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("page_index must be greater than or equal to 0")
        return value

    @field_validator("table_id")
    @classmethod
    def validate_table_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("table_id must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float | None) -> float | None:
        return _validate_confidence(value)


class StandardOCRPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_index: int
    width: float | None = None
    height: float | None = None
    unit: str | None = None
    text_blocks: list[StandardOCRTextBlock] = Field(default_factory=list)
    key_value_candidates: list[StandardOCRKeyValueCandidate] = Field(default_factory=list)
    table_candidates: list[StandardOCRTableCandidate] = Field(default_factory=list)

    @field_validator("page_index")
    @classmethod
    def validate_page_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("page_index must be greater than or equal to 0")
        return value

    @field_validator("width", "height")
    @classmethod
    def validate_dimension(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("page dimensions must be greater than 0")
        return value


class StandardOCRResult(BaseModel):
    """Provider-independent OCR input contract for future parser adapters.

    This model intentionally does not include provider raw JSON, full OCR text,
    absolute local paths, or DB storage paths. 6-week-C/8-week work can add
    mappers around this contract without changing existing OCRResult flows.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    source_file_id: str | None = None
    source_file_name: str | None = None
    provider: str
    provider_version: str | None = None
    engine_runtime: str | None = None
    status: str
    pages: list[StandardOCRPage] = Field(default_factory=list)
    safe_text_summary: str | None = None
    text_blocks: list[StandardOCRTextBlock] = Field(default_factory=list)
    key_value_candidates: list[StandardOCRKeyValueCandidate] = Field(default_factory=list)
    table_candidates: list[StandardOCRTableCandidate] = Field(default_factory=list)
    provider_fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
    diagnostic_code: str | None = None
    created_at: datetime

    @field_validator("id", "provider", "status")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required text fields must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float | None) -> float | None:
        return _validate_confidence(value)

    @field_validator("source_file_name")
    @classmethod
    def validate_source_file_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if has_absolute_path_risk(value) or "/" in value or "\\" in value:
            raise ValueError("source_file_name must be a file name, not a path")
        return value

    @field_validator("safe_text_summary")
    @classmethod
    def validate_safe_text_summary(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 1000:
            raise ValueError("safe_text_summary must be 1000 characters or fewer")
        return value

    @model_validator(mode="after")
    def validate_no_forbidden_payload(self) -> "StandardOCRResult":
        assert_no_forbidden_ocr_payload(self.model_dump(mode="json"))
        return self


def has_raw_payload_risk(data: Any) -> bool:
    return _contains_forbidden_key(data, FORBIDDEN_PAYLOAD_KEYS)


def has_absolute_path_risk(data: Any) -> bool:
    for text in _iter_strings(data):
        if any(re.search(pattern, text) for pattern in ABSOLUTE_PATH_PATTERNS):
            return True
    return False


def has_sensitive_secret_risk(data: Any) -> bool:
    if _contains_forbidden_key(data, FORBIDDEN_SECRET_KEYS):
        return True
    for text in _iter_strings(data):
        lower_text = text.lower()
        if any(f"{key}=" in lower_text for key in FORBIDDEN_SECRET_KEYS):
            return True
    return False


def assert_no_forbidden_ocr_payload(data: Any) -> None:
    if has_raw_payload_risk(data):
        raise ValueError("OCR raw payload fields are not allowed in StandardOCRResult")
    if has_absolute_path_risk(data):
        raise ValueError("absolute local paths are not allowed in StandardOCRResult")
    if has_sensitive_secret_risk(data):
        raise ValueError("secrets are not allowed in StandardOCRResult")


def _validate_confidence(value: float | None) -> float | None:
    if value is not None and not 0 <= value <= 1:
        raise ValueError("confidence must be between 0 and 1")
    return value


def _contains_forbidden_key(data: Any, forbidden_keys: set[str]) -> bool:
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in forbidden_keys:
                return True
            if _contains_forbidden_key(value, forbidden_keys):
                return True
    elif isinstance(data, list):
        return any(_contains_forbidden_key(item, forbidden_keys) for item in data)
    return False


def _iter_strings(data: Any) -> list[str]:
    if isinstance(data, str):
        return [data]
    if isinstance(data, dict):
        result: list[str] = []
        for key, value in data.items():
            result.extend(_iter_strings(str(key)))
            result.extend(_iter_strings(value))
        return result
    if isinstance(data, list):
        result = []
        for item in data:
            result.extend(_iter_strings(item))
        return result
    return []

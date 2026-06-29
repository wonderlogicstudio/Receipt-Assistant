from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.standard_ocr import StandardOCRResult, assert_no_forbidden_ocr_payload
from app.parser.address_hint import extract_address_hint_from_safe_lines


AMOUNT_CANDIDATE_TYPES = {
    "total_amount",
    "gross_amount",
    "discount_amount",
    "final_amount",
    "paid_amount",
    "supply_amount",
    "vat_amount",
}
REVIEW_HINT_CANDIDATE_TYPES = {
    "vat_missing",
    "vat_review_hint",
    "sensitive_hint",
}


class StandardOCRParserContext(BaseModel):
    """Safe intermediate shape for future ReceiptParser migration.

    This context is not wired into the current app flow. It exists to define
    the boundary between Provider Adapters and the future parser input.
    """

    model_config = ConfigDict(extra="forbid")

    source_file_name: str | None = None
    provider: str
    status: str
    safe_text_lines: list[str] = Field(default_factory=list)
    candidate_map: dict[str, list[str]] = Field(default_factory=dict)
    amount_candidate_map: dict[str, list[str]] = Field(default_factory=dict)
    non_amount_candidate_map: dict[str, list[str]] = Field(default_factory=dict)
    review_hints: list[str] = Field(default_factory=list)
    sensitive_categories: list[str] = Field(default_factory=list)
    address_hint: dict[str, str | None] | None = None
    diagnostic_code: str | None = None

    @model_validator(mode="after")
    def validate_safe_payload(self) -> "StandardOCRParserContext":
        assert_no_forbidden_ocr_payload(self.model_dump(mode="json"))
        return self


def build_parser_context_from_standard_ocr(result: StandardOCRResult) -> StandardOCRParserContext:
    candidate_map = extract_candidate_map(result)
    safe_text_lines = get_text_lines_for_parser(result)
    address_hint = extract_address_hint_from_safe_lines(safe_text_lines)
    context = StandardOCRParserContext(
        source_file_name=result.source_file_name,
        provider=result.provider,
        status=result.status,
        safe_text_lines=safe_text_lines,
        candidate_map=candidate_map,
        amount_candidate_map=_filter_amount_candidate_map(candidate_map),
        non_amount_candidate_map=_filter_non_amount_candidate_map(candidate_map),
        review_hints=get_review_hints_from_standard_ocr(result),
        sensitive_categories=_unique(
            [
                _safe_sensitive_category(block.sensitive_category)
                for block in result.text_blocks
                if block.sensitive_category
            ]
        ),
        address_hint=address_hint.as_dict() if address_hint is not None else None,
        diagnostic_code=result.diagnostic_code,
    )
    assert_no_forbidden_ocr_payload(context.model_dump(mode="json"))
    return context


def extract_candidate_map(result: StandardOCRResult) -> dict[str, list[str]]:
    candidate_map: dict[str, list[str]] = {}
    for candidate in result.key_value_candidates:
        candidate_type = _candidate_type(candidate.candidate_type, candidate.key)
        value = _candidate_value(candidate.normalized_value, candidate.value)
        if candidate_type == "sensitive_hint":
            value = _safe_sensitive_category(value)
        if value is None:
            continue
        candidate_map.setdefault(candidate_type, []).append(value)
    return {key: _unique(values) for key, values in candidate_map.items()}


def extract_amount_candidate_map(result: StandardOCRResult) -> dict[str, list[str]]:
    return _filter_amount_candidate_map(extract_candidate_map(result))


def extract_non_amount_candidate_map(result: StandardOCRResult) -> dict[str, list[str]]:
    return _filter_non_amount_candidate_map(extract_candidate_map(result))


def _filter_amount_candidate_map(candidate_map: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        key: values
        for key, values in candidate_map.items()
        if key in AMOUNT_CANDIDATE_TYPES
    }


def _filter_non_amount_candidate_map(candidate_map: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        key: values
        for key, values in candidate_map.items()
        if key not in AMOUNT_CANDIDATE_TYPES
    }


def get_text_lines_for_parser(result: StandardOCRResult) -> list[str]:
    safe_lines: list[str] = []
    blocks = sorted(
        result.text_blocks,
        key=lambda block: (
            block.page_index,
            block.line_order if block.line_order is not None else 10**9,
            block.block_id,
        ),
    )
    for block in blocks:
        if block.sensitive_category:
            safe_lines.append("[REDACTED]")
            continue
        text = block.normalized_text or block.text
        if text:
            safe_lines.append(text)
    return safe_lines


def get_review_hints_from_standard_ocr(result: StandardOCRResult) -> list[str]:
    hints: list[str] = list(result.warnings)
    if result.status != "completed":
        hints.append(f"ocr_status:{result.status}")
    if result.diagnostic_code and result.status != "completed":
        hints.append(f"diagnostic_code:{result.diagnostic_code}")
    for candidate in result.key_value_candidates:
        candidate_type = _candidate_type(candidate.candidate_type, candidate.key)
        if candidate_type in REVIEW_HINT_CANDIDATE_TYPES:
            value = _candidate_value(candidate.normalized_value, candidate.value)
            if candidate_type == "sensitive_hint":
                value = _safe_sensitive_category(value)
            hints.append(candidate_type if value is None else f"{candidate_type}:{value}")
    for block in result.text_blocks:
        if block.sensitive_category:
            hints.append(f"sensitive_category:{_safe_sensitive_category(block.sensitive_category)}")
    return _unique(hints)


def compare_parser_context_shape(
    left: StandardOCRParserContext,
    right: StandardOCRParserContext,
) -> dict[str, object]:
    left_candidate_types = set(left.candidate_map)
    right_candidate_types = set(right.candidate_map)
    left_amount_types = set(left.amount_candidate_map)
    right_amount_types = set(right.amount_candidate_map)
    left_non_amount_types = set(left.non_amount_candidate_map)
    right_non_amount_types = set(right.non_amount_candidate_map)

    return {
        "left_provider": left.provider,
        "right_provider": right.provider,
        "left_candidate_types": sorted(left_candidate_types),
        "right_candidate_types": sorted(right_candidate_types),
        "shared_candidate_types": sorted(left_candidate_types & right_candidate_types),
        "left_only_candidate_types": sorted(left_candidate_types - right_candidate_types),
        "right_only_candidate_types": sorted(right_candidate_types - left_candidate_types),
        "left_amount_candidate_types": sorted(left_amount_types),
        "right_amount_candidate_types": sorted(right_amount_types),
        "shared_amount_candidate_types": sorted(left_amount_types & right_amount_types),
        "left_non_amount_candidate_types": sorted(left_non_amount_types),
        "right_non_amount_candidate_types": sorted(right_non_amount_types),
        "shared_non_amount_candidate_types": sorted(left_non_amount_types & right_non_amount_types),
        "left_review_hint_count": len(left.review_hints),
        "right_review_hint_count": len(right.review_hints),
        "left_sensitive_categories": sorted(left.sensitive_categories),
        "right_sensitive_categories": sorted(right.sensitive_categories),
    }


def _candidate_type(candidate_type: str | None, fallback_key: str) -> str:
    return str(candidate_type or fallback_key).strip()


def _candidate_value(normalized_value: str | None, value: str | None) -> str | None:
    selected = normalized_value if normalized_value is not None else value
    if selected is None:
        return None
    text = str(selected).strip()
    return text or None


def _safe_sensitive_category(value: str | None) -> str | None:
    if value is None:
        return None
    return str(value).replace("password", "credential")


def _unique(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result

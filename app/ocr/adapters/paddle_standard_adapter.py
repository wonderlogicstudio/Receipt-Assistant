"""Sanitized PaddleOCR-like result to StandardOCRResult adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping
from uuid import uuid4

from app.core.standard_ocr import (
    StandardOCRKeyValueCandidate,
    StandardOCRPage,
    StandardOCRResult,
    StandardOCRTableCandidate,
    StandardOCRTextBlock,
    assert_no_forbidden_ocr_payload,
)


class PaddleStandardOCRAdapter:
    """Convert sanitized PaddleOCR-like mappings into StandardOCRResult."""

    adapter_version = "paddle-standard-adapter-v1"
    provider_name = "paddleocr"

    def convert(
        self,
        paddle_result: Mapping[str, Any],
        *,
        source_file_id: str | None = None,
        source_file_name: str | None = None,
        provider_version: str | None = None,
        diagnostic_code: str | None = None,
        warnings: list[str] | None = None,
    ) -> StandardOCRResult:
        payload = dict(paddle_result)
        assert_no_forbidden_ocr_payload(payload)
        _assert_no_paddle_forbidden_payload(payload)

        pages = [_page_from_mapping(page) for page in _as_list(payload.get("pages"))]
        lines = list(_iter_lines(payload))
        text_blocks = [_text_block_from_line(line, index) for index, line in enumerate(lines)]
        text_blocks.sort(key=lambda block: (block.page_index, block.line_order))

        candidates = [
            _candidate_from_mapping(candidate)
            for candidate in _as_list(payload.get("key_value_candidates"))
        ]
        tables = [_table_from_mapping(table) for table in _as_list(payload.get("tables"))]

        combined_warnings = list(warnings or [])
        combined_warnings.extend(str(item) for item in _as_list(payload.get("warnings")))
        status = _status(payload.get("status"))
        if status in {"failed", "partial", "skipped"}:
            combined_warnings.append(f"paddle_status:{status}")
        if any(block.sensitive_category for block in text_blocks):
            combined_warnings.append("sensitive_text_redacted")
        if any(block.confidence is not None and block.confidence < 0.75 for block in text_blocks):
            combined_warnings.append("paddle_low_confidence")

        if not pages and text_blocks:
            page_indexes = sorted({block.page_index for block in text_blocks})
            pages = [StandardOCRPage(page_index=page_index) for page_index in page_indexes]

        provider_fields = {
            "provider_family": "paddleocr",
            "engine": _string(payload.get("engine")) or "paddleocr",
            "engine_runtime": "pc_local",
            "adapter_version": self.adapter_version,
            "language_hint": _string(payload.get("language_hint")),
            "page_count": len(pages),
            "image_count": _int(payload.get("image_count"), default=1),
            "normalized_block_count": len(text_blocks),
            "normalized_candidate_count": len(candidates),
            "normalized_table_count": len(tables),
            "has_angle_classifier": bool(payload.get("has_angle_classifier", False)),
            "has_gpu": bool(payload.get("has_gpu", False)),
            "input_type": _string(payload.get("input_type")) or "image",
        }
        runtime_provider = _safe_token(payload.get("provider"))
        if runtime_provider:
            provider_fields["provider"] = runtime_provider
        device = _safe_token(payload.get("device"))
        if device:
            provider_fields["device"] = device
        if "cuda_compiled" in payload:
            provider_fields["cuda_compiled"] = payload.get("cuda_compiled")
        image_extension = _safe_extension(payload.get("image_extension"))
        if image_extension:
            provider_fields["image_extension"] = image_extension
        for key in ("init_elapsed_ms", "ocr_elapsed_ms", "total_elapsed_ms"):
            if key in payload:
                provider_fields[key] = _non_negative_int(payload.get(key))
        runtime_status = _safe_token(payload.get("runtime_status"))
        if runtime_status:
            provider_fields["status"] = runtime_status
        runtime_diagnostic_code = _safe_token(payload.get("runtime_diagnostic_code"))
        if runtime_diagnostic_code:
            provider_fields["diagnostic_code"] = runtime_diagnostic_code
        diagnostic_detail_code = _string(payload.get("diagnostic_detail_code"))
        if diagnostic_detail_code:
            provider_fields["diagnostic_detail_code"] = diagnostic_detail_code

        return StandardOCRResult(
            id=str(payload.get("id") or f"paddle-standard-{uuid4().hex}"),
            source_file_id=source_file_id or _string(payload.get("source_file_id")),
            source_file_name=_safe_file_name(source_file_name or _string(payload.get("source_file_name"))),
            provider=self.provider_name,
            provider_version=provider_version or _string(payload.get("engine_version")),
            engine_runtime="pc_local",
            status=status,
            confidence=_confidence(payload.get("confidence")),
            pages=pages,
            text_blocks=text_blocks,
            key_value_candidates=candidates,
            table_candidates=tables,
            warnings=_unique(combined_warnings),
            diagnostic_code=diagnostic_code or _string(payload.get("diagnostic_code")),
            safe_text_summary=_safe_text_summary(text_blocks),
            provider_fields=provider_fields,
            created_at=_created_at(payload.get("created_at")) or datetime.utcnow(),
        )


def convert_paddle_result_to_standard_ocr(
    paddle_result: Mapping[str, Any],
    **kwargs: Any,
) -> StandardOCRResult:
    return PaddleStandardOCRAdapter().convert(paddle_result, **kwargs)


def _iter_lines(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for line in _as_list(payload.get("lines")):
        if isinstance(line, Mapping):
            yield line
    for page in _as_list(payload.get("pages")):
        if not isinstance(page, Mapping):
            continue
        for line in _as_list(page.get("lines")):
            if isinstance(line, Mapping):
                enriched = dict(line)
                enriched.setdefault("page_index", page.get("page_index"))
                yield enriched


def _page_from_mapping(page: Any) -> StandardOCRPage:
    if not isinstance(page, Mapping):
        return StandardOCRPage(page_index=0)
    return StandardOCRPage(
        page_index=_int(page.get("page_index"), default=0),
        width=_float(page.get("width")),
        height=_float(page.get("height")),
        unit=_string(page.get("unit")),
    )


def _text_block_from_line(line: Mapping[str, Any], index: int) -> StandardOCRTextBlock:
    sensitive_category = _string(line.get("sensitive_category"))
    text = "[REDACTED]" if sensitive_category else (_string(line.get("text")) or "")
    normalized_text = "[REDACTED]" if sensitive_category else (
        _string(line.get("normalized_text")) or text
    )
    return StandardOCRTextBlock(
        block_id=_string(line.get("block_id")) or f"paddle-p{_int(line.get('page_index'), 0)}-l{index}",
        page_index=_int(line.get("page_index"), default=0),
        text=text,
        normalized_text=normalized_text,
        confidence=_confidence(line.get("confidence")),
        bbox=_bbox(line.get("bbox") or line.get("polygon") or line.get("box")),
        line_order=_int(line.get("line_order"), default=index),
        block_type=_string(line.get("block_type")) or "line",
        sensitive_category=sensitive_category,
    )


def _candidate_from_mapping(candidate: Any) -> StandardOCRKeyValueCandidate:
    mapping = candidate if isinstance(candidate, Mapping) else {}
    candidate_type = _string(mapping.get("candidate_type")) or _string(mapping.get("key")) or "unknown"
    value = _string(mapping.get("value"))
    normalized_value = _string(mapping.get("normalized_value")) or value
    if candidate_type == "sensitive_hint":
        value = "[REDACTED]"
        normalized_value = _string(mapping.get("sensitive_category")) or normalized_value or "[REDACTED]"
    return StandardOCRKeyValueCandidate(
        key=_string(mapping.get("key")),
        value=value,
        normalized_value=normalized_value,
        candidate_type=candidate_type,
        confidence=_confidence(mapping.get("confidence")),
        source_block_ids=[str(item) for item in _as_list(mapping.get("source_block_ids"))],
    )


def _table_from_mapping(table: Any) -> StandardOCRTableCandidate:
    mapping = table if isinstance(table, Mapping) else {}
    rows = mapping.get("rows")
    safe_rows = rows if isinstance(rows, list) else []
    return StandardOCRTableCandidate(
        table_id=_string(mapping.get("table_id")) or "paddle-table-0",
        page_index=_int(mapping.get("page_index"), default=0),
        rows=safe_rows,
        confidence=_confidence(mapping.get("confidence")),
        source_block_ids=[str(item) for item in _as_list(mapping.get("source_block_ids"))],
    )


def _bbox(value: Any) -> list[float] | None:
    if value is None:
        return None
    flattened: list[Any] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, list):
                flattened.extend(item)
            elif isinstance(item, Mapping):
                flattened.extend([item.get("x"), item.get("y")])
            else:
                flattened.append(item)
    else:
        return None
    numbers = [_float(item) for item in flattened]
    numbers = [item for item in numbers if item is not None]
    if len(numbers) in {4, 8}:
        return numbers
    return None


def _confidence(value: Any) -> float | None:
    number = _float(value)
    if number is None:
        return None
    if 0 <= number <= 1:
        return number
    if 1 < number <= 100:
        return round(number / 100, 4)
    return None


def _created_at(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _safe_text_summary(text_blocks: list[StandardOCRTextBlock]) -> str | None:
    lines = [block.normalized_text or block.text for block in text_blocks[:12]]
    lines = [line for line in lines if line]
    return "\n".join(lines) if lines else None


def _safe_file_name(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("\\", "/").split("/")[-1]


def _status(value: Any) -> str:
    normalized = _string(value)
    if normalized in {"succeeded", "success", "completed"}:
        return "completed"
    if normalized in {"failed", "partial", "skipped"}:
        return normalized
    return "completed"


def _string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_token(value: Any) -> str | None:
    text = _string(value)
    if not text:
        return None
    text = "".join(char if char.isalnum() or char in {"_", "-", ":", "."} else "_" for char in text.lower())
    return text[:80] or None


def _safe_extension(value: Any) -> str | None:
    text = _string(value)
    if not text:
        return None
    text = text.lower()
    if not text.startswith("."):
        text = f".{text}"
    if len(text) <= 9 and text[1:].isalnum():
        return text
    return None


def _non_negative_int(value: Any) -> int:
    number = _int(value, default=0)
    return number if number >= 0 else 0


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _assert_no_paddle_forbidden_payload(value: Any) -> None:
    forbidden_keys = {
        "absolute_path",
        "api_key",
        "endpoint",
        "full_ocr_text",
        "headers",
        "image_path",
        "local_file_path",
        "model_path",
        "password",
        "paddle_raw_output",
        "provider_raw_response",
        "raw_json",
        "raw_response",
        "raw_text",
        "secret",
        "token",
    }
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = str(key).lower()
            if normalized_key in forbidden_keys:
                raise ValueError(f"Forbidden PaddleOCR payload key: {key}")
            _assert_no_paddle_forbidden_payload(nested_value)
    elif isinstance(value, list):
        for item in value:
            _assert_no_paddle_forbidden_payload(item)

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from uuid import uuid4

from app.core.standard_ocr import (
    StandardOCRKeyValueCandidate,
    StandardOCRPage,
    StandardOCRResult,
    StandardOCRTableCandidate,
    StandardOCRTextBlock,
    assert_no_forbidden_ocr_payload,
)


AMOUNT_CANDIDATE_TYPES = {
    "total_amount",
    "gross_amount",
    "discount_amount",
    "final_amount",
    "paid_amount",
    "supply_amount",
    "vat_amount",
}

KEY_TO_CANDIDATE_TYPE = {
    "merchant": "merchant_name",
    "merchant_name": "merchant_name",
    "store_name": "merchant_name",
    "transaction_date": "transaction_date",
    "date": "transaction_date",
    "business_number": "business_number",
    "biz_number": "business_number",
    "total": "total_amount",
    "total_amount": "total_amount",
    "gross_amount": "gross_amount",
    "discount_amount": "discount_amount",
    "final_amount": "final_amount",
    "paid_amount": "paid_amount",
    "supply_amount": "supply_amount",
    "vat": "vat_amount",
    "vat_amount": "vat_amount",
    "vat_missing": "vat_missing",
    "vat_review_hint": "vat_review_hint",
    "payment_method": "payment_method",
    "approval_number": "approval_number",
    "quantity": "quantity",
    "footer_number": "footer_number",
    "sensitive_hint": "sensitive_hint",
}

STATUS_MAP = {
    "succeeded": "completed",
    "success": "completed",
    "completed": "completed",
    "failed": "failed",
    "partial": "partial",
    "skipped": "skipped",
}


class AzureStandardOCRAdapter:
    """Convert sanitized Azure-like OCR mappings into StandardOCRResult.

    This adapter deliberately accepts plain Mapping data only. It does not call
    Azure, import Azure SDK objects, or change the existing AzureProvider flow.
    """

    adapter_version = "azure-standard-adapter-v1"

    def convert(
        self,
        azure_response: Mapping[str, Any],
        *,
        source_file_id: str | None = None,
        source_file_name: str | None = None,
        provider_version: str | None = None,
        diagnostic_code: str | None = None,
        warnings: list[str] | None = None,
    ) -> StandardOCRResult:
        assert_no_forbidden_ocr_payload(dict(azure_response))

        pages = self._build_pages(azure_response)
        text_blocks = self._build_text_blocks(azure_response)
        key_value_candidates = self._build_key_value_candidates(azure_response)
        table_candidates = self._build_table_candidates(azure_response)
        result_warnings = self._build_warnings(azure_response, warnings, text_blocks)
        result_diagnostic_code = str(
            diagnostic_code or azure_response.get("diagnostic_code") or ""
        ).strip() or None

        provider_fields = self._build_provider_fields(
            azure_response,
            page_count=len(pages),
            block_count=len(text_blocks),
            candidate_count=len(key_value_candidates),
            table_count=len(table_candidates),
        )

        result = StandardOCRResult(
            id=str(azure_response.get("id") or f"azure-standard-{uuid4().hex}"),
            source_file_id=source_file_id,
            source_file_name=source_file_name,
            provider="azure",
            provider_version=provider_version or _optional_text(azure_response.get("api_version")),
            engine_runtime="server",
            status=_normalize_status(azure_response.get("status")),
            pages=pages,
            safe_text_summary=_safe_summary(text_blocks),
            text_blocks=text_blocks,
            key_value_candidates=key_value_candidates,
            table_candidates=table_candidates,
            provider_fields=provider_fields,
            confidence=_average_confidence(
                [
                    *(block.confidence for block in text_blocks),
                    *(candidate.confidence for candidate in key_value_candidates),
                    *(table.confidence for table in table_candidates),
                ]
            ),
            warnings=result_warnings,
            diagnostic_code=result_diagnostic_code,
            created_at=_parse_created_at(azure_response.get("created_at")),
        )
        assert_no_forbidden_ocr_payload(result.model_dump(mode="json"))
        return result

    def _build_pages(self, azure_response: Mapping[str, Any]) -> list[StandardOCRPage]:
        pages: list[StandardOCRPage] = []
        for page_index, page in enumerate(_mapping_list(azure_response.get("pages"))):
            pages.append(
                StandardOCRPage(
                    page_index=_int_or_default(page.get("page_index"), page_index),
                    width=_positive_float(page.get("width")),
                    height=_positive_float(page.get("height")),
                    unit=_optional_text(page.get("unit")),
                )
            )
        return pages

    def _build_text_blocks(self, azure_response: Mapping[str, Any]) -> list[StandardOCRTextBlock]:
        blocks: list[StandardOCRTextBlock] = []
        for page_index, page in enumerate(_mapping_list(azure_response.get("pages"))):
            normalized_page_index = _int_or_default(page.get("page_index"), page_index)
            lines = _mapping_list(page.get("lines"))
            for line_index, line in enumerate(lines):
                blocks.append(
                    _text_block_from_line(
                        line,
                        page_index=normalized_page_index,
                        line_index=line_index,
                        fallback_block_id=f"p{normalized_page_index}-l{line_index}",
                    )
                )

        for line_index, line in enumerate(_mapping_list(azure_response.get("safe_content_lines"))):
            page_index = _int_or_default(line.get("page_index"), 0)
            blocks.append(
                _text_block_from_line(
                    line,
                    page_index=page_index,
                    line_index=len(blocks) + line_index,
                    fallback_block_id=f"safe-{page_index}-{line_index}",
                )
            )

        return sorted(
            blocks,
            key=lambda block: (
                block.page_index,
                block.line_order if block.line_order is not None else 10**9,
                block.block_id,
            ),
        )

    def _build_key_value_candidates(
        self,
        azure_response: Mapping[str, Any],
    ) -> list[StandardOCRKeyValueCandidate]:
        candidates: list[StandardOCRKeyValueCandidate] = []
        for document in _mapping_list(azure_response.get("documents")):
            fields = document.get("fields")
            if isinstance(fields, Mapping):
                for key, field in fields.items():
                    if isinstance(field, Mapping):
                        candidates.append(_candidate_from_mapping(str(key), field))

        for item in _mapping_list(azure_response.get("key_value_pairs")):
            key = str(item.get("key") or item.get("name") or item.get("candidate_type") or "").strip()
            if key:
                candidates.append(_candidate_from_mapping(key, item))
        return candidates

    def _build_table_candidates(
        self,
        azure_response: Mapping[str, Any],
    ) -> list[StandardOCRTableCandidate]:
        tables: list[StandardOCRTableCandidate] = []
        for table_index, table in enumerate(_mapping_list(azure_response.get("tables"))):
            rows = table.get("rows") if isinstance(table.get("rows"), list) else []
            sanitized_rows = [[str(cell) for cell in row] for row in rows if isinstance(row, list)]
            tables.append(
                StandardOCRTableCandidate(
                    page_index=_int_or_default(table.get("page_index"), 0),
                    table_id=str(table.get("table_id") or f"azure-table-{table_index}"),
                    rows=sanitized_rows,
                    confidence=_confidence(table.get("confidence")),
                    source_block_ids=_string_list(table.get("source_block_ids")),
                )
            )
        return tables

    def _build_provider_fields(
        self,
        azure_response: Mapping[str, Any],
        *,
        page_count: int,
        block_count: int,
        candidate_count: int,
        table_count: int,
    ) -> dict[str, Any]:
        provider_fields = {
            "provider_family": "azure",
            "api_model": _optional_text(azure_response.get("model_id")),
            "api_version": _optional_text(azure_response.get("api_version")),
            "document_type": _optional_text(azure_response.get("document_type")),
            "page_count": page_count,
            "has_key_value_pairs": candidate_count > 0,
            "has_tables": table_count > 0,
            "has_styles": bool(azure_response.get("has_styles", False)),
            "locale_hint": _optional_text(azure_response.get("locale_hint")),
            "adapter_version": self.adapter_version,
            "normalized_block_count": block_count,
            "normalized_candidate_count": candidate_count,
            "normalized_table_count": table_count,
        }
        return {key: value for key, value in provider_fields.items() if value is not None}

    def _build_warnings(
        self,
        azure_response: Mapping[str, Any],
        warnings: list[str] | None,
        text_blocks: list[StandardOCRTextBlock],
    ) -> list[str]:
        result: list[str] = []
        result.extend(_string_list(azure_response.get("warnings")))
        if warnings:
            result.extend(str(warning) for warning in warnings if str(warning).strip())
        if azure_response.get("status") in {"partial", "failed"}:
            result.append(f"azure_status:{_normalize_status(azure_response.get('status'))}")
        if not text_blocks and _normalize_status(azure_response.get("status")) == "completed":
            result.append("no_text_blocks")
        for block in text_blocks:
            if block.sensitive_category:
                result.append("sensitive_text_redacted")
                break
        return _unique(result)


def convert_azure_response_to_standard_ocr(
    azure_response: Mapping[str, Any],
    *,
    source_file_id: str | None = None,
    source_file_name: str | None = None,
    provider_version: str | None = None,
    diagnostic_code: str | None = None,
    warnings: list[str] | None = None,
) -> StandardOCRResult:
    return AzureStandardOCRAdapter().convert(
        azure_response,
        source_file_id=source_file_id,
        source_file_name=source_file_name,
        provider_version=provider_version,
        diagnostic_code=diagnostic_code,
        warnings=warnings,
    )


def _text_block_from_line(
    line: Mapping[str, Any],
    *,
    page_index: int,
    line_index: int,
    fallback_block_id: str,
) -> StandardOCRTextBlock:
    sensitive_category = _safe_sensitive_category(line.get("sensitive_category"))
    text = str(line.get("text") or "").strip()
    normalized_text = _optional_text(line.get("normalized_text"))
    if sensitive_category:
        text = "[REDACTED]"
        normalized_text = "[REDACTED]"
    return StandardOCRTextBlock(
        page_index=page_index,
        block_id=str(line.get("block_id") or line.get("line_id") or fallback_block_id),
        text=text,
        normalized_text=normalized_text,
        confidence=_confidence(line.get("confidence")),
        bbox=_bbox(line.get("bbox") or line.get("polygon")),
        line_order=_int_or_default(line.get("line_order"), line_index),
        block_type=_optional_text(line.get("block_type")) or "line",
        sensitive_category=sensitive_category,
    )


def _candidate_from_mapping(key: str, field: Mapping[str, Any]) -> StandardOCRKeyValueCandidate:
    candidate_type = _candidate_type(
        field.get("candidate_type")
        or field.get("type")
        or KEY_TO_CANDIDATE_TYPE.get(key.strip().lower())
        or key.strip().lower()
    )
    value = _optional_text(field.get("value") if "value" in field else field.get("content"))
    normalized_value = _optional_text(field.get("normalized_value"))
    if candidate_type == "sensitive_hint":
        value = "[REDACTED]"
        normalized_value = _safe_sensitive_category(
            field.get("sensitive_category") or normalized_value or "sensitive_hint"
        )
    return StandardOCRKeyValueCandidate(
        key=key,
        value=value,
        normalized_value=normalized_value,
        confidence=_confidence(field.get("confidence")),
        source_block_ids=_string_list(
            field.get("source_block_ids")
            or field.get("source_block_id")
            or field.get("block_id")
            or field.get("line_id")
        ),
        candidate_type=candidate_type,
    )


def _candidate_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    return KEY_TO_CANDIDATE_TYPE.get(text, text)


def _normalize_status(value: Any) -> str:
    text = str(value or "completed").strip().lower()
    return STATUS_MAP.get(text, text or "completed")


def _parse_created_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value)
    return datetime.now().astimezone()


def _safe_summary(text_blocks: list[StandardOCRTextBlock]) -> str | None:
    lines = []
    for block in text_blocks[:12]:
        lines.append("[REDACTED]" if block.sensitive_category else block.normalized_text or block.text)
    summary = "\n".join(line for line in lines if line).strip()
    return summary[:1000] or None


def _average_confidence(values: list[float | None]) -> float | None:
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return None
    return round(sum(valid_values) / len(valid_values), 4)


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _confidence(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 1 else None


def _bbox(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) not in {4, 8}:
        return None
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None


def _int_or_default(value: Any, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number >= 0 else default


def _safe_sensitive_category(value: Any) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    return text.replace("password", "credential")


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result

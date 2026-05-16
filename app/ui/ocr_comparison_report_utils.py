from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from app.core.ocr_models import OCRResult
from app.core.receipt_models import ReceiptRecord
from app.core.standard_ocr import (
    StandardOCRResult,
    assert_no_forbidden_ocr_payload,
)
from app.ocr.adapters.azure_adapter_bridge import build_standard_ocr_from_azure_summary
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr
from app.security.sensitive_filter import sanitize_lines_for_parsing


LOW_CONFIDENCE_THRESHOLD = 0.75
CORE_COMPARISON_FIELDS = (
    "merchant_name",
    "transaction_date",
    "business_number",
    "total_amount",
    "gross_amount",
    "discount_amount",
    "final_amount",
    "paid_amount",
    "supply_amount",
    "vat_amount",
    "estimated_supply_amount",
    "estimated_vat_amount",
    "vat_review_required",
    "payment_method",
    "approval_number",
    "review_status",
    "review_reasons",
    "parser_warnings",
    "validation_warnings",
    "confidence",
    "ocr_provider",
)


@dataclass(frozen=True)
class OCRComparisonProviderResult:
    provider: str
    provider_status: str
    diagnostic_code: str | None
    diagnostic_detail_code: str | None
    elapsed_ms: int | None
    standard_text_block_count: int
    standard_candidate_count: int
    table_candidate_count: int
    parser_safe_text_line_count: int
    parser_review_hint_count: int
    sensitive_category_count: int
    warning_count: int
    low_confidence_total_count: int
    redacted_total_count: int
    receipt_record: ReceiptRecord | None
    parse_error_code: str | None

    def as_summary_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "provider_status": self.provider_status,
            "diagnostic_code": self.diagnostic_code,
            "diagnostic_detail_code": self.diagnostic_detail_code,
            "elapsed_ms": self.elapsed_ms,
            "standard_text_block_count": self.standard_text_block_count,
            "standard_candidate_count": self.standard_candidate_count,
            "table_candidate_count": self.table_candidate_count,
            "parser_safe_text_line_count": self.parser_safe_text_line_count,
            "parser_review_hint_count": self.parser_review_hint_count,
            "sensitive_category_count": self.sensitive_category_count,
            "warning_count": self.warning_count,
            "low_confidence_total_count": self.low_confidence_total_count,
            "redacted_total_count": self.redacted_total_count,
            "review_status": _record_value(self.receipt_record, "review_status"),
            "review_reason_count": len(_as_list(_record_value(self.receipt_record, "review_reasons"))),
            "parser_warning_count": len(_as_list(_record_value(self.receipt_record, "parser_warnings"))),
            "validation_warning_count": len(_as_list(_record_value(self.receipt_record, "validation_warnings"))),
            "parse_error_code": self.parse_error_code,
        }


@dataclass(frozen=True)
class OCRComparisonFieldRow:
    field_name: str
    azure_value: object
    paddle_value: object
    azure_present: bool
    paddle_present: bool
    is_same: bool | None
    match_status: str

    def as_display_dict(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "azure_value": _display_value(self.azure_value),
            "paddle_value": _display_value(self.paddle_value),
            "azure_present": self.azure_present,
            "paddle_present": self.paddle_present,
            "is_same": self.is_same,
            "match_status": self.match_status,
        }


@dataclass(frozen=True)
class OCRSideBySideReport:
    sample_id: str
    source_file_name: str
    azure: OCRComparisonProviderResult
    paddle: OCRComparisonProviderResult
    field_rows: list[OCRComparisonFieldRow]

    def as_safe_dict(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "source_file_name": self.source_file_name,
            "summary_rows": comparison_report_to_summary_rows(self),
            "match_summary": comparison_report_to_match_summary(self),
            "field_rows": comparison_report_to_field_rows(self),
        }


def build_provider_comparison_result(
    result: StandardOCRResult,
    *,
    elapsed_ms: int | None = None,
) -> OCRComparisonProviderResult:
    context = build_parser_context_from_standard_ocr(result)
    receipt_record: ReceiptRecord | None = None
    parse_error_code: str | None = None
    if result.status != "completed":
        parse_error_code = result.diagnostic_code or f"provider_status_{result.status}"
    else:
        try:
            receipt_record = ReceiptParser().parse_standard_context(
                context,
                source_file_id=result.source_file_id,
                source_file_name=result.source_file_name,
                ocr_provider=result.provider,
                confidence=result.confidence,
            )
        except Exception as exc:  # pragma: no cover - exercised via defensive behavior
            parse_error_code = _safe_error_code(exc)

    provider_result = OCRComparisonProviderResult(
        provider=result.provider,
        provider_status=result.status,
        diagnostic_code=result.diagnostic_code,
        diagnostic_detail_code=_safe_provider_detail_code(result.provider_fields),
        elapsed_ms=elapsed_ms,
        standard_text_block_count=len(result.text_blocks),
        standard_candidate_count=len(result.key_value_candidates),
        table_candidate_count=len(result.table_candidates),
        parser_safe_text_line_count=len(context.safe_text_lines),
        parser_review_hint_count=len(context.review_hints),
        sensitive_category_count=len(context.sensitive_categories),
        warning_count=len(result.warnings),
        low_confidence_total_count=_low_confidence_total_count(result),
        redacted_total_count=_redacted_total_count(result),
        receipt_record=receipt_record,
        parse_error_code=parse_error_code,
    )
    assert_no_forbidden_ocr_payload(provider_result.as_summary_dict())
    return provider_result


def build_side_by_side_report(
    *,
    sample_id: str,
    source_file_name: str,
    azure_result: StandardOCRResult,
    paddle_result: StandardOCRResult,
    azure_elapsed_ms: int | None = None,
    paddle_elapsed_ms: int | None = None,
) -> OCRSideBySideReport:
    safe_file_name = _safe_file_name(source_file_name)
    azure = build_provider_comparison_result(azure_result, elapsed_ms=azure_elapsed_ms)
    paddle = build_provider_comparison_result(paddle_result, elapsed_ms=paddle_elapsed_ms)
    report = OCRSideBySideReport(
        sample_id=_safe_sample_id(sample_id, safe_file_name),
        source_file_name=safe_file_name,
        azure=azure,
        paddle=paddle,
        field_rows=_build_field_rows(azure.receipt_record, paddle.receipt_record),
    )
    assert_no_forbidden_ocr_payload(report.as_safe_dict())
    return report


def comparison_report_to_summary_rows(report: OCRSideBySideReport) -> list[dict[str, object]]:
    return [
        report.azure.as_summary_dict(),
        report.paddle.as_summary_dict(),
    ]


def comparison_report_to_field_rows(report: OCRSideBySideReport) -> list[dict[str, object]]:
    return [row.as_display_dict() for row in report.field_rows]


def comparison_report_to_match_summary(report: OCRSideBySideReport) -> dict[str, object]:
    rows = report.field_rows
    return {
        "sample_id": report.sample_id,
        "source_file_name": report.source_file_name,
        "field_count": len(rows),
        "matched_field_count": sum(1 for row in rows if row.match_status == "matched"),
        "mismatched_field_count": sum(1 for row in rows if row.match_status == "mismatched"),
        "azure_only_field_count": sum(1 for row in rows if row.match_status == "azure_only"),
        "paddle_only_field_count": sum(1 for row in rows if row.match_status == "paddle_only"),
        "both_missing_field_count": sum(1 for row in rows if row.match_status == "both_missing"),
    }


def build_diagnostic_standard_ocr_result(
    *,
    provider: str,
    source_file_name: str,
    status: str,
    diagnostic_code: str,
    source_file_id: str | None = None,
    engine_runtime: str | None = None,
    diagnostic_detail_code: str | None = None,
) -> StandardOCRResult:
    safe_file_name = _safe_file_name(source_file_name)
    provider_fields = {
        "comparison_role": "side_by_side_diagnostic",
        "has_standard_result": False,
    }
    if diagnostic_detail_code:
        provider_fields["diagnostic_detail_code"] = _safe_provider_detail_code(
            {"diagnostic_detail_code": diagnostic_detail_code}
        )
    return StandardOCRResult(
        id=f"{provider}-comparison-{uuid4().hex}",
        source_file_id=source_file_id,
        source_file_name=safe_file_name,
        provider=provider,
        provider_version=None,
        engine_runtime=engine_runtime,
        status=status,
        pages=[],
        safe_text_summary=None,
        text_blocks=[],
        key_value_candidates=[],
        table_candidates=[],
        provider_fields=provider_fields,
        confidence=None,
        warnings=[diagnostic_code],
        diagnostic_code=diagnostic_code,
        created_at=datetime.utcnow(),
    )


def build_standard_ocr_from_safe_azure_ocr_result(
    ocr_result: OCRResult,
    *,
    source_file_name: str | None = None,
) -> StandardOCRResult:
    safe_file_name = _safe_file_name(source_file_name or ocr_result.source_file_name)
    if ocr_result.status != "completed":
        return build_diagnostic_standard_ocr_result(
            provider="azure",
            source_file_id=ocr_result.source_file_id,
            source_file_name=safe_file_name,
            status=ocr_result.status,
            diagnostic_code=ocr_result.diagnostic_code or "azure_not_completed",
            engine_runtime="server",
            diagnostic_detail_code=getattr(ocr_result, "diagnostic_detail_code", None),
        )

    sanitized_payload = ocr_result.raw_json or {}
    mapped_fields = _azure_mapped_fields(sanitized_payload)
    lines = _safe_azure_lines(ocr_result.raw_text)
    summary = {
        "status": "completed",
        "provider": "azure",
        "confidence": ocr_result.confidence,
        "pages": [
            {
                "page_index": 0,
                "lines": [
                    {
                        "line_id": f"azure-safe-line-{index}",
                        "text": line,
                        "normalized_text": line,
                        "confidence": ocr_result.confidence,
                        "line_order": index,
                    }
                    for index, line in enumerate(lines)
                ],
            }
        ]
        if lines
        else [],
        "documents": [
            {
                "fields": mapped_fields,
            }
        ],
        "warnings": _as_list(sanitized_payload.get("warnings")),
    }
    return build_standard_ocr_from_azure_summary(
        summary,
        source_file_id=ocr_result.source_file_id,
        source_file_name=safe_file_name,
        diagnostic_code=ocr_result.diagnostic_code,
    )


def _build_field_rows(
    azure_record: ReceiptRecord | None,
    paddle_record: ReceiptRecord | None,
) -> list[OCRComparisonFieldRow]:
    rows: list[OCRComparisonFieldRow] = []
    for field_name in CORE_COMPARISON_FIELDS:
        azure_value = _record_value(azure_record, field_name)
        paddle_value = _record_value(paddle_record, field_name)
        azure_present = _is_present(azure_value)
        paddle_present = _is_present(paddle_value)
        is_same = None
        if azure_present or paddle_present:
            is_same = _normalize_compare_value(azure_value) == _normalize_compare_value(paddle_value)
        match_status = _match_status(
            azure_present=azure_present,
            paddle_present=paddle_present,
            is_same=is_same,
        )
        rows.append(
            OCRComparisonFieldRow(
                field_name=field_name,
                azure_value=azure_value,
                paddle_value=paddle_value,
                azure_present=azure_present,
                paddle_present=paddle_present,
                is_same=is_same,
                match_status=match_status,
            )
        )
    return rows


def _match_status(
    *,
    azure_present: bool,
    paddle_present: bool,
    is_same: bool | None,
) -> str:
    if azure_present and paddle_present:
        return "matched" if is_same else "mismatched"
    if azure_present:
        return "azure_only"
    if paddle_present:
        return "paddle_only"
    return "both_missing"


def _safe_provider_detail_code(provider_fields: Mapping[str, Any]) -> str | None:
    value = provider_fields.get("diagnostic_detail_code")
    if value in {None, ""}:
        return None
    text = str(value).strip()
    if not text:
        return None
    safe_text = "".join(character for character in text if character.isalnum() or character in {"_", "-"})
    return safe_text[:80] or None


def _azure_mapped_fields(payload: Mapping[str, Any]) -> dict[str, dict[str, object]]:
    fields = payload.get("fields")
    result: dict[str, dict[str, object]] = {}
    if isinstance(fields, Mapping):
        for field_name, value in fields.items():
            if not isinstance(value, Mapping):
                continue
            mapped_value = value.get("value")
            if mapped_value not in {None, ""}:
                result[str(field_name)] = {
                    "value": mapped_value,
                    "confidence": value.get("confidence"),
                }

    fallback_fields = {
        "MerchantName": payload.get("merchant_name"),
        "TransactionDate": payload.get("transaction_date"),
        "Total": payload.get("total_amount"),
        "TotalTax": payload.get("vat_amount"),
        "PaymentMethod": payload.get("payment_method"),
    }
    for field_name, value in fallback_fields.items():
        if value in {None, ""} or field_name in result:
            continue
        result[field_name] = {"value": value, "confidence": payload.get("confidence")}
    return result


def _safe_azure_lines(value: str) -> list[str]:
    safe_text = sanitize_lines_for_parsing(value or "")
    return [line.strip() for line in safe_text.splitlines() if line.strip()][:120]


def _record_value(record: ReceiptRecord | None, field_name: str) -> object:
    if record is None:
        return None
    return getattr(record, field_name, None)


def _low_confidence_total_count(
    result: StandardOCRResult,
    *,
    threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> int:
    return sum(
        1
        for block in result.text_blocks
        if block.confidence is not None and block.confidence < threshold
    )


def _redacted_total_count(result: StandardOCRResult) -> int:
    return sum(
        1
        for block in result.text_blocks
        if block.sensitive_category
        or block.text == "[REDACTED]"
        or block.normalized_text == "[REDACTED]"
    )


def _safe_file_name(value: str) -> str:
    return Path(str(value or "comparison_sample.png").replace("\\", "/")).name or "comparison_sample.png"


def _safe_sample_id(value: str, fallback_file_name: str) -> str:
    raw_value = str(value or Path(fallback_file_name).stem or "sample")
    safe = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in raw_value)
    safe = safe.strip("-_")
    return safe[:80] or "sample"


def _safe_error_code(exc: Exception) -> str:
    name = exc.__class__.__name__
    result = []
    for index, character in enumerate(name):
        if character.isupper() and index > 0:
            result.append("_")
        result.append(character.lower())
    return "".join(result) or "parse_error"


def _is_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _normalize_compare_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_normalize_compare_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_compare_value(item) for item in value)
    if isinstance(value, str):
        return " ".join(value.split()).strip().lower()
    return value


def _display_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return value


def _as_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []

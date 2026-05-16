from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.standard_ocr import StandardOCRResult, StandardOCRTextBlock


REDACTED_TEXT = "[REDACTED]"
PREVIEW_TEXT_MAX_CHARS = 160


@dataclass(frozen=True)
class SafeOCRPreviewRow:
    line_order: int | None
    page_index: int
    block_id: str
    text: str
    confidence: float | None
    confidence_label: str
    is_low_confidence: bool
    sensitive_category: str | None
    is_redacted: bool

    def as_display_dict(self) -> dict[str, object]:
        return {
            "page": self.page_index + 1,
            "line_order": self.line_order if self.line_order is not None else "-",
            "block_id": self.block_id,
            "text": self.text,
            "confidence": self.confidence_label,
            "low_confidence": self.is_low_confidence,
            "sensitive_category": self.sensitive_category or "-",
            "redacted": self.is_redacted,
        }


@dataclass(frozen=True)
class SafeOCRPreviewSummary:
    provider: str
    status: str
    diagnostic_code: str | None
    source_file_name: str | None
    text_block_count: int
    preview_line_count: int
    low_confidence_line_count: int
    redacted_line_count: int
    max_lines: int
    low_confidence_threshold: float

    def as_display_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "status": self.status,
            "diagnostic_code": self.diagnostic_code or "-",
            "source_file_name": self.source_file_name or "-",
            "text_block_count": self.text_block_count,
            "preview_line_count": self.preview_line_count,
            "low_confidence_line_count": self.low_confidence_line_count,
            "redacted_line_count": self.redacted_line_count,
            "max_lines": self.max_lines,
            "low_confidence_threshold": self.low_confidence_threshold,
        }


@dataclass(frozen=True)
class SafeOCRPreview:
    summary: SafeOCRPreviewSummary
    rows: list[SafeOCRPreviewRow]


def build_safe_ocr_preview_rows(
    result: StandardOCRResult,
    *,
    max_lines: int = 20,
    low_confidence_threshold: float = 0.75,
) -> list[SafeOCRPreviewRow]:
    limit = max(0, int(max_lines))
    if limit == 0:
        return []

    rows: list[SafeOCRPreviewRow] = []
    for block in sorted(result.text_blocks, key=_block_sort_key):
        text = _safe_preview_text(block)
        if not text:
            continue
        is_redacted = bool(block.sensitive_category)
        confidence = block.confidence
        rows.append(
            SafeOCRPreviewRow(
                line_order=block.line_order,
                page_index=block.page_index,
                block_id=block.block_id,
                text=text,
                confidence=confidence,
                confidence_label=_confidence_label(confidence),
                is_low_confidence=confidence is not None
                and confidence < low_confidence_threshold,
                sensitive_category=_safe_sensitive_category(block.sensitive_category),
                is_redacted=is_redacted,
            )
        )
        if len(rows) >= limit:
            break
    return rows


def build_safe_ocr_preview_summary(
    result: StandardOCRResult,
    rows: list[SafeOCRPreviewRow],
    *,
    max_lines: int = 20,
    low_confidence_threshold: float = 0.75,
) -> SafeOCRPreviewSummary:
    return SafeOCRPreviewSummary(
        provider=result.provider,
        status=result.status,
        diagnostic_code=result.diagnostic_code,
        source_file_name=_safe_file_name(result.source_file_name),
        text_block_count=len(result.text_blocks),
        preview_line_count=len(rows),
        low_confidence_line_count=sum(1 for row in rows if row.is_low_confidence),
        redacted_line_count=sum(1 for row in rows if row.is_redacted),
        max_lines=max(0, int(max_lines)),
        low_confidence_threshold=float(low_confidence_threshold),
    )


def build_safe_ocr_preview(
    result: StandardOCRResult,
    *,
    max_lines: int = 20,
    low_confidence_threshold: float = 0.75,
) -> SafeOCRPreview:
    rows = build_safe_ocr_preview_rows(
        result,
        max_lines=max_lines,
        low_confidence_threshold=low_confidence_threshold,
    )
    summary = build_safe_ocr_preview_summary(
        result,
        rows,
        max_lines=max_lines,
        low_confidence_threshold=low_confidence_threshold,
    )
    return SafeOCRPreview(summary=summary, rows=rows)


def _block_sort_key(block: StandardOCRTextBlock) -> tuple[int, int, str]:
    line_order = block.line_order if block.line_order is not None else 1_000_000
    return (block.page_index, line_order, block.block_id)


def _safe_preview_text(block: StandardOCRTextBlock) -> str:
    if block.sensitive_category:
        return REDACTED_TEXT
    text = (block.normalized_text or block.text or "").strip()
    if len(text) <= PREVIEW_TEXT_MAX_CHARS:
        return text
    return f"{text[:PREVIEW_TEXT_MAX_CHARS].rstrip()}..."


def _confidence_label(confidence: float | None) -> str:
    if confidence is None:
        return "-"
    return f"{confidence * 100:.0f}%"


def _safe_sensitive_category(category: str | None) -> str | None:
    if not category:
        return None
    return category.replace("password", "credential").replace("secret", "credential")


def _safe_file_name(value: str | None) -> str | None:
    if not value:
        return None
    name = Path(str(value).replace("\\", "/")).name
    return name or None

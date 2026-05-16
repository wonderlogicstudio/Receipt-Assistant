from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app.core.standard_ocr import StandardOCRResult, StandardOCRTextBlock
from app.ocr.adapters.azure_standard_adapter import AzureStandardOCRAdapter
from app.ocr.adapters.paddle_standard_adapter import PaddleStandardOCRAdapter
from app.ui.ocr_preview_utils import (
    REDACTED_TEXT,
    SafeOCRPreview,
    build_safe_ocr_preview,
    build_safe_ocr_preview_rows,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"
FORBIDDEN_PREVIEW_PATTERNS = [
    r"raw_json",
    r"raw_text",
    r"provider_raw_response",
    r"full_ocr_text",
    r"provider_fields",
    r"operation_location",
    r"api_key",
    r"secret",
    r"token",
    r"password",
    r"https?://",
    r"[A-Za-z]:\\",
    r"/Users/",
    r"/home/",
    r"/var/",
    r"/tmp/",
    r"\b\d{13,19}\b",
    r"\b\d{6}-\d{7}\b",
]


def test_paddle_result_builds_safe_preview_rows_and_summary() -> None:
    result = _paddle_result("paddle_receipt_sanitized_result.json")

    preview = build_safe_ocr_preview(result, max_lines=3)

    assert isinstance(preview, SafeOCRPreview)
    assert preview.summary.provider == "paddleocr"
    assert preview.summary.status == "completed"
    assert preview.summary.source_file_name == "sample_paddle_receipt.png"
    assert preview.summary.text_block_count == len(result.text_blocks)
    assert preview.summary.preview_line_count == 3
    assert len(preview.rows) == 3
    assert all(row.confidence_label for row in preview.rows)


def test_azure_result_uses_same_preview_contract() -> None:
    result = _azure_result("azure_receipt_sanitized_response.json")

    preview = build_safe_ocr_preview(result, max_lines=2)

    assert preview.summary.provider == "azure"
    assert preview.summary.source_file_name == "sample_azure_receipt.pdf"
    assert preview.summary.preview_line_count == 2
    assert [row.page_index for row in preview.rows] == [0, 0]


def test_preview_rows_are_ordered_and_limited() -> None:
    result = _custom_result(
        [
            _block("b3", "third", line_order=3),
            _block("b1", "first", line_order=1),
            _block("b2", "second", line_order=2),
        ]
    )

    rows = build_safe_ocr_preview_rows(result, max_lines=2)

    assert [row.text for row in rows] == ["first", "second"]
    assert [row.line_order for row in rows] == [1, 2]


def test_low_confidence_and_missing_confidence_are_labeled_safely() -> None:
    result = _custom_result(
        [
            _block("b1", "low", confidence=0.5, line_order=1),
            _block("b2", "missing", confidence=None, line_order=2),
        ]
    )

    preview = build_safe_ocr_preview(result, low_confidence_threshold=0.75)

    assert preview.rows[0].confidence_label == "50%"
    assert preview.rows[0].is_low_confidence is True
    assert preview.rows[1].confidence_label == "-"
    assert preview.rows[1].is_low_confidence is False
    assert preview.summary.low_confidence_line_count == 1


def test_sensitive_blocks_keep_redacted_text_and_safe_category_only() -> None:
    result = _custom_result(
        [
            _block(
                "b1",
                "wifi pw should not be displayed",
                line_order=1,
                sensitive_category="wifi_password",
            )
        ]
    )

    preview = build_safe_ocr_preview(result)

    assert preview.rows[0].text == REDACTED_TEXT
    assert preview.rows[0].is_redacted is True
    assert preview.rows[0].sensitive_category == "wifi_credential"
    assert preview.summary.redacted_line_count == 1
    _assert_preview_has_no_forbidden_text(preview)


def test_empty_text_blocks_do_not_create_preview_rows() -> None:
    result = _custom_result(
        [
            _block("b1", "   ", line_order=1),
            _block("b2", "", line_order=2),
        ]
    )

    preview = build_safe_ocr_preview(result)

    assert preview.rows == []
    assert preview.summary.text_block_count == 2
    assert preview.summary.preview_line_count == 0


def test_failed_or_empty_provider_result_still_has_safe_summary() -> None:
    result = _paddle_result("paddle_receipt_empty_sanitized_result.json")

    preview = build_safe_ocr_preview(result)

    assert preview.summary.status == "failed"
    assert preview.summary.diagnostic_code == "paddle_no_text_detected"
    assert preview.summary.text_block_count == 0
    assert preview.rows == []


def test_preview_summary_strips_path_like_source_file_names_defensively() -> None:
    result = _custom_result([_block("b1", "safe line")])
    result_with_path_like_name = result.model_copy(
        update={"source_file_name": r"C:\private\receipts\sample.png"}
    )

    preview = build_safe_ocr_preview(result_with_path_like_name)

    assert preview.summary.source_file_name == "sample.png"
    _assert_preview_has_no_forbidden_text(preview)


def test_preview_does_not_copy_provider_metadata_or_raw_payload_fields() -> None:
    result = _paddle_result("paddle_receipt_edge_sanitized_result.json")

    preview = build_safe_ocr_preview(result, max_lines=20)

    dumped = json.dumps(asdict(preview), ensure_ascii=False, default=str)
    assert "provider_fields" not in dumped
    assert "adapter_version" not in dumped
    _assert_preview_has_no_forbidden_text(preview)


def _paddle_result(name: str) -> StandardOCRResult:
    payload = json.loads((FIXTURE_DIR / "paddle" / name).read_text(encoding="utf-8"))
    return PaddleStandardOCRAdapter().convert(
        payload,
        source_file_id=f"source-{name}",
        source_file_name="sample_paddle_receipt.png",
    )


def _azure_result(name: str) -> StandardOCRResult:
    payload = json.loads((FIXTURE_DIR / "azure" / name).read_text(encoding="utf-8"))
    return AzureStandardOCRAdapter().convert(
        payload,
        source_file_id=f"source-{name}",
        source_file_name="sample_azure_receipt.pdf",
    )


def _custom_result(blocks: list[StandardOCRTextBlock]) -> StandardOCRResult:
    return StandardOCRResult(
        id="preview-test",
        source_file_name="custom.png",
        provider="paddleocr",
        provider_version="test",
        engine_runtime="pc_local",
        status="completed",
        text_blocks=blocks,
        provider_fields={"provider_family": "paddleocr"},
        created_at=datetime(2026, 1, 1),
    )


def _block(
    block_id: str,
    text: str,
    *,
    confidence: float | None = 0.9,
    line_order: int | None = 1,
    sensitive_category: str | None = None,
) -> StandardOCRTextBlock:
    return StandardOCRTextBlock(
        page_index=0,
        block_id=block_id,
        text=text,
        confidence=confidence,
        line_order=line_order,
        sensitive_category=sensitive_category,
    )


def _assert_preview_has_no_forbidden_text(preview: SafeOCRPreview) -> None:
    dumped = json.dumps(asdict(preview), ensure_ascii=False, default=str)
    for pattern in FORBIDDEN_PREVIEW_PATTERNS:
        assert not re.search(pattern, dumped, flags=re.IGNORECASE), pattern

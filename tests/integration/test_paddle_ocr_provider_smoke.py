from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path

import pytest

from app.core.standard_ocr import StandardOCRResult
from app.ocr.paddle_provider import PaddleOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr


OPT_IN_TRUE_VALUES = {"1", "true", "yes", "on"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_STATUSES = {"completed", "partial", "failed", "skipped"}
FORBIDDEN_PATTERNS = [
    r"raw_json",
    r"raw_text",
    r"provider_raw_response",
    r"full_ocr_text",
    r"paddle_raw_output",
    r"image_path",
    r"absolute_path",
    r"local_file_path",
    r"model_path",
    r"[A-Za-z]:\\",
    r"/Users/",
    r"/home/",
    r"/var/",
    r"/tmp/",
    r"api_key",
    r"secret",
    r"token",
    r"password",
    r"traceback",
    r"\b\d{13,19}\b",
    r"\b\d{6}-\d{7}\b",
]


def _opt_in_enabled() -> bool:
    return os.environ.get("RUN_PADDLEOCR_TESTS", "").strip().lower() in OPT_IN_TRUE_VALUES


def _require_opt_in_image_path() -> Path:
    if not _opt_in_enabled():
        pytest.skip("PaddleOCR smoke test is opt-in; set RUN_PADDLEOCR_TESTS=1.")
    image_path_value = os.environ.get("PADDLEOCR_TEST_IMAGE_PATH", "").strip()
    if not image_path_value:
        pytest.skip("PADDLEOCR_TEST_IMAGE_PATH is not configured.")

    image_path = Path(image_path_value)
    if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
        pytest.skip("Configured smoke test file is not a supported image extension.")
    if not image_path.exists():
        pytest.skip(f"Configured smoke test image is missing: {image_path.name}")
    if importlib.util.find_spec("paddleocr") is None:
        pytest.skip("paddleocr package is not installed in this environment.")
    return image_path


def _result_text(result: StandardOCRResult) -> str:
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, default=str)


def _assert_no_forbidden_text(text: str) -> None:
    for pattern in FORBIDDEN_PATTERNS:
        assert not re.search(pattern, text, flags=re.IGNORECASE), pattern


def test_paddle_ocr_provider_real_image_smoke_opt_in() -> None:
    image_path = _require_opt_in_image_path()
    provider = PaddleOCRProvider()

    result = provider.extract(
        image_path,
        source_file_name=image_path.name,
    )

    assert isinstance(result, StandardOCRResult)
    assert result.provider == "paddleocr"
    assert result.engine_runtime == "pc_local"
    assert result.status in ALLOWED_STATUSES
    assert result.source_file_name == image_path.name
    assert result.provider_fields["provider_family"] == "paddleocr"
    assert result.provider_fields["input_type"] == "image"
    assert isinstance(result.text_blocks, list)
    assert isinstance(result.key_value_candidates, list)
    assert isinstance(result.table_candidates, list)
    assert "paddle_raw_output" not in result.provider_fields
    assert "image_path" not in result.provider_fields
    assert "model_path" not in result.provider_fields

    context = build_parser_context_from_standard_ocr(result)
    record = ReceiptParser().parse_standard_context(context)

    assert context.provider == "paddleocr"
    assert record.ocr_provider == "paddleocr"
    _assert_no_forbidden_text(_result_text(result))
    _assert_no_forbidden_text(json.dumps(context.model_dump(mode="json"), ensure_ascii=False, default=str))


def test_paddle_pdf_remains_unsupported_without_pdf_conversion() -> None:
    result = PaddleOCRProvider().extract("sample_receipt.pdf", source_file_name="sample_receipt.pdf")

    assert result.provider == "paddleocr"
    assert result.status == "failed"
    assert result.diagnostic_code == "paddle_pdf_not_supported"
    assert result.text_blocks == []
    assert result.key_value_candidates == []
    assert result.table_candidates == []
    _assert_no_forbidden_text(_result_text(result))

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.standard_ocr import (
    StandardOCRKeyValueCandidate,
    StandardOCRPage,
    StandardOCRResult,
    StandardOCRTableCandidate,
    StandardOCRTextBlock,
    assert_no_forbidden_ocr_payload,
    has_absolute_path_risk,
    has_raw_payload_risk,
    has_sensitive_secret_risk,
)


def _text_block(**overrides: object) -> StandardOCRTextBlock:
    data = {
        "page_index": 0,
        "block_id": "b001",
        "text": "합계 12,000",
        "normalized_text": "합계 12000",
        "confidence": 0.95,
        "bbox": [10, 20, 300, 60],
        "line_order": 0,
        "block_type": "line",
        "sensitive_category": None,
    }
    data.update(overrides)
    return StandardOCRTextBlock(**data)


def _candidate(**overrides: object) -> StandardOCRKeyValueCandidate:
    data = {
        "key": "total_amount",
        "value": "12,000",
        "normalized_value": "12000",
        "confidence": 0.95,
        "source_block_ids": ["b001"],
        "candidate_type": "total_amount",
    }
    data.update(overrides)
    return StandardOCRKeyValueCandidate(**data)


def test_standard_ocr_result_model_can_be_created() -> None:
    block = _text_block()
    candidate = _candidate()
    page = StandardOCRPage(
        page_index=0,
        width=1080,
        height=1920,
        unit="pixel",
        text_blocks=[block],
        key_value_candidates=[candidate],
        table_candidates=[],
    )
    table = StandardOCRTableCandidate(
        page_index=0,
        table_id="t001",
        rows=[["품목", "금액"], ["테스트", "12000"]],
        confidence=0.8,
        source_block_ids=["b001"],
    )

    result = StandardOCRResult(
        id="standard_ocr_test_001",
        source_file_id="file_001",
        source_file_name="sample_receipt.png",
        provider="mock",
        provider_version="mock-v1",
        engine_runtime="mock",
        status="completed",
        pages=[page],
        safe_text_summary="합계 12,000",
        text_blocks=[block],
        key_value_candidates=[candidate],
        table_candidates=[table],
        confidence=0.95,
        warnings=[],
        diagnostic_code="completed",
        created_at=datetime.fromisoformat("2026-05-14T21:00:00+09:00"),
    )

    assert result.provider == "mock"
    assert result.pages[0].page_index == 0
    assert result.key_value_candidates[0].candidate_type == "total_amount"


def test_standard_ocr_page_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError):
        StandardOCRPage(page_index=-1)

    with pytest.raises(ValidationError):
        StandardOCRPage(page_index=0, width=0)

    with pytest.raises(ValidationError):
        StandardOCRPage(page_index=0, height=-1)


def test_standard_ocr_text_block_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError):
        _text_block(page_index=-1)

    with pytest.raises(ValidationError):
        _text_block(block_id="")

    with pytest.raises(ValidationError):
        _text_block(confidence=1.1)

    with pytest.raises(ValidationError):
        _text_block(line_order=-1)


def test_standard_ocr_confidence_validation_is_shared() -> None:
    with pytest.raises(ValidationError):
        _candidate(confidence=-0.1)

    with pytest.raises(ValidationError):
        StandardOCRTableCandidate(page_index=0, table_id="t001", confidence=2)


def test_standard_ocr_bbox_accepts_none_4_or_8_values() -> None:
    assert _text_block(bbox=None).bbox is None
    assert _text_block(bbox=[1, 2, 3, 4]).bbox == [1, 2, 3, 4]
    assert _text_block(bbox=[1, 2, 3, 4, 5, 6, 7, 8]).bbox == [1, 2, 3, 4, 5, 6, 7, 8]

    with pytest.raises(ValidationError):
        _text_block(bbox=[1, 2, 3])


def test_source_file_name_rejects_absolute_or_nested_paths() -> None:
    base = {
        "id": "standard_ocr_test_002",
        "provider": "mock",
        "status": "completed",
        "created_at": datetime.fromisoformat("2026-05-14T21:00:00+09:00"),
    }

    with pytest.raises(ValidationError):
        StandardOCRResult(**base, source_file_name="C:\\secret\\receipt.png")

    with pytest.raises(ValidationError):
        StandardOCRResult(**base, source_file_name="nested/receipt.png")

    assert has_absolute_path_risk("D:\\hidden\\receipt.png") is True


def test_forbidden_raw_payload_fields_are_not_model_fields() -> None:
    result_fields = set(StandardOCRResult.model_fields)

    assert "raw_json" not in result_fields
    assert "raw_text" not in result_fields
    assert "provider_raw_json" not in result_fields
    assert "provider_raw_response" not in result_fields
    assert "full_ocr_text" not in result_fields


def test_forbidden_payload_helpers_detect_risky_data() -> None:
    assert has_raw_payload_risk({"raw_json": {"value": "not allowed"}}) is True
    assert has_sensitive_secret_risk({"api_key": "not-allowed"}) is True
    assert has_sensitive_secret_risk("token=not-allowed") is True
    assert has_absolute_path_risk("/Users/example/receipt.png") is True

    with pytest.raises(ValueError):
        assert_no_forbidden_ocr_payload({"provider_raw_response": {}})

    assert_no_forbidden_ocr_payload(
        {
            "safe_text_summary": "제한된 요약",
            "sensitive_category": "wifi_password",
            "text": "[REDACTED]",
        }
    )


def test_extra_raw_fields_are_rejected_by_model() -> None:
    with pytest.raises(ValidationError):
        StandardOCRResult(
            id="standard_ocr_test_003",
            provider="mock",
            status="completed",
            created_at=datetime.fromisoformat("2026-05-14T21:00:00+09:00"),
            raw_json={},
        )

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.core.standard_ocr import (
    StandardOCRResult,
    assert_no_forbidden_ocr_payload,
    has_absolute_path_risk,
    has_raw_payload_risk,
    has_sensitive_secret_risk,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "standard_ocr"
FIXTURE_NAMES = [
    "mock_receipt_standard.json",
    "azure_like_receipt_standard.json",
    "edge_case_receipt_standard.json",
]
FORBIDDEN_TOP_LEVEL_KEYS = {
    "raw_json",
    "raw_text",
    "provider_raw_response",
    "full_ocr_text",
}
CARD_NUMBER_PATTERN = re.compile(r"(?<!\d)\d{13,19}(?!\d)")
RESIDENT_NUMBER_PATTERN = re.compile(r"\d{6}-[1-4]\d{6}")
SECRET_ASSIGNMENT_PATTERN = re.compile(r"(token|secret|password|api_key)\s*=", re.IGNORECASE)


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_standard_ocr_fixture_loads(fixture_name: str) -> None:
    data = _load_fixture(fixture_name)

    result = StandardOCRResult.model_validate(data)

    assert result.id
    assert result.provider in {"mock", "azure"}
    assert result.status in {"completed", "failed", "skipped", "partial"}


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_fixture_does_not_include_forbidden_payload_keys(fixture_name: str) -> None:
    data = _load_fixture(fixture_name)

    assert FORBIDDEN_TOP_LEVEL_KEYS.isdisjoint(data)
    assert has_raw_payload_risk(data) is False
    assert_no_forbidden_ocr_payload(data)


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_fixture_does_not_include_absolute_paths_or_secret_keys(fixture_name: str) -> None:
    text = _fixture_text(fixture_name)
    data = json.loads(text)

    assert has_absolute_path_risk(data) is False
    assert has_sensitive_secret_risk(data) is False
    assert "C:\\" not in text
    assert "D:\\" not in text
    assert "/Users/" not in text
    assert "/home/" not in text
    assert "/var/" not in text
    assert "/tmp/" not in text
    assert SECRET_ASSIGNMENT_PATTERN.search(text) is None


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_fixture_does_not_include_obvious_real_sensitive_number_patterns(fixture_name: str) -> None:
    text = _fixture_text(fixture_name)

    assert CARD_NUMBER_PATTERN.search(text) is None
    assert RESIDENT_NUMBER_PATTERN.search(text) is None


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_safe_text_summary_is_limited(fixture_name: str) -> None:
    result = StandardOCRResult.model_validate(_load_fixture(fixture_name))

    assert result.safe_text_summary is not None
    assert len(result.safe_text_summary) <= 1000


def test_sensitive_block_is_redacted_and_categorized() -> None:
    result = StandardOCRResult.model_validate(_load_fixture("azure_like_receipt_standard.json"))

    sensitive_blocks = [block for block in result.text_blocks if block.sensitive_category]

    assert sensitive_blocks
    assert all(block.text == "[REDACTED]" for block in sensitive_blocks)
    assert {block.sensitive_category for block in sensitive_blocks} == {"wifi_password"}


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_candidate_source_block_ids_reference_existing_blocks(fixture_name: str) -> None:
    result = StandardOCRResult.model_validate(_load_fixture(fixture_name))
    block_ids = {block.block_id for block in result.text_blocks}

    for candidate in result.key_value_candidates:
        for block_id in candidate.source_block_ids:
            assert block_id in block_ids

    for table in result.table_candidates:
        for block_id in table.source_block_ids:
            assert block_id in block_ids


def test_non_amount_numeric_candidates_are_separate_from_total_amount() -> None:
    result = StandardOCRResult.model_validate(_load_fixture("edge_case_receipt_standard.json"))
    candidates_by_type = _candidates_by_type(result)

    assert {"quantity", "approval_number", "footer_number"}.issubset(candidates_by_type)
    assert "total_amount" in candidates_by_type

    total_amount_sources = {
        block_id
        for candidate in candidates_by_type["total_amount"]
        for block_id in candidate.source_block_ids
    }
    non_amount_sources = {
        block_id
        for candidate_type in ["quantity", "approval_number", "footer_number"]
        for candidate in candidates_by_type[candidate_type]
        for block_id in candidate.source_block_ids
    }

    assert total_amount_sources.isdisjoint(non_amount_sources)


def _load_fixture(fixture_name: str) -> dict[str, Any]:
    return json.loads(_fixture_text(fixture_name))


def _fixture_text(fixture_name: str) -> str:
    return (FIXTURE_DIR / fixture_name).read_text(encoding="utf-8")


def _candidates_by_type(result: StandardOCRResult) -> dict[str, list[Any]]:
    candidates: dict[str, list[Any]] = {}
    for candidate in result.key_value_candidates:
        if candidate.candidate_type is None:
            continue
        candidates.setdefault(candidate.candidate_type, []).append(candidate)
    return candidates

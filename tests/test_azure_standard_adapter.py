from __future__ import annotations

import json
import re
from pathlib import Path

from app.core.standard_ocr import StandardOCRResult
from app.ocr.adapters.azure_standard_adapter import (
    AMOUNT_CANDIDATE_TYPES,
    AzureStandardOCRAdapter,
)
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "azure"
STANDARD_FIXTURES = [
    FIXTURE_DIR / "azure_receipt_sanitized_response.json",
    FIXTURE_DIR / "azure_receipt_edge_sanitized_response.json",
    FIXTURE_DIR / "azure_receipt_failed_sanitized_response.json",
]

FORBIDDEN_PROVIDER_FIELD_KEYS = {
    "raw_response",
    "raw_json",
    "provider_raw_response",
    "full_ocr_text",
    "analyze_result",
    "read_result",
    "headers",
    "endpoint",
    "operation_location",
    "api_key",
    "secret",
    "token",
    "password",
    "pages",
    "lines",
    "words",
    "key_value_pairs",
    "tables",
}
FORBIDDEN_TEXT_PATTERNS = [
    r"https?://",
    r"operation_location",
    r"api_key",
    r"secret",
    r"token",
    r"password",
    r"[A-Za-z]:\\",
    r"/Users/",
    r"/home/",
    r"/var/",
    r"/tmp/",
    r"\b\d{13,19}\b",
    r"\b\d{6}-\d{7}\b",
]


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def convert_fixture(name: str) -> StandardOCRResult:
    return AzureStandardOCRAdapter().convert(
        load_fixture(name),
        source_file_id=f"source-{name}",
        source_file_name="sample_azure_receipt.pdf",
    )


def candidate_types(result: StandardOCRResult) -> set[str]:
    return {
        candidate.candidate_type
        for candidate in result.key_value_candidates
        if candidate.candidate_type
    }


def test_convert_sanitized_azure_receipt_to_standard_ocr_result() -> None:
    result = convert_fixture("azure_receipt_sanitized_response.json")

    assert isinstance(result, StandardOCRResult)
    assert result.provider == "azure"
    assert result.provider_version == "test"
    assert result.engine_runtime == "server"
    assert result.status == "completed"
    assert result.provider_fields["adapter_version"] == "azure-standard-adapter-v1"
    assert result.provider_fields["provider_family"] == "azure"
    assert result.pages
    assert result.text_blocks
    assert result.key_value_candidates
    assert result.table_candidates
    assert result.confidence is None or 0 <= result.confidence <= 1


def test_provider_fields_contain_only_safe_metadata() -> None:
    result = convert_fixture("azure_receipt_sanitized_response.json")
    provider_fields = result.provider_fields

    assert FORBIDDEN_PROVIDER_FIELD_KEYS.isdisjoint(provider_fields)
    assert provider_fields == {
        "provider_family": "azure",
        "api_model": "prebuilt-receipt",
        "api_version": "test",
        "document_type": "receipt",
        "page_count": 1,
        "has_key_value_pairs": True,
        "has_tables": True,
        "has_styles": False,
        "locale_hint": "ko-KR",
        "adapter_version": "azure-standard-adapter-v1",
        "normalized_block_count": 6,
        "normalized_candidate_count": 6,
        "normalized_table_count": 1,
    }


def test_sanitized_azure_fixtures_do_not_contain_forbidden_text() -> None:
    for fixture_path in STANDARD_FIXTURES:
        fixture_text = fixture_path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            assert not re.search(pattern, fixture_text, flags=re.IGNORECASE), (
                fixture_path.name,
                pattern,
            )


def test_adapter_output_does_not_contain_forbidden_text() -> None:
    for fixture_path in STANDARD_FIXTURES:
        result = convert_fixture(fixture_path.name)
        result_text = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            assert not re.search(pattern, result_text, flags=re.IGNORECASE), (
                fixture_path.name,
                pattern,
            )


def test_candidate_types_are_mapped_from_regular_fixture() -> None:
    result = convert_fixture("azure_receipt_sanitized_response.json")

    assert {
        "merchant_name",
        "transaction_date",
        "total_amount",
        "supply_amount",
        "vat_amount",
        "payment_method",
    }.issubset(candidate_types(result))


def test_edge_candidate_types_keep_amount_and_non_amount_values_separate() -> None:
    result = convert_fixture("azure_receipt_edge_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)

    assert {"gross_amount", "discount_amount", "final_amount", "paid_amount"}.issubset(
        context.amount_candidate_map
    )
    for non_amount_type in [
        "quantity",
        "approval_number",
        "footer_number",
        "business_number",
    ]:
        assert non_amount_type in context.non_amount_candidate_map
        assert non_amount_type not in context.amount_candidate_map
    assert "vat_missing" not in context.amount_candidate_map
    assert "vat_review_hint" not in context.amount_candidate_map
    assert any(hint.startswith("vat_missing:") for hint in context.review_hints)
    assert any(hint.startswith("vat_review_hint:") for hint in context.review_hints)


def test_amount_candidate_type_boundary_matches_transition_contract() -> None:
    result = convert_fixture("azure_receipt_edge_sanitized_response.json")
    amount_types = {
        candidate.candidate_type
        for candidate in result.key_value_candidates
        if candidate.candidate_type in AMOUNT_CANDIDATE_TYPES
    }

    assert amount_types == {
        "gross_amount",
        "discount_amount",
        "final_amount",
        "paid_amount",
    }
    assert "quantity" not in amount_types
    assert "approval_number" not in amount_types
    assert "footer_number" not in amount_types
    assert "business_number" not in amount_types
    assert "vat_missing" not in amount_types
    assert "vat_review_hint" not in amount_types


def test_text_blocks_are_ordered_and_linked_to_source_blocks() -> None:
    result = convert_fixture("azure_receipt_sanitized_response.json")
    line_orders = [block.line_order for block in result.text_blocks]
    block_ids = {block.block_id for block in result.text_blocks}

    assert line_orders == sorted(line_orders)
    assert all(block.block_id for block in result.text_blocks)
    for candidate in result.key_value_candidates:
        assert candidate.source_block_ids
        assert set(candidate.source_block_ids).issubset(block_ids)


def test_sensitive_text_is_redacted_and_category_only_reaches_context() -> None:
    result = convert_fixture("azure_receipt_edge_sanitized_response.json")
    sensitive_blocks = [block for block in result.text_blocks if block.sensitive_category]
    context = build_parser_context_from_standard_ocr(result)

    assert sensitive_blocks
    assert all(block.text == "[REDACTED]" for block in sensitive_blocks)
    assert context.sensitive_categories == ["wifi_credential"]
    assert any("wifi_credential" in hint for hint in context.review_hints)
    assert all("wifi_credential" != line for line in context.safe_text_lines)


def test_table_candidates_are_optional() -> None:
    result_with_table = convert_fixture("azure_receipt_sanitized_response.json")
    result_without_table = convert_fixture("azure_receipt_edge_sanitized_response.json")

    assert len(result_with_table.table_candidates) == 1
    assert result_without_table.table_candidates == []


def test_failed_response_maps_diagnostic_code_without_raw_error_body() -> None:
    result = convert_fixture("azure_receipt_failed_sanitized_response.json")

    assert result.status == "failed"
    assert result.diagnostic_code == "poll_timeout"
    assert result.warnings == ["poll_timeout", "azure_status:failed"]
    assert "raw" not in " ".join(result.warnings).lower()


def test_adapter_output_can_build_parser_context_without_raw_payload_fields() -> None:
    result = convert_fixture("azure_receipt_edge_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)
    dumped = context.model_dump(mode="json")

    assert {"raw_json", "raw_text", "provider_raw_response", "full_ocr_text"}.isdisjoint(
        dumped
    )
    assert "paid_amount" in context.amount_candidate_map
    assert "approval_number" in context.non_amount_candidate_map
    assert "vat_missing" in context.non_amount_candidate_map


def test_output_shape_is_stable_for_week_7c_connection_review() -> None:
    result = convert_fixture("azure_receipt_sanitized_response.json")

    assert set(result.provider_fields) == {
        "provider_family",
        "api_model",
        "api_version",
        "document_type",
        "page_count",
        "has_key_value_pairs",
        "has_tables",
        "has_styles",
        "locale_hint",
        "adapter_version",
        "normalized_block_count",
        "normalized_candidate_count",
        "normalized_table_count",
    }
    assert result.diagnostic_code is None
    assert isinstance(result.warnings, list)
    assert all(candidate.candidate_type for candidate in result.key_value_candidates)

from __future__ import annotations

import json
import re
from pathlib import Path

from app.ocr.adapters.azure_adapter_bridge import build_standard_ocr_from_azure_summary
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "azure"
FORBIDDEN_CONTEXT_FIELDS = {
    "raw_json",
    "raw_text",
    "provider_raw_response",
    "full_ocr_text",
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
]


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def build_result(name: str):
    return build_standard_ocr_from_azure_summary(
        load_fixture(name),
        source_file_id=f"contract-{name}",
        source_file_name="sample_azure_receipt.pdf",
    )


def context_text_from_fixture(name: str) -> str:
    result = build_result(name)
    context = build_parser_context_from_standard_ocr(result)
    return json.dumps(context.model_dump(mode="json"), ensure_ascii=False)


def test_bridge_builds_standard_result_and_parser_context_from_sanitized_fixture() -> None:
    result = build_result("azure_receipt_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)

    assert result.provider == "azure"
    assert result.provider_fields["adapter_version"] == "azure-standard-adapter-v1"
    assert context.provider == "azure"
    assert context.status == "completed"
    assert context.amount_candidate_map["total_amount"] == ["12000"]
    assert context.amount_candidate_map["supply_amount"] == ["10909"]
    assert context.amount_candidate_map["vat_amount"] == ["1091"]


def test_parser_context_has_no_raw_payload_fields_or_provider_fields() -> None:
    result = build_result("azure_receipt_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)
    dumped = context.model_dump(mode="json")

    assert FORBIDDEN_CONTEXT_FIELDS.isdisjoint(dumped)
    assert "provider_fields" not in dumped
    assert "adapter_version" not in json.dumps(dumped, ensure_ascii=False)


def test_parser_context_contains_no_forbidden_security_text() -> None:
    for fixture_name in [
        "azure_receipt_sanitized_response.json",
        "azure_receipt_edge_sanitized_response.json",
        "azure_receipt_failed_sanitized_response.json",
    ]:
        context_text = context_text_from_fixture(fixture_name)
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            assert not re.search(pattern, context_text, flags=re.IGNORECASE), (
                fixture_name,
                pattern,
            )


def test_edge_context_keeps_non_amount_candidates_out_of_amount_map() -> None:
    result = build_result("azure_receipt_edge_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)

    assert {"gross_amount", "discount_amount", "final_amount", "paid_amount"}.issubset(
        context.amount_candidate_map
    )
    for candidate_type in [
        "quantity",
        "approval_number",
        "footer_number",
        "business_number",
    ]:
        assert candidate_type in context.non_amount_candidate_map
        assert candidate_type not in context.amount_candidate_map


def test_vat_review_hints_are_not_explicit_vat_amount_candidates() -> None:
    result = build_result("azure_receipt_edge_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)

    assert "vat_amount" not in context.amount_candidate_map
    assert "vat_missing" in context.non_amount_candidate_map
    assert "vat_review_hint" in context.non_amount_candidate_map
    assert any(hint.startswith("vat_missing:") for hint in context.review_hints)
    assert any(hint.startswith("vat_review_hint:") for hint in context.review_hints)


def test_failed_response_still_builds_safe_diagnostic_context() -> None:
    result = build_result("azure_receipt_failed_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)

    assert result.status == "failed"
    assert context.status == "failed"
    assert context.diagnostic_code == "poll_timeout"
    assert "ocr_status:failed" in context.review_hints
    assert "diagnostic_code:poll_timeout" in context.review_hints


def test_adapter_output_shape_is_ready_for_week_8_parser_boundary() -> None:
    result = build_result("azure_receipt_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)

    assert result.text_blocks
    assert result.key_value_candidates
    assert context.safe_text_lines
    assert set(context.amount_candidate_map) == {
        "total_amount",
        "supply_amount",
        "vat_amount",
    }
    assert "payment_method" in context.non_amount_candidate_map

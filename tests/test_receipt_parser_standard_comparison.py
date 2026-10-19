from __future__ import annotations

from dataclasses import fields
import inspect
import json
import re
from pathlib import Path
from typing import Any

from app.core.enums import ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.core.standard_ocr import StandardOCRResult
from app.ocr.adapters.azure_standard_adapter import AzureStandardOCRAdapter
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr


STANDARD_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "standard_ocr"
AZURE_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "azure"
LEGACY_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "parser_legacy"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORE_COMPARISON_FIELDS = [
    "transaction_date",
    "merchant_name",
    "business_number",
    "total_amount",
    "gross_amount",
    "discount_amount",
    "final_amount",
    "paid_amount",
    "amount_source",
    "supply_amount",
    "vat_amount",
    "estimated_supply_amount",
    "estimated_vat_amount",
    "vat_source",
    "vat_review_required",
    "payment_method",
    "approval_number",
    "review_status",
    "sensitive_text_detected",
    "sensitive_text_categories",
    "ocr_provider",
]

DOWNSTREAM_REQUIRED_FIELDS = [
    "transaction_date",
    "merchant_name",
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
    "parser_warnings",
    "amount_warnings",
    "vat_warnings",
    "sensitive_text_detected",
    "sensitive_text_categories",
    "ocr_provider",
]

AMOUNT_FIELD_NAMES = {
    "total_amount",
    "gross_amount",
    "discount_amount",
    "final_amount",
    "paid_amount",
    "supply_amount",
    "vat_amount",
}

FORBIDDEN_OUTPUT_PATTERNS = [
    r"raw_json",
    r"raw_text",
    r"provider_raw_response",
    r"full_ocr_text",
    r"endpoint",
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


def load_standard_result(name: str) -> StandardOCRResult:
    return StandardOCRResult.model_validate_json(
        (STANDARD_FIXTURE_DIR / name).read_text(encoding="utf-8")
    )


def parse_standard_fixture(name: str) -> ReceiptRecord:
    return ReceiptParser().parse_from_standard_ocr(load_standard_result(name))


def parse_legacy_fixture(name: str) -> ReceiptRecord:
    raw_text = (LEGACY_FIXTURE_DIR / name).read_text(encoding="utf-8")
    return ReceiptParser().parse_text(
        raw_text,
        source_file_name=name.replace(".txt", ".jpg"),
        source_file_id=f"legacy-{name}",
    )


def convert_azure_fixture(name: str) -> StandardOCRResult:
    response = json.loads((AZURE_FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return AzureStandardOCRAdapter().convert(
        response,
        source_file_id=f"azure-{name}",
        source_file_name="sample_azure_receipt.pdf",
    )


def parse_azure_adapter_fixture(name: str) -> ReceiptRecord:
    result = convert_azure_fixture(name)
    context = build_parser_context_from_standard_ocr(result)
    return ReceiptParser().parse_standard_context(
        context,
        source_file_id=result.source_file_id,
        source_file_name=result.source_file_name,
        ocr_provider=result.provider,
        confidence=result.confidence,
    )


def core_fields(record: ReceiptRecord) -> dict[str, Any]:
    data = record.to_dict()
    return {field_name: data.get(field_name) for field_name in CORE_COMPARISON_FIELDS}


def warning_sets(record: ReceiptRecord) -> dict[str, set[str]]:
    return {
        "parser_warnings": set(record.parser_warnings),
        "amount_warnings": set(record.amount_warnings),
        "vat_warnings": set(record.vat_warnings),
        "sensitive_warnings": set(record.sensitive_warnings),
        "review_reasons": set(record.review_reasons),
    }


def assert_selected_core_fields_match(
    legacy_record: ReceiptRecord,
    standard_record: ReceiptRecord,
    field_names: list[str],
) -> None:
    legacy_fields = core_fields(legacy_record)
    standard_fields = core_fields(standard_record)
    for field_name in field_names:
        assert standard_fields[field_name] == legacy_fields[field_name], field_name


def assert_no_forbidden_parser_output(record: ReceiptRecord) -> None:
    dumped = json.dumps(record.to_dict(), ensure_ascii=False, default=str)
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        assert not re.search(pattern, dumped, flags=re.IGNORECASE), pattern


def assert_amount_fields_do_not_use_values(record: ReceiptRecord, forbidden_values: set[int]) -> None:
    data = record.to_dict()
    for field_name in AMOUNT_FIELD_NAMES:
        value = data.get(field_name)
        if field_name == "total_amount" and value == 0:
            continue
        assert value not in forbidden_values, field_name


def assert_receipt_record_shape_for_downstream(record: ReceiptRecord) -> None:
    field_names = {field.name for field in fields(ReceiptRecord)}
    data = record.to_dict()
    for field_name in DOWNSTREAM_REQUIRED_FIELDS:
        assert field_name in field_names, field_name
        assert field_name in data, field_name


def test_parse_mock_standard_context_core_fields() -> None:
    receipt = parse_standard_fixture("mock_receipt_standard.json")

    assert receipt.merchant_name == "테스트카페"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-05-14"
    assert receipt.total_amount == 12000
    assert receipt.supply_amount == 10909
    assert receipt.vat_amount == 1091
    assert receipt.payment_method == "card"
    assert receipt.ocr_provider == "mock"
    assert receipt.vat_review_required is False
    assert_receipt_record_shape_for_downstream(receipt)
    assert_no_forbidden_parser_output(receipt)


def test_parse_azure_like_standard_context_core_fields() -> None:
    receipt = parse_standard_fixture("azure_like_receipt_standard.json")

    assert receipt.merchant_name == "테스트마트"
    assert receipt.business_number == "000-00-00000"
    assert receipt.total_amount == 20000
    assert receipt.gross_amount == 22000
    assert receipt.discount_amount == 2000
    assert receipt.final_amount == 20000
    assert receipt.paid_amount == 20000
    assert receipt.vat_amount is None
    assert receipt.estimated_vat_amount is None
    assert receipt.vat_review_required is True
    assert "vat_review_hint" in receipt.vat_warnings
    assert receipt.sensitive_text_detected is True
    assert receipt.sensitive_text_categories == ["wifi_credential"]
    assert receipt.ocr_provider == "azure"
    assert_receipt_record_shape_for_downstream(receipt)
    assert_no_forbidden_parser_output(receipt)


def test_parse_edge_case_standard_context_core_fields() -> None:
    receipt = parse_standard_fixture("edge_case_receipt_standard.json")

    assert receipt.total_amount == 0
    assert receipt.final_amount == 5000
    assert receipt.paid_amount == 0
    assert receipt.approval_number == "APPROVAL-TEST-42"
    assert receipt.export_included is True
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "zero_paid_amount_requires_review" in receipt.parser_warnings
    assert "final_paid_amount_mismatch" in receipt.amount_warnings
    assert receipt.vat_amount is None
    assert "vat_review_hint" in receipt.vat_warnings
    assert_receipt_record_shape_for_downstream(receipt)
    assert_no_forbidden_parser_output(receipt)


def test_mock_standard_context_matches_legacy_core_fields() -> None:
    standard = parse_standard_fixture("mock_receipt_standard.json")
    legacy = parse_legacy_fixture("mock_receipt_legacy_text.txt")

    assert_selected_core_fields_match(
        legacy,
        standard,
        ["transaction_date", "total_amount", "supply_amount", "vat_amount", "vat_review_required"],
    )
    assert standard.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "diagnostic_code:completed" in standard.parser_warnings
    assert legacy.review_status == ReviewStatus.PENDING.value


def test_azure_like_standard_context_matches_legacy_core_fields() -> None:
    standard = parse_standard_fixture("azure_like_receipt_standard.json")
    legacy = parse_legacy_fixture("azure_like_receipt_legacy_text.txt")

    assert_selected_core_fields_match(
        legacy,
        standard,
        [
            "business_number",
            "total_amount",
            "gross_amount",
            "discount_amount",
            "paid_amount",
            "supply_amount",
            "vat_amount",
            "estimated_supply_amount",
            "estimated_vat_amount",
            "vat_source",
            "vat_review_required",
        ],
    )
    assert standard.final_amount == 20000  # Explicit standard candidate.
    assert legacy.final_amount is None  # No longer computed from gross minus discount.
    assert warning_sets(standard)["vat_warnings"] >= {"vat_not_explicit"}
    assert standard.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert legacy.review_status == ReviewStatus.NEEDS_REVIEW.value


def test_edge_case_standard_context_matches_legacy_safe_fields() -> None:
    standard = parse_standard_fixture("edge_case_receipt_standard.json")
    legacy = parse_legacy_fixture("edge_case_receipt_legacy_text.txt")

    assert_selected_core_fields_match(
        legacy,
        standard,
        ["total_amount", "paid_amount", "vat_amount"],
    )
    assert standard.ocr_provider == "mock"
    assert legacy.ocr_provider == "manual"
    assert standard.final_amount == 5000
    assert legacy.final_amount is None
    assert standard.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert legacy.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "final_paid_amount_mismatch" in standard.amount_warnings


def test_parse_azure_adapter_output_from_sanitized_fixture() -> None:
    receipt = parse_azure_adapter_fixture("azure_receipt_sanitized_response.json")

    assert receipt.merchant_name == "샘플카페"
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-05-14"
    assert receipt.total_amount == 12000
    assert receipt.supply_amount == 10909
    assert receipt.vat_amount == 1091
    assert receipt.payment_method == "card"
    assert receipt.ocr_provider == "azure"
    assert receipt.review_status == ReviewStatus.PENDING.value
    assert_no_forbidden_parser_output(receipt)


def test_parse_azure_adapter_edge_output_preserves_amount_separation() -> None:
    receipt = parse_azure_adapter_fixture("azure_receipt_edge_sanitized_response.json")

    assert receipt.gross_amount == 18000
    assert receipt.discount_amount == 3000
    assert receipt.final_amount == 15000
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0
    assert receipt.approval_number == "APPROVAL-42"
    assert receipt.vat_amount is None
    assert receipt.vat_review_required is True
    assert receipt.sensitive_text_detected is True
    assert receipt.sensitive_text_categories == ["wifi_credential"]
    assert "final_paid_amount_mismatch" in receipt.amount_warnings
    assert_no_forbidden_parser_output(receipt)


def test_parse_failed_azure_adapter_output_marks_needs_review() -> None:
    receipt = parse_azure_adapter_fixture("azure_receipt_failed_sanitized_response.json")

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert receipt.total_amount is None
    assert "ocr_status:failed" in receipt.parser_warnings
    assert "diagnostic_code:poll_timeout" in receipt.parser_warnings
    assert "poll_timeout" in receipt.parser_warnings
    assert_no_forbidden_parser_output(receipt)


def test_quantity_is_not_used_as_amount() -> None:
    receipt = parse_standard_fixture("edge_case_receipt_standard.json")

    assert_amount_fields_do_not_use_values(receipt, {1, 3, 10})
    assert receipt.total_amount == 0


def test_approval_number_is_not_used_as_amount() -> None:
    receipt = parse_standard_fixture("edge_case_receipt_standard.json")
    dumped_amounts = {receipt.to_dict().get(field_name) for field_name in AMOUNT_FIELD_NAMES}

    assert receipt.approval_number == "APPROVAL-TEST-42"
    assert "APPROVAL-TEST-42" not in dumped_amounts


def test_footer_number_is_not_used_as_amount() -> None:
    receipt = parse_standard_fixture("edge_case_receipt_standard.json")
    dumped = json.dumps(receipt.to_dict(), ensure_ascii=False, default=str)

    assert "REF-88" not in dumped
    assert_amount_fields_do_not_use_values(receipt, {88})


def test_business_number_is_not_used_as_amount() -> None:
    receipt = parse_standard_fixture("azure_like_receipt_standard.json")

    assert receipt.business_number == "000-00-00000"
    assert_amount_fields_do_not_use_values(receipt, {0})
    assert receipt.total_amount == 20000


def test_vat_missing_is_not_used_as_vat_amount() -> None:
    azure_like = parse_standard_fixture("azure_like_receipt_standard.json")
    edge = parse_standard_fixture("edge_case_receipt_standard.json")
    azure_edge = parse_azure_adapter_fixture("azure_receipt_edge_sanitized_response.json")

    assert azure_like.vat_amount is None
    assert edge.vat_amount is None
    assert azure_edge.vat_amount is None
    assert "vat_review_hint" in azure_like.vat_warnings
    assert "vat_review_hint" in edge.vat_warnings
    assert "vat_review_hint" in azure_edge.vat_warnings


def test_standard_parser_output_does_not_expose_raw_payload_fields() -> None:
    for receipt in [
        parse_standard_fixture("mock_receipt_standard.json"),
        parse_standard_fixture("azure_like_receipt_standard.json"),
        parse_standard_fixture("edge_case_receipt_standard.json"),
        parse_azure_adapter_fixture("azure_receipt_sanitized_response.json"),
        parse_azure_adapter_fixture("azure_receipt_edge_sanitized_response.json"),
        parse_azure_adapter_fixture("azure_receipt_failed_sanitized_response.json"),
    ]:
        assert_no_forbidden_parser_output(receipt)


def test_sensitive_categories_do_not_include_raw_sensitive_values() -> None:
    receipt = parse_standard_fixture("azure_like_receipt_standard.json")

    assert receipt.sensitive_text_detected is True
    assert receipt.sensitive_text_categories == ["wifi_credential"]
    assert "password" not in json.dumps(receipt.to_dict(), ensure_ascii=False, default=str).lower()
    assert "[REDACTED]" not in json.dumps(receipt.to_dict(), ensure_ascii=False, default=str)


def test_provider_fields_are_not_copied_to_receipt_record_as_raw_metadata() -> None:
    receipt = parse_azure_adapter_fixture("azure_receipt_sanitized_response.json")
    dumped = json.dumps(receipt.to_dict(), ensure_ascii=False, default=str)

    assert "provider_fields" not in dumped
    assert "adapter_version" not in dumped
    assert "normalized_block_count" not in dumped
    assert "normalized_candidate_count" not in dumped
    assert "provider_family" not in dumped


def test_legacy_raw_text_parser_still_passes_existing_entry_shape() -> None:
    receipt = parse_legacy_fixture("mock_receipt_legacy_text.txt")

    assert receipt.ocr_provider == "manual"
    assert receipt.total_amount == 12000
    assert receipt.vat_amount == 1091
    assert ReceiptParser().parse_text is not None


def test_standard_parser_entry_does_not_replace_legacy_entry() -> None:
    signature = inspect.signature(ReceiptParser.parse)

    assert list(signature.parameters) == ["self", "ocr_result"]
    assert hasattr(ReceiptParser, "parse_standard_context")
    assert hasattr(ReceiptParser, "parse_from_standard_ocr")


def test_standard_parser_entry_is_not_connected_to_default_app_flow() -> None:
    for relative_path in [
        "app/main.py",
        "app/ocr/azure_provider.py",
        "app/ocr/mock_provider.py",
    ]:
        text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "parse_standard_context" not in text
        assert "parse_from_standard_ocr" not in text


def test_standard_parser_record_has_downstream_required_shape() -> None:
    for receipt in [
        parse_standard_fixture("mock_receipt_standard.json"),
        parse_standard_fixture("azure_like_receipt_standard.json"),
        parse_standard_fixture("edge_case_receipt_standard.json"),
        parse_azure_adapter_fixture("azure_receipt_sanitized_response.json"),
    ]:
        assert_receipt_record_shape_for_downstream(receipt)
        assert_no_forbidden_parser_output(receipt)

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

from app.core.enums import EvidenceType, ReviewStatus
from app.core.standard_ocr import StandardOCRResult
from app.ocr.adapters.azure_standard_adapter import AzureStandardOCRAdapter
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import (
    StandardOCRParserContext,
    build_parser_context_from_standard_ocr,
)


STANDARD_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "standard_ocr"
AZURE_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "azure"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TEXT_PATTERNS = [
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
]


def load_standard_result(name: str) -> StandardOCRResult:
    return StandardOCRResult.model_validate_json(
        (STANDARD_FIXTURE_DIR / name).read_text(encoding="utf-8")
    )


def load_standard_context(name: str) -> StandardOCRParserContext:
    return build_parser_context_from_standard_ocr(load_standard_result(name))


def convert_azure_fixture(name: str) -> StandardOCRResult:
    response = json.loads((AZURE_FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return AzureStandardOCRAdapter().convert(
        response,
        source_file_id=f"source-{name}",
        source_file_name="sample_azure_receipt.pdf",
    )


def parse_fixture(name: str):
    result = load_standard_result(name)
    return ReceiptParser().parse_from_standard_ocr(result)


def test_parse_standard_context_from_mock_fixture_maps_core_fields() -> None:
    result = load_standard_result("mock_receipt_standard.json")
    context = build_parser_context_from_standard_ocr(result)

    receipt = ReceiptParser().parse_standard_context(
        context,
        source_file_id=result.source_file_id,
        source_file_name=result.source_file_name,
        ocr_provider=result.provider,
        confidence=result.confidence,
    )

    assert receipt.source_file_id == "file_mock_001"
    assert receipt.source_file_name == "sample_receipt_001.png"
    assert receipt.evidence_type == EvidenceType.RECEIPT_IMAGE.value
    assert receipt.merchant_name == context.candidate_map["merchant_name"][0]
    assert receipt.transaction_date and receipt.transaction_date.isoformat() == "2026-05-14"
    assert receipt.total_amount == 12000
    assert receipt.supply_amount == 10909
    assert receipt.vat_amount == 1091
    assert receipt.vat_source == "explicit"
    assert receipt.payment_method == "card"
    assert receipt.ocr_provider == "mock"
    assert receipt.confidence == 0.95


def test_parse_from_standard_ocr_keeps_standard_result_metadata() -> None:
    receipt = parse_fixture("mock_receipt_standard.json")

    assert receipt.source_file_id == "file_mock_001"
    assert receipt.source_file_name == "sample_receipt_001.png"
    assert receipt.ocr_provider == "mock"
    assert receipt.confidence == 0.95
    assert receipt.ocr_result_id is None
    assert receipt.stored_relative_path is None


def test_azure_like_context_keeps_amount_fields_and_vat_review_separate() -> None:
    context = load_standard_context("azure_like_receipt_standard.json")
    receipt = ReceiptParser().parse_standard_context(context)

    assert receipt.ocr_provider == "azure"
    assert receipt.business_number == "000-00-00000"
    assert receipt.gross_amount == 22000
    assert receipt.discount_amount == 2000
    assert receipt.final_amount == 20000
    assert receipt.paid_amount == 20000
    assert receipt.total_amount == 20000
    assert receipt.total_amount != receipt.business_number
    assert receipt.vat_amount is None
    assert receipt.vat_review_required is True
    assert "vat_review_required" in receipt.parser_warnings
    assert "vat_review_hint" in receipt.vat_warnings
    assert receipt.sensitive_text_detected is True
    assert receipt.sensitive_text_categories == ["wifi_credential"]


def test_edge_context_keeps_non_amount_numeric_candidates_out_of_total_amount() -> None:
    context = load_standard_context("edge_case_receipt_standard.json")
    receipt = ReceiptParser().parse_standard_context(context)

    assert receipt.total_amount == 0
    assert receipt.final_amount == 5000
    assert receipt.paid_amount == 0
    assert receipt.approval_number == "APPROVAL-TEST-42"
    assert receipt.total_amount not in {1, 3, 10}
    assert receipt.total_amount != "APPROVAL-TEST-42"
    assert receipt.total_amount != "REF-88"
    assert "final_paid_amount_mismatch" in receipt.amount_warnings
    assert "zero_paid_amount_requires_review" in receipt.parser_warnings
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert receipt.export_included is True


def test_azure_adapter_output_can_use_standard_context_parser_entry() -> None:
    result = convert_azure_fixture("azure_receipt_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)
    receipt = ReceiptParser().parse_standard_context(context, confidence=result.confidence)

    assert receipt.ocr_provider == "azure"
    assert receipt.total_amount == 12000
    assert receipt.supply_amount == 10909
    assert receipt.vat_amount == 1091
    assert receipt.payment_method == "card"
    assert receipt.review_status == ReviewStatus.PENDING.value


def test_failed_or_partial_context_returns_needs_review_record_with_diagnostic() -> None:
    result = convert_azure_fixture("azure_receipt_failed_sanitized_response.json")
    context = build_parser_context_from_standard_ocr(result)

    receipt = ReceiptParser().parse_standard_context(context)

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "ocr_status:failed" in receipt.parser_warnings
    assert "diagnostic_code:poll_timeout" in receipt.parser_warnings
    assert receipt.ocr_provider == "azure"


def test_standard_context_parser_output_does_not_expose_forbidden_payloads() -> None:
    context = load_standard_context("azure_like_receipt_standard.json")
    receipt = ReceiptParser().parse_standard_context(context)
    dumped = json.dumps(
        {
            "context": context.model_dump(mode="json"),
            "receipt": receipt.to_dict(),
        },
        ensure_ascii=False,
        default=str,
    )

    for pattern in FORBIDDEN_TEXT_PATTERNS:
        assert not re.search(pattern, dumped, flags=re.IGNORECASE), pattern
    assert "[REDACTED]" in dumped
    assert "wifi_credential" in dumped


def test_standard_context_parser_public_legacy_entry_is_unchanged() -> None:
    signature = inspect.signature(ReceiptParser.parse)

    assert list(signature.parameters) == ["self", "ocr_result"]


def test_standard_context_parser_entry_is_not_wired_to_runtime_flows() -> None:
    for relative_path in [
        "app/main.py",
        "app/ocr/azure_provider.py",
        "app/ocr/mock_provider.py",
    ]:
        text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "parse_standard_context" not in text
        assert "parse_from_standard_ocr" not in text

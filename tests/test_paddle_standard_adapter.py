from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from app.core.standard_ocr import StandardOCRResult
from app.ocr.adapters.azure_standard_adapter import AzureStandardOCRAdapter
from app.ocr.adapters.paddle_standard_adapter import PaddleStandardOCRAdapter
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "paddle"
AZURE_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "azure"
PADDLE_FIXTURES = [
    FIXTURE_DIR / "paddle_receipt_sanitized_result.json",
    FIXTURE_DIR / "paddle_receipt_edge_sanitized_result.json",
    FIXTURE_DIR / "paddle_receipt_empty_sanitized_result.json",
]

AMOUNT_CANDIDATE_TYPES = {
    "total_amount",
    "gross_amount",
    "discount_amount",
    "final_amount",
    "paid_amount",
    "supply_amount",
    "vat_amount",
}
FORBIDDEN_PROVIDER_FIELD_KEYS = {
    "raw_response",
    "raw_json",
    "provider_raw_response",
    "full_ocr_text",
    "paddle_raw_output",
    "image_path",
    "absolute_path",
    "model_path",
    "local_file_path",
    "headers",
    "endpoint",
    "api_key",
    "secret",
    "token",
    "password",
    "lines",
    "boxes",
    "key_value_candidates",
}
FORBIDDEN_TEXT_PATTERNS = [
    r"image_path",
    r"model_path",
    r"absolute_path",
    r"local_file_path",
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
    return PaddleStandardOCRAdapter().convert(
        load_fixture(name),
        source_file_id=f"source-{name}",
        source_file_name="sample_paddle_receipt.png",
    )


def candidate_types(result: StandardOCRResult) -> set[str]:
    return {
        candidate.candidate_type
        for candidate in result.key_value_candidates
        if candidate.candidate_type
    }


def test_convert_sanitized_paddle_receipt_to_standard_ocr_result() -> None:
    result = convert_fixture("paddle_receipt_sanitized_result.json")

    assert isinstance(result, StandardOCRResult)
    assert result.provider == "paddleocr"
    assert result.provider_version == "test"
    assert result.engine_runtime == "pc_local"
    assert result.status == "completed"
    assert result.provider_fields["adapter_version"] == "paddle-standard-adapter-v1"
    assert result.provider_fields["provider_family"] == "paddleocr"
    assert result.provider_fields["input_type"] == "image"
    assert result.pages
    assert result.text_blocks
    assert result.key_value_candidates
    assert result.confidence is None or 0 <= result.confidence <= 1


def test_provider_fields_contain_only_safe_metadata() -> None:
    result = convert_fixture("paddle_receipt_sanitized_result.json")
    provider_fields = result.provider_fields

    assert FORBIDDEN_PROVIDER_FIELD_KEYS.isdisjoint(provider_fields)
    assert provider_fields == {
        "provider_family": "paddleocr",
        "engine": "paddleocr",
        "engine_runtime": "pc_local",
        "adapter_version": "paddle-standard-adapter-v1",
        "language_hint": "ko",
        "page_count": 1,
        "image_count": 1,
        "normalized_block_count": 6,
        "normalized_candidate_count": 6,
        "normalized_table_count": 0,
        "has_angle_classifier": True,
        "has_gpu": False,
        "input_type": "image",
    }


def test_sanitized_paddle_fixtures_do_not_contain_forbidden_text() -> None:
    for fixture_path in PADDLE_FIXTURES:
        fixture_text = fixture_path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            assert not re.search(pattern, fixture_text, flags=re.IGNORECASE), (
                fixture_path.name,
                pattern,
            )


def test_adapter_output_does_not_contain_forbidden_text() -> None:
    for fixture_path in PADDLE_FIXTURES:
        result = convert_fixture(fixture_path.name)
        result_text = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            assert not re.search(pattern, result_text, flags=re.IGNORECASE), (
                fixture_path.name,
                pattern,
            )


def test_paddle_adapter_does_not_import_or_require_paddleocr() -> None:
    adapter_source = Path("app/ocr/adapters/paddle_standard_adapter.py").read_text(encoding="utf-8").lower()
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()

    assert "import paddleocr" not in adapter_source
    assert "from paddleocr" not in adapter_source
    assert "paddleocr" not in requirements


def test_candidate_types_are_mapped_from_regular_fixture() -> None:
    result = convert_fixture("paddle_receipt_sanitized_result.json")

    assert {
        "merchant_name",
        "transaction_date",
        "total_amount",
        "supply_amount",
        "vat_amount",
        "payment_method",
    }.issubset(candidate_types(result))


def test_edge_candidate_types_keep_amount_and_non_amount_values_separate() -> None:
    result = convert_fixture("paddle_receipt_edge_sanitized_result.json")
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
    result = convert_fixture("paddle_receipt_edge_sanitized_result.json")
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


def test_bbox_and_confidence_are_normalized() -> None:
    result = convert_fixture("paddle_receipt_sanitized_result.json")
    first_block = result.text_blocks[0]

    assert first_block.bbox == [20.0, 20.0, 220.0, 20.0, 220.0, 60.0, 20.0, 60.0]
    assert first_block.confidence == 0.96
    assert all(block.confidence is None or 0 <= block.confidence <= 1 for block in result.text_blocks)


def test_bbox_is_optional_and_low_confidence_is_warned() -> None:
    result = PaddleStandardOCRAdapter().convert(
        {
            "engine": "paddleocr",
            "engine_version": "test",
            "status": "succeeded",
            "input_type": "image",
            "image_count": 1,
            "lines": [
                {
                    "block_id": "no-bbox-low-confidence",
                    "text": "낮은 신뢰도 라인",
                    "confidence": 61,
                    "line_order": 0,
                }
            ],
            "key_value_candidates": [],
        },
        source_file_name="low_confidence.png",
    )

    assert result.text_blocks[0].bbox is None
    assert result.text_blocks[0].confidence == 0.61
    assert "paddle_low_confidence" in result.warnings


def test_empty_result_maps_diagnostic_code_without_exception() -> None:
    result = convert_fixture("paddle_receipt_empty_sanitized_result.json")
    context = build_parser_context_from_standard_ocr(result)

    assert result.status == "failed"
    assert result.diagnostic_code == "paddle_no_text_detected"
    assert "paddle_empty_result" in result.warnings
    assert context.safe_text_lines == []
    assert "paddle_no_text_detected" in " ".join(context.review_hints)


def test_adapter_output_can_build_parser_context_without_raw_payload_fields() -> None:
    result = convert_fixture("paddle_receipt_edge_sanitized_result.json")
    context = build_parser_context_from_standard_ocr(result)
    dumped = context.model_dump(mode="json")

    assert {"raw_json", "raw_text", "provider_raw_response", "full_ocr_text"}.isdisjoint(
        dumped
    )
    assert "paid_amount" in context.amount_candidate_map
    assert "approval_number" in context.non_amount_candidate_map
    assert "vat_missing" in context.non_amount_candidate_map


def test_adapter_output_can_be_parsed_by_standard_receipt_parser_entry() -> None:
    result = convert_fixture("paddle_receipt_sanitized_result.json")
    context = build_parser_context_from_standard_ocr(result)
    record = ReceiptParser().parse_standard_context(context, confidence=result.confidence)

    assert record.ocr_provider == "paddleocr"
    assert record.merchant_name == "샘플카페"
    assert record.transaction_date is not None
    assert record.total_amount == 12000
    assert record.supply_amount == 10909
    assert record.vat_amount == 1091
    assert record.source_file_name == "sample_paddle_receipt.png"


def test_edge_output_preserves_non_amount_and_vat_review_boundaries_in_parser_entry() -> None:
    result = convert_fixture("paddle_receipt_edge_sanitized_result.json")
    context = build_parser_context_from_standard_ocr(result)
    record = ReceiptParser().parse_standard_context(context, confidence=result.confidence)

    assert record.total_amount == 0
    assert record.gross_amount == 10000
    assert record.discount_amount == 10000
    assert record.final_amount == 0
    assert record.paid_amount == 0
    assert record.approval_number == "APPROVAL-PADDLE-42"
    assert record.business_number == "000-00-00000"
    assert record.vat_amount is None
    assert record.vat_review_required is True
    assert record.sensitive_text_detected is True
    assert record.sensitive_text_categories == ["wifi_credential"]


def test_empty_output_can_be_parsed_as_needs_review_record() -> None:
    result = convert_fixture("paddle_receipt_empty_sanitized_result.json")
    record = ReceiptParser().parse_from_standard_ocr(result)

    assert record.ocr_provider == "paddleocr"
    assert record.review_status == "needs_review"
    assert record.total_amount is None
    assert "paddle_no_text_detected" in " ".join(record.parser_warnings)


def test_provider_fields_are_not_copied_to_receipt_record_as_raw_metadata() -> None:
    result = convert_fixture("paddle_receipt_sanitized_result.json")
    record = ReceiptParser().parse_from_standard_ocr(result)
    record_text = json.dumps(asdict(record), ensure_ascii=False, default=str)

    assert "provider_fields" not in record_text
    assert "adapter_version" not in record_text
    assert "normalized_block_count" not in record_text


def test_paddle_and_azure_adapter_outputs_have_comparable_standard_shapes() -> None:
    paddle_result = convert_fixture("paddle_receipt_sanitized_result.json")
    azure_result = AzureStandardOCRAdapter().convert(
        json.loads(
            (AZURE_FIXTURE_DIR / "azure_receipt_sanitized_response.json").read_text(
                encoding="utf-8"
            )
        ),
        source_file_name="sample_azure_receipt.pdf",
    )

    assert isinstance(paddle_result, StandardOCRResult)
    assert isinstance(azure_result, StandardOCRResult)
    assert all(result.text_blocks for result in [paddle_result, azure_result])
    assert all(result.key_value_candidates for result in [paddle_result, azure_result])
    assert {"provider_family", "adapter_version"}.issubset(paddle_result.provider_fields)
    assert {"provider_family", "adapter_version"}.issubset(azure_result.provider_fields)


def test_pdf_processing_is_not_part_of_paddle_sanitized_adapter_scope() -> None:
    for fixture_path in PADDLE_FIXTURES:
        payload = load_fixture(fixture_path.name)
        assert payload.get("input_type") == "image"
        assert "pdf" not in json.dumps(payload, ensure_ascii=False).lower()

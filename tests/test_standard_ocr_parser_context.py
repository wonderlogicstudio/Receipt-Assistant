from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.core.standard_ocr import (
    StandardOCRKeyValueCandidate,
    StandardOCRResult,
    StandardOCRTextBlock,
    assert_no_forbidden_ocr_payload,
    has_absolute_path_risk,
    has_sensitive_secret_risk,
)
from app.parser.standard_ocr_context import (
    AMOUNT_CANDIDATE_TYPES,
    StandardOCRParserContext,
    build_parser_context_from_standard_ocr,
    compare_parser_context_shape,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "standard_ocr"


def test_mock_fixture_builds_parser_context() -> None:
    context = _context_from_fixture("mock_receipt_standard.json")

    assert context.provider == "mock"
    assert context.status == "completed"
    assert "테스트카페" in context.safe_text_lines
    assert context.amount_candidate_map["total_amount"] == ["12000"]
    assert context.non_amount_candidate_map["merchant_name"] == ["테스트카페"]


def test_azure_like_fixture_builds_parser_context() -> None:
    context = _context_from_fixture("azure_like_receipt_standard.json")

    assert context.provider == "azure"
    assert context.amount_candidate_map["gross_amount"] == ["22000"]
    assert context.amount_candidate_map["discount_amount"] == ["2000"]
    assert context.amount_candidate_map["final_amount"] == ["20000"]
    assert context.amount_candidate_map["paid_amount"] == ["20000"]
    assert "vat_missing:missing" in context.review_hints
    assert context.sensitive_categories == ["wifi_credential"]


def test_edge_case_fixture_builds_parser_context() -> None:
    context = _context_from_fixture("edge_case_receipt_standard.json")

    assert context.status == "partial"
    assert "ocr_status:partial" in context.review_hints
    assert "diagnostic_code:partial" in context.review_hints
    assert context.amount_candidate_map["final_amount"] == ["5000"]
    assert context.amount_candidate_map["paid_amount"] == ["0"]
    assert context.amount_candidate_map["total_amount"] == ["0"]


def test_parser_context_has_no_raw_payload_fields() -> None:
    context = _context_from_fixture("mock_receipt_standard.json")
    fields = set(StandardOCRParserContext.model_fields)
    payload = context.model_dump(mode="json")

    assert "raw_json" not in fields
    assert "raw_text" not in fields
    assert "provider_raw_response" not in fields
    assert "full_ocr_text" not in fields
    assert "raw_json" not in payload
    assert "raw_text" not in payload
    assert "provider_raw_response" not in payload
    assert "full_ocr_text" not in payload


def test_parser_context_has_no_paths_or_secret_keywords() -> None:
    context = _context_from_fixture("azure_like_receipt_standard.json")
    payload = context.model_dump(mode="json")
    payload_text = json.dumps(payload, ensure_ascii=False)

    assert has_absolute_path_risk(payload) is False
    assert has_sensitive_secret_risk(payload) is False
    assert "C:\\" not in payload_text
    assert "D:\\" not in payload_text
    assert "/Users/" not in payload_text
    assert "/home/" not in payload_text
    assert "/var/" not in payload_text
    assert "/tmp/" not in payload_text
    assert "api_key" not in payload_text.lower()
    assert "secret" not in payload_text.lower()
    assert "token" not in payload_text.lower()
    assert "password" not in payload_text.lower()
    assert "endpoint" not in payload_text.lower()


def test_sensitive_category_is_carried_without_sensitive_text() -> None:
    context = _context_from_fixture("azure_like_receipt_standard.json")

    assert context.sensitive_categories == ["wifi_credential"]
    assert "[REDACTED]" in context.safe_text_lines
    assert "wifi_credential" in context.review_hints[-1]


def test_non_amount_numeric_candidates_are_not_amount_candidates() -> None:
    context = _context_from_fixture("edge_case_receipt_standard.json")

    assert "quantity" not in context.amount_candidate_map
    assert "approval_number" not in context.amount_candidate_map
    assert "footer_number" not in context.amount_candidate_map
    assert context.non_amount_candidate_map["quantity"] == ["1", "3", "10"]
    assert context.non_amount_candidate_map["approval_number"] == ["APPROVAL-TEST-42"]
    assert context.non_amount_candidate_map["footer_number"] == ["REF-88"]


def test_business_number_is_not_amount_candidate() -> None:
    context = _context_from_fixture("azure_like_receipt_standard.json")

    assert "business_number" not in context.amount_candidate_map
    assert context.non_amount_candidate_map["business_number"] == ["0000000000"]


def test_known_amount_candidate_types_are_amount_candidates() -> None:
    result = _standard_result_with_candidates(
        [
            ("total_amount", "1000"),
            ("gross_amount", "1200"),
            ("discount_amount", "200"),
            ("final_amount", "1000"),
            ("paid_amount", "1000"),
            ("supply_amount", "909"),
            ("vat_amount", "91"),
        ]
    )

    context = build_parser_context_from_standard_ocr(result)

    assert set(context.amount_candidate_map) == AMOUNT_CANDIDATE_TYPES
    assert not set(context.amount_candidate_map) & set(context.non_amount_candidate_map)


def test_vat_review_candidates_are_review_hints_not_amounts() -> None:
    context = _context_from_fixture("edge_case_receipt_standard.json")

    assert "vat_missing" not in context.amount_candidate_map
    assert "vat_review_hint" not in context.amount_candidate_map
    assert context.non_amount_candidate_map["vat_missing"] == ["missing"]
    assert context.non_amount_candidate_map["vat_review_hint"] == ["review_required"]
    assert "vat_missing:missing" in context.review_hints
    assert "vat_review_hint:review_required" in context.review_hints


def test_candidate_without_source_block_ids_is_safe() -> None:
    result = _standard_result_with_candidates([("payment_method", "card")], source_block_ids=[])

    context = build_parser_context_from_standard_ocr(result)

    assert context.non_amount_candidate_map["payment_method"] == ["card"]


def test_context_generation_allows_empty_text_blocks() -> None:
    result = StandardOCRResult(
        id="standard_ocr_empty_blocks",
        provider="mock",
        status="completed",
        text_blocks=[],
        key_value_candidates=[],
        created_at=datetime.fromisoformat("2026-05-14T21:00:00+09:00"),
    )

    context = build_parser_context_from_standard_ocr(result)

    assert context.safe_text_lines == []
    assert context.candidate_map == {}


def test_context_generation_allows_empty_pages() -> None:
    result = StandardOCRResult(
        id="standard_ocr_empty_pages",
        provider="mock",
        status="completed",
        pages=[],
        text_blocks=[
            StandardOCRTextBlock(page_index=0, block_id="b001", text="합계 1,000")
        ],
        created_at=datetime.fromisoformat("2026-05-14T21:00:00+09:00"),
    )

    context = build_parser_context_from_standard_ocr(result)

    assert context.safe_text_lines == ["합계 1,000"]


def test_failed_result_adds_review_hints() -> None:
    result = StandardOCRResult(
        id="standard_ocr_failed",
        provider="azure",
        status="failed",
        warnings=["ocr_failed"],
        diagnostic_code="poll_http_503",
        created_at=datetime.fromisoformat("2026-05-14T21:00:00+09:00"),
    )

    context = build_parser_context_from_standard_ocr(result)

    assert "ocr_failed" in context.review_hints
    assert "ocr_status:failed" in context.review_hints
    assert "diagnostic_code:poll_http_503" in context.review_hints
    assert context.diagnostic_code == "poll_http_503"


def test_mock_and_azure_like_context_shape_can_be_compared() -> None:
    mock_context = _context_from_fixture("mock_receipt_standard.json")
    azure_context = _context_from_fixture("azure_like_receipt_standard.json")

    comparison = compare_parser_context_shape(mock_context, azure_context)

    assert comparison["left_provider"] == "mock"
    assert comparison["right_provider"] == "azure"
    assert "merchant_name" in comparison["shared_candidate_types"]
    assert "merchant_name" in comparison["shared_non_amount_candidate_types"]
    assert "gross_amount" in comparison["right_amount_candidate_types"]


def test_edge_case_total_amount_sources_are_separate_from_non_amount_sources() -> None:
    context = _context_from_fixture("edge_case_receipt_standard.json")

    assert context.amount_candidate_map["total_amount"] == ["0"]
    assert "0" not in context.non_amount_candidate_map["quantity"]
    assert set(context.amount_candidate_map).isdisjoint({"quantity", "approval_number", "footer_number"})


def test_context_payload_passes_forbidden_payload_guard() -> None:
    context = _context_from_fixture("edge_case_receipt_standard.json")

    assert_no_forbidden_ocr_payload(context.model_dump(mode="json"))


def test_context_extracts_address_hint_from_safe_lines() -> None:
    result = StandardOCRResult(
        id="standard_ocr_address_hint",
        provider="paddleocr",
        status="completed",
        text_blocks=[
            StandardOCRTextBlock(page_index=0, block_id="b001", text="상호명 테스트상점"),
            StandardOCRTextBlock(page_index=0, block_id="b002", text="주소 서울특별시 서대문구 이화여대길 52-31"),
        ],
        key_value_candidates=[],
        created_at=datetime.fromisoformat("2026-05-14T21:00:00+09:00"),
    )

    context = build_parser_context_from_standard_ocr(result)

    assert context.address_hint == {
        "road_address_hint": "서울특별시 서대문구 이화여대길 52-31",
        "road_name": "이화여대길",
        "building_main_number": "52",
        "building_sub_number": "31",
    }


def test_context_does_not_extract_forbidden_numeric_lines_as_address_hint() -> None:
    result = StandardOCRResult(
        id="standard_ocr_no_address_hint",
        provider="paddleocr",
        status="completed",
        text_blocks=[
            StandardOCRTextBlock(page_index=0, block_id="b001", text="사업자번호 123-45-67890"),
            StandardOCRTextBlock(page_index=0, block_id="b002", text="전화 02-1234-5678"),
            StandardOCRTextBlock(page_index=0, block_id="b003", text="합계금액 50,000원"),
            StandardOCRTextBlock(page_index=0, block_id="b004", text="거래일자 2026-06-10"),
        ],
        key_value_candidates=[],
        created_at=datetime.fromisoformat("2026-05-14T21:00:00+09:00"),
    )

    context = build_parser_context_from_standard_ocr(result)

    assert context.address_hint is None


def _context_from_fixture(fixture_name: str) -> StandardOCRParserContext:
    return build_parser_context_from_standard_ocr(_standard_result_from_fixture(fixture_name))


def _standard_result_from_fixture(fixture_name: str) -> StandardOCRResult:
    return StandardOCRResult.model_validate_json((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))


def _standard_result_with_candidates(
    candidates: list[tuple[str, str]],
    *,
    source_block_ids: list[str] | None = None,
) -> StandardOCRResult:
    blocks = [
        StandardOCRTextBlock(
            page_index=0,
            block_id="b001",
            text="테스트 라인",
            normalized_text="테스트 라인",
        )
    ]
    candidate_models = [
        StandardOCRKeyValueCandidate(
            key=candidate_type,
            value=value,
            normalized_value=value,
            source_block_ids=["b001"] if source_block_ids is None else source_block_ids,
            candidate_type=candidate_type,
        )
        for candidate_type, value in candidates
    ]
    return StandardOCRResult(
        id="standard_ocr_candidate_test",
        provider="mock",
        status="completed",
        text_blocks=blocks,
        key_value_candidates=candidate_models,
        created_at=datetime.fromisoformat("2026-05-14T21:00:00+09:00"),
    )

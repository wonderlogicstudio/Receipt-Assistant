from __future__ import annotations

from datetime import date
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

from app.core.enums import ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.core.standard_ocr import StandardOCRResult
from app.ocr.adapters.paddle_standard_adapter import PaddleStandardOCRAdapter
from app.ocr.paddle_provider import build_paddle_candidate_hints_from_safe_lines
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "paddle_synthetic"
CASES_PATH = FIXTURE_DIR / "cases.json"

FORBIDDEN_KEYS = {
    "raw_text",
    "raw_json",
    "raw_response",
    "provider_raw_response",
    "full_ocr_text",
    "paddle_raw_output",
}
FORBIDDEN_TEXT_PATTERNS = [
    r"raw_text",
    r"raw_json",
    r"raw_response",
    r"provider_raw_response",
    r"full_ocr_text",
    r"paddle_raw_output",
    r"secret",
    r"token",
    r"endpoint",
    r"operation-location",
    r"https?://",
    r"[A-Za-z]:\\",
    r"/Users/",
    r"/home/",
    r"주민등록번호",
    r"비밀번호",
    r"WiFi PW",
    r"카드번호",
    r"\b\d{13,19}\b",
    r"\b\d{6}-\d{7}\b",
    r"\b0\d{1,2}[-\s]\d{3,4}[-\s]\d{4}\b",
]
AMOUNT_FIELDS = {
    "total_amount",
    "gross_amount",
    "discount_amount",
    "final_amount",
    "paid_amount",
    "supply_amount",
    "vat_amount",
    "estimated_supply_amount",
    "estimated_vat_amount",
}


def load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def build_paddle_standard_result_from_synthetic_case(case: dict[str, Any]) -> StandardOCRResult:
    lines: list[dict[str, Any]] = []
    for index, line in enumerate(case["paddle_lines"]):
        sensitive_category = line.get("sensitive_category")
        text = "[REDACTED]" if sensitive_category else str(line["text"]).strip()
        lines.append(
            {
                "block_id": f"{case['sample_id']}-p0-l{index}",
                "page_index": 0,
                "line_order": index,
                "text": text,
                "normalized_text": text,
                "confidence": line.get("confidence"),
                "sensitive_category": sensitive_category,
                "block_type": "line",
            }
        )

    candidates = build_paddle_candidate_hints_from_safe_lines(lines)
    payload = {
        "engine": "paddleocr",
        "engine_version": "synthetic",
        "status": "succeeded",
        "language_hint": "ko",
        "input_type": "image",
        "image_count": 1,
        "pages": [{"page_index": 0, "unit": "synthetic"}],
        "lines": lines,
        "key_value_candidates": candidates,
        "warnings": ["synthetic_paddle_quality_fixture"],
    }
    return PaddleStandardOCRAdapter().convert(
        payload,
        source_file_id=f"synthetic-{case['sample_id']}",
        source_file_name=case["source_file_name"],
        provider_version="synthetic",
    )


def parse_synthetic_case(case: dict[str, Any]) -> ReceiptRecord:
    result = build_paddle_standard_result_from_synthetic_case(case)
    context = build_parser_context_from_standard_ocr(result)
    return ReceiptParser().parse_standard_context(
        context,
        source_file_id=result.source_file_id,
        source_file_name=result.source_file_name,
        ocr_provider=result.provider,
        confidence=result.confidence,
    )


def assert_no_forbidden_key_names(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            assert str(key).lower() not in FORBIDDEN_KEYS, key
            assert_no_forbidden_key_names(nested_value)
    elif isinstance(value, list):
        for item in value:
            assert_no_forbidden_key_names(item)


def assert_no_forbidden_text(value: Any) -> None:
    dumped = json.dumps(value, ensure_ascii=False, default=str)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        assert not re.search(pattern, dumped, flags=re.IGNORECASE), pattern


def record_value(record: ReceiptRecord, field_name: str) -> Any:
    value = getattr(record, field_name)
    if isinstance(value, date):
        return value.isoformat()
    return value


def assert_expected_fields(case: dict[str, Any], record: ReceiptRecord) -> None:
    expected = dict(case["expected"])
    review_required_expected = expected.pop("review_required_expected", None)
    for field_name, expected_value in expected.items():
        actual_value = record_value(record, field_name)
        if isinstance(expected_value, list):
            assert set(expected_value).issubset(set(actual_value or [])), (case["sample_id"], field_name)
        else:
            assert actual_value == expected_value, (case["sample_id"], field_name, actual_value, expected_value)

    if review_required_expected is True:
        assert record.review_status == ReviewStatus.NEEDS_REVIEW.value or record.review_reasons
    elif review_required_expected is False:
        assert record.review_status == ReviewStatus.PENDING.value


def candidate_values(result: StandardOCRResult) -> list[str]:
    return [
        str(candidate.normalized_value or candidate.value or "")
        for candidate in result.key_value_candidates
    ]


@pytest.fixture(scope="module")
def synthetic_cases() -> list[dict[str, Any]]:
    return load_cases()


def test_loads_at_least_twenty_synthetic_cases(synthetic_cases: list[dict[str, Any]]) -> None:
    assert len(synthetic_cases) >= 20
    sample_ids = [case["sample_id"] for case in synthetic_cases]
    assert len(sample_ids) == len(set(sample_ids))


def test_synthetic_fixture_shape_and_security(synthetic_cases: list[dict[str, Any]]) -> None:
    assert_no_forbidden_key_names(synthetic_cases)
    assert_no_forbidden_text(synthetic_cases)
    for case in synthetic_cases:
        assert case["sample_id"].startswith("synthetic_")
        assert case["source_file_name"].startswith("synthetic_")
        assert "/" not in case["source_file_name"]
        assert "\\" not in case["source_file_name"]
        assert isinstance(case.get("description"), str) and case["description"]
        assert isinstance(case.get("paddle_lines"), list) and case["paddle_lines"]
        assert isinstance(case.get("expected"), dict) and case["expected"]
        for line in case["paddle_lines"]:
            assert "text" in line
            assert "confidence" in line
            if line.get("sensitive_category"):
                assert line["text"] == "[REDACTED]"


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["sample_id"])
def test_synthetic_cases_parse_to_expected_receipt_fields(case: dict[str, Any]) -> None:
    result = build_paddle_standard_result_from_synthetic_case(case)
    context = build_parser_context_from_standard_ocr(result)
    record = ReceiptParser().parse_standard_context(
        context,
        source_file_id=result.source_file_id,
        source_file_name=result.source_file_name,
        ocr_provider=result.provider,
        confidence=result.confidence,
    )

    assert isinstance(result, StandardOCRResult)
    assert result.provider == "paddleocr"
    assert context.provider == "paddleocr"
    assert record.ocr_provider == "paddleocr"
    assert_expected_fields(case, record)
    assert_no_forbidden_text(result.model_dump(mode="json"))
    assert_no_forbidden_text(context.model_dump(mode="json"))
    assert_no_forbidden_text(record.to_dict())


def test_sensitive_redacted_lines_are_not_used_as_parser_candidates(synthetic_cases: list[dict[str, Any]]) -> None:
    sensitive_cases = [case for case in synthetic_cases if any(line.get("sensitive_category") for line in case["paddle_lines"])]
    assert sensitive_cases
    for case in sensitive_cases:
        result = build_paddle_standard_result_from_synthetic_case(case)
        assert "[REDACTED]" not in candidate_values(result)
        context = build_parser_context_from_standard_ocr(result)
        record = ReceiptParser().parse_standard_context(context)
        expected_categories = [
            line["sensitive_category"]
            for line in case["paddle_lines"]
            if line.get("sensitive_category")
        ]
        assert set(expected_categories).issubset(set(record.sensitive_text_categories))
        assert record.sensitive_text_detected is True


def test_noise_numbers_are_not_used_as_amounts(synthetic_cases: list[dict[str, Any]]) -> None:
    noise_cases = {
        "synthetic_approval_number_001": {12345678},
        "synthetic_quantity_many_001": {1, 3, 10},
        "synthetic_footer_number_001": {12, 45},
    }
    by_id = {case["sample_id"]: case for case in synthetic_cases}
    for sample_id, forbidden_amounts in noise_cases.items():
        record = parse_synthetic_case(by_id[sample_id])
        for field_name in AMOUNT_FIELDS:
            value = getattr(record, field_name)
            if field_name == "total_amount" and value == 0:
                continue
            assert value not in forbidden_amounts, (sample_id, field_name, value)


def test_vat_missing_cases_keep_vat_amount_unset(synthetic_cases: list[dict[str, Any]]) -> None:
    for case in synthetic_cases:
        if case["expected"].get("vat_amount", "not-set") is not None:
            continue
        record = parse_synthetic_case(case)
        assert record.vat_amount is None, case["sample_id"]


def test_hoam_card_sales_slip_matches_saved_azure_anchor_without_live_azure(
    synthetic_cases: list[dict[str, Any]],
) -> None:
    case = next(case for case in synthetic_cases if case["sample_id"] == "synthetic_card_sales_slip_hoam_001")
    record = parse_synthetic_case(case)

    assert record.merchant_name == "호암비엠 종각역점"
    assert record.transaction_date and record.transaction_date.isoformat() == "2026-05-10"
    assert record.business_number == "897-81-03545"
    assert record.total_amount == 60000
    assert record.final_amount == 60000
    assert record.payment_method == "카드"
    assert record.supply_amount == 54546
    assert record.vat_amount == 5454


def test_candidate_hint_builder_does_not_guess_unlabeled_merchant_or_total() -> None:
    lines = [
        {
            "block_id": "unlabeled-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "SAMPLE STORE",
            "normalized_text": "SAMPLE STORE",
            "confidence": 0.98,
        },
        {
            "block_id": "unlabeled-p0-l1",
            "page_index": 0,
            "line_order": 1,
            "text": "item 1 2,000",
            "normalized_text": "item 1 2,000",
            "confidence": 0.93,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert "merchant_name" not in candidates
    assert "total_amount" not in candidates


def test_candidate_hint_builder_does_not_use_card_brand_as_amount_label() -> None:
    lines = [
        {
            "block_id": "card-brand-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "신한카드",
            "normalized_text": "신한카드",
            "confidence": 0.97,
        },
        {
            "block_id": "card-brand-p0-l1",
            "page_index": 0,
            "line_order": 1,
            "text": "4,897",
            "normalized_text": "4,897",
            "confidence": 0.99,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["payment_method"] == "카드"
    assert "paid_amount" not in candidates
    assert "total_amount" not in candidates
    assert "final_amount" not in candidates


def test_candidate_hint_builder_prefers_top_repeated_card_slip_amount() -> None:
    lines = [
        {
            "block_id": "card-slip-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "509",
            "normalized_text": "509",
            "confidence": 1.0,
        },
        {
            "block_id": "card-slip-p0-l1",
            "page_index": 0,
            "line_order": 1,
            "text": "5,600",
            "normalized_text": "5,600",
            "confidence": 1.0,
        },
        {
            "block_id": "card-slip-p0-l2",
            "page_index": 0,
            "line_order": 2,
            "text": "신한카드",
            "normalized_text": "신한카드",
            "confidence": 0.97,
        },
        {
            "block_id": "card-slip-p0-l3",
            "page_index": 0,
            "line_order": 3,
            "text": "5,091",
            "normalized_text": "5,091",
            "confidence": 1.0,
        },
        {
            "block_id": "card-slip-p0-l4",
            "page_index": 0,
            "line_order": 4,
            "text": "5,600",
            "normalized_text": "5,600",
            "confidence": 1.0,
        },
        {
            "block_id": "card-slip-p0-l5",
            "page_index": 0,
            "line_order": 5,
            "text": "5,091",
            "normalized_text": "5,091",
            "confidence": 1.0,
        },
        {
            "block_id": "card-slip-p0-l6",
            "page_index": 0,
            "line_order": 6,
            "text": "5,600",
            "normalized_text": "5,600",
            "confidence": 1.0,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["payment_method"] == "카드"
    assert candidates["total_amount"] == "5600"
    assert candidates["paid_amount"] == "5600"
    assert "final_amount" not in candidates


def test_candidate_hint_builder_uses_top_amount_instead_of_late_repeat() -> None:
    lines = [
        {
            "block_id": "late-repeat-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "19,100",
            "normalized_text": "19,100",
            "confidence": 1.0,
        },
        {
            "block_id": "late-repeat-p0-l1",
            "page_index": 0,
            "line_order": 1,
            "text": "우리카드",
            "normalized_text": "우리카드",
            "confidence": 0.99,
        },
        *[
            {
                "block_id": f"late-repeat-p0-l{index}",
                "page_index": 0,
                "line_order": index,
                "text": "내용",
                "normalized_text": "내용",
                "confidence": 0.9,
            }
            for index in range(2, 9)
        ],
        {
            "block_id": "late-repeat-p0-l9",
            "page_index": 0,
            "line_order": 9,
            "text": "6,900",
            "normalized_text": "6,900",
            "confidence": 1.0,
        },
        {
            "block_id": "late-repeat-p0-l10",
            "page_index": 0,
            "line_order": 10,
            "text": "6,900",
            "normalized_text": "6,900",
            "confidence": 1.0,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["payment_method"] == "카드"
    assert candidates["total_amount"] == "19100"
    assert candidates["paid_amount"] == "19100"
    assert "final_amount" not in candidates


def test_candidate_hint_builder_uses_strong_repeated_card_amount() -> None:
    lines = [
        {
            "block_id": "strong-repeat-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "신한카드",
            "normalized_text": "신한카드",
            "confidence": 0.98,
        },
        {"block_id": "strong-repeat-p0-l1", "page_index": 0, "line_order": 1, "text": "1,600", "normalized_text": "1,600", "confidence": 1.0},
        {"block_id": "strong-repeat-p0-l2", "page_index": 0, "line_order": 2, "text": "600", "normalized_text": "600", "confidence": 1.0},
        {"block_id": "strong-repeat-p0-l3", "page_index": 0, "line_order": 3, "text": "2,000", "normalized_text": "2,000", "confidence": 1.0},
        {"block_id": "strong-repeat-p0-l4", "page_index": 0, "line_order": 4, "text": "1,600", "normalized_text": "1,600", "confidence": 1.0},
        {"block_id": "strong-repeat-p0-l5", "page_index": 0, "line_order": 5, "text": "400", "normalized_text": "400", "confidence": 1.0},
        {"block_id": "strong-repeat-p0-l6", "page_index": 0, "line_order": 6, "text": "1,600", "normalized_text": "1,600", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["payment_method"] == "카드"
    assert candidates["paid_amount"] == "1600"
    assert candidates["total_amount"] == "1600"


def test_candidate_hint_builder_prefers_company_over_address_near_business_number() -> None:
    lines = [
        {
            "block_id": "business-block-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "주식회사청초수",
            "normalized_text": "주식회사청초수",
            "confidence": 0.99,
        },
        {
            "block_id": "business-block-p0-l1",
            "page_index": 0,
            "line_order": 1,
            "text": "강원도속초시",
            "normalized_text": "강원도속초시",
            "confidence": 0.92,
        },
        {
            "block_id": "business-block-p0-l2",
            "page_index": 0,
            "line_order": 2,
            "text": "2278120556",
            "normalized_text": "2278120556",
            "confidence": 0.99,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "2278120556"
    assert candidates["merchant_name"] == "주식회사청초수"


def test_candidate_hint_builder_rejects_short_or_noisy_business_block_merchants() -> None:
    lines = [
        {
            "block_id": "noisy-business-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "마",
            "normalized_text": "마",
            "confidence": 0.99,
        },
        {
            "block_id": "noisy-business-p0-l1",
            "page_index": 0,
            "line_order": 1,
            "text": "점확하고",
            "normalized_text": "점확하고",
            "confidence": 0.9,
        },
        {
            "block_id": "noisy-business-p0-l2",
            "page_index": 0,
            "line_order": 2,
            "text": "104-81-91189",
            "normalized_text": "104-81-91189",
            "confidence": 0.99,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "104-81-91189"
    assert "merchant_name" not in candidates


def test_candidate_hint_builder_finds_labeled_business_name_farther_above_number() -> None:
    lines = [
        {"block_id": "far-business-p0-l0", "page_index": 0, "line_order": 0, "text": "직영프라자주유소", "normalized_text": "직영프라자주유소", "confidence": 0.99},
        {"block_id": "far-business-p0-l1", "page_index": 0, "line_order": 1, "text": "단가:003원/", "normalized_text": "단가:003원/", "confidence": 0.9},
        {"block_id": "far-business-p0-l2", "page_index": 0, "line_order": 2, "text": "고유번호:71-2-2004", "normalized_text": "고유번호:71-2-2004", "confidence": 0.9},
        {"block_id": "far-business-p0-l3", "page_index": 0, "line_order": 3, "text": "835013001", "normalized_text": "835013001", "confidence": 0.9},
        {"block_id": "far-business-p0-l4", "page_index": 0, "line_order": 4, "text": "점확하고", "normalized_text": "점확하고", "confidence": 0.9},
        {"block_id": "far-business-p0-l5", "page_index": 0, "line_order": 5, "text": "롬몰/J0", "normalized_text": "롬몰/J0", "confidence": 0.66},
        {"block_id": "far-business-p0-l6", "page_index": 0, "line_order": 6, "text": "123-45-67891", "normalized_text": "123-45-67891", "confidence": 0.92},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "123-45-67891"
    assert candidates["merchant_name"] == "직영프라자주유소"


def test_candidate_hint_builder_accepts_two_digit_year_receipt_date() -> None:
    lines = [
        {
            "block_id": "two-digit-date-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "26/05/24",
            "normalized_text": "26/05/24",
            "confidence": 0.93,
        }
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["transaction_date"] == "26/05/24"


def test_candidate_hint_builder_reconstructs_korean_date_fragments_and_trailing_dash_business_number() -> None:
    lines = [
        {"block_id": "korean-date-p0-l0", "page_index": 0, "line_order": 0, "text": "행촌제2주유소", "normalized_text": "행촌제2주유소", "confidence": 0.99},
        {"block_id": "korean-date-p0-l1", "page_index": 0, "line_order": 1, "text": "사업자N0:110-20-", "normalized_text": "사업자N0:110-20-", "confidence": 0.99},
        {"block_id": "korean-date-p0-l2", "page_index": 0, "line_order": 2, "text": "-28152", "normalized_text": "-28152", "confidence": 0.99},
        {"block_id": "korean-date-p0-l3", "page_index": 0, "line_order": 3, "text": "[등록]2026", "normalized_text": "[등록]2026", "confidence": 0.99},
        {"block_id": "korean-date-p0-l4", "page_index": 0, "line_order": 4, "text": "02", "normalized_text": "02", "confidence": 0.99},
        {"block_id": "korean-date-p0-l5", "page_index": 0, "line_order": 5, "text": "POSNo", "normalized_text": "POSNo", "confidence": 0.9},
        {"block_id": "korean-date-p0-l6", "page_index": 0, "line_order": 6, "text": "년05", "normalized_text": "년05", "confidence": 0.99},
        {"block_id": "korean-date-p0-l7", "page_index": 0, "line_order": 7, "text": "월27일수", "normalized_text": "월27일수", "confidence": 0.99},
        {"block_id": "korean-date-p0-l8", "page_index": 0, "line_order": 8, "text": "신용카드", "normalized_text": "신용카드", "confidence": 0.99},
        {"block_id": "korean-date-p0-l9", "page_index": 0, "line_order": 9, "text": "50,000", "normalized_text": "50,000", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "110-20-28152"
    assert candidates["transaction_date"] == "2026-05-27"


def test_candidate_hint_builder_uses_top_card_slip_amount_without_final_guess() -> None:
    lines = [
        {
            "block_id": "top-card-amount-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "20,000",
            "normalized_text": "20,000",
            "confidence": 0.95,
        },
        {
            "block_id": "top-card-amount-p0-l1",
            "page_index": 0,
            "line_order": 1,
            "text": "신한카드",
            "normalized_text": "신한카드",
            "confidence": 0.97,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["payment_method"] == "카드"
    assert candidates["paid_amount"] == "20000"
    assert candidates["total_amount"] == "20000"
    assert "final_amount" not in candidates


def test_candidate_hint_builder_uses_largest_nearby_amount_for_split_total_label() -> None:
    lines = [
        {"block_id": "split-total-p0-l0", "page_index": 0, "line_order": 0, "text": "Total:", "normalized_text": "Total:", "confidence": 0.99},
        {"block_id": "split-total-p0-l1", "page_index": 0, "line_order": 1, "text": "95", "normalized_text": "95", "confidence": 0.75},
        {"block_id": "split-total-p0-l2", "page_index": 0, "line_order": 2, "text": "공급가액:", "normalized_text": "공급가액:", "confidence": 0.99},
        {"block_id": "split-total-p0-l3", "page_index": 0, "line_order": 3, "text": "86,364", "normalized_text": "86,364", "confidence": 0.94},
        {"block_id": "split-total-p0-l4", "page_index": 0, "line_order": 4, "text": "부가세:", "normalized_text": "부가세:", "confidence": 0.99},
        {"block_id": "split-total-p0-l5", "page_index": 0, "line_order": 5, "text": "8,636", "normalized_text": "8,636", "confidence": 1.0},
        {"block_id": "split-total-p0-l6", "page_index": 0, "line_order": 6, "text": "합계금액:", "normalized_text": "합계금액:", "confidence": 1.0},
        {"block_id": "split-total-p0-l7", "page_index": 0, "line_order": 7, "text": "95,000", "normalized_text": "95,000", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "95000"
    assert candidates["final_amount"] == "95000"
    assert candidates["supply_amount"] == "86364"
    assert candidates["vat_amount"] == "8636"


def test_candidate_hint_builder_uses_previous_amount_for_columnar_supply_and_split_vat_label() -> None:
    lines = [
        {"block_id": "column-tax-p0-l0", "page_index": 0, "line_order": 0, "text": "합계금액", "normalized_text": "합계금액", "confidence": 1.0},
        {"block_id": "column-tax-p0-l1", "page_index": 0, "line_order": 1, "text": "115,456", "normalized_text": "115,456", "confidence": 1.0},
        {"block_id": "column-tax-p0-l2", "page_index": 0, "line_order": 2, "text": "공급가액", "normalized_text": "공급가액", "confidence": 1.0},
        {"block_id": "column-tax-p0-l3", "page_index": 0, "line_order": 3, "text": "11,544", "normalized_text": "11,544", "confidence": 1.0},
        {"block_id": "column-tax-p0-l4", "page_index": 0, "line_order": 4, "text": "부", "normalized_text": "부", "confidence": 1.0},
        {"block_id": "column-tax-p0-l5", "page_index": 0, "line_order": 5, "text": "가", "normalized_text": "가", "confidence": 1.0},
        {"block_id": "column-tax-p0-l6", "page_index": 0, "line_order": 6, "text": "127,000", "normalized_text": "127,000", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["supply_amount"] == "115456"
    assert candidates["vat_amount"] == "11544"
    assert candidates["total_amount"] == "127000"


def test_candidate_hint_builder_does_not_pull_total_into_split_vat_label() -> None:
    lines = [
        {"block_id": "split-vat-guard-p0-l0", "page_index": 0, "line_order": 0, "text": "부가세", "normalized_text": "부가세", "confidence": 1.0},
        {"block_id": "split-vat-guard-p0-l1", "page_index": 0, "line_order": 1, "text": "과세물품가액", "normalized_text": "과세물품가액", "confidence": 1.0},
        {"block_id": "split-vat-guard-p0-l2", "page_index": 0, "line_order": 2, "text": "41", "normalized_text": "41", "confidence": 1.0},
        {"block_id": "split-vat-guard-p0-l3", "page_index": 0, "line_order": 3, "text": "820", "normalized_text": "820", "confidence": 1.0},
        {"block_id": "split-vat-guard-p0-l4", "page_index": 0, "line_order": 4, "text": "180", "normalized_text": "180", "confidence": 1.0},
        {"block_id": "split-vat-guard-p0-l5", "page_index": 0, "line_order": 5, "text": "부", "normalized_text": "부", "confidence": 1.0},
        {"block_id": "split-vat-guard-p0-l6", "page_index": 0, "line_order": 6, "text": "가", "normalized_text": "가", "confidence": 1.0},
        {"block_id": "split-vat-guard-p0-l7", "page_index": 0, "line_order": 7, "text": "46,000", "normalized_text": "46,000", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert "vat_amount" not in candidates
    assert candidates["supply_amount"] == "41820"


def test_parser_estimates_vat_from_explicit_supply_difference_without_confirming_vat() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_supply_difference_estimated_vat_001",
            "source_file_name": "synthetic_supply_difference_estimated_vat_001.jpg",
            "paddle_lines": [
                {"text": "매장명 오대산가마솥식당", "confidence": 0.99},
                {"text": "사업자등록번호 219-30-43463", "confidence": 0.99},
                {"text": "매출일 2026-05-22", "confidence": 0.99},
                {"text": "과세물품가액", "confidence": 0.99},
                {"text": "41", "confidence": 0.99},
                {"text": "820", "confidence": 0.99},
                {"text": "받은금액 46,000", "confidence": 0.99},
                {"text": "신용 카드 46,000", "confidence": 0.99},
            ],
            "expected": {
                "merchant_name": "오대산가마솥식당",
                "business_number": "219-30-43463",
                "transaction_date": "2026-05-22",
                "total_amount": 46000,
                "final_amount": 46000,
                "paid_amount": 46000,
                "supply_amount": 41820,
                "vat_amount": None,
                "estimated_vat_amount": 4180,
                "vat_review_required": True,
                "review_required_expected": True,
            },
        }
    )

    assert record.vat_amount is None
    assert record.estimated_supply_amount == 41820
    assert record.estimated_vat_amount == 4180


def test_parser_uses_standalone_total_label_and_does_not_treat_supply_as_vat() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_standalone_total_and_tax_order_guard_001",
            "source_file_name": "synthetic_standalone_total_and_tax_order_guard_001.jpg",
            "paddle_lines": [
                {"text": "매장명 총각김밥", "confidence": 0.99},
                {"text": "사업자등록번호 152-21-01299", "confidence": 0.99},
                {"text": "2026-05-19 12:57:04", "confidence": 0.99},
                {"text": "묵은지참치김밥", "confidence": 0.88},
                {"text": "5600", "confidence": 0.99},
                {"text": "계", "confidence": 0.99},
                {"text": "5600", "confidence": 0.99},
                {"text": "부가세", "confidence": 0.99},
                {"text": "과세물품가액", "confidence": 0.99},
                {"text": "5091", "confidence": 0.99},
                {"text": "509", "confidence": 0.99},
                {"text": "카드 5600", "confidence": 0.99},
            ],
            "expected": {
                "merchant_name": "총각김밥",
                "business_number": "152-21-01299",
                "transaction_date": "2026-05-19",
                "total_amount": 5600,
                "final_amount": 5600,
                "paid_amount": 5600,
                "supply_amount": 5091,
                "vat_amount": None,
                "estimated_vat_amount": 509,
                "payment_method": "카드",
                "review_required_expected": True,
            },
        }
    )

    assert record.vat_amount is None
    assert record.supply_amount == 5091
    assert record.estimated_vat_amount == 509


def test_candidate_hint_builder_reconstructs_split_date_and_business_number_fragments() -> None:
    lines = [
        {"block_id": "split-id-date-p0-l0", "page_index": 0, "line_order": 0, "text": "[226-", "normalized_text": "[226-", "confidence": 1.0},
        {"block_id": "split-id-date-p0-l1", "page_index": 0, "line_order": 1, "text": "82", "normalized_text": "82", "confidence": 1.0},
        {"block_id": "split-id-date-p0-l2", "page_index": 0, "line_order": 2, "text": "-67609]", "normalized_text": "-67609]", "confidence": 1.0},
        {"block_id": "split-id-date-p0-l3", "page_index": 0, "line_order": 3, "text": "2026-", "normalized_text": "2026-", "confidence": 1.0},
        {"block_id": "split-id-date-p0-l4", "page_index": 0, "line_order": 4, "text": "-05-23", "normalized_text": "-05-23", "confidence": 1.0},
        {"block_id": "split-id-date-p0-l5", "page_index": 0, "line_order": 5, "text": "합계금액 6,000", "normalized_text": "합계금액 6,000", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "226-82-67609"
    assert candidates["transaction_date"] == "2026-05-23"


def test_candidate_hint_builder_reconstructs_labeled_business_number_around_phone_fragment() -> None:
    lines = [
        {"block_id": "business-prefix-p0-l0", "page_index": 0, "line_order": 0, "text": "행촌제2주유소", "normalized_text": "행촌제2주유소", "confidence": 0.96},
        {"block_id": "business-prefix-p0-l1", "page_index": 0, "line_order": 1, "text": "서울시", "normalized_text": "서울시", "confidence": 0.99},
        {"block_id": "business-prefix-p0-l2", "page_index": 0, "line_order": 2, "text": "자N0:110-20", "normalized_text": "자N0:110-20", "confidence": 0.98},
        {"block_id": "business-prefix-p0-l3", "page_index": 0, "line_order": 3, "text": "Te1]02-", "normalized_text": "Te1]02-", "confidence": 0.92},
        {"block_id": "business-prefix-p0-l4", "page_index": 0, "line_order": 4, "text": "365-5189", "normalized_text": "365-5189", "confidence": 0.99},
        {"block_id": "business-prefix-p0-l5", "page_index": 0, "line_order": 5, "text": "28152", "normalized_text": "28152", "confidence": 0.99},
        {"block_id": "business-prefix-p0-l6", "page_index": 0, "line_order": 6, "text": "[등록]2026", "normalized_text": "[등록]2026", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "110-20-28152"
    assert candidates["merchant_name"] == "행촌제2주유소"


def test_candidate_hint_builder_reconstructs_business_number_before_next_label() -> None:
    lines = [
        {"block_id": "next-label-business-p0-l0", "page_index": 0, "line_order": 0, "text": "점포명:109. 종각역점", "normalized_text": "점포명:109. 종각역점", "confidence": 0.99},
        {"block_id": "next-label-business-p0-l1", "page_index": 0, "line_order": 1, "text": "사업", "normalized_text": "사업", "confidence": 0.99},
        {"block_id": "next-label-business-p0-l2", "page_index": 0, "line_order": 2, "text": "자번호:211-88-", "normalized_text": "자번호:211-88-", "confidence": 0.99},
        {"block_id": "next-label-business-p0-l3", "page_index": 0, "line_order": 3, "text": "95935", "normalized_text": "95935", "confidence": 0.99},
        {"block_id": "next-label-business-p0-l4", "page_index": 0, "line_order": 4, "text": "전화번", "normalized_text": "전화번", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "211-88-95935"
    assert candidates["merchant_name"] == "종각역점"


def test_parser_uses_larger_paid_amount_when_split_total_is_lower_without_discount() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_paid_corrects_low_split_total_001",
            "description": "명확한 결제금액이 낮게 조합된 합계 후보보다 큰 경우",
            "source_file_name": "synthetic_paid_corrects_low_split_total_001.jpg",
            "paddle_lines": [
                {"text": "사업자등록번호 104-81-91189", "confidence": 0.99},
                {"text": "2026-05-05", "confidence": 0.99},
                {"text": "합계 66,500", "confidence": 0.99},
                {"text": "결제수단", "confidence": 0.99},
                {"text": "99500", "confidence": 0.99},
                {"text": "네이버카드", "confidence": 0.99},
            ],
            "expected": {
                "business_number": "104-81-91189",
                "transaction_date": "2026-05-05",
                "total_amount": 99500,
                "final_amount": 99500,
                "paid_amount": 99500,
                "payment_method": "카드",
                "review_required_expected": True,
            },
        }
    )

    assert "total_amount_replaced_by_paid_amount_candidate" in record.amount_warnings
    assert "final_amount_replaced_by_paid_amount_candidate" in record.amount_warnings


def test_parser_ignores_supply_amount_inconsistent_with_total_without_explicit_vat() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_inconsistent_supply_candidate_001",
            "description": "잘못 조합된 공급가 후보는 총액 기준 VAT 추정으로 되돌림",
            "source_file_name": "synthetic_inconsistent_supply_candidate_001.jpg",
            "paddle_lines": [
                {"text": "사업자등록번호 104-81-91189", "confidence": 0.99},
                {"text": "2026-05-05", "confidence": 0.99},
                {"text": "과세물품가액", "confidence": 0.99},
                {"text": "29045", "confidence": 0.77},
                {"text": "합계금액 99500", "confidence": 0.99},
                {"text": "결제수단 99500", "confidence": 0.99},
                {"text": "네이버카드", "confidence": 0.99},
            ],
            "expected": {
                "business_number": "104-81-91189",
                "transaction_date": "2026-05-05",
                "total_amount": 99500,
                "final_amount": 99500,
                "paid_amount": 99500,
                "supply_amount": None,
                "estimated_supply_amount": 90455,
                "estimated_vat_amount": 9045,
                "payment_method": "카드",
                "review_required_expected": True,
            },
        }
    )

    assert "supply_amount_inconsistent_with_total_ignored" in record.vat_warnings


def test_parser_prefers_explicit_supply_vat_total_for_small_amount_ocr_drift() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_explicit_vat_corrects_amount_drift_001",
            "description": "공급가와 부가세 명시 합계가 흔들린 결제금액보다 강한 근거",
            "source_file_name": "synthetic_explicit_vat_corrects_amount_drift_001.jpg",
            "paddle_lines": [
                {"text": "사업자등록번호 332-87-01571", "confidence": 0.99},
                {"text": "2026-05-20", "confidence": 0.99},
                {"text": "부가세 과세 물품가액: 12,818", "confidence": 0.99},
                {"text": "부가세: 1,282", "confidence": 0.99},
                {"text": "합계 14,195", "confidence": 0.62},
                {"text": "카드결제: 14,180", "confidence": 0.92},
            ],
            "expected": {
                "business_number": "332-87-01571",
                "transaction_date": "2026-05-20",
                "total_amount": 14100,
                "final_amount": 14100,
                "paid_amount": 14100,
                "supply_amount": 12818,
                "vat_amount": 1282,
                "payment_method": "카드",
                "review_required_expected": True,
            },
        }
    )

    assert "total_amount_replaced_by_explicit_vat_total" in record.amount_warnings
    assert "final_amount_replaced_by_explicit_vat_total" in record.amount_warnings
    assert "paid_amount_replaced_by_explicit_vat_total" in record.amount_warnings


def test_candidate_hint_builder_reconstructs_amount_split_around_total_label() -> None:
    lines = [
        {"block_id": "around-total-p0-l0", "page_index": 0, "line_order": 0, "text": "상품", "normalized_text": "상품", "confidence": 0.99},
        {"block_id": "around-total-p0-l1", "page_index": 0, "line_order": 1, "text": "69", "normalized_text": "69", "confidence": 0.99},
        {"block_id": "around-total-p0-l2", "page_index": 0, "line_order": 2, "text": "계", "normalized_text": "계", "confidence": 0.99},
        {"block_id": "around-total-p0-l3", "page_index": 0, "line_order": 3, "text": "000", "normalized_text": "000", "confidence": 0.99},
        {"block_id": "around-total-p0-l4", "page_index": 0, "line_order": 4, "text": "신한카드", "normalized_text": "신한카드", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "69000"
    assert candidates["final_amount"] == "69000"


def test_candidate_hint_builder_does_not_join_discount_fragment_around_total_label() -> None:
    lines = [
        {"block_id": "discount-around-total-p0-l0", "page_index": 0, "line_order": 0, "text": "24", "normalized_text": "24", "confidence": 0.99},
        {"block_id": "discount-around-total-p0-l1", "page_index": 0, "line_order": 1, "text": "400", "normalized_text": "400", "confidence": 0.99},
        {"block_id": "discount-around-total-p0-l2", "page_index": 0, "line_order": 2, "text": "계", "normalized_text": "계", "confidence": 0.99},
        {"block_id": "discount-around-total-p0-l3", "page_index": 0, "line_order": 3, "text": "-5", "normalized_text": "-5", "confidence": 0.99},
        {"block_id": "discount-around-total-p0-l4", "page_index": 0, "line_order": 4, "text": "300", "normalized_text": "300", "confidence": 0.99},
        {"block_id": "discount-around-total-p0-l5", "page_index": 0, "line_order": 5, "text": "결제금액", "normalized_text": "결제금액", "confidence": 0.99},
        {"block_id": "discount-around-total-p0-l6", "page_index": 0, "line_order": 6, "text": "19100", "normalized_text": "19100", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates.get("total_amount") != "400300"
    assert candidates.get("final_amount") != "400300"


def test_candidate_hint_builder_does_not_use_coupon_identifier_as_discount_amount() -> None:
    lines = [
        {"block_id": "coupon-code-p0-l0", "page_index": 0, "line_order": 0, "text": "쿠폰", "normalized_text": "쿠폰", "confidence": 0.99},
        {"block_id": "coupon-code-p0-l1", "page_index": 0, "line_order": 1, "text": "인증번호", "normalized_text": "인증번호", "confidence": 0.99},
        {"block_id": "coupon-code-p0-l2", "page_index": 0, "line_order": 2, "text": "16544", "normalized_text": "16544", "confidence": 0.99},
        {"block_id": "coupon-code-p0-l3", "page_index": 0, "line_order": 3, "text": "결제금액", "normalized_text": "결제금액", "confidence": 0.99},
        {"block_id": "coupon-code-p0-l4", "page_index": 0, "line_order": 4, "text": "19100", "normalized_text": "19100", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert "discount_amount" not in candidates


def test_parser_infers_discount_from_total_and_paid_difference_when_discount_label_is_broken() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_broken_discount_label_difference_001",
            "description": "할인 라벨이 조각나도 총액과 결제금액 차이를 검토용 할인 후보로 보강",
            "source_file_name": "synthetic_broken_discount_label_difference_001.jpg",
            "paddle_lines": [
                {"text": "사업자번호 211-88-95935", "confidence": 0.99},
                {"text": "2026-05-26", "confidence": 0.99},
                {"text": "합계 24,400", "confidence": 0.99},
                {"text": "할", "confidence": 0.99},
                {"text": "인", "confidence": 0.99},
                {"text": "-5", "confidence": 0.99},
                {"text": "300", "confidence": 0.99},
                {"text": "결제금액", "confidence": 0.99},
                {"text": "19100", "confidence": 0.99},
                {"text": "신용카드", "confidence": 0.99},
            ],
            "expected": {
                "business_number": "211-88-95935",
                "transaction_date": "2026-05-26",
                "total_amount": 24400,
                "discount_amount": 5300,
                "final_amount": 19100,
                "paid_amount": 19100,
                "payment_method": "카드",
                "review_required_expected": True,
            },
        }
    )

    assert "discount_inferred_from_total_paid_difference" in record.amount_warnings


def test_candidate_hint_builder_reconstructs_card_receipt_zero_group_amount() -> None:
    lines = [
        {"block_id": "card-zero-p0-l0", "page_index": 0, "line_order": 0, "text": "신한카드", "normalized_text": "신한카드", "confidence": 0.99},
        {"block_id": "card-zero-p0-l1", "page_index": 0, "line_order": 1, "text": "거래금액", "normalized_text": "거래금액", "confidence": 0.99},
        {"block_id": "card-zero-p0-l2", "page_index": 0, "line_order": 2, "text": "부", "normalized_text": "부", "confidence": 0.99},
        {"block_id": "card-zero-p0-l3", "page_index": 0, "line_order": 3, "text": "가세", "normalized_text": "가세", "confidence": 0.99},
        {"block_id": "card-zero-p0-l4", "page_index": 0, "line_order": 4, "text": "190", "normalized_text": "190", "confidence": 0.72},
        {"block_id": "card-zero-p0-l5", "page_index": 0, "line_order": 5, "text": "총", "normalized_text": "총", "confidence": 0.82},
        {"block_id": "card-zero-p0-l6", "page_index": 0, "line_order": 6, "text": "합계", "normalized_text": "합계", "confidence": 0.99},
        {"block_id": "card-zero-p0-l7", "page_index": 0, "line_order": 7, "text": "909", "normalized_text": "909", "confidence": 0.63},
        {"block_id": "card-zero-p0-l8", "page_index": 0, "line_order": 8, "text": "10", "normalized_text": "10", "confidence": 0.99},
        {"block_id": "card-zero-p0-l9", "page_index": 0, "line_order": 9, "text": "OCC", "normalized_text": "OCC", "confidence": 0.86},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "10000"
    assert candidates["final_amount"] == "10000"
    assert candidates["paid_amount"] == "10000"


def test_candidate_hint_builder_prefers_plausible_zero_group_prefix_when_ocr_order_shifts() -> None:
    lines = [
        {"block_id": "card-zero-shift-p0-l0", "page_index": 0, "line_order": 0, "text": "카드", "normalized_text": "카드", "confidence": 0.99},
        {"block_id": "card-zero-shift-p0-l1", "page_index": 0, "line_order": 1, "text": "거래금액", "normalized_text": "거래금액", "confidence": 0.99},
        {"block_id": "card-zero-shift-p0-l2", "page_index": 0, "line_order": 2, "text": "605", "normalized_text": "605", "confidence": 0.70},
        {"block_id": "card-zero-shift-p0-l3", "page_index": 0, "line_order": 3, "text": "盔", "normalized_text": "盔", "confidence": 0.70},
        {"block_id": "card-zero-shift-p0-l4", "page_index": 0, "line_order": 4, "text": "O0O", "normalized_text": "O0O", "confidence": 0.86},
        {"block_id": "card-zero-shift-p0-l5", "page_index": 0, "line_order": 5, "text": "10", "normalized_text": "10", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "10000"
    assert candidates["final_amount"] == "10000"
    assert candidates["paid_amount"] == "10000"


def test_candidate_hint_builder_uses_card_tax_adjacent_amount_when_label_is_missed() -> None:
    lines = [
        {"block_id": "card-tax-adjacent-p0-l0", "page_index": 0, "line_order": 0, "text": "대VISA", "normalized_text": "대VISA", "confidence": 0.90},
        {"block_id": "card-tax-adjacent-p0-l1", "page_index": 0, "line_order": 1, "text": "승인번호", "normalized_text": "승인번호", "confidence": 0.90},
        {"block_id": "card-tax-adjacent-p0-l2", "page_index": 0, "line_order": 2, "text": "00592623", "normalized_text": "00592623", "confidence": 0.99},
        {"block_id": "card-tax-adjacent-p0-l3", "page_index": 0, "line_order": 3, "text": "11:58:53", "normalized_text": "11:58:53", "confidence": 0.99},
        {"block_id": "card-tax-adjacent-p0-l4", "page_index": 0, "line_order": 4, "text": "60000", "normalized_text": "60000", "confidence": 0.99},
        {"block_id": "card-tax-adjacent-p0-l5", "page_index": 0, "line_order": 5, "text": "가세", "normalized_text": "가세", "confidence": 0.99},
        {"block_id": "card-tax-adjacent-p0-l6", "page_index": 0, "line_order": 6, "text": "54", "normalized_text": "54", "confidence": 0.99},
        {"block_id": "card-tax-adjacent-p0-l7", "page_index": 0, "line_order": 7, "text": "546", "normalized_text": "546", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "60000"
    assert candidates["final_amount"] == "60000"
    assert candidates["paid_amount"] == "60000"


def test_candidate_hint_builder_ignores_installment_card_metadata_amount_fragments() -> None:
    lines = [
        {"block_id": "installment-card-p0-l0", "page_index": 0, "line_order": 0, "text": "합계 95,000", "normalized_text": "합계 95,000", "confidence": 0.99},
        {"block_id": "installment-card-p0-l1", "page_index": 0, "line_order": 1, "text": "[신한카드]", "normalized_text": "[신한카드]", "confidence": 0.99},
        {
            "block_id": "installment-card-p0-l2",
            "page_index": 0,
            "line_order": 2,
            "text": "422 15530oocopoonok /할부:00",
            "normalized_text": "422 15530oocopoonok /할부:00",
            "confidence": 0.76,
        },
        {"block_id": "installment-card-p0-l3", "page_index": 0, "line_order": 3, "text": "CARD번호", "normalized_text": "CARD번호", "confidence": 0.98},
        {"block_id": "installment-card-p0-l4", "page_index": 0, "line_order": 4, "text": "승인번호", "normalized_text": "승인번호", "confidence": 0.98},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "95000"
    assert candidates["final_amount"] == "95000"
    assert "paid_amount" not in candidates


def test_candidate_hint_builder_uses_card_receipt_won_amount_when_payment_label_is_missed() -> None:
    lines = [
        {"block_id": "card-won-p0-l0", "page_index": 0, "line_order": 0, "text": "GS25한화리조트설악", "normalized_text": "GS25한화리조트설악", "confidence": 0.92},
        {"block_id": "card-won-p0-l1", "page_index": 0, "line_order": 1, "text": "2026/05/23", "normalized_text": "2026/05/23", "confidence": 0.90},
        {"block_id": "card-won-p0-l2", "page_index": 0, "line_order": 2, "text": "합계수량/", "normalized_text": "합계수량/", "confidence": 0.99},
        {"block_id": "card-won-p0-l3", "page_index": 0, "line_order": 3, "text": "신용카드", "normalized_text": "신용카드", "confidence": 0.98},
        {"block_id": "card-won-p0-l4", "page_index": 0, "line_order": 4, "text": "카드번호", "normalized_text": "카드번호", "confidence": 0.98},
        {"block_id": "card-won-p0-l5", "page_index": 0, "line_order": 5, "text": "4221", "normalized_text": "4221", "confidence": 0.99},
        {"block_id": "card-won-p0-l6", "page_index": 0, "line_order": 6, "text": "2300원", "normalized_text": "2300원", "confidence": 0.99},
        {"block_id": "card-won-p0-l7", "page_index": 0, "line_order": 7, "text": "할부 0", "normalized_text": "할부 0", "confidence": 0.90},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "2300"
    assert candidates["final_amount"] == "2300"
    assert candidates["paid_amount"] == "2300"


def test_candidate_hint_builder_reconstructs_top_tax_total_sequence_without_using_cancel_amount() -> None:
    lines = [
        {"block_id": "gas-top-tax-p0-l0", "page_index": 0, "line_order": 0, "text": "SEQNO:1211", "normalized_text": "SEQNO:1211", "confidence": 0.99},
        {"block_id": "gas-top-tax-p0-l1", "page_index": 0, "line_order": 1, "text": "130000", "normalized_text": "130000", "confidence": 0.98},
        {"block_id": "gas-top-tax-p0-l2", "page_index": 0, "line_order": 2, "text": "118182", "normalized_text": "118182", "confidence": 0.99},
        {"block_id": "gas-top-tax-p0-l3", "page_index": 0, "line_order": 3, "text": "11818", "normalized_text": "11818", "confidence": 0.99},
        {"block_id": "gas-top-tax-p0-l4", "page_index": 0, "line_order": 4, "text": "제1자유로주유소", "normalized_text": "제1자유로주유소", "confidence": 0.99},
        {"block_id": "gas-top-tax-p0-l5", "page_index": 0, "line_order": 5, "text": "128-35-95660", "normalized_text": "128-35-95660", "confidence": 0.99},
        {"block_id": "gas-top-tax-p0-l6", "page_index": 0, "line_order": 6, "text": "원거래 190000원은 취소", "normalized_text": "원거래 190000원은 취소", "confidence": 0.99},
        {"block_id": "gas-top-tax-p0-l7", "page_index": 0, "line_order": 7, "text": "카드", "normalized_text": "카드", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "128-35-95660"
    assert candidates["total_amount"] == "130000"
    assert candidates["final_amount"] == "130000"
    assert candidates["paid_amount"] == "130000"
    assert candidates["supply_amount"] == "118182"
    assert candidates["vat_amount"] == "11818"


def test_candidate_hint_builder_does_not_join_masked_card_fragments_as_business_number() -> None:
    lines = [
        {"block_id": "masked-business-p0-l0", "page_index": 0, "line_order": 0, "text": "자유로94", "normalized_text": "자유로94", "confidence": 0.99},
        {"block_id": "masked-business-p0-l1", "page_index": 0, "line_order": 1, "text": "*699-****-**29-", "normalized_text": "*699-****-**29-", "confidence": 0.93},
        {"block_id": "masked-business-p0-l2", "page_index": 0, "line_order": 2, "text": "920거래", "normalized_text": "920거래", "confidence": 0.75},
        {"block_id": "masked-business-p0-l3", "page_index": 0, "line_order": 3, "text": "128-35-95660", "normalized_text": "128-35-95660", "confidence": 0.99},
    ]

    candidates = [
        candidate
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
        if candidate["candidate_type"] == "business_number"
    ]

    assert [candidate["normalized_value"] for candidate in candidates] == ["128-35-95660"]


def test_candidate_hint_builder_reconstructs_labeled_tax_sum_sequence() -> None:
    lines = [
        {"block_id": "labeled-tax-sum-p0-l0", "page_index": 0, "line_order": 0, "text": "총각김밥", "normalized_text": "총각김밥", "confidence": 0.99},
        {"block_id": "labeled-tax-sum-p0-l1", "page_index": 0, "line_order": 1, "text": "152-21-01299", "normalized_text": "152-21-01299", "confidence": 0.99},
        {"block_id": "labeled-tax-sum-p0-l2", "page_index": 0, "line_order": 2, "text": "신한카드", "normalized_text": "신한카드", "confidence": 0.98},
        {"block_id": "labeled-tax-sum-p0-l3", "page_index": 0, "line_order": 3, "text": "5091", "normalized_text": "5091", "confidence": 0.99},
        {"block_id": "labeled-tax-sum-p0-l4", "page_index": 0, "line_order": 4, "text": "판", "normalized_text": "판", "confidence": 0.97},
        {"block_id": "labeled-tax-sum-p0-l5", "page_index": 0, "line_order": 5, "text": "매", "normalized_text": "매", "confidence": 0.99},
        {"block_id": "labeled-tax-sum-p0-l6", "page_index": 0, "line_order": 6, "text": "금", "normalized_text": "금", "confidence": 0.99},
        {"block_id": "labeled-tax-sum-p0-l7", "page_index": 0, "line_order": 7, "text": "액:", "normalized_text": "액:", "confidence": 0.70},
        {"block_id": "labeled-tax-sum-p0-l8", "page_index": 0, "line_order": 8, "text": "509", "normalized_text": "509", "confidence": 0.99},
        {"block_id": "labeled-tax-sum-p0-l9", "page_index": 0, "line_order": 9, "text": "가세", "normalized_text": "가세", "confidence": 0.99},
        {"block_id": "labeled-tax-sum-p0-l10", "page_index": 0, "line_order": 10, "text": "5600", "normalized_text": "5600", "confidence": 0.99},
        {"block_id": "labeled-tax-sum-p0-l11", "page_index": 0, "line_order": 11, "text": "승인번호", "normalized_text": "승인번호", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["supply_amount"] == "5091"
    assert candidates["vat_amount"] == "509"
    assert candidates["total_amount"] == "5600"
    assert candidates["final_amount"] == "5600"
    assert candidates["paid_amount"] == "5600"


def test_candidate_hint_builder_reconstructs_gas_split_tax_total_sequence() -> None:
    lines = [
        {"block_id": "gas-split-tax-p0-l0", "page_index": 0, "line_order": 0, "text": "양평휴게서울주유소", "normalized_text": "양평휴게서울주유소", "confidence": 0.90},
        {"block_id": "gas-split-tax-p0-l1", "page_index": 0, "line_order": 1, "text": "상품명(주유기) 단가 수량 금액", "normalized_text": "상품명(주유기) 단가 수량 금액", "confidence": 0.99},
        {"block_id": "gas-split-tax-p0-l2", "page_index": 0, "line_order": 2, "text": "133", "normalized_text": "133", "confidence": 0.99},
        {"block_id": "gas-split-tax-p0-l3", "page_index": 0, "line_order": 3, "text": "534", "normalized_text": "534", "confidence": 0.99},
        {"block_id": "gas-split-tax-p0-l4", "page_index": 0, "line_order": 4, "text": "000", "normalized_text": "000", "confidence": 0.99},
        {"block_id": "gas-split-tax-p0-l5", "page_index": 0, "line_order": 5, "text": "보통휘발유", "normalized_text": "보통휘발유", "confidence": 0.88},
        {"block_id": "gas-split-tax-p0-l6", "page_index": 0, "line_order": 6, "text": "12", "normalized_text": "12", "confidence": 0.99},
        {"block_id": "gas-split-tax-p0-l7", "page_index": 0, "line_order": 7, "text": "090", "normalized_text": "090", "confidence": 0.96},
        {"block_id": "gas-split-tax-p0-l8", "page_index": 0, "line_order": 8, "text": "120910", "normalized_text": "120910", "confidence": 0.99},
        {"block_id": "gas-split-tax-p0-l9", "page_index": 0, "line_order": 9, "text": "과세금액 부가세", "normalized_text": "과세금액 부가세", "confidence": 0.80},
        {"block_id": "gas-split-tax-p0-l10", "page_index": 0, "line_order": 10, "text": "비씨카드", "normalized_text": "비씨카드", "confidence": 0.90},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["supply_amount"] == "120910"
    assert candidates["vat_amount"] == "12090"
    assert candidates["total_amount"] == "133000"
    assert candidates["final_amount"] == "133000"
    assert candidates["paid_amount"] == "133000"


def test_candidate_hint_builder_reconstructs_reverse_labeled_business_number_and_korean_date_parts() -> None:
    lines = [
        {"block_id": "reverse-business-p0-l0", "page_index": 0, "line_order": 0, "text": "10일!", "normalized_text": "10일!", "confidence": 0.79},
        {"block_id": "reverse-business-p0-l1", "page_index": 0, "line_order": 1, "text": "[등록]2026년04원", "normalized_text": "[등록]2026년04원", "confidence": 0.93},
        {"block_id": "reverse-business-p0-l2", "page_index": 0, "line_order": 2, "text": "08930", "normalized_text": "08930", "confidence": 0.92},
        {"block_id": "reverse-business-p0-l3", "page_index": 0, "line_order": 3, "text": "사업자N0:214-86", "normalized_text": "사업자N0:214-86", "confidence": 0.98},
        {"block_id": "reverse-business-p0-l4", "page_index": 0, "line_order": 4, "text": "양평휴게서울주유소", "normalized_text": "양평휴게서울주유소", "confidence": 0.90},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "214-86-08930"
    assert candidates["transaction_date"] == "2026-04-10"


def test_candidate_hint_builder_reconstructs_top_split_business_number_and_ignores_representative() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_top_split_business_number_001",
            "description": "상단 사업자번호가 두 줄로 분리되고 대표자 라인이 가까운 경우",
            "source_file_name": "synthetic_top_split_business_number_001.jpg",
            "paddle_lines": [
                {"text": "Starfield", "confidence": 0.89},
                {"text": "AVENUE", "confidence": 0.98},
                {"text": "808-85-", "confidence": 0.99},
                {"text": "-03280", "confidence": 0.92},
                {"text": "대표:조경찬", "confidence": 0.99},
                {"text": "구매 2026-05-14", "confidence": 0.99},
                {"text": "합계 14,000", "confidence": 0.99},
                {"text": "카드 결제액 14,000", "confidence": 0.99},
            ],
            "expected": {
                "merchant_name": "깐깐",
                "business_number": "808-85-03280",
                "transaction_date": "2026-05-14",
                "total_amount": 14000,
                "final_amount": 14000,
                "paid_amount": 14000,
                "payment_method": "카드",
                "review_required_expected": True,
            },
        }
    )

    assert record.merchant_name != "대표:조경찬"


def test_candidate_hint_builder_reconstructs_business_number_when_second_fragment_has_no_dash() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_top_split_business_number_no_second_dash_001",
            "description": "상단 사업자번호가 762-58- / 00827로 분리된 경우",
            "source_file_name": "synthetic_top_split_business_number_no_second_dash_001.jpg",
            "paddle_lines": [
                {"text": "승진식품", "confidence": 0.79},
                {"text": "762-58-", "confidence": 0.99},
                {"text": "00827", "confidence": 0.97},
                {"text": "TEL", "confidence": 0.97},
                {"text": "010", "confidence": 0.60},
                {"text": "3900", "confidence": 0.60},
                {"text": "2026-05-24", "confidence": 0.99},
                {"text": "거래금액", "confidence": 0.99},
                {"text": "10,000", "confidence": 0.99},
                {"text": "카드", "confidence": 0.99},
            ],
            "expected": {
                "merchant_name": "승진식품",
                "business_number": "762-58-00827",
                "transaction_date": "2026-05-24",
                "total_amount": 10000,
                "final_amount": 10000,
                "payment_method": "카드",
                "review_required_expected": True,
            },
        }
    )

    assert record.business_number == "762-58-00827"
    assert record.merchant_name == "승진식품"


def test_standard_context_prefers_business_number_dictionary_merchant_over_partial_ocr_name() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_business_number_dictionary_merchant_001",
            "description": "OCR 상호가 지점명/법인표기를 일부 놓친 경우 사업자번호 앵커 사전을 우선한다",
            "source_file_name": "synthetic_business_number_dictionary_merchant_001.jpg",
            "paddle_lines": [
                {"text": "한화호텔앤드리조트주", "confidence": 0.96},
                {"text": "101-81", "confidence": 0.99},
                {"text": "-30747", "confidence": 0.98},
                {"text": "2026-05-24", "confidence": 0.99},
                {"text": "합계금액 20,000", "confidence": 0.99},
                {"text": "신용카드 20,000", "confidence": 0.99},
            ],
            "expected": {
                "merchant_name": "한화호텔앤드리조트(주) 설악",
                "business_number": "101-81-30747",
                "transaction_date": "2026-05-24",
                "total_amount": 20000,
                "final_amount": 20000,
                "paid_amount": 20000,
                "payment_method": "카드",
                "review_required_expected": True,
            },
        }
    )

    assert record.business_number == "101-81-30747"
    assert record.merchant_name == "한화호텔앤드리조트(주) 설악"


def test_candidate_hint_builder_reconstructs_columnar_tax_summary_amounts() -> None:
    lines = [
        {"block_id": "column-summary-p0-l0", "page_index": 0, "line_order": 0, "text": "공급가", "normalized_text": "공급가", "confidence": 1.0},
        {"block_id": "column-summary-p0-l1", "page_index": 0, "line_order": 1, "text": "주문합계", "normalized_text": "주문합계", "confidence": 1.0},
        {"block_id": "column-summary-p0-l2", "page_index": 0, "line_order": 2, "text": "부가세", "normalized_text": "부가세", "confidence": 1.0},
        {"block_id": "column-summary-p0-l3", "page_index": 0, "line_order": 3, "text": "15455", "normalized_text": "15455", "confidence": 1.0},
        {"block_id": "column-summary-p0-l4", "page_index": 0, "line_order": 4, "text": "154", "normalized_text": "154", "confidence": 1.0},
        {"block_id": "column-summary-p0-l5", "page_index": 0, "line_order": 5, "text": "545", "normalized_text": "545", "confidence": 1.0},
        {"block_id": "column-summary-p0-l6", "page_index": 0, "line_order": 6, "text": "170", "normalized_text": "170", "confidence": 1.0},
        {"block_id": "column-summary-p0-l7", "page_index": 0, "line_order": 7, "text": "000", "normalized_text": "000", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["vat_amount"] == "15455"
    assert candidates["supply_amount"] == "154545"
    assert candidates["total_amount"] == "170000"
    assert candidates["final_amount"] == "170000"


def test_candidate_hint_builder_reconstructs_total_from_compact_tax_amounts() -> None:
    lines = [
        {"block_id": "compact-tax-p0-l0", "page_index": 0, "line_order": 0, "text": "매출", "normalized_text": "매출", "confidence": 1.0},
        {"block_id": "compact-tax-p0-l1", "page_index": 0, "line_order": 1, "text": "2", "normalized_text": "2", "confidence": 1.0},
        {"block_id": "compact-tax-p0-l2", "page_index": 0, "line_order": 2, "text": "091", "normalized_text": "091", "confidence": 1.0},
        {"block_id": "compact-tax-p0-l3", "page_index": 0, "line_order": 3, "text": "209", "normalized_text": "209", "confidence": 1.0},
        {"block_id": "compact-tax-p0-l4", "page_index": 0, "line_order": 4, "text": "신용카드", "normalized_text": "신용카드", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["supply_amount"] == "2091"
    assert candidates["vat_amount"] == "209"
    assert candidates["total_amount"] == "2300"
    assert candidates["final_amount"] == "2300"
    assert candidates["payment_method"] == "카드"


def test_candidate_hint_builder_uses_split_amount_before_total_label() -> None:
    lines = [
        {"block_id": "previous-total-p0-l0", "page_index": 0, "line_order": 0, "text": "신용카", "normalized_text": "신용카", "confidence": 1.0},
        {"block_id": "previous-total-p0-l1", "page_index": 0, "line_order": 1, "text": "20", "normalized_text": "20", "confidence": 1.0},
        {"block_id": "previous-total-p0-l2", "page_index": 0, "line_order": 2, "text": "000", "normalized_text": "000", "confidence": 1.0},
        {"block_id": "previous-total-p0-l3", "page_index": 0, "line_order": 3, "text": "합계금액", "normalized_text": "합계금액", "confidence": 1.0},
        {"block_id": "previous-total-p0-l4", "page_index": 0, "line_order": 4, "text": "SK주유400우리카드로", "normalized_text": "SK주유400우리카드로", "confidence": 1.0},
        {"block_id": "previous-total-p0-l5", "page_index": 0, "line_order": 5, "text": "400원", "normalized_text": "400원", "confidence": 1.0},
        {"block_id": "previous-total-p0-l6", "page_index": 0, "line_order": 6, "text": "할인", "normalized_text": "할인", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["paid_amount"] == "20000"
    assert candidates["total_amount"] == "20000"
    assert candidates["final_amount"] == "20000"


def test_candidate_hint_builder_prefers_previous_amount_for_split_total_label_before_supply() -> None:
    lines = [
        {"block_id": "previous-total-before-supply-p0-l0", "page_index": 0, "line_order": 0, "text": "5,600", "normalized_text": "5,600", "confidence": 1.0},
        {"block_id": "previous-total-before-supply-p0-l1", "page_index": 0, "line_order": 1, "text": "5,600", "normalized_text": "5,600", "confidence": 1.0},
        {"block_id": "previous-total-before-supply-p0-l2", "page_index": 0, "line_order": 2, "text": "합", "normalized_text": "합", "confidence": 1.0},
        {"block_id": "previous-total-before-supply-p0-l3", "page_index": 0, "line_order": 3, "text": "계", "normalized_text": "계", "confidence": 1.0},
        {"block_id": "previous-total-before-supply-p0-l4", "page_index": 0, "line_order": 4, "text": "금", "normalized_text": "금", "confidence": 1.0},
        {"block_id": "previous-total-before-supply-p0-l5", "page_index": 0, "line_order": 5, "text": "액", "normalized_text": "액", "confidence": 1.0},
        {"block_id": "previous-total-before-supply-p0-l6", "page_index": 0, "line_order": 6, "text": "부가세 과세물품가액", "normalized_text": "부가세 과세물품가액", "confidence": 1.0},
        {"block_id": "previous-total-before-supply-p0-l7", "page_index": 0, "line_order": 7, "text": "5,091", "normalized_text": "5,091", "confidence": 1.0},
        {"block_id": "previous-total-before-supply-p0-l8", "page_index": 0, "line_order": 8, "text": "부가세", "normalized_text": "부가세", "confidence": 1.0},
        {"block_id": "previous-total-before-supply-p0-l9", "page_index": 0, "line_order": 9, "text": "509", "normalized_text": "509", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "5600"
    assert candidates["final_amount"] == "5600"
    assert candidates["supply_amount"] == "5091"


def test_candidate_hint_builder_prefers_immediate_amount_after_standalone_total_label() -> None:
    lines = [
        {"block_id": "immediate-total-p0-l0", "page_index": 0, "line_order": 0, "text": "과세물품", "normalized_text": "과세물품", "confidence": 1.0},
        {"block_id": "immediate-total-p0-l1", "page_index": 0, "line_order": 1, "text": "32455", "normalized_text": "32455", "confidence": 1.0},
        {"block_id": "immediate-total-p0-l2", "page_index": 0, "line_order": 2, "text": "부가세", "normalized_text": "부가세", "confidence": 1.0},
        {"block_id": "immediate-total-p0-l3", "page_index": 0, "line_order": 3, "text": "3245", "normalized_text": "3245", "confidence": 1.0},
        {"block_id": "immediate-total-p0-l4", "page_index": 0, "line_order": 4, "text": "계", "normalized_text": "계", "confidence": 1.0},
        {"block_id": "immediate-total-p0-l5", "page_index": 0, "line_order": 5, "text": "35700", "normalized_text": "35700", "confidence": 1.0},
        {"block_id": "immediate-total-p0-l6", "page_index": 0, "line_order": 6, "text": "결제대상금", "normalized_text": "결제대상금", "confidence": 1.0},
        {"block_id": "immediate-total-p0-l7", "page_index": 0, "line_order": 7, "text": "액", "normalized_text": "액", "confidence": 1.0},
        {"block_id": "immediate-total-p0-l8", "page_index": 0, "line_order": 8, "text": "35700", "normalized_text": "35700", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "35700"
    assert candidates["final_amount"] == "35700"
    assert candidates["vat_amount"] == "3245"


def test_candidate_hint_builder_prefers_balanced_previous_vat_amount() -> None:
    lines = [
        {"block_id": "previous-vat-p0-l0", "page_index": 0, "line_order": 0, "text": "20,000", "normalized_text": "20,000", "confidence": 1.0},
        {"block_id": "previous-vat-p0-l1", "page_index": 0, "line_order": 1, "text": "1,818", "normalized_text": "1,818", "confidence": 1.0},
        {"block_id": "previous-vat-p0-l2", "page_index": 0, "line_order": 2, "text": "부가세액", "normalized_text": "부가세액", "confidence": 1.0},
        {"block_id": "previous-vat-p0-l3", "page_index": 0, "line_order": 3, "text": "18,182", "normalized_text": "18,182", "confidence": 1.0},
        {"block_id": "previous-vat-p0-l4", "page_index": 0, "line_order": 4, "text": "신용카", "normalized_text": "신용카", "confidence": 1.0},
        {"block_id": "previous-vat-p0-l5", "page_index": 0, "line_order": 5, "text": "20", "normalized_text": "20", "confidence": 1.0},
        {"block_id": "previous-vat-p0-l6", "page_index": 0, "line_order": 6, "text": "000", "normalized_text": "000", "confidence": 1.0},
        {"block_id": "previous-vat-p0-l7", "page_index": 0, "line_order": 7, "text": "합계금액", "normalized_text": "합계금액", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["vat_amount"] == "1818"
    assert candidates["total_amount"] == "20000"


def test_candidate_hint_builder_treats_vat_taxable_goods_label_as_supply_and_split_vat() -> None:
    lines = [
        {"block_id": "split-taxable-p0-l0", "page_index": 0, "line_order": 0, "text": "부가세", "normalized_text": "부가세", "confidence": 1.0},
        {"block_id": "split-taxable-p0-l1", "page_index": 0, "line_order": 1, "text": "물품가", "normalized_text": "물품가", "confidence": 1.0},
        {"block_id": "split-taxable-p0-l2", "page_index": 0, "line_order": 2, "text": "액", "normalized_text": "액", "confidence": 1.0},
        {"block_id": "split-taxable-p0-l3", "page_index": 0, "line_order": 3, "text": "140545", "normalized_text": "140545", "confidence": 1.0},
        {"block_id": "split-taxable-p0-l4", "page_index": 0, "line_order": 4, "text": "부", "normalized_text": "부", "confidence": 1.0},
        {"block_id": "split-taxable-p0-l5", "page_index": 0, "line_order": 5, "text": "14055", "normalized_text": "14055", "confidence": 1.0},
        {"block_id": "split-taxable-p0-l6", "page_index": 0, "line_order": 6, "text": "가", "normalized_text": "가", "confidence": 1.0},
        {"block_id": "split-taxable-p0-l7", "page_index": 0, "line_order": 7, "text": "154600", "normalized_text": "154600", "confidence": 1.0},
        {"block_id": "split-taxable-p0-l8", "page_index": 0, "line_order": 8, "text": "신용카드", "normalized_text": "신용카드", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["supply_amount"] == "140545"
    assert candidates["vat_amount"] == "14055"
    assert candidates["payment_method"] == "카드"


def test_candidate_hint_builder_does_not_use_total_amount_as_vat() -> None:
    lines = [
        {"block_id": "vat-total-guard-p0-l0", "page_index": 0, "line_order": 0, "text": "합계:", "normalized_text": "합계:", "confidence": 1.0},
        {"block_id": "vat-total-guard-p0-l1", "page_index": 0, "line_order": 1, "text": "61,000", "normalized_text": "61,000", "confidence": 1.0},
        {"block_id": "vat-total-guard-p0-l2", "page_index": 0, "line_order": 2, "text": "공급가:", "normalized_text": "공급가:", "confidence": 1.0},
        {"block_id": "vat-total-guard-p0-l3", "page_index": 0, "line_order": 3, "text": "0", "normalized_text": "0", "confidence": 1.0},
        {"block_id": "vat-total-guard-p0-l4", "page_index": 0, "line_order": 4, "text": "부가세:", "normalized_text": "부가세:", "confidence": 1.0},
        {"block_id": "vat-total-guard-p0-l5", "page_index": 0, "line_order": 5, "text": "61,000", "normalized_text": "61,000", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "61000"
    assert candidates["final_amount"] == "61000"
    assert candidates["supply_amount"] == "0"
    assert "vat_amount" not in candidates


def test_candidate_hint_builder_ignores_pos_identifier_near_payment_label() -> None:
    lines = [
        {"block_id": "pos-identifier-p0-l0", "page_index": 0, "line_order": 0, "text": "결제금액", "normalized_text": "결제금액", "confidence": 1.0},
        {"block_id": "pos-identifier-p0-l1", "page_index": 0, "line_order": 1, "text": "109848", "normalized_text": "109848", "confidence": 1.0},
        {"block_id": "pos-identifier-p0-l2", "page_index": 0, "line_order": 2, "text": "07:30:48", "normalized_text": "07:30:48", "confidence": 1.0},
        {"block_id": "pos-identifier-p0-l3", "page_index": 0, "line_order": 3, "text": "POS:02", "normalized_text": "POS:02", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates.get("paid_amount") != "109848"
    assert candidates.get("total_amount") != "109848"


def test_candidate_hint_builder_does_not_join_card_fragments_as_business_number() -> None:
    lines = [
        {"block_id": "card-fragment-p0-l0", "page_index": 0, "line_order": 0, "text": "우리비씨카드", "normalized_text": "우리비씨카드", "confidence": 1.0},
        {"block_id": "card-fragment-p0-l1", "page_index": 0, "line_order": 1, "text": "5206-", "normalized_text": "5206-", "confidence": 1.0},
        {"block_id": "card-fragment-p0-l2", "page_index": 0, "line_order": 2, "text": "67", "normalized_text": "67", "confidence": 1.0},
        {"block_id": "card-fragment-p0-l3", "page_index": 0, "line_order": 3, "text": "일시불", "normalized_text": "일시불", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert "business_number" not in candidates


def test_candidate_hint_builder_does_not_use_masked_card_number_as_business_number() -> None:
    lines = [
        {"block_id": "masked-card-p0-l0", "page_index": 0, "line_order": 0, "text": "카드번호", "normalized_text": "카드번호", "confidence": 1.0},
        {"block_id": "masked-card-p0-l1", "page_index": 0, "line_order": 1, "text": "4221558190", "normalized_text": "4221558190", "confidence": 1.0},
        {"block_id": "masked-card-p0-l2", "page_index": 0, "line_order": 2, "text": "승인번호", "normalized_text": "승인번호", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert "business_number" not in candidates


def test_candidate_hint_builder_reconstructs_repeated_split_card_amount() -> None:
    lines = [
        {"block_id": "split-card-p0-l0", "page_index": 0, "line_order": 0, "text": "GS THE FRESH", "normalized_text": "GS THE FRESH", "confidence": 1.0},
        {"block_id": "split-card-p0-l1", "page_index": 0, "line_order": 1, "text": "신용카드", "normalized_text": "신용카드", "confidence": 1.0},
        {"block_id": "split-card-p0-l2", "page_index": 0, "line_order": 2, "text": "26", "normalized_text": "26", "confidence": 1.0},
        {"block_id": "split-card-p0-l3", "page_index": 0, "line_order": 3, "text": "390据!", "normalized_text": "390据!", "confidence": 1.0},
        {"block_id": "split-card-p0-l4", "page_index": 0, "line_order": 4, "text": "포인트", "normalized_text": "포인트", "confidence": 1.0},
        {"block_id": "split-card-p0-l5", "page_index": 0, "line_order": 5, "text": "26", "normalized_text": "26", "confidence": 1.0},
        {"block_id": "split-card-p0-l6", "page_index": 0, "line_order": 6, "text": "390", "normalized_text": "390", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "26390"
    assert candidates["final_amount"] == "26390"
    assert candidates["paid_amount"] == "26390"


def test_candidate_hint_builder_reconstructs_single_card_tax_split_amount() -> None:
    lines = [
        {"block_id": "single-card-split-p0-l0", "page_index": 0, "line_order": 0, "text": "26", "normalized_text": "26", "confidence": 1.0},
        {"block_id": "single-card-split-p0-l1", "page_index": 0, "line_order": 1, "text": "390", "normalized_text": "390", "confidence": 1.0},
        {"block_id": "single-card-split-p0-l2", "page_index": 0, "line_order": 2, "text": "카", "normalized_text": "카", "confidence": 1.0},
        {"block_id": "single-card-split-p0-l3", "page_index": 0, "line_order": 3, "text": "2398", "normalized_text": "2398", "confidence": 1.0},
        {"block_id": "single-card-split-p0-l4", "page_index": 0, "line_order": 4, "text": "가세:", "normalized_text": "가세:", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "26390"
    assert candidates["paid_amount"] == "26390"


def test_candidate_hint_builder_does_not_join_three_digit_product_price_pairs() -> None:
    lines = [
        {"block_id": "product-pair-p0-l0", "page_index": 0, "line_order": 0, "text": "신용카드", "normalized_text": "신용카드", "confidence": 1.0},
        {"block_id": "product-pair-p0-l1", "page_index": 0, "line_order": 1, "text": "400", "normalized_text": "400", "confidence": 1.0},
        {"block_id": "product-pair-p0-l2", "page_index": 0, "line_order": 2, "text": "400", "normalized_text": "400", "confidence": 1.0},
        {"block_id": "product-pair-p0-l3", "page_index": 0, "line_order": 3, "text": "상품", "normalized_text": "상품", "confidence": 1.0},
        {"block_id": "product-pair-p0-l4", "page_index": 0, "line_order": 4, "text": "400", "normalized_text": "400", "confidence": 1.0},
        {"block_id": "product-pair-p0-l5", "page_index": 0, "line_order": 5, "text": "400", "normalized_text": "400", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates.get("total_amount") != "400400"
    assert candidates.get("paid_amount") != "400400"


def test_candidate_hint_builder_does_not_use_card_advertising_amount_as_paid_amount() -> None:
    lines = [
        {"block_id": "card-ad-p0-l0", "page_index": 0, "line_order": 0, "text": "합계금액", "normalized_text": "합계금액", "confidence": 1.0},
        {"block_id": "card-ad-p0-l1", "page_index": 0, "line_order": 1, "text": "50,000", "normalized_text": "50,000", "confidence": 1.0},
        {"block_id": "card-ad-p0-l2", "page_index": 0, "line_order": 2, "text": "광고SK주유400우리카드", "normalized_text": "광고SK주유400우리카드", "confidence": 1.0},
        {"block_id": "card-ad-p0-l3", "page_index": 0, "line_order": 3, "text": "400원", "normalized_text": "400원", "confidence": 1.0},
        {"block_id": "card-ad-p0-l4", "page_index": 0, "line_order": 4, "text": "고객센터", "normalized_text": "고객센터", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "50000"
    assert candidates.get("paid_amount") != "400"


def test_candidate_hint_builder_treats_korean_zero_as_amount_fragment() -> None:
    lines = [
        {"block_id": "korean-zero-p0-l0", "page_index": 0, "line_order": 0, "text": "\uacc4:", "normalized_text": "\uacc4:", "confidence": 1.0},
        {"block_id": "korean-zero-p0-l1", "page_index": 0, "line_order": 1, "text": "50", "normalized_text": "50", "confidence": 1.0},
        {"block_id": "korean-zero-p0-l2", "page_index": 0, "line_order": 2, "text": "\uacf5000", "normalized_text": "\uacf5000", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["total_amount"] == "50000"
    assert candidates["final_amount"] == "50000"


def test_business_number_dictionary_fills_known_sample_merchant() -> None:
    lines = [
        {"text": "사업자등록번호 227-82-06089", "confidence": 0.99},
        {"text": "합계 1,600", "confidence": 0.98},
    ]
    case = {
        "sample_id": "synthetic_known_business_merchant_001",
        "source_file_name": "synthetic_known_business_merchant_001.jpg",
        "paddle_lines": lines,
        "expected": {"merchant_name": "속초시시설관리공단"},
    }

    record = parse_synthetic_case(case)

    assert record.merchant_name == "속초시시설관리공단"


def test_business_number_dictionary_fills_human_anchor_sample_merchants() -> None:
    cases = [
        ("101-81-30747", "한화호텔앤드리조트(주) 설악"),
        ("104-81-91189", "롯데 유스컬처빌 파주점"),
        ("106-81-03487", "용산 아이파크 대원샵"),
        ("110-20-28152", "행촌제2주유소"),
        ("130-37-61978", "청해진"),
        ("139-17-01270", "GS25한화리조트설악"),
        ("144-04-03173", "이가네양꼬치/종각직영점"),
        ("152-21-01299", "총각김밥"),
        ("205-39-03897", "모쿠카츠"),
        ("214-86-08930", "양평휴게서울주유소"),
        ("219-30-43463", "오대산가마솥식당"),
        ("226-82-67609", "문화재구역주차료"),
        ("227-85-05723", "직염 프라자주유소"),
        ("227-82-06089", "속초시시설관리공단"),
        ("227-81-20556", "주식회사청초수"),
        ("261-81-16391", "매드포갈릭 D타워점"),
        ("287-87-01999", "오근내닭갈비 인사동점"),
        ("337-85-02907", "루원(광화문점)"),
        ("435-05-03469", "파리바게뜨 종로구청점"),
        ("503-33-22495", "플레이월드 파주점"),
        ("550-19-09550", "GS THE FRESH"),
        ("563-09-02031", "배스킨라빈스 서강신수점"),
        ("716-81-03135", "주식회사속초바베큐338"),
        ("728-32-00545", "크린에이드 이대역서희스타힐스점"),
        ("808-85-03280", "깐깐"),
    ]

    for business_number, merchant_name in cases:
        record = parse_synthetic_case(
            {
                "sample_id": f"synthetic_known_business_{business_number.replace('-', '')}",
                "source_file_name": f"synthetic_known_business_{business_number.replace('-', '')}.jpg",
                "paddle_lines": [
                    {"text": f"사업자등록번호 {business_number}", "confidence": 0.99},
                    {"text": "합계 10,000", "confidence": 0.98},
                ],
                "expected": {"merchant_name": merchant_name},
            }
        )

        assert record.merchant_name == merchant_name


def test_candidate_hint_builder_uses_merchant_label_value_on_following_line() -> None:
    lines = [
        {"block_id": "next-merchant-p0-l0", "page_index": 0, "line_order": 0, "text": "[매장명]", "normalized_text": "[매장명]", "confidence": 1.0},
        {"block_id": "next-merchant-p0-l1", "page_index": 0, "line_order": 1, "text": "청해진", "normalized_text": "청해진", "confidence": 1.0},
        {"block_id": "next-merchant-p0-l2", "page_index": 0, "line_order": 2, "text": "[사업자] 130-37-61978", "normalized_text": "[사업자] 130-37-61978", "confidence": 1.0},
        {"block_id": "next-merchant-p0-l3", "page_index": 0, "line_order": 3, "text": "합계금액 511,000", "normalized_text": "합계금액 511,000", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "청해진"


def test_candidate_hint_builder_uses_spaced_merchant_label_value() -> None:
    lines = [
        {"block_id": "spaced-merchant-p0-l0", "page_index": 0, "line_order": 0, "text": "가 맹 점 명 : 청해진", "normalized_text": "가 맹 점 명 : 청해진", "confidence": 1.0},
        {"block_id": "spaced-merchant-p0-l1", "page_index": 0, "line_order": 1, "text": "사업자 130-37-61978", "normalized_text": "사업자 130-37-61978", "confidence": 1.0},
        {"block_id": "spaced-merchant-p0-l2", "page_index": 0, "line_order": 2, "text": "합계금액 511,000", "normalized_text": "합계금액 511,000", "confidence": 1.0},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "청해진"


def test_candidate_hint_builder_skips_owner_name_after_spaced_merchant_label() -> None:
    lines = [
        {"block_id": "owner-after-label-p0-l0", "page_index": 0, "line_order": 0, "text": "속초시시설관리공단", "normalized_text": "속초시시설관리공단", "confidence": 0.98},
        {"block_id": "owner-after-label-p0-l1", "page_index": 0, "line_order": 1, "text": "상    호", "normalized_text": "상    호", "confidence": 0.98},
        {"block_id": "owner-after-label-p0-l2", "page_index": 0, "line_order": 2, "text": ":", "normalized_text": ":", "confidence": 0.98},
        {"block_id": "owner-after-label-p0-l3", "page_index": 0, "line_order": 3, "text": "이선규", "normalized_text": "이선규", "confidence": 0.98},
        {"block_id": "owner-after-label-p0-l4", "page_index": 0, "line_order": 4, "text": "대", "normalized_text": "대", "confidence": 0.98},
        {"block_id": "owner-after-label-p0-l5", "page_index": 0, "line_order": 5, "text": "표", "normalized_text": "표", "confidence": 0.98},
        {"block_id": "owner-after-label-p0-l6", "page_index": 0, "line_order": 6, "text": "사업자 227-82-06089", "normalized_text": "사업자 227-82-06089", "confidence": 0.98},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "속초시시설관리공단"
    assert candidates["business_number"] == "227-82-06089"


def test_candidate_hint_builder_uses_multiline_known_merchant_after_noisy_label_notice() -> None:
    lines = [
        {"block_id": "multiline-known-p0-l0", "page_index": 0, "line_order": 0, "text": "가맹점명", "normalized_text": "가맹점명", "confidence": 0.98},
        {"block_id": "multiline-known-p0-l1", "page_index": 0, "line_order": 1, "text": "실제와", "normalized_text": "실제와", "confidence": 0.98},
        {"block_id": "multiline-known-p0-l2", "page_index": 0, "line_order": 2, "text": "다른", "normalized_text": "다른", "confidence": 0.98},
        {"block_id": "multiline-known-p0-l3", "page_index": 0, "line_order": 3, "text": "크린에이드", "normalized_text": "크린에이드", "confidence": 0.98},
        {"block_id": "multiline-known-p0-l4", "page_index": 0, "line_order": 4, "text": "이대역서희스타힐", "normalized_text": "이대역서희스타힐", "confidence": 0.98},
        {"block_id": "multiline-known-p0-l5", "page_index": 0, "line_order": 5, "text": "스점", "normalized_text": "스점", "confidence": 0.98},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "크린에이드 이대역서희스타힐스점"


def test_candidate_hint_builder_uses_known_oilbank_fragment() -> None:
    lines = [
        {"block_id": "oilbank-p0-l0", "page_index": 0, "line_order": 0, "text": "동시D현대오일뱅크", "normalized_text": "동시D현대오일뱅크", "confidence": 0.90},
        {"block_id": "oilbank-p0-l1", "page_index": 0, "line_order": 1, "text": "프라자주유소", "normalized_text": "프라자주유소", "confidence": 0.90},
        {"block_id": "oilbank-p0-l2", "page_index": 0, "line_order": 2, "text": "합계 50,000", "normalized_text": "합계 50,000", "confidence": 0.98},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "현대오일뱅크 프라자주유소"


def test_candidate_hint_builder_uses_top_known_merchant_and_rejects_address_fragments() -> None:
    lines = [
        {"block_id": "top-merchant-p0-l0", "page_index": 0, "line_order": 0, "text": "행촌제2주유소", "normalized_text": "행촌제2주유소", "confidence": 0.96},
        {"block_id": "top-merchant-p0-l1", "page_index": 0, "line_order": 1, "text": "서울시", "normalized_text": "서울시", "confidence": 0.96},
        {"block_id": "top-merchant-p0-l2", "page_index": 0, "line_order": 2, "text": "서대문구", "normalized_text": "서대문구", "confidence": 0.96},
        {"block_id": "top-merchant-p0-l3", "page_index": 0, "line_order": 3, "text": "성산로", "normalized_text": "성산로", "confidence": 0.96},
        {"block_id": "top-merchant-p0-l4", "page_index": 0, "line_order": 4, "text": "자N0:110-20", "normalized_text": "자N0:110-20", "confidence": 0.8},
        {"block_id": "top-merchant-p0-l5", "page_index": 0, "line_order": 5, "text": "28152", "normalized_text": "28152", "confidence": 0.95},
        {"block_id": "top-merchant-p0-l6", "page_index": 0, "line_order": 6, "text": "신용카", "normalized_text": "신용카", "confidence": 0.96},
        {"block_id": "top-merchant-p0-l7", "page_index": 0, "line_order": 7, "text": "20", "normalized_text": "20", "confidence": 0.96},
        {"block_id": "top-merchant-p0-l8", "page_index": 0, "line_order": 8, "text": "000", "normalized_text": "000", "confidence": 0.96},
        {"block_id": "top-merchant-p0-l9", "page_index": 0, "line_order": 9, "text": "합계금액", "normalized_text": "합계금액", "confidence": 0.96},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "행촌제2주유소"
    assert candidates["total_amount"] == "20000"
    assert candidates["payment_method"] == "카드"


def test_candidate_hint_builder_uses_top_english_fresh_merchant() -> None:
    lines = [
        {"block_id": "top-fresh-p0-l0", "page_index": 0, "line_order": 0, "text": "GS THE FRESH", "normalized_text": "GS THE FRESH", "confidence": 0.96},
        {"block_id": "top-fresh-p0-l1", "page_index": 0, "line_order": 1, "text": "2026/05/15", "normalized_text": "2026/05/15", "confidence": 0.96},
        {"block_id": "top-fresh-p0-l2", "page_index": 0, "line_order": 2, "text": "신용카드", "normalized_text": "신용카드", "confidence": 0.96},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "GS THE FRESH"


def test_candidate_hint_builder_maps_gste_header_to_gs_the_fresh() -> None:
    lines = [
        {"block_id": "gste-p0-l0", "page_index": 0, "line_order": 0, "text": "GSTE", "normalized_text": "GSTE", "confidence": 0.9},
        {"block_id": "gste-p0-l1", "page_index": 0, "line_order": 1, "text": "2026/05/15", "normalized_text": "2026/05/15", "confidence": 0.96},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "GS THE FRESH"


def test_candidate_hint_builder_maps_noisy_gste_header_to_gs_the_fresh() -> None:
    lines = [
        {"block_id": "noisy-gste-p0-l0", "page_index": 0, "line_order": 0, "text": "WWW gSTelaIlLCOI", "normalized_text": "WWW gSTelaIlLCOI", "confidence": 0.9},
        {"block_id": "noisy-gste-p0-l1", "page_index": 0, "line_order": 1, "text": "2026/05/15", "normalized_text": "2026/05/15", "confidence": 0.96},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "GS THE FRESH"


def test_candidate_hint_builder_uses_top_samsung_service_merchant() -> None:
    lines = [
        {"block_id": "samsung-p0-l0", "page_index": 0, "line_order": 0, "text": "카드영수증", "normalized_text": "카드영수증", "confidence": 0.98},
        {"block_id": "samsung-p0-l1", "page_index": 0, "line_order": 1, "text": "삼성전자서비스", "normalized_text": "삼성전자서비스", "confidence": 0.99},
        {"block_id": "samsung-p0-l2", "page_index": 0, "line_order": 2, "text": "합계", "normalized_text": "합계", "confidence": 0.98},
        {"block_id": "samsung-p0-l3", "page_index": 0, "line_order": 3, "text": "269091", "normalized_text": "269091", "confidence": 0.98},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "삼성전자서비스"


def test_candidate_hint_builder_reads_split_card_label_as_payment_method() -> None:
    lines = [
        {"block_id": "split-card-p0-l0", "page_index": 0, "line_order": 0, "text": "카", "normalized_text": "카", "confidence": 0.99},
        {"block_id": "split-card-p0-l1", "page_index": 0, "line_order": 1, "text": "드", "normalized_text": "드", "confidence": 0.99},
        {"block_id": "split-card-p0-l2", "page_index": 0, "line_order": 2, "text": "종", "normalized_text": "종", "confidence": 0.99},
        {"block_id": "split-card-p0-l3", "page_index": 0, "line_order": 3, "text": "'류", "normalized_text": "'류", "confidence": 0.99},
        {"block_id": "split-card-p0-l4", "page_index": 0, "line_order": 4, "text": "현대법인비자", "normalized_text": "현대법인비자", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["payment_method"] == "카드"


def test_candidate_hint_builder_maps_top_baskin_header_to_safe_brand_name() -> None:
    lines = [
        {"block_id": "baskin-p0-l0", "page_index": 0, "line_order": 0, "text": "baskiN!31 robbins", "normalized_text": "baskiN!31 robbins", "confidence": 0.9},
        {"block_id": "baskin-p0-l1", "page_index": 0, "line_order": 1, "text": "[정상]", "normalized_text": "[정상]", "confidence": 0.96},
        {"block_id": "baskin-p0-l2", "page_index": 0, "line_order": 2, "text": "2026-05--", "normalized_text": "2026-05--", "confidence": 0.96},
        {"block_id": "baskin-p0-l3", "page_index": 0, "line_order": 3, "text": "10", "normalized_text": "10", "confidence": 0.96},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "배스킨라빈스"
    assert candidates["transaction_date"] == "2026-05-10"


def test_candidate_hint_builder_reads_same_line_korean_registration_date() -> None:
    lines = [
        {"block_id": "korean-date-p0-l0", "page_index": 0, "line_order": 0, "text": "[등록]2026년05월10일일", "normalized_text": "[등록]2026년05월10일일", "confidence": 0.99},
        {"block_id": "korean-date-p0-l1", "page_index": 0, "line_order": 1, "text": "합계금액", "normalized_text": "합계금액", "confidence": 0.99},
        {"block_id": "korean-date-p0-l2", "page_index": 0, "line_order": 2, "text": "20", "normalized_text": "20", "confidence": 0.99},
        {"block_id": "korean-date-p0-l3", "page_index": 0, "line_order": 3, "text": "000", "normalized_text": "000", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["transaction_date"] == "2026-05-10"


def test_candidate_hint_builder_reads_labeled_short_card_approval_date() -> None:
    lines = [
        {"block_id": "short-date-p0-l0", "page_index": 0, "line_order": 0, "text": "승인일시", "normalized_text": "승인일시", "confidence": 0.95},
        {"block_id": "short-date-p0-l1", "page_index": 0, "line_order": 1, "text": "260523504096", "normalized_text": "260523504096", "confidence": 0.99},
        {"block_id": "short-date-p0-l2", "page_index": 0, "line_order": 2, "text": "승인번호", "normalized_text": "승인번호", "confidence": 0.95},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["transaction_date"] == "2026-05-23"


def test_candidate_hint_builder_reads_split_sales_date_label_with_yyyymmdd() -> None:
    lines = [
        {"block_id": "sales-date-p0-l0", "page_index": 0, "line_order": 0, "text": "매출일", "normalized_text": "매출일", "confidence": 0.95},
        {"block_id": "sales-date-p0-l1", "page_index": 0, "line_order": 1, "text": "20260608", "normalized_text": "20260608", "confidence": 0.99},
        {"block_id": "sales-date-p0-l2", "page_index": 0, "line_order": 2, "text": "승인번호", "normalized_text": "승인번호", "confidence": 0.95},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["transaction_date"] == "2026-06-08"


def test_candidate_hint_builder_reads_split_merchant_label_after_noise() -> None:
    lines = [
        {"block_id": "split-store-p0-l0", "page_index": 0, "line_order": 0, "text": "매장명", "normalized_text": "매장명", "confidence": 0.95},
        {"block_id": "split-store-p0-l1", "page_index": 0, "line_order": 1, "text": "-", "normalized_text": "-", "confidence": 0.7},
        {"block_id": "split-store-p0-l2", "page_index": 0, "line_order": 2, "text": "테스트카페 종로점", "normalized_text": "테스트카페 종로점", "confidence": 0.97},
        {"block_id": "split-store-p0-l3", "page_index": 0, "line_order": 3, "text": "사업자번호 123-45-67891", "normalized_text": "사업자번호 123-45-67891", "confidence": 0.95},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "테스트카페 종로점"


def test_candidate_hint_builder_uses_same_line_merchant_before_business_number() -> None:
    lines = [
        {
            "block_id": "inline-business-merchant-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "무명분식 / 123-45-67891 / 서울시",
            "normalized_text": "무명분식 / 123-45-67891 / 서울시",
            "confidence": 0.98,
        },
        {"block_id": "inline-business-merchant-p0-l1", "page_index": 0, "line_order": 1, "text": "합계 8,000", "normalized_text": "합계 8,000", "confidence": 0.98},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "123-45-67891"
    assert candidates["merchant_name"] == "무명분식"


def test_candidate_hint_builder_uses_business_number_dictionary_for_chonggak_kimbap() -> None:
    lines = [
        {
            "block_id": "known-inline-business-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "총각김밥 / 152-21-01299 / 서울 종로",
            "normalized_text": "총각김밥 / 152-21-01299 / 서울 종로",
            "confidence": 0.98,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "152-21-01299"
    assert candidates["merchant_name"] == "총각김밥"


def test_candidate_hint_builder_does_not_use_identifier_before_business_number_as_merchant() -> None:
    lines = [
        {
            "block_id": "identifier-before-business-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "승인번호 20260526 / 123-45-67891",
            "normalized_text": "승인번호 20260526 / 123-45-67891",
            "confidence": 0.98,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "123-45-67891"
    assert "merchant_name" not in candidates


def test_candidate_hint_builder_reads_compact_date_before_approval_time() -> None:
    lines = [
        {"block_id": "approval-time-p0-l0", "page_index": 0, "line_order": 0, "text": "승인시간", "normalized_text": "승인시간", "confidence": 0.95},
        {"block_id": "approval-time-p0-l1", "page_index": 0, "line_order": 1, "text": "20260526", "normalized_text": "20260526", "confidence": 0.99},
        {"block_id": "approval-time-p0-l2", "page_index": 0, "line_order": 2, "text": "12:53:09", "normalized_text": "12:53:09", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["transaction_date"] == "20260526 12:53:09"


def test_candidate_hint_builder_reads_contiguous_compact_approval_datetime() -> None:
    lines = [
        {"block_id": "compact-approval-datetime-p0-l0", "page_index": 0, "line_order": 0, "text": "승인일시", "normalized_text": "승인일시", "confidence": 0.95},
        {"block_id": "compact-approval-datetime-p0-l1", "page_index": 0, "line_order": 1, "text": "20260526125309", "normalized_text": "20260526125309", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["transaction_date"] == "20260526 12:53:09"


def test_candidate_hint_builder_uses_merchant_business_owner_line() -> None:
    lines = [
        {
            "block_id": "merchant-owner-line-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "총각김밥 / 152-21-01299 / 박준이",
            "normalized_text": "총각김밥 / 152-21-01299 / 박준이",
            "confidence": 0.98,
        },
        {"block_id": "merchant-owner-line-p0-l1", "page_index": 0, "line_order": 1, "text": "승인일시", "normalized_text": "승인일시", "confidence": 0.95},
        {"block_id": "merchant-owner-line-p0-l2", "page_index": 0, "line_order": 2, "text": "20260526125309", "normalized_text": "20260526125309", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "총각김밥"
    assert candidates["business_number"] == "152-21-01299"
    assert candidates["transaction_date"] == "20260526 12:53:09"


def test_candidate_hint_builder_uses_split_merchant_business_owner_line() -> None:
    lines = [
        {
            "block_id": "split-merchant-owner-line-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "총각김밥 /",
            "normalized_text": "총각김밥 /",
            "confidence": 0.98,
        },
        {
            "block_id": "split-merchant-owner-line-p0-l1",
            "page_index": 0,
            "line_order": 1,
            "text": "152-21-01299 / 박준이",
            "normalized_text": "152-21-01299 / 박준이",
            "confidence": 0.98,
        },
        {"block_id": "split-merchant-owner-line-p0-l2", "page_index": 0, "line_order": 2, "text": "승인일시 :", "normalized_text": "승인일시 :", "confidence": 0.95},
        {"block_id": "split-merchant-owner-line-p0-l3", "page_index": 0, "line_order": 3, "text": "20260526", "normalized_text": "20260526", "confidence": 0.99},
        {"block_id": "split-merchant-owner-line-p0-l4", "page_index": 0, "line_order": 4, "text": "12:53:09", "normalized_text": "12:53:09", "confidence": 0.99},
        {"block_id": "split-merchant-owner-line-p0-l5", "page_index": 0, "line_order": 5, "text": "합계 5,600", "normalized_text": "합계 5,600", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "총각김밥"
    assert candidates["business_number"] == "152-21-01299"
    assert candidates["transaction_date"] == "20260526 12:53:09"
    assert candidates["total_amount"] == "5600"


def test_parser_receipt_keeps_split_merchant_business_owner_line() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_split_merchant_business_owner_001",
            "source_file_name": "synthetic_split_merchant_business_owner_001.jpg",
            "description": "상호/사업자번호/소유자 구조가 줄 단위로 갈라져도 상호와 날짜를 유지",
            "paddle_lines": [
                {"text": "총각김밥 /", "confidence": 0.98},
                {"text": "152-21-01299 / 박준이", "confidence": 0.98},
                {"text": "승인일시 :", "confidence": 0.95},
                {"text": "20260526", "confidence": 0.99},
                {"text": "12:53:09", "confidence": 0.99},
                {"text": "합계 5,600", "confidence": 0.99},
            ],
            "expected": {
                "merchant_name": "총각김밥",
                "business_number": "152-21-01299",
                "transaction_date": "2026-05-26",
                "total_amount": 5600,
                "review_required_expected": True,
            },
        }
    )

    assert record.merchant_name == "총각김밥"
    assert record.business_number == "152-21-01299"
    assert record.transaction_date and record.transaction_date.isoformat() == "2026-05-26"
    assert record.total_amount == 5600


def test_parser_prefers_business_anchor_over_short_owner_or_fragment_merchants() -> None:
    cases = [
        ("synthetic_owner_anchor_sokcho", "이선규", "227-82-06089", "속초시시설관리공단"),
        ("synthetic_market_place_anchor_sokcho", "속초관광수산시장", "227-82-06089", "속초시시설관리공단"),
        ("synthetic_short_fragment_anchor_haengchon", "시0", "110-20-28152", "행촌제2주유소"),
        ("synthetic_branch_fragment_anchor_lotte", "파주점", "104-81-91189", "롯데 유스컬처빌 파주점"),
        ("synthetic_parking_owner_anchor", "박동순", "226-82-67609", "문화재구역주차료"),
    ]

    for sample_id, merchant_candidate, business_number, expected_merchant in cases:
        record = parse_synthetic_case(
            {
                "sample_id": sample_id,
                "source_file_name": f"{sample_id}.jpg",
                "paddle_lines": [
                    {"text": merchant_candidate, "confidence": 0.98},
                    {"text": f"사업자 {business_number}", "confidence": 0.98},
                    {"text": "합계 10,000", "confidence": 0.98},
                ],
                "expected": {
                    "merchant_name": expected_merchant,
                    "business_number": business_number,
                    "total_amount": 10000,
                    "review_required_expected": True,
                },
            }
        )

        assert record.merchant_name == expected_merchant
        assert record.business_number == business_number


def test_parser_keeps_labeled_total_when_legacy_paid_amount_is_long_identifier() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_total_not_replaced_by_long_identifier_001",
            "source_file_name": "synthetic_total_not_replaced_by_long_identifier_001.jpg",
            "paddle_lines": [
                {"text": "이가네양꼬치/종각직영점", "confidence": 0.98},
                {"text": "사업자 144-04-03173", "confidence": 0.98},
                {"text": "합 계 금 액 170,000", "confidence": 0.98},
                {"text": "카드결제 170000775", "confidence": 0.80},
            ],
            "expected": {
                "merchant_name": "이가네양꼬치/종각직영점",
                "business_number": "144-04-03173",
                "total_amount": 170000,
                "review_required_expected": True,
            },
        }
    )

    assert record.merchant_name == "이가네양꼬치/종각직영점"
    assert record.total_amount == 170000
    assert "paid_amount_identifier_candidate_ignored" in record.amount_warnings


def test_candidate_hint_builder_reads_app_receipt_short_labeled_date_and_split_amount() -> None:
    lines = [
        {"block_id": "app-short-p0-l0", "page_index": 0, "line_order": 0, "text": "영수증", "normalized_text": "영수증", "confidence": 0.98},
        {"block_id": "app-short-p0-l1", "page_index": 0, "line_order": 1, "text": "결제", "normalized_text": "결제", "confidence": 0.98},
        {"block_id": "app-short-p0-l2", "page_index": 0, "line_order": 2, "text": "취소", "normalized_text": "취소", "confidence": 0.98},
        {"block_id": "app-short-p0-l3", "page_index": 0, "line_order": 3, "text": "하나로마트서강점", "normalized_text": "하나로마트서강점", "confidence": 0.98},
        {"block_id": "app-short-p0-l4", "page_index": 0, "line_order": 4, "text": "날짜:", "normalized_text": "날짜:", "confidence": 0.98},
        {"block_id": "app-short-p0-l5", "page_index": 0, "line_order": 5, "text": "202659", "normalized_text": "202659", "confidence": 0.98},
        {"block_id": "app-short-p0-l6", "page_index": 0, "line_order": 6, "text": "오후", "normalized_text": "오후", "confidence": 0.98},
        {"block_id": "app-short-p0-l7", "page_index": 0, "line_order": 7, "text": "5:28:37", "normalized_text": "5:28:37", "confidence": 0.98},
        {"block_id": "app-short-p0-l8", "page_index": 0, "line_order": 8, "text": "금액:", "normalized_text": "금액:", "confidence": 0.98},
        {"block_id": "app-short-p0-l9", "page_index": 0, "line_order": 9, "text": "W81", "normalized_text": "W81", "confidence": 0.98},
        {"block_id": "app-short-p0-l10", "page_index": 0, "line_order": 10, "text": "1920", "normalized_text": "1920", "confidence": 0.98},
    ]

    candidates = {candidate["candidate_type"]: candidate["value"] for candidate in build_paddle_candidate_hints_from_safe_lines(lines)}

    assert candidates["merchant_name"] == "하나로마트서강점"
    assert candidates["transaction_date"] == "2026-05-09"
    assert candidates["total_amount"] == "81920"


def test_parser_receipt_reads_app_receipt_short_labeled_date_and_split_amount() -> None:
    case = {
        "sample_id": "synthetic_app_receipt_short_labeled_date_001",
        "source_file_name": "synthetic_app_receipt_short_labeled_date_001.jpg",
        "paddle_lines": [
            {"text": "영수증", "confidence": 0.98},
            {"text": "결제", "confidence": 0.98},
            {"text": "취소", "confidence": 0.98},
            {"text": "하나로마트서강점", "confidence": 0.98},
            {"text": "날짜:", "confidence": 0.98},
            {"text": "202659", "confidence": 0.98},
            {"text": "오후", "confidence": 0.98},
            {"text": "5:28:37", "confidence": 0.98},
            {"text": "금액:", "confidence": 0.98},
            {"text": "W81", "confidence": 0.98},
            {"text": "1920", "confidence": 0.98},
        ],
        "expected": {
            "merchant_name": "하나로마트서강점",
            "transaction_date": "2026-05-09",
            "total_amount": 81920,
        },
    }

    record = parse_synthetic_case(case)

    assert record.merchant_name == "하나로마트서강점"
    assert record.transaction_date and record.transaction_date.isoformat() == "2026-05-09"
    assert record.total_amount == 81920


def test_candidate_hint_builder_reads_app_payment_info_center_merchant() -> None:
    lines = [
        {"block_id": "app-info-p0-l0", "page_index": 0, "line_order": 0, "text": "결제", "normalized_text": "결제", "confidence": 0.98},
        {"block_id": "app-info-p0-l1", "page_index": 0, "line_order": 1, "text": "정보", "normalized_text": "정보", "confidence": 0.98},
        {"block_id": "app-info-p0-l2", "page_index": 0, "line_order": 2, "text": "카테고리", "normalized_text": "카테고리", "confidence": 0.98},
        {"block_id": "app-info-p0-l3", "page_index": 0, "line_order": 3, "text": "미지정", "normalized_text": "미지정", "confidence": 0.98},
        {"block_id": "app-info-p0-l4", "page_index": 0, "line_order": 4, "text": "모쿠", "normalized_text": "모쿠", "confidence": 0.98},
        {"block_id": "app-info-p0-l5", "page_index": 0, "line_order": 5, "text": "결제 날짜 및 시간:", "normalized_text": "결제 날짜 및 시간:", "confidence": 0.98},
        {"block_id": "app-info-p0-l6", "page_index": 0, "line_order": 6, "text": "2026.04.27. 오후 09:30", "normalized_text": "2026.04.27. 오후 09:30", "confidence": 0.98},
        {"block_id": "app-info-p0-l7", "page_index": 0, "line_order": 7, "text": "총액:", "normalized_text": "총액:", "confidence": 0.98},
        {"block_id": "app-info-p0-l8", "page_index": 0, "line_order": 8, "text": "81,500원", "normalized_text": "81,500원", "confidence": 0.98},
    ]

    candidates = {candidate["candidate_type"]: candidate["value"] for candidate in build_paddle_candidate_hints_from_safe_lines(lines)}

    assert candidates["merchant_name"] == "모쿠"
    assert candidates["transaction_date"] == "2026-04-27"
    assert candidates["total_amount"] == "81500"


def test_candidate_hint_builder_does_not_guess_merchant_from_single_app_marker() -> None:
    lines = [
        {"block_id": "single-marker-p0-l0", "page_index": 0, "line_order": 0, "text": "영수증", "normalized_text": "영수증", "confidence": 0.98},
        {"block_id": "single-marker-p0-l1", "page_index": 0, "line_order": 1, "text": "일반 안내문", "normalized_text": "일반 안내문", "confidence": 0.98},
        {"block_id": "single-marker-p0-l2", "page_index": 0, "line_order": 2, "text": "이벤트", "normalized_text": "이벤트", "confidence": 0.98},
        {"block_id": "single-marker-p0-l3", "page_index": 0, "line_order": 3, "text": "단가 수량", "normalized_text": "단가 수량", "confidence": 0.98},
        {"block_id": "single-marker-p0-l4", "page_index": 0, "line_order": 4, "text": "금액", "normalized_text": "금액", "confidence": 0.98},
        {"block_id": "single-marker-p0-l5", "page_index": 0, "line_order": 5, "text": "5,000", "normalized_text": "5,000", "confidence": 0.98},
    ]

    candidates = {candidate["candidate_type"]: candidate["value"] for candidate in build_paddle_candidate_hints_from_safe_lines(lines)}

    assert "merchant_name" not in candidates


def test_candidate_hint_builder_reads_split_total_label_amount_before_receipt_number() -> None:
    lines = [
        {"block_id": "split-total-p0-l0", "page_index": 0, "line_order": 0, "text": "영수증 # 20260512", "normalized_text": "영수증 # 20260512", "confidence": 0.98},
        {"block_id": "split-total-p0-l1", "page_index": 0, "line_order": 1, "text": "10047", "normalized_text": "10047", "confidence": 0.98},
        {"block_id": "split-total-p0-l2", "page_index": 0, "line_order": 2, "text": "합계", "normalized_text": "합계", "confidence": 0.98},
        {"block_id": "split-total-p0-l3", "page_index": 0, "line_order": 3, "text": "금액", "normalized_text": "금액", "confidence": 0.98},
        {"block_id": "split-total-p0-l4", "page_index": 0, "line_order": 4, "text": "15", "normalized_text": "15", "confidence": 0.98},
        {"block_id": "split-total-p0-l5", "page_index": 0, "line_order": 5, "text": "000", "normalized_text": "000", "confidence": 0.98},
        {"block_id": "split-total-p0-l6", "page_index": 0, "line_order": 6, "text": "승인금액:15000", "normalized_text": "승인금액:15000", "confidence": 0.98},
    ]

    candidates = {candidate["candidate_type"]: candidate["value"] for candidate in build_paddle_candidate_hints_from_safe_lines(lines)}

    assert candidates["total_amount"] == "15000"
    assert candidates["final_amount"] == "15000"


def test_standard_context_uses_dailyfix_business_number_anchor_only_when_identifier_present() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_dailyfix_business_anchor_001",
            "source_file_name": "synthetic_dailyfix_business_anchor_001.jpg",
            "paddle_lines": [
                {"text": "데일링픽스", "confidence": 0.90},
                {"text": "1798502903", "confidence": 0.98},
                {"text": "합계", "confidence": 0.98},
                {"text": "금액", "confidence": 0.98},
                {"text": "15", "confidence": 0.98},
                {"text": "000", "confidence": 0.98},
                {"text": "일시: 2026-05-12", "confidence": 0.98},
            ],
            "expected": {
                "merchant_name": "데일리픽스 을지로",
                "business_number": "179-85-02903",
                "transaction_date": "2026-05-12",
                "total_amount": 15000,
                "review_required_expected": True,
            },
        }
    )

    assert record.merchant_name == "데일리픽스 을지로"
    assert record.business_number == "179-85-02903"
    assert record.total_amount == 15000


def test_candidate_hint_builder_reads_card_sales_total_adjacent_amount() -> None:
    lines = [
        {"block_id": "card-sales-p0-l0", "page_index": 0, "line_order": 0, "text": "평양고깃집", "normalized_text": "평양고깃집", "confidence": 0.98},
        {"block_id": "card-sales-p0-l1", "page_index": 0, "line_order": 1, "text": "384-11-02561", "normalized_text": "384-11-02561", "confidence": 0.98},
        {"block_id": "card-sales-p0-l2", "page_index": 0, "line_order": 2, "text": "2026-05-10", "normalized_text": "2026-05-10", "confidence": 0.98},
        {"block_id": "card-sales-p0-l3", "page_index": 0, "line_order": 3, "text": "45000", "normalized_text": "45000", "confidence": 0.98},
        {"block_id": "card-sales-p0-l4", "page_index": 0, "line_order": 4, "text": "매출합계카드", "normalized_text": "매출합계카드", "confidence": 0.98},
    ]

    candidates = {candidate["candidate_type"]: candidate["value"] for candidate in build_paddle_candidate_hints_from_safe_lines(lines)}

    assert candidates["merchant_name"] == "평양고깃집"
    assert candidates["transaction_date"] == "2026-05-10"
    assert candidates["business_number"] == "384-11-02561"
    assert candidates["total_amount"] == "45000"


def test_candidate_hint_builder_recovers_noisy_embedded_approval_datetime() -> None:
    lines = [
        {"block_id": "noisy-datetime-p0-l0", "page_index": 0, "line_order": 0, "text": "승", "normalized_text": "승", "confidence": 0.96},
        {"block_id": "noisy-datetime-p0-l1", "page_index": 0, "line_order": 1, "text": "인", "normalized_text": "인", "confidence": 0.96},
        {"block_id": "noisy-datetime-p0-l2", "page_index": 0, "line_order": 2, "text": "간", "normalized_text": "간", "confidence": 0.96},
        {
            "block_id": "noisy-datetime-p0-l3",
            "page_index": 0,
            "line_order": 3,
            "text": "N9260525085745208437",
            "normalized_text": "N9260525085745208437",
            "confidence": 0.93,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["transaction_date"] == "20260525 08:57:45"


def test_candidate_hint_builder_recovers_split_tax_total_missing_zero() -> None:
    lines = [
        {"block_id": "split-tax-p0-l0", "page_index": 0, "line_order": 0, "text": "비씨카드", "normalized_text": "비씨카드", "confidence": 0.97},
        {"block_id": "split-tax-p0-l1", "page_index": 0, "line_order": 1, "text": "272원", "normalized_text": "272원", "confidence": 0.96},
        {"block_id": "split-tax-p0-l2", "page_index": 0, "line_order": 2, "text": "657", "normalized_text": "657", "confidence": 0.96},
        {"block_id": "split-tax-p0-l3", "page_index": 0, "line_order": 3, "text": "728원", "normalized_text": "728원", "confidence": 0.96},
        {"block_id": "split-tax-p0-l4", "page_index": 0, "line_order": 4, "text": "65", "normalized_text": "65", "confidence": 0.96},
        {"block_id": "split-tax-p0-l5", "page_index": 0, "line_order": 5, "text": "72300원", "normalized_text": "72300원", "confidence": 0.96},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["supply_amount"] == "657272"
    assert candidates["vat_amount"] == "65728"
    assert candidates["total_amount"] == "723000"
    assert candidates["final_amount"] == "723000"


def test_candidate_hint_builder_normalizes_noisy_labeled_known_merchant() -> None:
    lines = [
        {
            "block_id": "noisy-known-merchant-p0-l0",
            "page_index": 0,
            "line_order": 0,
            "text": "상호명 어스즈 플레이월드 파주점 STO",
            "normalized_text": "상호명 어스즈 플레이월드 파주점 STO",
            "confidence": 0.98,
        },
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "플레이월드 파주점"


def test_standard_context_normalizes_noisy_known_merchant_without_business_number() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_noisy_known_merchant_name_001",
            "source_file_name": "synthetic_noisy_known_merchant_name_001.jpg",
            "description": "라벨 상호에 OCR 노이즈가 붙어도 known merchant anchor로 정리",
            "paddle_lines": [
                {"text": "상호명 어스즈 플레이월드 파주점 STO", "confidence": 0.98},
                {"text": "출력일시 : 2026-06-06 11:01:24", "confidence": 0.98},
                {"text": "합계금액 61,000", "confidence": 0.99},
            ],
            "expected": {
                "merchant_name": "플레이월드 파주점",
                "transaction_date": "2026-06-06",
                "total_amount": 61000,
                "final_amount": 61000,
                "review_required_expected": True,
            },
        }
    )

    assert record.merchant_name == "플레이월드 파주점"


def test_candidate_hint_builder_does_not_read_approval_number_as_compact_date() -> None:
    lines = [
        {"block_id": "approval-number-date-p0-l0", "page_index": 0, "line_order": 0, "text": "승인번호", "normalized_text": "승인번호", "confidence": 0.95},
        {"block_id": "approval-number-date-p0-l1", "page_index": 0, "line_order": 1, "text": "202605260001", "normalized_text": "202605260001", "confidence": 0.99},
        {"block_id": "approval-number-date-p0-l2", "page_index": 0, "line_order": 2, "text": "합계 5,000", "normalized_text": "합계 5,000", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert "transaction_date" not in candidates


def test_candidate_hint_builder_extracts_livestock_distribution_merchant_near_business_number() -> None:
    lines = [
        {"block_id": "livestock-p0-l0", "page_index": 0, "line_order": 0, "text": "정선축산유통", "normalized_text": "정선축산유통", "confidence": 0.98},
        {"block_id": "livestock-p0-l1", "page_index": 0, "line_order": 1, "text": "사업자번호 206-85-10228", "normalized_text": "사업자번호 206-85-10228", "confidence": 0.98},
        {"block_id": "livestock-p0-l2", "page_index": 0, "line_order": 2, "text": "승인일시 20260526152446", "normalized_text": "승인일시 20260526152446", "confidence": 0.98},
        {"block_id": "livestock-p0-l3", "page_index": 0, "line_order": 3, "text": "승인번호 73297759", "normalized_text": "승인번호 73297759", "confidence": 0.98},
        {"block_id": "livestock-p0-l4", "page_index": 0, "line_order": 4, "text": "합계 107,000", "normalized_text": "합계 107,000", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["merchant_name"] == "정선축산유통"
    assert candidates["transaction_date"] == "20260526 15:24:46"
    assert candidates["approval_number"] == "73297759"
    assert candidates["total_amount"] == "107000"


def test_parser_receipt_keeps_livestock_distribution_merchant_and_approval_number() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_livestock_distribution_approval_001",
            "source_file_name": "synthetic_livestock_distribution_approval_001.jpg",
            "description": "사업자번호 주변 상호와 승인번호를 보수적으로 복원",
            "paddle_lines": [
                {"text": "정선축산유통", "confidence": 0.98},
                {"text": "사업자번호 206-85-10228", "confidence": 0.98},
                {"text": "승인일시 20260526152446", "confidence": 0.98},
                {"text": "승인번호 73297759", "confidence": 0.98},
                {"text": "합계 107,000", "confidence": 0.99},
            ],
            "expected": {
                "merchant_name": "정선축산유통",
                "transaction_date": "2026-05-26",
                "approval_number": "73297759",
                "total_amount": 107000,
                "review_required_expected": True,
            },
        }
    )

    assert record.merchant_name == "정선축산유통"
    assert record.transaction_date and record.transaction_date.isoformat() == "2026-05-26"
    assert record.approval_number == "73297759"
    assert record.total_amount == 107000


def test_candidate_hint_builder_extracts_split_approval_number_without_using_it_as_date() -> None:
    lines = [
        {"block_id": "approval-split-p0-l0", "page_index": 0, "line_order": 0, "text": "승인일시", "normalized_text": "승인일시", "confidence": 0.98},
        {"block_id": "approval-split-p0-l1", "page_index": 0, "line_order": 1, "text": "20260526125309", "normalized_text": "20260526125309", "confidence": 0.98},
        {"block_id": "approval-split-p0-l2", "page_index": 0, "line_order": 2, "text": "승인번호", "normalized_text": "승인번호", "confidence": 0.98},
        {"block_id": "approval-split-p0-l3", "page_index": 0, "line_order": 3, "text": "202605252085745", "normalized_text": "202605252085745", "confidence": 0.98},
        {"block_id": "approval-split-p0-l4", "page_index": 0, "line_order": 4, "text": "합계 5,600", "normalized_text": "합계 5,600", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["transaction_date"] == "20260526 12:53:09"
    assert candidates["approval_number"] == "202605252085745"
    assert candidates["total_amount"] == "5600"


def test_parser_receipt_keeps_split_contiguous_datetime_and_approval_number() -> None:
    record = parse_synthetic_case(
        {
            "sample_id": "synthetic_split_contiguous_datetime_approval_001",
            "source_file_name": "synthetic_split_contiguous_datetime_approval_001.jpg",
            "description": "분리된 승인일시 라벨과 긴 승인번호를 별도 후보로 유지",
            "paddle_lines": [
                {"text": "승인일시", "confidence": 0.98},
                {"text": "20260526125309", "confidence": 0.98},
                {"text": "승인번호", "confidence": 0.98},
                {"text": "202605252085745", "confidence": 0.98},
                {"text": "합계 5,600", "confidence": 0.99},
            ],
            "expected": {
                "transaction_date": "2026-05-26",
                "approval_number": "202605252085745",
                "total_amount": 5600,
                "review_required_expected": True,
            },
        }
    )

    assert record.transaction_date and record.transaction_date.isoformat() == "2026-05-26"
    assert record.approval_number == "202605252085745"
    assert record.total_amount == 5600


def test_candidate_hint_builder_does_not_use_address_fragment_as_known_merchant() -> None:
    lines = [
        {"block_id": "address-only-p0-l0", "page_index": 0, "line_order": 0, "text": "서울시", "normalized_text": "서울시", "confidence": 0.99},
        {"block_id": "address-only-p0-l1", "page_index": 0, "line_order": 1, "text": "서대문구", "normalized_text": "서대문구", "confidence": 0.99},
        {"block_id": "address-only-p0-l2", "page_index": 0, "line_order": 2, "text": "성산로", "normalized_text": "성산로", "confidence": 0.99},
        {"block_id": "address-only-p0-l3", "page_index": 0, "line_order": 3, "text": "123-45-67891", "normalized_text": "123-45-67891", "confidence": 0.99},
    ]

    candidates = {
        candidate["candidate_type"]: candidate["normalized_value"]
        for candidate in build_paddle_candidate_hints_from_safe_lines(lines)
    }

    assert candidates["business_number"] == "123-45-67891"
    assert "merchant_name" not in candidates


def test_default_synthetic_quality_tests_do_not_import_paddleocr() -> None:
    assert "paddleocr" not in sys.modules

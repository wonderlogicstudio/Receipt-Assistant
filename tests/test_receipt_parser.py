from __future__ import annotations

from app.core.enums import CardMatchStatus, EvidenceType, OCRProviderName, OCRStatus, ReviewStatus
from app.core.ocr_models import OCRResult
from app.parser.normalizers import (
    calculate_estimated_vat_amounts,
    normalize_amount,
    normalize_business_number,
    normalize_date,
    normalize_discount_amount,
)
from app.parser.receipt_parser import (
    ReceiptParser,
    build_receipt_amount_diagnostics,
    diagnose_discount_lines,
    is_valid_merchant_candidate,
)


SAMPLE_OCR_TEXT = "\n".join(
    [
        "상호명: 테스트카페",
        "사업자번호: 123-45-67890",
        "거래일자: 2026.05.07",
        "공급가액: 10,909원",
        "부가세: 1,091원",
        "합계: 12,000원",
        "결제수단: 신용카드",
    ]
)

DISCOUNT_ZERO_PAYMENT_TRACE_TEXT = "\n".join(
    [
        "제품명",
        "(할인내역)        수량        금액",
        "                  (할인금액)",
        "레디팩(아몬드봉봉)          10,800",
        "KT 멤버십 VVIP 초이스      -10,800",
        ">>드라이아이스(분) 10       0",
        "총매출액                  10,800",
        "할인금액                  10,800",
        "합계금액                  0",
        "받은금액                  0",
    ]
)


def make_ocr_result(
    raw_text: str = SAMPLE_OCR_TEXT,
    status: str = OCRStatus.COMPLETED.value,
    raw_json: dict[str, object] | None = None,
) -> OCRResult:
    if status == OCRStatus.COMPLETED.value:
        return OCRResult.completed(
            source_file_id="source-file-1",
            source_file_name="sample_receipt.jpg",
            stored_relative_path="data/uploads/session-1/sample_receipt.jpg",
            provider=OCRProviderName.MOCK.value,
            raw_text=raw_text,
            raw_json=raw_json or {},
            confidence=0.94,
        )
    return OCRResult.failed(
        source_file_id="source-file-1",
        source_file_name="sample_receipt.jpg",
        stored_relative_path="data/uploads/session-1/sample_receipt.jpg",
        provider=OCRProviderName.MOCK.value,
        error_message="mock failure",
    )


def test_sample_ocr_raw_text_is_converted_to_receipt_record():
    receipt = ReceiptParser().parse(make_ocr_result())

    assert receipt.transaction_date.isoformat() == "2026-05-07"
    assert receipt.merchant_name == "테스트카페"
    assert receipt.business_number == "123-45-67890"
    assert receipt.supply_amount == 10909
    assert receipt.vat_amount == 1091
    assert receipt.estimated_supply_amount is None
    assert receipt.estimated_vat_amount is None
    assert receipt.vat_source == "explicit"
    assert receipt.vat_review_required is False
    assert receipt.total_amount == 12000
    assert receipt.payment_method == "신용카드"
    assert receipt.review_status == ReviewStatus.PENDING.value


def test_ocr_result_metadata_is_reflected_in_receipt_record():
    ocr_result = make_ocr_result()

    receipt = ReceiptParser().parse(ocr_result)

    assert receipt.ocr_result_id == ocr_result.id
    assert receipt.source_file_id == "source-file-1"
    assert receipt.source_file_name == "sample_receipt.jpg"
    assert receipt.stored_relative_path == "data/uploads/session-1/sample_receipt.jpg"
    assert receipt.session_id == "session-1"
    assert receipt.confidence == 0.94


def test_receipt_normalizers_handle_supported_formats():
    assert normalize_date("2026.05.07").isoformat() == "2026-05-07"
    assert normalize_date("20260507").isoformat() == "2026-05-07"
    assert normalize_amount("12,000원") == 12000
    assert normalize_amount("₩12,000") == 12000
    assert normalize_amount("－10,800") == -10800
    assert normalize_amount(" - 10,800") == -10800
    assert normalize_amount("(-10,800)") == -10800
    assert normalize_amount("10.800") == 10800
    assert normalize_amount("10, 800") == 10800
    assert normalize_amount("10 800") == 10800
    assert normalize_discount_amount("-10,800") == 10800
    assert calculate_estimated_vat_amounts(5100) == (4636, 464)
    assert normalize_business_number("1234567890") == "123-45-67890"
    assert normalize_business_number("123-45-67890") == "123-45-67890"


def test_missing_total_amount_needs_review_with_warning():
    raw_text = "\n".join(["테스트카페", "거래일자: 2026.05.07", "사업자번호: 123-45-67890"])

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "금액누락" in receipt.parser_warnings
    assert "금액누락" in receipt.review_reason


def test_discounted_zero_payment_receipt_keeps_zero_total_and_amount_fields():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "상품금액: 10,800원",
            "할인금액: -10,800원",
            "합계금액: 0원",
            "받은금액: 0원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0
    assert receipt.amount_source == "paid_amount"
    assert "discount_detected" in receipt.amount_warnings
    assert "zero_payment_after_discount" in receipt.amount_warnings
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert receipt.export_included is True


def test_positive_summary_discount_keeps_paid_zero_total():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "KT 할인대상 상품금액 10,800",
            "KT 할인금액 -10,800",
            "총매출액 10,800",
            "할인금액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0
    assert receipt.amount_source == "paid_amount"
    assert "discount_detected" in receipt.amount_warnings
    assert "zero_payment_after_discount" in receipt.amount_warnings
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value


def test_discount_target_amount_is_not_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "KT 할인대상 상품금액 10,800",
            "합계금액 10,800",
            "받은금액 10,800",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount is None
    assert receipt.total_amount == 10800
    assert "discount_target_amount_not_discount" in receipt.amount_warnings
    assert "discount_detected" not in receipt.amount_warnings


def test_summary_discount_is_preferred_over_duplicate_item_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "KT 멤버십 VVIP 초이스 -10,800",
            "총매출액 10,800",
            "할인금액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0
    assert "discount_summary_preferred" in receipt.amount_warnings
    assert "discount_candidate_duplicate_ignored" in receipt.amount_warnings


def test_item_discount_is_used_when_summary_discount_is_missing():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "상품금액 10,800",
            "KT 멤버십 VVIP 초이스 -10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0


def test_positive_discount_amount_line_is_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인금액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0


def test_ocr_spaced_discount_label_is_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할 인 금 액        10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0
    assert "discount_detected" in receipt.amount_warnings
    assert "zero_payment_after_discount" in receipt.amount_warnings


def test_ocr_split_discount_label_is_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인 금 액        10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0


def test_ocr_kt_discount_amount_with_spaces_and_negative_sign_is_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "KT 할인대상 상품금액 10,800",
            "KT 할인 금액 -10,800",
            "총매출액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0
    assert "discount_target_amount_not_discount" in receipt.amount_warnings


def test_ocr_dot_thousands_separator_discount_amount_is_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인금액 10.800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0


def test_ocr_spaced_thousands_separator_discount_amount_is_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인금액 10, 800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0


def test_ocr_discount_amount_can_be_read_from_next_line():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인금액",
            "10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0
    assert "discount_amount_from_next_line" in receipt.amount_warnings


def test_ocr_discount_target_amount_next_line_is_not_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "KT 할인대상 상품금액",
            "10,800",
            "합계금액 10,800",
            "받은금액 10,800",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount is None
    assert receipt.total_amount == 10800
    assert "discount_target_amount_not_discount" in receipt.amount_warnings


def test_ocr_amount_letter_o_is_corrected_inside_discount_amount_candidate():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인금액 10,8O0",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0
    assert "discount_detected" in receipt.amount_warnings


def test_ocr_amount_letter_l_is_corrected_inside_discount_amount_candidate():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인금액 l0,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0


def test_ocr_amount_letter_b_is_corrected_inside_discount_amount_candidate():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인금액 10,B00",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0


def test_ocr_fuzzy_discount_label_is_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할안금액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0
    assert "discount_label_fuzzy_matched" in receipt.amount_warnings


def test_ocr_fuzzy_kt_discount_label_is_treated_as_discount_without_target_confusion():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "KT 할인대상 상품금액 10,800",
            "KT 할민 금액 -10,800",
            "총매출액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0
    assert "discount_target_amount_not_discount" in receipt.amount_warnings


def test_fuzzy_discount_target_label_is_preferred_over_discount_amount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "KT 할인대상 상품금액 10,800",
            "합계금액 10,800",
            "받은금액 10,800",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount is None
    assert receipt.total_amount == 10800


def test_raw_json_table_cells_are_used_for_discount_amount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )
    raw_json = {
        "analyzeResult": {
            "tables": [
                {
                    "cells": [
                        {"rowIndex": 0, "columnIndex": 0, "content": "할인금액"},
                        {"rowIndex": 0, "columnIndex": 1, "content": "10,800"},
                    ]
                }
            ]
        }
    }

    receipt = ReceiptParser().parse(make_ocr_result(raw_text, raw_json=raw_json))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0


def test_raw_text_and_raw_json_duplicate_discount_amount_is_not_summed_twice():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인금액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )
    raw_json = {
        "analyzeResult": {
            "tables": [
                {
                    "cells": [
                        {"rowIndex": 0, "columnIndex": 0, "content": "할인금액"},
                        {"rowIndex": 0, "columnIndex": 1, "content": "10,800"},
                    ]
                }
            ]
        }
    }

    receipt = ReceiptParser().parse(make_ocr_result(raw_text, raw_json=raw_json))

    assert receipt.discount_amount == 10800
    assert "discount_candidate_duplicate_ignored" in receipt.amount_warnings


def test_discount_diagnostics_do_not_include_original_line_or_amount_value():
    diagnostics = diagnose_discount_lines("할안금액 10,8O0")

    assert diagnostics
    first = diagnostics[0]
    assert first["line_type"] == "discount_summary"
    assert first["label_match_method"] == "fuzzy"
    assert first["amount_detected"] is True
    assert first["amount_shape"] == "ocr_corrected_amount"
    assert "line" not in first
    assert "10,8O0" not in str(first)


def test_realistic_discount_receipt_keeps_parser_amount_fields_at_zero_payment():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            DISCOUNT_ZERO_PAYMENT_TRACE_TEXT,
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0
    assert receipt.amount_source == "paid_amount"
    assert "discount_detected" in receipt.amount_warnings
    assert "zero_payment_after_discount" in receipt.amount_warnings
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value


def test_discount_zero_payment_pipeline_trace_parser_result_and_diagnostics_are_non_sensitive():
    receipt = ReceiptParser().parse(make_ocr_result(DISCOUNT_ZERO_PAYMENT_TRACE_TEXT))
    diagnostics = build_receipt_amount_diagnostics(DISCOUNT_ZERO_PAYMENT_TRACE_TEXT)
    line_types = {item["line_type"] for item in diagnostics}

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0
    assert receipt.amount_source in {"paid_amount", "final_amount"}
    assert "discount_detected" in receipt.amount_warnings
    assert "zero_payment_after_discount" in receipt.amount_warnings
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value

    assert {"discount_summary", "final_amount", "paid_amount"}.issubset(line_types)
    assert any(item["used_for_discount"] for item in diagnostics)
    assert any(item["used_for_total"] for item in diagnostics)
    assert all("line" not in item for item in diagnostics)
    assert "레디팩" not in str(diagnostics)
    assert "10,800" not in str(diagnostics)


def test_columnar_summary_amount_labels_are_paired_with_following_amount_column():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.10",
            "제품명",
            "레디팩(아몬드봉봉) 10,800",
            "KT 멤버십 VVIP 초이스 -10,800",
            "총매출액",
            "할인금액",
            "합계금액",
            "받은금액",
            "10,800",
            "10,800",
            "0",
            "0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))
    diagnostics = build_receipt_amount_diagnostics(raw_text)

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0
    assert receipt.amount_source == "paid_amount"
    assert "discount_detected" in receipt.amount_warnings
    assert "zero_payment_after_discount" in receipt.amount_warnings
    assert any(item["source"] == "text_column_pair" for item in diagnostics)
    assert "레디팩" not in str(diagnostics)
    assert "10,800" not in str(diagnostics)


def test_quantity_one_is_not_used_as_discount_amount_candidate():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.10",
            "제품명 수량 금액",
            "레디팩 1 10,800",
            "KT 멤버십 VVIP 초이스 -10,800",
            "총매출액 10,800",
            "할인금액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.discount_amount != 1
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0


def test_zero_amount_line_item_quantities_are_not_used_as_discount_amounts():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.10",
            "제품명 수량 금액",
            ">>드라이아이스(분) 10 0",
            ">>스푼 3 0",
            "총매출액 10,800",
            "할인금액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )
    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.discount_amount not in {3, 10}
    assert receipt.total_amount == 0


def test_card_approval_number_is_not_used_as_discount_amount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.10",
            "총매출액 28,750",
            "할인금액 2,800",
            "합계금액 25,950",
            "받은금액 25,950",
            "신용카드",
            "카드/승인번호 490613** 00240338",
            "결제금액 25,950",
            "KT 멤버십",
            "카드/승인번호 291710** 304220779882",
            "할인금액 2,800",
        ]
    )
    diagnostics = build_receipt_amount_diagnostics(raw_text)

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 28750
    assert receipt.discount_amount == 2800
    assert receipt.final_amount == 25950
    assert receipt.paid_amount == 25950
    assert receipt.total_amount == 25950
    assert receipt.discount_amount != 304220779882
    assert any(item["ignored_reason"] in {"approval_number_candidate", "long_number_candidate"} for item in diagnostics)


def test_suspicious_raw_json_discount_amount_is_recalculated_from_gross_and_final():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.10",
            "총매출액 28,750",
            "합계금액 25,950",
            "받은금액 25,950",
        ]
    )
    raw_json = {"discount_amount": "304220779882"}

    receipt = ReceiptParser().parse(make_ocr_result(raw_text, raw_json=raw_json))

    assert receipt.gross_amount == 28750
    assert receipt.discount_amount == 2800
    assert receipt.final_amount == 25950
    assert receipt.paid_amount == 25950
    assert receipt.total_amount == 25950
    assert "discount_identifier_candidate_ignored" in receipt.amount_warnings
    assert "discount_recalculated_from_gross_and_final" in receipt.amount_warnings


def test_payment_reference_line_does_not_pull_footer_number_as_paid_amount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.04.25",
            "합계 105,720",
            "결제대상금액 105,720",
            "※ 해당카드 결제금액 기준",
            "캐셔:063453 김00",
            "1520",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.final_amount == 105720
    assert receipt.paid_amount is None
    assert receipt.total_amount == 105720
    assert receipt.amount_source == "payment_target_amount"


def test_low_confidence_paid_amount_is_ignored_when_final_amount_is_available():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.04.25",
            "결제대상금액 105,720",
            "결제금액 1,520",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.final_amount == 105720
    assert receipt.paid_amount is None
    assert receipt.total_amount == 105720
    assert receipt.amount_source == "payment_target_amount"
    assert "paid_amount_low_confidence_ignored" in receipt.amount_warnings


def test_card_payment_line_wins_over_later_footer_number():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.04.25",
            "결제대상금액 105,720",
            "카드결제(IC) 일시불 / 105,720",
            "※ 해당카드 결제금액 기준",
            "캐셔:063453 김00",
            "1520",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.final_amount == 105720
    assert receipt.paid_amount == 105720
    assert receipt.total_amount == 105720
    assert receipt.amount_source == "paid_amount"


def test_single_digit_discount_candidate_is_ignored_as_quantity():
    receipt = ReceiptParser().parse(make_ocr_result("상호명: 테스트상점\n거래일자: 2026.05.10", raw_json={"discount_amount": 1}))

    assert receipt.discount_amount is None
    assert "discount_quantity_candidate_ignored" in receipt.amount_warnings


def test_discount_table_header_does_not_pull_next_product_amount_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.10",
            "제품명 수량 금액",
            "(할인내역)",
            "금액 (할인금액)",
            "컵)트리플주니어 1 7,200",
            ">>깨물먹는 1 0",
            ">>크런티 1 0",
            ">>스푼 1 0",
        ]
    )
    diagnostics = build_receipt_amount_diagnostics(raw_text)

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount is None
    assert receipt.total_amount is None
    assert receipt.discount_amount != 7200
    assert receipt.discount_amount != 1
    assert any(item["line_type"] == "discount_table_header" for item in diagnostics)


def test_zero_payment_ocr_letter_o_is_used_for_final_and_paid_amounts():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "제품명",
            "(할인내역) 수량 금액",
            "(할인금액)",
            "레디팩(아몬드봉봉) 10,800",
            "KT 멤버십 VVIP 초이스 -10,800",
            "총매출액 10,800",
            "합계 금액 O",
            "받은 금액 O",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0


def test_paid_amount_misread_label_still_keeps_zero_total():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "할인금액 10,800",
            "합계금액 0",
            "반은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0


def test_discount_is_inferred_from_gross_and_zero_payment_when_explicit_discount_is_missing():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0
    assert "discount_inferred_from_zero_payment" in receipt.amount_warnings
    assert "zero_payment_after_discount" in receipt.amount_warnings
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value


def test_discount_section_item_level_discount_is_used_without_summary_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "제품명",
            "(할인내역) 수량 금액",
            "(할인금액)",
            "레디팩(아몬드봉봉) 10,800",
            "KT 멤버십 VVIP 초이스 -10,800",
            "총매출액 10,800",
            "합계금액 0",
            "받은금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0
    assert "item_level_discount_detected" in receipt.amount_warnings


def test_discount_candidate_without_final_or_paid_amount_does_not_use_gross_as_total():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액 10,800",
            "KT 멤버십 VVIP 초이스 -10,800",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.total_amount != 10800
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "gross_total_not_used_due_to_discount" in receipt.amount_warnings


def test_zero_amount_line_item_is_not_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            ">>드라이아이스(분) 10 0",
            "총매출액 10,800",
            "합계금액 10,800",
            "받은금액 10,800",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount is None
    assert receipt.total_amount == 10800


def test_general_negative_line_without_discount_hint_is_not_treated_as_discount():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "상품A -10,800",
            "총매출액 10,800",
            "합계금액 0",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.discount_amount is None


def test_amount_diagnostics_include_total_related_line_types_without_original_text():
    diagnostics = build_receipt_amount_diagnostics("할인금액 10,800\n합계금액 0\n받은금액 0")
    line_types = {item["line_type"] for item in diagnostics}

    assert {"discount_summary", "final_amount", "paid_amount"}.issubset(line_types)
    assert all("line" not in item for item in diagnostics)
    assert "할인금액" not in str(diagnostics)
    assert "10,800" not in str(diagnostics)


def test_missing_explicit_vat_uses_reference_estimate_without_filling_vat_amount():
    raw_text = "\n".join(
        [
            "상호명: 테스트카페",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "합계: 5,100원",
            "결제수단: 신용카드",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.supply_amount is None
    assert receipt.vat_amount is None
    assert receipt.estimated_supply_amount == 4636
    assert receipt.estimated_vat_amount == 464
    assert receipt.estimated_supply_amount + receipt.estimated_vat_amount == receipt.total_amount
    assert receipt.vat_source == "estimated_reference"
    assert receipt.vat_review_required is True
    assert "vat_not_explicit" in receipt.vat_warnings
    assert "vat_estimated_reference_only" in receipt.vat_warnings
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value


def test_zero_total_skips_reference_vat_estimate_without_error():
    raw_text = "\n".join(
        [
            "상호명: 테스트카페",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "합계금액: 0원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.total_amount == 0
    assert receipt.supply_amount is None
    assert receipt.vat_amount is None
    assert receipt.estimated_supply_amount is None
    assert receipt.estimated_vat_amount is None
    assert receipt.vat_source == "zero_amount"
    assert receipt.vat_review_required is False
    assert "vat_estimate_skipped_zero_amount" in receipt.vat_warnings


def test_sensitive_wifi_text_is_detected_without_breaking_discount_amounts():
    raw_text = "\n".join(
        [
            "상호명: 테스트상점",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총매출액: 10,800원",
            "할인금액: -10,800원",
            "합계금액: 0원",
            "받은금액: 0원",
            "WIFI PW: sample-password-1234",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))
    data = receipt.to_dict()

    assert receipt.discount_amount == 10800
    assert receipt.total_amount == 0
    assert receipt.sensitive_text_detected is True
    assert "wifi_password" in receipt.sensitive_text_categories
    assert "sample-password-1234" not in str(data)


def test_sensitive_wifi_text_is_detected_without_breaking_estimated_vat():
    raw_text = "\n".join(
        [
            "상호명: 테스트카페",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "총금액: 5,100원",
            "WIFI PW: sample-password-1234",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))
    data = receipt.to_dict()

    assert receipt.estimated_supply_amount == 4636
    assert receipt.estimated_vat_amount == 464
    assert receipt.vat_source == "estimated_reference"
    assert receipt.sensitive_text_detected is True
    assert "wifi_password" in receipt.sensitive_text_categories
    assert "sample-password-1234" not in str(data)


def test_sensitive_text_line_is_not_selected_as_merchant_name():
    raw_text = "\n".join(
        [
            "WIFI PW: sample-password-1234",
            "거래일자: 2026.05.07",
            "사업자번호: 123-45-67890",
            "합계: 12,000원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.merchant_name is None
    assert receipt.sensitive_text_detected is True
    assert "wifi_password" in receipt.sensitive_text_categories


def test_missing_merchant_name_needs_review_with_warning():
    raw_text = "\n".join(["거래일자: 2026.05.07", "합계: 12,000원", "사업자번호: 123-45-67890"])

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "상호누락" in receipt.parser_warnings


def test_missing_transaction_date_needs_review_with_warning():
    raw_text = "\n".join(["테스트카페", "합계: 12,000원", "사업자번호: 123-45-67890"])

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "날짜누락" in receipt.parser_warnings


def test_complete_required_fields_stay_pending_and_unmatched():
    receipt = ReceiptParser().parse(make_ocr_result())

    assert receipt.review_status == ReviewStatus.PENDING.value
    assert receipt.card_match_status == CardMatchStatus.UNMATCHED.value
    assert receipt.expense_category is None
    assert receipt.evidence_type == EvidenceType.RECEIPT_IMAGE.value


def test_failed_ocr_result_becomes_needs_review():
    receipt = ReceiptParser().parse(make_ocr_result(status=OCRStatus.FAILED.value))

    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert any("OCR 상태 확인 필요" in warning for warning in receipt.parser_warnings)


def test_unclear_business_number_adds_parser_warning():
    raw_text = "\n".join(["테스트카페", "사업자번호: 123-45-678", "거래일자: 2026.05.07", "합계: 12,000원"])

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.business_number is None
    assert "사업자번호 형식 확인 필요" in receipt.parser_warnings


def test_receipt_record_does_not_store_raw_ocr_text():
    receipt = ReceiptParser().parse(make_ocr_result())
    data = receipt.to_dict()

    assert "raw_text" not in data
    assert "raw_json" not in data
    assert receipt.ocr_raw_text == ""


def test_overlay_title_is_not_selected_as_merchant_name():
    raw_text = "\n".join(
        [
            "슈퍼 마리오",
            "거래일자: 2026.05.07",
            "사업자번호: 123-45-67890",
            "합계: 12,000원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.merchant_name is None
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "merchant_name_missing_or_low_confidence" in receipt.parser_warnings


def test_overlay_title_with_punctuation_is_not_selected_as_merchant_name():
    raw_text = "\n".join(
        [
            "슈퍼 마리오!",
            "거래일자: 2026.04.25",
            "합계: 105,720원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text, raw_json={"MerchantName": "슈퍼 마리오!"}))

    assert receipt.merchant_name is None
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value
    assert "merchant_name_missing_or_low_confidence" in receipt.parser_warnings


def test_status_bar_text_is_skipped_and_receipt_merchant_candidate_is_used():
    raw_text = "\n".join(
        [
            "KT 9:37",
            "테스트카페",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "합계: 12,000원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.merchant_name == "테스트카페"


def test_business_number_dictionary_maps_merchant_name():
    raw_text = "\n".join(
        [
            "슈퍼 마리오",
            "사업자번호: 206-86-50913",
            "거래일자: 2026.05.07",
            "합계: 12,000원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.business_number == "206-86-50913"
    assert receipt.merchant_name == "이마트 영등포점"


def test_business_number_mapping_wins_when_receipt_name_is_present():
    raw_text = "\n".join(
        [
            "이마트 영등포점",
            "사업자번호: 206-86-50913",
            "거래일자: 2026.05.07",
            "합계: 12,000원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.merchant_name == "이마트 영등포점"


def test_receipt_business_keyword_merchant_is_selected_without_business_number_mapping():
    raw_text = "\n".join(
        [
            "이마트 영등포점 T: (02)3468-1234",
            "서울특별시 영등포구 영중로 15",
            "거래일자: 2026.02.16",
            "합계: 35,700원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.merchant_name == "이마트 영등포점"


def test_product_line_is_not_selected_as_merchant_name():
    raw_text = "\n".join(
        [
            "미미 인어공주미미",
            "사업자번호: 123-45-67890",
            "거래일자: 2026.05.07",
            "합계: 12,000원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.merchant_name is None
    assert "merchant_name_missing_or_low_confidence" in receipt.parser_warnings


def test_ai_robot_product_line_is_not_selected_as_merchant_name():
    raw_text = "\n".join(
        [
            "AI 로봇 강아지 마일",
            "거래일자: 2026.05.07",
            "사업자번호: 123-45-67890",
            "합계: 12,000원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text))

    assert receipt.merchant_name is None


def test_raw_json_merchant_name_has_priority_over_raw_text():
    raw_text = "\n".join(
        [
            "슈퍼 마리오",
            "테스트카페",
            "거래일자: 2026.05.07",
            "사업자번호: 123-45-67890",
            "합계: 12,000원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text, raw_json={"MerchantName": "원본상호"}))

    assert receipt.merchant_name == "원본상호"


def test_raw_json_overlay_merchant_name_is_ignored():
    raw_text = "\n".join(
        [
            "거래일자: 2026.05.07",
            "사업자번호: 123-45-67890",
            "합계: 12,000원",
        ]
    )

    receipt = ReceiptParser().parse(make_ocr_result(raw_text, raw_json={"MerchantName": "슈퍼 마리오"}))

    assert receipt.merchant_name is None
    assert receipt.review_status == ReviewStatus.NEEDS_REVIEW.value


def test_app_overlay_titles_are_not_valid_merchant_candidates():
    assert is_valid_merchant_candidate("카카오톡") is False
    assert is_valid_merchant_candidate("갤러리") is False
    assert is_valid_merchant_candidate("Samsung") is False
    assert is_valid_merchant_candidate("iPhone") is False

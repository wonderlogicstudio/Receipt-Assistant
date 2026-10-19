from dataclasses import replace

import pytest

from app.core.ocr_models import OCRResult
from app.parser.receipt_parser import ReceiptParser
from app.storage.file_store import StoredFileMetadata
from app.ui.streamlit_app import process_receipt_files_with_mock_ocr
from app.parser.standard_ocr_context import StandardOCRParserContext


@pytest.mark.parametrize("suffix", ["", *[f"_{i:02}" for i in range(1, 8)]])
def test_upload_name_cannot_override_observed_receipt_fields(suffix):
    filename = f"KakaoTalk_20260608_232201696{suffix}.jpg"
    metadata = StoredFileMetadata(
        original_file_name=filename, stored_file_name="opaque.jpg",
        stored_relative_path="data/uploads/test/opaque.jpg", file_extension=".jpg",
        file_size_bytes=1, session_id="test",
    )

    class ObservedProvider:
        def extract(self, source):
            return OCRResult.completed(
                source_file_id="test", source_file_name=filename,
                stored_relative_path=None, provider="mock", confidence=0.99,
                raw_text="상호명: 독립검증문구점\n사업자번호: 999-88-12345\n거래일자: 2026-10-01\n합계: 1,234원",
                raw_json={},
            )

    record = process_receipt_files_with_mock_ocr([metadata], ocr_provider=ObservedProvider()).receipt_records[0]
    assert record.merchant_name == "독립검증문구점"
    assert record.business_number == "999-88-12345"
    assert record.transaction_date.isoformat() == "2026-10-01"
    assert record.total_amount == 1234
    assert record.supply_amount is None
    assert record.vat_amount is None


@pytest.mark.parametrize("name", ["크린에이드 새빛점", "현대오일뱅크 바다점", "Independent Shop", "레고스토어", "슈퍼 마리오"])
def test_business_number_or_brand_cannot_replace_observed_merchant(name):
    result = OCRResult.completed(
        source_file_id="test", source_file_name="arbitrary.jpg", stored_relative_path=None,
        provider="mock", confidence=0.99,
        raw_text=f"상호명: {name}\n사업자번호: 206-86-50913\n합계: 1,234원", raw_json={},
    )
    record = ReceiptParser().parse(result)
    renamed = ReceiptParser().parse(replace(result, source_file_name="another.jpg"))
    assert record.merchant_name == name
    assert renamed.merchant_name == name


def test_business_number_without_merchant_does_not_invent_a_name():
    result = OCRResult.completed(
        source_file_id="test", source_file_name="arbitrary.jpg", stored_relative_path=None,
        provider="mock", confidence=0.99,
        raw_text="사업자번호: 206-86-50913\n합계: 1,234원", raw_json={},
    )
    assert ReceiptParser().parse(result).merchant_name is None


def test_tax_zero_on_one_line_does_not_absorb_next_amount():
    record = ReceiptParser().parse_text("상호명: 새빛문구\n부가세\n0\n61,000\n합계: 61,000")
    assert record.vat_amount == 0


def test_notice_is_not_payment_evidence_or_merchant():
    record = ReceiptParser().parse_text("상호명: 새빛문구\n신용카드 결제시 세금계산서 발행불가\n합계: 12,345")
    assert record.payment_method is None


@pytest.mark.parametrize("lines", [
    ["발행불가", "세금계산서", "결제시", "제9항", "제42조", "시행령", "신용카드", "*"],
    ["신용카드", "결제시 세금계산서 발행불가"],
])
def test_split_statutory_notice_does_not_supply_a_payment_method(lines):
    text = "\n".join(["상호명: 새빛문구", "합계: 12,345", *lines])
    assert ReceiptParser().parse_text(text).payment_method is None
    context = StandardOCRParserContext(provider="independent", status="completed", safe_text_lines=text.splitlines())
    assert ReceiptParser().parse_standard_context(context).payment_method is None


def test_separate_explicit_payment_is_preserved_next_to_card_notice():
    text = "현금 12,345\n신용카드\n시행령 제42조"
    assert ReceiptParser().parse_text(text).payment_method == "현금"
    text = "신용카드 12,345\n시행령 제42조"
    assert ReceiptParser().parse_text(text).payment_method == "신용카드"


def test_standalone_payment_and_amount_are_not_discarded_by_distant_notice():
    text = "신용카드\n12,345\n시행령 제42조"
    assert ReceiptParser().parse_text(text).payment_method == "신용카드"


def test_redaction_placeholder_cannot_be_a_merchant():
    record = ReceiptParser().parse_text("상호명: [REDACTED]\n합계: 12,345")
    assert record.merchant_name is None


def test_standard_context_does_not_assign_unpositioned_next_block_to_tax():
    context = StandardOCRParserContext(provider="independent", status="completed",
        safe_text_lines=["부가세", "61,234", "온라인예매"])
    record = ReceiptParser().parse_standard_context(context)
    assert record.vat_amount is None
    assert record.vat_review_required


def test_standard_context_preserves_inline_tax_and_typed_explicit_zero():
    inline = StandardOCRParserContext(provider="independent", status="completed",
        safe_text_lines=["공급가액: 12,000", "부가세: 123"])
    record = ReceiptParser().parse_standard_context(inline)
    assert record.supply_amount == 12000
    assert record.vat_amount == 123
    typed_zero = inline.model_copy(update={"amount_candidate_map": {"vat_amount": ["0"]}})
    assert ReceiptParser().parse_standard_context(typed_zero).vat_amount == 0


def test_legacy_text_tax_wrapper_remains_compatible():
    assert ReceiptParser().parse_text("부가세\n123").vat_amount == 123

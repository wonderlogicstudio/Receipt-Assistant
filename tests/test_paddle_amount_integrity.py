from app.ocr.paddle_provider import build_paddle_candidate_hints_from_safe_lines
import pytest


def candidates_for(*texts):
    return {
        item["candidate_type"]: item["value"]
        for item in build_paddle_candidate_hints_from_safe_lines([
            {"block_id": str(i), "text": text, "confidence": 0.99}
            for i, text in enumerate(texts)
        ])
    }


def test_tax_components_cannot_generate_unprinted_total():
    values = candidates_for("공급가액 10,000", "부가세 1,000")
    assert values.get("total_amount") is None
    assert values.get("final_amount") is None


def test_tax_balance_cannot_append_unobserved_zero_to_total():
    values = candidates_for("비씨카드", "272원", "657", "728원", "65", "72300원")
    assert values.get("total_amount") != "723000"
    assert values.get("final_amount") != "723000"


def test_generic_sales_fragments_cannot_become_unlabeled_tax_components():
    values = candidates_for("매출", "10", "000", "1000")
    assert values.get("supply_amount") is None
    assert values.get("vat_amount") is None
    assert values.get("total_amount") != "11000"


def test_card_instructions_and_tax_law_numbers_are_not_payment_evidence():
    values = candidates_for("교환/환불은 구매점포에서", "(결제카드 필요)", "현금 12,345",
                            "신용카드 결제시 세금계산서 발행불가", "부가가치세법 시행령 제57조")
    assert values["payment_method"] == "현금"
    assert values.get("paid_amount") != "57"


def test_ocr_letter_zero_is_only_accepted_with_amount_label():
    values = candidates_for("공급가액 O", "부가세 O", "합계 12,345")
    assert values["supply_amount"] == "0"
    assert values["vat_amount"] == "0"


@pytest.mark.parametrize("vat", [1, 5, 509])
def test_small_explicit_tax_on_following_line_is_preserved(vat):
    values = candidates_for("합계 5,600", "부가세", str(vat))
    assert values["vat_amount"] == str(vat)


def test_card_marker_and_won_suffix_do_not_identify_a_total():
    for text in ("65,432원", "부가세 65,432원"):
        values = candidates_for("카드", text)
        assert values.get("total_amount") is None
        assert values.get("paid_amount") is None

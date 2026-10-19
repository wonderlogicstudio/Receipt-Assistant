import pytest
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import StandardOCRParserContext


@pytest.mark.parametrize('name', ['주식회사별빛공방527', 'AB42봄빛상회'])
def test_observed_alphanumeric_merchant_is_not_a_money_line(name):
    context = StandardOCRParserContext(provider='paddleocr',status='completed',
        candidate_map={'merchant_name':[name]},non_amount_candidate_map={'merchant_name':[name]})
    assert ReceiptParser().parse_standard_context(context).merchant_name == name


def test_conflicting_typed_totals_do_not_pick_first_or_legacy_text():
    context = StandardOCRParserContext(provider='paddleocr',status='completed',
        safe_text_lines=['합계금액 7,800','합계금액 8,900'],
        candidate_map={'total_amount':['7800','8900'],'final_amount':['7800','8900']},
        amount_candidate_map={'total_amount':['7800','8900'],'final_amount':['7800','8900']})
    record = ReceiptParser().parse_standard_context(context)
    assert record.total_amount is None
    assert record.final_amount is None
    assert 'candidate_conflict:total_amount' in record.parser_warnings


def test_repeated_agreeing_candidates_preserve_zero():
    context = StandardOCRParserContext(provider='paddleocr',status='completed',
        candidate_map={'total_amount':['0','0']},amount_candidate_map={'total_amount':['0','0']})
    assert ReceiptParser().parse_standard_context(context).total_amount == 0


def test_smaller_individual_card_approval_does_not_replace_explicit_receipt_total():
    context = StandardOCRParserContext(provider='paddleocr',status='completed',
        candidate_map={'total_amount':['82300'],'final_amount':['82300'],'paid_amount':['12300']},
        amount_candidate_map={'total_amount':['82300'],'final_amount':['82300'],'paid_amount':['12300']})
    record = ReceiptParser().parse_standard_context(context)
    assert record.total_amount == 82300
    assert 'final_paid_amount_mismatch' in record.amount_warnings


def test_larger_paid_candidate_does_not_override_an_explicit_total():
    context = StandardOCRParserContext(provider='paddleocr',status='completed',
        candidate_map={'total_amount':['12300'],'final_amount':['12300'],'paid_amount':['82300']},
        amount_candidate_map={'total_amount':['12300'],'final_amount':['12300'],'paid_amount':['82300']})
    record = ReceiptParser().parse_standard_context(context)
    assert record.total_amount == 12300
    assert record.final_amount == 12300
    assert 'final_paid_amount_mismatch' in record.amount_warnings

import pytest

from app.core.receipt_evidence import is_receipt_instruction
from app.ocr.paddle_provider import build_paddle_candidate_hints_from_safe_lines
from app.parser.receipt_parser import ReceiptParser


@pytest.mark.parametrize('text', [
    '구매 점포에서 14일(신선 3일) 이내 가능',
    '구입매장에서7일이내교환가능',
    '교환 · 환불은 구매 후 7일 이내',
    '단, 정상(미개봉) 상품에 한함',
])
def test_return_policy_fragments_are_instructions_even_without_the_previous_line(text):
    assert is_receipt_instruction(text)
    assert not ReceiptParser().parse_text('상호: '+text+'\n합계 17,530').merchant_name
    candidates = build_paddle_candidate_hints_from_safe_lines([
        dict(block_id='policy', text=text, confidence=.99),
        dict(block_id='amount', text='합계 17,530', confidence=.99)])
    assert not any(c['candidate_type']=='merchant_name' for c in candidates)


@pytest.mark.parametrize('name', ['교환상점', '신선24마켓', 'Fresh Day', '구매상점14'])
def test_instruction_filter_does_not_reject_similarly_named_merchants(name):
    assert not is_receipt_instruction(name)
    assert ReceiptParser().parse_text('상호: '+name+'\n합계 17,530').merchant_name == name

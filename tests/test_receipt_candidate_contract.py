from datetime import datetime, timezone

import pytest

from app.core.standard_ocr import StandardOCRKeyValueCandidate, StandardOCRResult, StandardOCRTextBlock
from app.ocr.paddle_provider import build_paddle_candidate_hints_from_safe_lines
from app.parser.receipt_parser import ReceiptParser
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr


def parse_candidates(values):
    result = StandardOCRResult(id='synthetic', provider='paddleocr', status='completed',
        created_at=datetime.now(timezone.utc), key_value_candidates=[
            StandardOCRKeyValueCandidate(key=key, candidate_type=key, value=value)
            for key, candidates in values.items() for value in candidates])
    return ReceiptParser().parse_standard_context(build_parser_context_from_standard_ocr(result))


def parse_lines(*texts):
    lines = [dict(block_id=str(i), text=text, confidence=.99) for i, text in enumerate(texts)]
    result = StandardOCRResult(id='synthetic', provider='paddleocr', status='completed',
        created_at=datetime.now(timezone.utc),
        text_blocks=[StandardOCRTextBlock(page_index=0, block_id=str(i), text=text, line_order=i)
                     for i, text in enumerate(texts)],
        key_value_candidates=[StandardOCRKeyValueCandidate(**c) for c in build_paddle_candidate_hints_from_safe_lines(lines)])
    return ReceiptParser().parse_standard_context(build_parser_context_from_standard_ocr(result))


@pytest.mark.parametrize('name', ['하늘 24', 'Hotel Lumen', 'Postera', '새봄할인마트', '새봄24공방'])
def test_explicit_merchant_is_not_rejected_by_a_number_or_word_fragment(name):
    assert parse_lines('상호: '+name, '합계 17,500').merchant_name == name


@pytest.mark.parametrize('label', ['상호', '상호명', '매장명', '점포명', '업체명', '가맹점명'])
def test_merchant_label_variants_use_their_own_value(label):
    assert parse_lines(f'[{label}] 새봄공방', '주소: 강원 새빛시 봄길 19', '합계 17,500').merchant_name == '새봄공방'


@pytest.mark.parametrize('key', ['vat_amount', 'supply_amount', 'total_amount', 'discount_amount'])
@pytest.mark.parametrize('values', [['unclear', '275'], ['275', 'unclear']])
def test_invalid_candidates_do_not_hide_later_valid_money(key, values):
    assert getattr(parse_candidates({key: values}), key) == 275


@pytest.mark.parametrize('explicit_final', [False, True])
def test_explicit_total_cannot_be_overwritten_by_larger_paid_amount(explicit_final):
    values = {'total_amount': ['17500'], 'paid_amount': ['83900']}
    if explicit_final:
        values['final_amount'] = ['17500']
    record = parse_candidates(values)
    assert record.total_amount == 17500
    assert record.final_amount == 17500


def test_received_cash_and_change_are_not_the_total():
    assert parse_lines('합계 7,000', '받은금액 10,000', '거스름돈 3,000').total_amount == 7000


def test_discount_gross_and_card_amount_remain_separate():
    record = parse_lines('상품금액 10,000', '할인금액 2,000', '카드결제 8,000')
    assert (record.gross_amount, record.discount_amount, record.total_amount) == (10000, 2000, 8000)


def test_points_are_not_automatically_a_discount():
    record = parse_lines('상품금액 10,000', '포인트사용 5,000', '카드결제 5,000')
    assert record.discount_amount is None
    assert record.total_amount == 5000


def test_point_balance_and_accrual_are_not_a_payment():
    record = parse_lines('포인트사용 0', '적립예정 500', '잔여포인트 20,000')
    assert record.discount_amount is None
    assert record.total_amount is None


@pytest.mark.parametrize('payment_lines', [('카드결제 6,000', '현금결제 4,000'),
                                          ('카드 A 승인금액 6,000', '카드 B 승인금액 4,000')])
def test_split_payments_do_not_overwrite_the_explicit_total(payment_lines):
    assert parse_lines('합계 10,000', *payment_lines).total_amount == 10000


def test_equal_total_and_approval_are_not_summed():
    assert parse_lines('합계 17,500', '승인금액 17,500').total_amount == 17500


def test_repeated_payment_labels_and_approval_identifier_keep_one_observed_total():
    record = parse_lines('결제금액 17,530', '신용카드 17,530', '카드결제 17,530', '승인번호 17530024')
    assert record.total_amount == 17530
    assert record.final_amount == 17530


@pytest.mark.parametrize('label', ['최종결제금액', '실 결제 금액', '총결제금액'])
def test_explicit_zero_is_preserved(label):
    assert parse_lines(label+' 0').total_amount == 0


def test_conflicting_totals_remain_unresolved():
    record = parse_lines('합계금액 17,500', '합계금액 28,900')
    assert record.total_amount is None


def test_amounts_and_account_identifiers_in_item_area_do_not_create_total():
    record = parse_lines('상품명 단가 수량 금액', '새봄컵 2,500 3 7,500', '승인번호 12345678')
    assert record.total_amount is None

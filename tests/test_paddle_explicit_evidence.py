from app.ocr.paddle_provider import build_paddle_candidate_hints_from_safe_lines


def values(*texts):
    return {c['candidate_type']: c['value'] for c in build_paddle_candidate_hints_from_safe_lines(
        [{'block_id': str(i), 'text': text, 'confidence': .99} for i, text in enumerate(texts)])}


def test_bracketed_merchant_label_does_not_borrow_address():
    found = values('[매장명] 새빛정원', '[주소] 강원특별자치도 바다시 꽃길 17', '합계금액 7,800')
    assert found['merchant_name'] == '새빛정원'


def test_card_terminal_merchant_identifier_does_not_conflict_with_store_name():
    for identifier in ['가맹점# 퓨 7654321','가맹점 퓨 7654321']:
        found = values('상호: 새빛정원', identifier)
        assert found['merchant_name'] == '새빛정원'


def test_explicit_total_precedes_product_and_individual_approvals():
    found = values('상품명 단가 수량 금액', '정식 37,000 1 37,000', '합계금액 82,300',
                   '공급가액 74,818', '부가세 7,482', '신용승인정보 [1]', '승인금액 12,300',
                   '신용승인정보 [2]', '승인금액 70,000')
    assert found['total_amount'] == '82300'
    assert found['vat_amount'] == '7482'


def test_explicit_total_with_ocr_separator_cannot_take_tax_zero():
    found = values('합계금액 7 ;800', '부가세 면세물품가액 7,800', '부가세 과세물품가액 0', '부가세 0')
    assert found['total_amount'] == '7800'
    assert found['supply_amount'] == '0'
    assert found['vat_amount'] == '0'


def test_conflicting_equally_explicit_totals_remain_candidates_for_review():
    candidates = build_paddle_candidate_hints_from_safe_lines([
        {'block_id': 'a', 'text': '합계금액 7,800', 'confidence': .99},
        {'block_id': 'b', 'text': '합계금액 8,900', 'confidence': .99}])
    totals = [c for c in candidates if c['candidate_type'] == 'total_amount']
    assert {c['value'] for c in totals} == {'7800', '8900'}
    assert {s for c in totals for s in c['source_block_ids']} == {'a','b'}


def test_item_header_amount_column_is_not_a_total():
    assert 'total_amount' not in values('상품명 단가 수량 금액', '식사 37,000 1 37,000')


def test_explicit_small_total_and_zero_are_valid():
    assert values('합계금액 750')['total_amount'] == '750'
    assert values('합계금액 0')['total_amount'] == '0'


def test_low_confidence_numeric_candidate_is_not_promoted_as_explicit_tax():
    found = build_paddle_candidate_hints_from_safe_lines([
        {'block_id':'low','text':'공급가액 73','confidence':.5}])
    assert not any(c['candidate_type']=='supply_amount' for c in found)


def test_taxable_sales_label_means_supply_and_exempt_sales_does_not():
    found = values('과세 매출 6,123', '부가세 612', '면세 매출 4,000', '합계 10,735')
    assert found['supply_amount'] == '6123'


def test_long_receipt_keeps_explicit_summary_after_first_120_blocks():
    from app.ocr.paddle_provider import _lines_from_paddle_output
    raw = [{'text':'상품', 'confidence':.99} for _ in range(140)]
    raw.append({'text':'합계금액 7,800', 'confidence':.99})
    assert len(_lines_from_paddle_output(raw)) == 141
    found = build_paddle_candidate_hints_from_safe_lines(_lines_from_paddle_output(raw))
    assert next(c['value'] for c in found if c['candidate_type']=='total_amount') == '7800'


def test_positioned_missing_tax_cannot_borrow_exempt_sales_or_following_payment():
    def line(text,y):
        return {'block_id':str(y),'text':text,'confidence':.99,'bbox':[[0,y],[150,y],[150,y+20],[0,y+20]]}
    found = build_paddle_candidate_hints_from_safe_lines([
        line('부가세 면세물품가액 7,800',0),line('부가세 과세물품가액',40),
        line('부가세',80),line('받은금액 7,800',120)])
    assert not any(c['candidate_type'] in {'supply_amount','vat_amount'} for c in found)

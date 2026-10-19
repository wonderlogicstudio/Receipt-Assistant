from app.ocr.paddle_provider import build_paddle_candidate_hints_from_safe_lines


def line(text, x, y, width=120, height=24):
    return dict(block_id=f'{x}-{y}', text=text, confidence=.99,
        bbox=[[x,y],[x+width,y],[x+width,y+height],[x,y+height]])


def values(lines):
    return {c['candidate_type']:c['value'] for c in build_paddle_candidate_hints_from_safe_lines(lines)}


def test_currency_symbols_and_bracketed_tax_labels_keep_explicit_values():
    found=values([line('[공급가액]',0,0),line('₩34,321',240,0),
                  line('부가세(VAT)',0,40),line('₩3,432',240,40),
                  line('합계금액',0,80),line('₩37,753',240,80)])
    assert found['supply_amount']=='34321'
    assert found['vat_amount']=='3432'
    assert found['total_amount']=='37753'


def test_tall_numeric_currency_column_cannot_become_a_total():
    found=values([line('공급가액',0,0),line('34,321',230,0),
                  line('부가세',0,45),line('3,432',230,45),
                  line('합계',0,90),line('37,753',230,90),line('888',390,0,20,140)])
    assert found['total_amount']=='37753'
    assert found['vat_amount']=='3432'


def test_second_header_field_does_not_extend_a_labeled_merchant():
    found=values([line('가맹점명: 새봄공방 TeI:02-1234-5678',0,0,500)])
    assert found['merchant_name']=='새봄공방'


def test_sales_label_is_not_reclassified_as_supply_from_a_vat_neighbor():
    found=values([line('[판매금액]',0,0),line('34,321',240,0),
                  line('[부가세]',0,40),line('3,432',240,40),
                  line('[승인금액]',0,80),line('37,753',240,80)])
    assert 'supply_amount' not in found
    assert 'supply_amount' not in values([line('판매금액 37,753',0,0,340)])


def test_explicit_cash_received_is_not_promoted_as_total():
    found=values([line('받은금액 50,000',0,0,340),line('거스름돈 12,247',0,40,340)])
    assert 'total_amount' not in found


def test_horizontal_tax_header_uses_columns_without_arithmetic():
    found=values([line('과세물품가액',0,0),line('부가세(VAT)',180,0),line('합계금액',360,0),
                  line('₩34,321',0,40),line('₩3,432',180,40),line('₩37,753',360,40)])
    assert found['supply_amount']=='34321'
    assert found['vat_amount']=='3432'
    assert found['total_amount']=='37753'


def test_short_province_and_street_number_do_not_outrank_a_business_name():
    found = values([line('경기 새빛시 푸른동 321 새빛아울렛 바다점', 0, 0, 650),
                    line('주식회사 새봄상사 바다점', 0, 40, 450),
                    line('사업자번호: 123-45-67891', 0, 80, 450)])
    assert found['merchant_name'] == '주식회사 새봄상사 바다점'


def test_address_filter_keeps_a_numbered_branch_name():
    from app.ocr.paddle_provider import _looks_like_address_fragment

    assert _looks_like_address_fragment('경기새빛시푸른동321새빛아울렛바다점')
    assert not _looks_like_address_fragment('주식회사새봄338바다점')


def test_horizontal_tax_column_keeps_all_observed_digit_groups():
    found = values([line('과세물품가액', 0, 0), line('부가세(VAT)', 180, 0), line('합계금액', 360, 0),
                    line('#34', 10, 40, 45), line('321', 60, 47, 50),
                    line('#3,432', 180, 40), line('#37,753', 360, 40)])
    assert found['supply_amount'] == '34321'


def test_transaction_amount_is_not_reclassified_as_supply_from_a_vat_neighbor():
    found = values([line('거래금액 31,234', 0, 0, 360), line('부가세 3,123', 0, 40, 360)])
    assert 'supply_amount' not in found


def test_tax_column_value_can_overlap_the_header_bottom_by_one_pixel():
    found = values([line('과세물품가액', 0, 0), line('부가세(VAT)', 180, 0),
                    line('#34,321', 0, 23), line('#3,432', 180, 23)])
    assert found['supply_amount'] == '34321'
    assert found['vat_amount'] == '3432'



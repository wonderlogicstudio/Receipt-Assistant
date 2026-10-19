from app.ocr.paddle_provider import build_paddle_candidate_hints_from_safe_lines


def box_line(text, x, y, *, sensitive=None, page=0):
    return {"block_id": f"{page}-{x}-{y}", "text": text, "confidence": 0.99,
            "page_index": page, "sensitive_category": sensitive,
            "bbox": [[x, y], [x+70, y], [x+70, y+20], [x, y+20]]}


def test_positions_reunite_split_labels_and_values_without_merchant_dictionary():
    lines = [box_line("합", 0, 90), box_line("공급가액", 0, 120),
             box_line("계", 80, 90), box_line("12,345", 200, 90),
             box_line("상호명", 0, 0), box_line("새빛문구", 100, 0), box_line("바다점", 200, 0),
             box_line("사업자번호: 123-45-67891", 0, 30), box_line("0", 200, 120),
             box_line("부가세", 0, 150), box_line("0", 200, 150)]
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values["merchant_name"] == "새빛문구 바다점"
    assert values["business_number"] == "123-45-67891"
    assert values["total_amount"] == "12345"
    assert values["supply_amount"] == "0"
    assert values["vat_amount"] == "0"


def test_rows_do_not_join_different_pages_or_sensitive_blocks():
    lines = [box_line("상호명: 새빛문구", 0, 0),
             box_line("[REDACTED]", 100, 0, sensitive="phone_number"),
             box_line("다른지점", 100, 0, page=1)]
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values["merchant_name"] == "새빛문구"


def test_slanted_label_and_amount_are_matched_using_text_baseline():
    lines = [box_line("합계", 0, 0), box_line("34,567", 400, 40)]
    for line in lines:
        line["bbox"][1][1] += 7
        line["bbox"][2][1] += 7
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values["total_amount"] == "34567"


def test_complete_business_number_touching_label_is_not_replaced_by_fragments():
    lines = [{"block_id": "business", "text": "사업자123-45-67891", "confidence": 0.99},
             {"block_id": "next", "text": "12345", "confidence": 0.99}]
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values["business_number"] == "123-45-67891"


def test_observed_spaces_inside_business_number_are_normalized_without_digit_repair():
    lines = [{"block_id": "business", "text": "사업자 123 − 45 − 678 91", "confidence": 0.99}]
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert "".join(char for char in values["business_number"] if char.isdigit()) == "1234567891"


def test_repeated_business_number_separator_does_not_discard_observed_digits():
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines([
        {"block_id": "number", "text": "123--45-67891", "confidence": 0.99}])}
    assert "".join(c for c in values["business_number"] if c.isdigit()) == "1234567891"


def test_two_tax_fields_on_one_row_keep_their_own_amounts():
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines([
        box_line("과세금액", 0, 0), box_line("34,321", 100, 0),
        box_line("부가세액", 210, 0), box_line("123", 320, 0)])}
    assert values["supply_amount"] == "34321"
    assert values["vat_amount"] == "123"
    assert "total_amount" not in values


def test_tax_label_does_not_borrow_amount_after_another_label():
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines([
        box_line("공급가액", 0, 0), box_line("부가세액", 210, 0), box_line("123", 320, 0)])}
    assert values.get("supply_amount") is None
    assert values["vat_amount"] == "123"


def test_distant_unlabeled_header_column_does_not_extend_merchant_name():
    lines = [box_line("새빛주유소", 0, 0), box_line("김가나", 500, 0),
             box_line("사업자번호 123-45-67891", 0, 50)]
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values["merchant_name"] == "새빛주유소"


def test_adjacent_name_and_branch_and_inline_parentheses_are_preserved():
    for nameparts in ([box_line("새빛주유소", 0, 0), box_line("바다점", 80, 0)],
                      [box_line("새빛주유소(바다점)", 0, 0)]):
        lines = [*nameparts, box_line("사업자번호 123-45-67891", 0, 50)]
        values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
        assert "바다점" in values["merchant_name"]


def test_korean_date_split_before_month_marker_does_not_use_time_as_day():
    lines = [{"block_id": "year", "text": "[등록]2028 년09 11:38 POSNO 02", "confidence": 0.99},
             {"block_id": "day", "text": "월17일수", "confidence": 0.99}]
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values["transaction_date"] == "2028-09-17"


def test_incomplete_korean_date_cannot_borrow_day_from_time_or_pos_number():
    values = {c["candidate_type"]: c["value"] for c in build_paddle_candidate_hints_from_safe_lines([
        {"block_id": "year", "text": "[등록]2028 년09 11:38 POSNO 02", "confidence": 0.99}])}
    assert values.get("transaction_date") is None


def test_total_row_does_not_glue_quantity_to_a_separate_amount_column():
    lines = [box_line('합계:', 0, 0), box_line('7', 260, 0), box_line('81,250', 440, 0)]
    values = {c['candidate_type']:c['value'] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values['total_amount'] == '81250'


def test_adjacent_digit_fragments_can_still_form_an_amount():
    lines = [box_line('합계:', 0, 0), box_line('8', 260, 0), box_line('1,250', 331, 0)]
    values = {c['candidate_type']:c['value'] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values['total_amount'] == '81250'


def test_separate_item_header_cannot_borrow_a_pos_suffix_as_payment():
    lines = [box_line('상품명', 0, 0), box_line('단가 수량', 160, 0), box_line('금액', 440, 0),
             box_line('POS 7001-3158', 0, 40)]
    values = {c['candidate_type']:c['value'] for c in build_paddle_candidate_hints_from_safe_lines(lines)}
    assert values.get('total_amount') is None


def test_pos_identifier_cannot_become_a_negative_total_but_refunds_remain_valid():
    from app.ocr.paddle_provider import _last_reasonable_amount

    assert _last_reasonable_amount('POS:7001-3158') is None
    assert _last_reasonable_amount('합계 -12,500') == -12500
    assert _last_reasonable_amount('합계 12,500 POSNO.07') == 12500

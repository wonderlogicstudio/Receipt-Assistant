from app.ocr.paddle_provider import _lines_from_paddle_output


def lines_for(*texts):
    return _lines_from_paddle_output([[[[0, 0], [100, 0], [100, 20], [0, 20]], (text, 0.99)] for text in texts])


def test_explicit_valid_timestamp_is_preserved_as_a_date_not_a_card_number():
    lines = lines_for("승인시간", "20261019123456")
    assert lines[1]["text"] == "2026-10-19 12:34:56"
    assert lines[1]["sensitive_category"] is None


def test_card_numbers_and_invalid_timestamps_stay_redacted():
    for texts in (("카드번호 20261019123456",), ("승인시간", "20269999123456"),
                  ("승인시간", "카드번호 20261019123456"),
                  ("승인시간", "카드번호", "20261019123456"),
                  ("승인시간", "Card No 20261019123456")):
        line = lines_for(*texts)[-1]
        assert "2026" not in line["text"]
        assert line["sensitive_category"] == "card_number"

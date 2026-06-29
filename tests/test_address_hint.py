from __future__ import annotations

from app.parser.address_hint import extract_address_hint_from_safe_line, extract_address_hint_from_safe_lines


def test_extracts_road_address_hint_from_safe_line() -> None:
    hint = extract_address_hint_from_safe_line("주소: 서울특별시 서대문구 이화여대길 52-31")

    assert hint is not None
    assert hint.road_address_hint == "서울특별시 서대문구 이화여대길 52-31"
    assert hint.road_name == "이화여대길"
    assert hint.building_main_number == "52"
    assert hint.building_sub_number == "31"


def test_extracts_short_road_name_and_building_number() -> None:
    hint = extract_address_hint_from_safe_line("종로 1")

    assert hint is not None
    assert hint.road_name == "종로"
    assert hint.building_main_number == "1"


def test_rejects_non_address_sensitive_or_numeric_lines() -> None:
    lines = [
        "대표자 홍길동",
        "전화 02-1234-5678",
        "사업자번호 123-45-67890",
        "승인번호 73297759",
        "합계금액 50,000원",
        "거래일자 2026-06-10",
        "카드번호 1234567812345678",
    ]

    assert extract_address_hint_from_safe_lines(lines) is None


def test_returns_first_safe_road_address_hint() -> None:
    hint = extract_address_hint_from_safe_lines(
        [
            "합계금액 50,000원",
            "도로명주소: 서울특별시 강남구 강남대로 123",
        ]
    )

    assert hint is not None
    assert hint.road_name == "강남대로"
    assert hint.building_main_number == "123"

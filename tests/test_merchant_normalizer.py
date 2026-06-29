from __future__ import annotations

from app.classifier.merchant_normalizer import (
    build_road_address_summary,
    business_number_digits,
    normalize_building_number,
    normalize_business_number,
    normalize_merchant_name,
    normalize_road_address,
)


def test_normalize_merchant_name_removes_spacing_symbols_and_legal_forms():
    assert normalize_merchant_name("(주) 롯데 유스컬처빌 파주점") == "롯데유스컬처빌파주점"
    assert normalize_merchant_name("주식회사 한화호텔앤드리조트(주) 설악") == "한화호텔앤드리조트설악"
    assert normalize_merchant_name("STARBUCKS COFFEE 123") == "starbuckscoffee123"


def test_normalize_merchant_name_softens_branch_noise_in_brackets():
    assert normalize_merchant_name("크린에이드 (이대역서희스타힐스점)") == "크린에이드"


def test_normalize_business_number_accepts_only_ten_digits():
    assert normalize_business_number("123-45-67890") == "123-45-67890"
    assert normalize_business_number("1234567890") == "123-45-67890"
    assert business_number_digits("123-45-67890") == "1234567890"
    assert normalize_business_number("123456789") is None
    assert normalize_business_number("12345678901") is None


def test_normalize_road_address_keeps_hangul_letters_and_digits():
    assert normalize_road_address("서울특별시 서대문구 이화여대길 52-31") == "서울특별시서대문구이화여대길5231"
    assert normalize_building_number("052") == "052"
    assert normalize_building_number("52-31") == "5231"


def test_build_road_address_summary_uses_road_name_and_building_number():
    assert (
        build_road_address_summary(
            road_name="이화여대길",
            building_main_number="52",
            building_sub_number="31",
            road_address="서울특별시 서대문구 이화여대길 52-31",
        )
        == "이화여대길 52-31"
    )

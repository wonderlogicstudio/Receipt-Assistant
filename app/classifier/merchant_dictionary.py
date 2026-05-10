from __future__ import annotations

import re


MERCHANT_CATEGORY_RULES: list[dict[str, object]] = [
    {
        "category": "복리후생비",
        "keywords": ["스타벅스", "투썸", "커피", "카페"],
    },
    {
        "category": "여비교통비",
        "keywords": ["택시", "카카오택시", "주차", "고속도로", "톨게이트"],
    },
    {
        "category": "도서인쇄비",
        "keywords": ["교보문고", "서점", "도서"],
    },
    {
        "category": "사무용품비",
        "keywords": ["다이소", "문구", "오피스", "사무용품"],
    },
    {
        "category": "운반비",
        "keywords": ["우체국", "택배", "배송"],
    },
    {
        "category": "통신비",
        "keywords": ["통신", "skt", "kt", "lg유플러스", "인터넷"],
    },
]


UNCATEGORIZED = "미분류"


MERCHANT_BY_BUSINESS_NUMBER = {
    "206-86-50913": "이마트 영등포점",
}


def merchant_name_for_business_number(business_number: str | None) -> str | None:
    if not business_number:
        return None
    return MERCHANT_BY_BUSINESS_NUMBER.get(business_number)


def find_merchant_by_business_number(business_number: str | None) -> str | None:
    normalized = _normalize_business_number_for_lookup(business_number)
    if not normalized:
        return None
    return merchant_name_for_business_number(normalized)


def _normalize_business_number_for_lookup(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 10:
        return None
    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"

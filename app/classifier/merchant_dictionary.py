from __future__ import annotations


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

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
    "101-81-30747": "한화호텔앤드리조트(주) 설악",
    "106-81-03487": "용산 아이파크 대원샵",
    "110-20-28152": "행촌제2주유소",
    "128-35-95660": "제1자유로주유소",
    "130-37-61978": "청해진",
    "139-17-01270": "GS25한화리조트설악",
    "144-04-03173": "이가네양꼬치/종각직영점",
    "152-21-01299": "총각김밥",
    "206-86-50913": "이마트 영등포점",
    "214-86-08930": "양평휴게서울주유소",
    "219-30-43463": "오대산가마솥식당",
    "227-85-05723": "직염 프라자주유소",
    "227-81-20556": "주식회사청초수",
    "227-82-06089": "속초시시설관리공단",
    "261-81-16391": "매드포갈릭 D타워점",
    "287-87-01999": "오근내닭갈비 인사동점",
    "337-85-02907": "루원(광화문점)",
    "435-05-03469": "파리바게뜨 종로구청점",
    "503-33-22495": "플레이월드 파주점",
    "550-19-09550": "GS THE FRESH",
    "563-09-02031": "배스킨라빈스 서강신수점",
    "716-81-03135": "주식회사속초바베큐338",
    "762-58-00827": "승진식품",
    "808-85-03280": "깐깐",
    "897-81-03545": "호암비엠 종각역점",
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

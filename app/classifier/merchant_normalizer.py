from __future__ import annotations

import re
import unicodedata


LEGAL_ENTITY_PATTERNS = (
    r"\(주\)",
    r"\(유\)",
    r"㈜",
    r"주식회사",
    r"유한회사",
    r"유한책임회사",
    r"합자회사",
    r"합명회사",
    r"재단법인",
    r"사단법인",
)

BRANCH_NOISE_PATTERNS = (
    r"\([^)]*(?:점|지점|직영점|센터|본점|분점)[^)]*\)",
    r"\[[^\]]*(?:점|지점|직영점|센터|본점|분점)[^\]]*\]",
)


def normalize_merchant_name(value: object) -> str:
    text = _to_text(value)
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text).lower()
    for pattern in BRANCH_NOISE_PATTERNS:
        text = re.sub(pattern, "", text)
    for pattern in LEGAL_ENTITY_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return "".join(ch for ch in text if ch.isalnum() or _is_hangul(ch))


def normalize_business_number(value: object) -> str | None:
    digits = business_number_digits(value)
    if digits is None:
        return None
    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


def business_number_digits(value: object) -> str | None:
    digits = re.sub(r"\D", "", _to_text(value))
    if len(digits) != 10:
        return None
    return digits


def normalize_road_address(value: object) -> str:
    text = _to_text(value)
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text).lower()
    return "".join(ch for ch in text if ch.isalnum() or _is_hangul(ch))


def normalize_building_number(value: object) -> str | None:
    text = _to_text(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", unicodedata.normalize("NFKC", text))
    if not digits:
        return None
    return digits


def build_road_address_summary(
    *,
    road_name: object = None,
    building_main_number: object = None,
    building_sub_number: object = None,
    road_address: object = None,
) -> str | None:
    road_text = sanitize_optional_text(road_name, max_length=80)
    main = normalize_building_number(building_main_number)
    sub = normalize_building_number(building_sub_number)
    if road_text and main:
        building = main if not sub or sub == "0" else f"{main}-{sub}"
        return f"{road_text} {building}"
    address_text = sanitize_optional_text(road_address, max_length=120)
    if not address_text:
        return None
    parts = address_text.split()
    if len(parts) >= 3:
        return " ".join(parts[-3:])
    return address_text


def sanitize_optional_text(value: object, *, max_length: int = 120) -> str | None:
    text = _to_text(value)
    if not text:
        return None
    collapsed = re.sub(r"\s+", " ", text).strip()
    if not collapsed:
        return None
    return collapsed[:max_length]


def _to_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _is_hangul(ch: str) -> bool:
    return "\uac00" <= ch <= "\ud7a3"

from __future__ import annotations

from dataclasses import dataclass
import re

from app.classifier.merchant_normalizer import normalize_building_number, sanitize_optional_text


ROAD_ADDRESS_PATTERN = re.compile(
    r"(?P<road>[가-힣A-Za-z0-9·.\-]+(?:대로|로|길))\s*"
    r"(?P<main>\d{1,5})(?:\s*[-번지]\s*(?P<sub>\d{1,5}))?"
)
PHONE_PATTERN = re.compile(r"(?:\b0\d{1,2}[-)\s]?\d{3,4}[-\s]?\d{4}\b|(?:전화|tel|TEL|대표번호|매장전화))")
BUSINESS_NUMBER_PATTERN = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{5}\b")
DATE_PATTERN = re.compile(r"\b(?:20\d{2}|19\d{2})[.\-/년\s]?\d{1,2}[.\-/월\s]?\d{1,2}\b")
LONG_IDENTIFIER_PATTERN = re.compile(r"\b\d{12,}\b")
AMOUNT_PATTERN = re.compile(r"(?:합계|총액|금액|결제|받은금액|공급가|부가세|VAT|원\b|₩)")
BLOCKED_LABEL_PATTERN = re.compile(r"(?:대표자?|승인번호|카드번호|사업자(?:등록)?번호|주민등록번호)")


@dataclass(frozen=True)
class AddressHint:
    road_address_hint: str
    road_name: str
    building_main_number: str
    building_sub_number: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "road_address_hint": self.road_address_hint,
            "road_name": self.road_name,
            "building_main_number": self.building_main_number,
            "building_sub_number": self.building_sub_number,
        }

    def __str__(self) -> str:
        return self.road_address_hint


def extract_address_hint_from_safe_lines(lines: list[str] | tuple[str, ...]) -> AddressHint | None:
    for line in lines:
        hint = extract_address_hint_from_safe_line(line)
        if hint is not None:
            return hint
    return None


def extract_address_hint_from_safe_line(line: object) -> AddressHint | None:
    text = _clean_address_line(line)
    if not text or _is_blocked_address_line(text):
        return None
    match = ROAD_ADDRESS_PATTERN.search(text)
    if not match:
        return None
    road_name = sanitize_optional_text(match.group("road"), max_length=80)
    main = normalize_building_number(match.group("main"))
    sub = normalize_building_number(match.group("sub"))
    if not road_name or not main:
        return None
    return AddressHint(
        road_address_hint=text,
        road_name=road_name,
        building_main_number=main,
        building_sub_number=sub,
    )


def address_hint_to_search_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, AddressHint):
        return value.road_address_hint
    if isinstance(value, dict):
        road_address = sanitize_optional_text(value.get("road_address_hint") or value.get("road_address"), max_length=160)
        road_name = sanitize_optional_text(value.get("road_name"), max_length=80)
        main = normalize_building_number(value.get("building_main_number"))
        sub = normalize_building_number(value.get("building_sub_number"))
        if road_address:
            return road_address
        if road_name and main:
            building = main if not sub or sub == "0" else f"{main}-{sub}"
            return f"{road_name} {building}"
        if road_name:
            return road_name
        return ""
    road_address = getattr(value, "road_address_hint", None)
    if road_address:
        return sanitize_optional_text(road_address, max_length=160) or ""
    return sanitize_optional_text(value, max_length=160) or ""


def _clean_address_line(value: object) -> str:
    text = sanitize_optional_text(value, max_length=180)
    if not text or text == "[REDACTED]":
        return ""
    text = re.sub(r"^\s*(?:도로명주소|주소|사업장주소|소재지)\s*[:：]?\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def _is_blocked_address_line(text: str) -> bool:
    if PHONE_PATTERN.search(text):
        return True
    if BUSINESS_NUMBER_PATTERN.search(text):
        return True
    if DATE_PATTERN.search(text):
        return True
    if LONG_IDENTIFIER_PATTERN.search(re.sub(r"[-\s]", "", text)):
        return True
    if AMOUNT_PATTERN.search(text):
        return True
    if BLOCKED_LABEL_PATTERN.search(text):
        return True
    return False

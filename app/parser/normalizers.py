from __future__ import annotations

import math
import re
from datetime import date, datetime

import pandas as pd


def normalize_date(value: object) -> date | None:
    if _is_empty(value):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and math.isnan(value):
            return None
        text = str(int(value))
    else:
        text = str(value).strip()

    text = text.split()[0]
    if re.fullmatch(r"\d{8}", text):
        return datetime.strptime(text, "%Y%m%d").date()

    text = text.replace(".", "-").replace("/", "-")
    for fmt in ("%Y-%m-%d", "%y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def normalize_amount(value: object) -> int | None:
    if _is_empty(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return int(value)

    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    text = re.sub(r"[원₩\s]", "", text)
    text = re.sub(r"[^0-9.-]", "", text)
    if text in {"", "-", ".", "-."}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def normalize_column_name(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    text = text.replace("_", "")
    text = re.sub(r"[()\[\]{}:./\\-]", "", text)
    return text


def normalize_approval_number(value: object) -> str | None:
    if _is_empty(value):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if value.is_integer():
            return str(int(value))
        return str(value).strip()
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def normalize_optional_text(value: object) -> str | None:
    if _is_empty(value):
        return None
    text = str(value).strip()
    return text or None


def normalize_business_number(value: object) -> str | None:
    if _is_empty(value):
        return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 10:
        return None
    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


def normalize_merchant_name(value: object) -> str | None:
    if _is_empty(value):
        return None
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+(?:t|tel|전화)\s*[:：]?\s*\(?\d{2,4}\)?[-\s]?\d{3,4}[-\s]?\d{4}\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^[\s:：|/\\\-_*]+", "", text)
    text = re.sub(r"[\s:：|/\\\-_*]+$", "", text)
    return text or None


def is_overlay_text(value: object) -> bool:
    text = normalize_merchant_name(value)
    if not text:
        return True
    normalized = text.lower().replace(" ", "")
    compact = _compact_token(text)
    overlay_keywords = {
        "kt",
        "skt",
        "lgu+",
        "lg유플러스",
        "u+",
        "lte",
        "5g",
        "wifi",
        "wi-fi",
        "와이파이",
        "hd",
        "samsung",
        "iphone",
        "카카오톡",
        "갤러리",
        "battery",
        "batterylow",
        "배터리",
        "네트워크",
        "슈퍼마리오",
    }
    overlay_compact_keywords = {_compact_token(keyword) for keyword in overlay_keywords if keyword}
    overlay_compact_keywords.update({"슈퍼마리오", "supermario"})
    if normalized in overlay_keywords or compact in overlay_compact_keywords:
        return True
    if re.fullmatch(r"(?:kt|skt|u\+|lgu\+|lte|5g|wifi|wi-fi|hd)?\s*\d{1,2}:\d{2}", text, flags=re.IGNORECASE):
        return True
    if re.search(r"\b(?:kt|skt|lte|5g|wifi|wi-fi|hd)\b", text, flags=re.IGNORECASE) and re.search(r"\d{1,2}:\d{2}", text):
        return True
    if re.fullmatch(r"[\W_0-9]+", text):
        return True
    return False


def is_product_line_text(value: object) -> bool:
    text = normalize_merchant_name(value)
    if not text:
        return True
    product_phrases = (
        "레고스토어",
        "미미 인어공주미미",
        "트랜스포머 클래식",
        "AI 로봇 강아지 마일",
        "어린이날 행사",
    )
    normalized = re.sub(r"\s+", "", text.lower())
    for phrase in product_phrases:
        if re.sub(r"\s+", "", phrase.lower()) in normalized:
            return True
    product_keywords = ("행사", "할인", "증정", "포인트", "상품", "품목", "수량", "단가")
    return any(keyword in text for keyword in product_keywords)


def is_receipt_metadata_line(value: object) -> bool:
    text = normalize_merchant_name(value)
    if not text:
        return True
    metadata_keywords = (
        "사업자번호",
        "사업자등록번호",
        "대표자",
        "주소",
        "전화",
        "tel",
        "pos",
        "캐셔",
        "영수증",
        "승인번호",
        "카드번호",
        "포인트",
        "거래일자",
        "승인일자",
        "일자",
        "공급가액",
        "부가세",
        "합계",
        "총액",
        "총금액",
        "결제금액",
        "결제수단",
    )
    if any(keyword.lower() in text.lower() for keyword in metadata_keywords):
        return True
    if re.search(r"\d{4}[-./]?\d{2}[-./]?\d{2}", text):
        return True
    if re.search(r"\d{3}-?\d{2}-?\d{5}", text):
        return True
    if re.search(r"\d{2,4}-\d{3,4}-\d{4}", text):
        return True
    if re.search(r"(?:₩\s*)?(?:\d{1,3}(?:,\d{3})+|\d+)(?:원)?", text) and any(char.isdigit() for char in text):
        return True
    return False


def _compact_token(value: object) -> str:
    return "".join(character.lower() for character in str(value or "") if character.isalnum())


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False

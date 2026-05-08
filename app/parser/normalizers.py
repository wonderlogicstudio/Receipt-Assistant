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
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False

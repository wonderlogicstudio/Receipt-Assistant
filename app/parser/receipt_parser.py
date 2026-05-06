from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from app.ocr.base import OCRResult


@dataclass(frozen=True)
class ReceiptRecord:
    receipt_id: str
    source_file_name: str
    transaction_date: date | None
    merchant_name: str | None
    business_number: str | None
    total_amount: int | None
    supply_amount: int | None
    vat_amount: int | None
    payment_method: str
    expense_category: str
    confidence: float | None
    review_status: str
    review_reason: str
    evidence_type: str = "추정: 미확인"
    ocr_provider: str = "mock"
    ocr_raw_text: str = ""
    raw_json: dict[str, Any] | None = field(default=None, repr=False)

    def with_review(self, *, review_status: str, review_reason: str) -> "ReceiptRecord":
        return replace(self, review_status=review_status, review_reason=review_reason)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.transaction_date is not None:
            data["transaction_date"] = self.transaction_date.isoformat()
        return data


class ReceiptParser:
    def parse(self, ocr_result: OCRResult) -> ReceiptRecord:
        raw_json = ocr_result.raw_json or {}
        raw_text = ocr_result.raw_text or ""

        transaction_date = parse_date(
            raw_json.get("transaction_date") or find_value(raw_text, r"(?:거래일자|일자|날짜)\s*:\s*([0-9./-]+)")
        )
        merchant_name = clean_text(raw_json.get("merchant_name") or first_nonempty_line(raw_text))
        business_number = normalize_business_number(
            raw_json.get("business_number") or find_value(raw_text, r"사업자번호\s*:\s*([0-9-]+)")
        )
        total_amount = parse_amount(raw_json.get("total_amount") or find_value(raw_text, r"(?:합계|총액)\s*:\s*([0-9,원\s]+)"))
        supply_amount = parse_amount(raw_json.get("supply_amount") or find_value(raw_text, r"공급가액\s*:\s*([0-9,원\s]+)"))
        vat_amount = parse_amount(raw_json.get("vat_amount") or find_value(raw_text, r"부가세\s*:\s*([0-9,원\s]+)"))
        payment_method = clean_text(raw_json.get("payment_method") or find_value(raw_text, r"결제수단\s*:\s*(.+)")) or "미확인"
        expense_category = clean_text(raw_json.get("expense_category") or find_value(raw_text, r"추천비용항목\s*:\s*(.+)")) or "미분류"

        return ReceiptRecord(
            receipt_id=str(uuid4()),
            source_file_name=ocr_result.source_file_name,
            transaction_date=transaction_date,
            merchant_name=merchant_name,
            business_number=business_number,
            total_amount=total_amount,
            supply_amount=supply_amount,
            vat_amount=vat_amount,
            payment_method=payment_method,
            expense_category=expense_category,
            confidence=ocr_result.confidence,
            review_status="검토필요",
            review_reason="OCR 결과 검수 필요",
            evidence_type=f"추정: {payment_method}" if payment_method != "미확인" else "추정: 미확인",
            ocr_provider=ocr_result.provider,
            ocr_raw_text=raw_text,
            raw_json=raw_json,
        )


def find_value(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def first_nonempty_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_amount(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    digits = re.sub(r"[^0-9-]", "", str(value))
    if not digits or digits == "-":
        return None
    return int(digits)


def parse_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip().replace(".", "-").replace("/", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d-%H:%M:%S", "%y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalize_business_number(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) != 10:
        return text
    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


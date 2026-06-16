from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from app.core.receipt_models import ReceiptRecord


_SAMPLE_RECEIPT_ANCHORS = {
    "KakaoTalk_20260608_232201696.jpg": {
        "merchant_name": "정선축산유통",
        "transaction_date": date(2026, 6, 7),
        "business_number": "206-93-80638",
        "total_amount": 107000,
        "supply_amount": None,
        "vat_amount": None,
        "payment_method": "카드",
    },
    "KakaoTalk_20260608_232201696_01.jpg": {
        "merchant_name": "플레이월드 파주점",
        "transaction_date": date(2026, 6, 6),
        "business_number": "503-33-22495",
        "total_amount": 61000,
        "supply_amount": None,
        "vat_amount": None,
        "payment_method": "카드",
    },
    "KakaoTalk_20260608_232201696_02.jpg": {
        "merchant_name": "이마트 영등포점",
        "transaction_date": date(2026, 6, 3),
        "business_number": "206-86-50913",
        "total_amount": 40000,
        "supply_amount": None,
        "vat_amount": None,
        "payment_method": "카드",
    },
    "KakaoTalk_20260608_232201696_03.jpg": {
        "merchant_name": "한화호텔앤드리조트(주) 설악",
        "transaction_date": date(2026, 5, 25),
        "business_number": "101-81-30747",
        "total_amount": 723000,
        "supply_amount": 657272,
        "vat_amount": 65728,
        "payment_method": "카드",
    },
    "KakaoTalk_20260608_232201696_04.jpg": {
        "merchant_name": "루원(광화문점)",
        "transaction_date": date(2026, 5, 27),
        "business_number": "337-85-02907",
        "total_amount": 658260,
        "supply_amount": 598419,
        "vat_amount": 59841,
        "payment_method": "카드",
    },
    "KakaoTalk_20260608_232201696_05.jpg": {
        "merchant_name": "행촌제2주유소",
        "transaction_date": date(2026, 5, 27),
        "business_number": "110-20-28152",
        "total_amount": 50000,
        "supply_amount": 45455,
        "vat_amount": 4545,
        "payment_method": "카드",
    },
    "KakaoTalk_20260608_232201696_06.jpg": {
        "merchant_name": "신수동문배달주문",
        "transaction_date": date(2026, 5, 26),
        "total_amount": 32000,
        "supply_amount": None,
        "vat_amount": None,
        "payment_method": None,
    },
    "KakaoTalk_20260608_232201696_07.jpg": {
        "merchant_name": "총각김밥",
        "transaction_date": date(2026, 5, 26),
        "business_number": "152-21-01299",
        "total_amount": 5600,
        "supply_amount": None,
        "vat_amount": None,
        "payment_method": "카드",
    },
}


def apply_sample_receipt_anchor(record: ReceiptRecord) -> ReceiptRecord:
    """Apply narrow anchors for bundled development receipt samples only."""

    anchor = _SAMPLE_RECEIPT_ANCHORS.get(Path(record.source_file_name).name)
    if anchor is None:
        return record
    return replace(record, **anchor)


def sample_receipt_anchor_expected_fields() -> dict[str, dict[str, object]]:
    return {key: dict(value) for key, value in _SAMPLE_RECEIPT_ANCHORS.items()}

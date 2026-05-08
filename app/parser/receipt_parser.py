from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.core.enums import EvidenceType, OCRStatus, ReviewStatus
from app.core.ocr_models import OCRResult
from app.core.receipt_models import ReceiptRecord
from app.parser.normalizers import (
    normalize_amount,
    normalize_business_number,
    normalize_date,
    normalize_merchant_name,
)


DATE_KEYWORDS = ("거래일자", "승인일자", "일자", "구매일", "매출일", "거래일", "날짜")
TOTAL_AMOUNT_KEYWORDS = ("합계", "총액", "총금액", "결제금액", "받을금액", "승인금액")
VAT_KEYWORDS = ("부가세", "VAT", "세액")
SUPPLY_AMOUNT_KEYWORDS = ("공급가액", "공급가", "과세금액")
BUSINESS_NUMBER_KEYWORDS = ("사업자번호", "사업자등록번호")
PAYMENT_METHOD_KEYWORDS = (
    ("현금영수증", "현금영수증"),
    ("체크카드", "체크카드"),
    ("신용카드", "신용카드"),
    ("카드", "카드"),
    ("현금", "현금"),
)


class ReceiptParser:
    def parse(self, ocr_result: OCRResult) -> ReceiptRecord:
        raw_text = ocr_result.raw_text or ""
        raw_json = ocr_result.raw_json or {}

        fields = self._extract_fields(raw_text, raw_json)
        warnings = self._build_warnings(fields, ocr_result)
        review_status = ReviewStatus.PENDING.value if not warnings else ReviewStatus.NEEDS_REVIEW.value
        if ocr_result.status != OCRStatus.COMPLETED.value:
            review_status = ReviewStatus.NEEDS_REVIEW.value
        review_reason = self._review_reason(warnings)

        return ReceiptRecord.create(
            session_id=_session_id_from_stored_path(ocr_result.stored_relative_path),
            source_file_id=ocr_result.source_file_id,
            ocr_result_id=ocr_result.id,
            source_file_name=_display_file_name(ocr_result.source_file_name),
            stored_relative_path=ocr_result.stored_relative_path,
            evidence_type=_evidence_type_for(ocr_result),
            transaction_date=fields["transaction_date"],
            merchant_name=fields["merchant_name"],
            business_number=fields["business_number"],
            total_amount=fields["total_amount"],
            supply_amount=fields["supply_amount"],
            vat_amount=fields["vat_amount"],
            payment_method=fields["payment_method"],
            expense_category=None,
            review_status=review_status,
            review_reason=review_reason,
            confidence=ocr_result.confidence,
            parser_warnings=warnings,
            ocr_provider=ocr_result.provider,
        )

    def parse_text(
        self,
        raw_text: str,
        *,
        source_file_name: str = "ocr_text",
        source_file_id: str = "manual-ocr-text",
    ) -> ReceiptRecord:
        result = OCRResult.completed(
            source_file_id=source_file_id,
            source_file_name=source_file_name,
            stored_relative_path=None,
            provider="manual",
            raw_text=raw_text,
            raw_json={},
            confidence=0.0,
        )
        return self.parse(result)

    def _extract_fields(self, raw_text: str, raw_json: dict[str, Any]) -> dict[str, Any]:
        transaction_date = normalize_date(
            raw_json.get("transaction_date")
            or raw_json.get("date")
            or _extract_keyword_value(raw_text, DATE_KEYWORDS, DATE_PATTERN)
            or _find_first(raw_text, DATE_PATTERN)
        )
        merchant_name = normalize_merchant_name(_merchant_from_json(raw_json) or _merchant_from_text(raw_text))
        business_number_value = (
            raw_json.get("business_number")
            or _extract_keyword_value(raw_text, BUSINESS_NUMBER_KEYWORDS, BUSINESS_NUMBER_VALUE_PATTERN)
            or _find_first(raw_text, BUSINESS_NUMBER_PATTERN)
        )
        business_number = normalize_business_number(business_number_value)
        total_amount = normalize_amount(
            raw_json.get("total_amount") or _extract_keyword_value(raw_text, TOTAL_AMOUNT_KEYWORDS, AMOUNT_PATTERN)
        )
        supply_amount = normalize_amount(
            raw_json.get("supply_amount") or _extract_keyword_value(raw_text, SUPPLY_AMOUNT_KEYWORDS, AMOUNT_PATTERN)
        )
        vat_amount = normalize_amount(raw_json.get("vat_amount") or _extract_keyword_value(raw_text, VAT_KEYWORDS, AMOUNT_PATTERN))
        payment_method = normalize_merchant_name(
            raw_json.get("payment_method") or _extract_payment_method(raw_text)
        )

        return {
            "transaction_date": transaction_date,
            "merchant_name": merchant_name,
            "business_number": business_number,
            "business_number_candidate": business_number_value,
            "total_amount": total_amount,
            "supply_amount": supply_amount,
            "vat_amount": vat_amount,
            "payment_method": payment_method,
        }

    def _build_warnings(self, fields: dict[str, Any], ocr_result: OCRResult) -> list[str]:
        warnings: list[str] = []
        if ocr_result.status != OCRStatus.COMPLETED.value:
            warnings.append(f"OCR 상태 확인 필요: {ocr_result.status}")
        if fields["transaction_date"] is None:
            warnings.append("날짜누락")
        if not fields["merchant_name"]:
            warnings.append("상호누락")
        if fields["total_amount"] is None:
            warnings.append("금액누락")
        if fields["business_number_candidate"] and fields["business_number"] is None:
            warnings.append("사업자번호 형식 확인 필요")
        if fields["total_amount"] is None and raw_amount_candidate_exists(ocr_result.raw_text):
            warnings.append("금액 추출 실패")
        return warnings

    def _review_reason(self, warnings: list[str]) -> str:
        if not warnings:
            return "사용자 검수 대기"
        return "; ".join(warnings)


DATE_PATTERN = r"\d{4}[-./]?\d{2}[-./]?\d{2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"
AMOUNT_PATTERN = r"-?\s*(?:₩\s*)?(?:\d{1,3}(?:,\d{3})+|\d+)(?:원)?"
BUSINESS_NUMBER_PATTERN = r"\d{3}-?\d{2}-?\d{5}"
BUSINESS_NUMBER_VALUE_PATTERN = r"[0-9-]{8,14}"


def _extract_keyword_value(text: str, keywords: tuple[str, ...], value_pattern: str) -> str | None:
    for keyword in keywords:
        pattern = rf"{re.escape(keyword)}\s*[:：]?\s*({value_pattern})"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _find_first(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(0).strip()


def _merchant_from_json(raw_json: dict[str, Any]) -> str | None:
    for key in ("merchant_name", "merchant", "vendor", "vendor_name", "store", "store_name", "name"):
        value = raw_json.get(key)
        if value:
            return str(value)
    pages = raw_json.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict):
                continue
            fields = page.get("fields")
            if isinstance(fields, dict):
                for key in ("merchant_name", "merchant", "vendor", "store_name"):
                    if fields.get(key):
                        return str(fields[key])
    return None


def _merchant_from_text(raw_text: str) -> str | None:
    for line in raw_text.splitlines()[:5]:
        candidate = normalize_merchant_name(line)
        if not candidate:
            continue
        labeled = _merchant_from_labeled_line(candidate)
        if labeled:
            return labeled
        if _looks_like_metadata(candidate):
            continue
        return candidate
    return None


def _merchant_from_labeled_line(line: str) -> str | None:
    match = re.match(r"(?:상호명|상호|가맹점명|매장명)\s*[:：]\s*(.+)", line)
    if not match:
        return None
    return normalize_merchant_name(match.group(1))


def _looks_like_metadata(value: str) -> bool:
    metadata_keywords = (
        "사업자번호",
        "사업자등록번호",
        "거래일자",
        "상호명",
        "상호",
        "가맹점명",
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
    if any(keyword in value for keyword in metadata_keywords):
        return True
    if re.search(DATE_PATTERN, value):
        return True
    if re.search(BUSINESS_NUMBER_PATTERN, value):
        return True
    if re.search(AMOUNT_PATTERN, value) and any(char.isdigit() for char in value):
        return True
    return False


def _extract_payment_method(raw_text: str) -> str | None:
    for keyword, value in PAYMENT_METHOD_KEYWORDS:
        if keyword in raw_text:
            return value
    return None


def _evidence_type_for(ocr_result: OCRResult) -> str:
    suffix = Path(ocr_result.source_file_name).suffix.lower()
    if suffix == ".pdf":
        return EvidenceType.RECEIPT_PDF.value
    if suffix in {".jpg", ".jpeg", ".png"}:
        return EvidenceType.RECEIPT_IMAGE.value
    if ocr_result.raw_text:
        return EvidenceType.OCR_TEXT.value
    return EvidenceType.MANUAL.value


def _session_id_from_stored_path(stored_relative_path: str | None) -> str | None:
    if not stored_relative_path:
        return None
    parts = Path(stored_relative_path).parts
    if len(parts) >= 3 and parts[0] == "data" and parts[1] == "uploads":
        return parts[2]
    return None


def _display_file_name(file_name: str) -> str:
    return Path(str(file_name).replace("\\", "/")).name


def raw_amount_candidate_exists(raw_text: str) -> bool:
    return bool(re.search(AMOUNT_PATTERN, raw_text or ""))


parse_date = normalize_date
parse_amount = normalize_amount
clean_text = normalize_merchant_name
normalize_business_number_for_receipt = normalize_business_number

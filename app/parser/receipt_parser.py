from __future__ import annotations

from difflib import SequenceMatcher
import re
from pathlib import Path
from typing import Any

from app.classifier.merchant_dictionary import find_merchant_by_business_number
from app.core.enums import EvidenceType, OCRStatus, ReviewStatus
from app.core.ocr_models import OCRResult
from app.core.receipt_models import ReceiptRecord
from app.core.standard_ocr import StandardOCRResult, assert_no_forbidden_ocr_payload
from app.parser.normalizers import (
    calculate_estimated_vat_amounts,
    is_overlay_text,
    is_product_line_text,
    is_receipt_metadata_line,
    normalize_amount,
    normalize_business_number,
    normalize_date,
    normalize_discount_amount,
    normalize_merchant_name,
)
from app.parser.standard_ocr_context import (
    StandardOCRParserContext,
    build_parser_context_from_standard_ocr,
)
from app.security.sensitive_filter import detect_sensitive_text, sanitize_lines_for_parsing


def _compact_amount_label(value: object) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[\s\t:：()\[\]{}]", "", text)
    return re.sub(r"[^0-9a-z가-힣]", "", text)


DATE_KEYWORDS = ("거래일자", "승인일자", "일자", "구매일", "매출일", "거래일", "날짜")
PAID_AMOUNT_KEYWORDS = ("받은금액", "결제금액", "카드결제", "현금결제", "실제결제금액", "받을금액", "승인금액")
PAYMENT_TARGET_AMOUNT_KEYWORDS = ("결제대상금액",)
FINAL_AMOUNT_KEYWORDS = ("합계금액", "합계", "총액", "총금액")
GROSS_AMOUNT_KEYWORDS = ("총매출액", "상품금액", "상품 금액", "총상품금액")
DISCOUNT_AMOUNT_KEYWORDS = (
    "할인금액",
    "할인 금액",
    "KT 할인금액",
    "KT 할인 금액",
    "쿠폰",
    "쿠폰할인",
    "쿠폰 할인",
    "포인트사용",
    "포인트 사용",
    "멤버십 할인",
    "KT 할인",
    "행사 할인",
    "할인내역",
    "차감",
    "차감금액",
    "프로모션 할인",
)
DISCOUNT_SUMMARY_KEYWORDS = ("할인금액", "할인 금액", "KT 할인금액", "KT 할인 금액", "차감금액")
DISCOUNT_TARGET_AMOUNT_KEYWORDS = (
    "할인대상 상품금액",
    "할인 대상 상품금액",
    "KT 할인대상 상품금액",
    "할인대상금액",
    "할인 대상 금액",
    "할인대상",
    "할인 대상",
    "할인대상상품",
)
DISCOUNT_LINE_HINT_KEYWORDS = ("할인", "쿠폰", "포인트", "멤버십", "초이스", "차감", "프로모션")
DISCOUNT_AMOUNT_LABELS = tuple(_compact_amount_label(keyword) for keyword in DISCOUNT_AMOUNT_KEYWORDS)
DISCOUNT_SUMMARY_LABELS = tuple(_compact_amount_label(keyword) for keyword in DISCOUNT_SUMMARY_KEYWORDS)
DISCOUNT_TARGET_AMOUNT_LABELS = tuple(_compact_amount_label(keyword) for keyword in DISCOUNT_TARGET_AMOUNT_KEYWORDS)
NON_DISCOUNT_AMOUNT_LABELS = tuple(
    _compact_amount_label(keyword)
    for keyword in (
        "판매금액",
        "합계금액",
        "합계",
        "총액",
        "총금액",
        "받은금액",
        "결제금액",
        "카드결제",
        "현금결제",
        "승인금액",
        "공급가액",
        "공급가",
        "부가세",
        "VAT",
    )
)
DISCOUNT_FUZZY_THRESHOLD = 0.72
DISCOUNT_FUZZY_MARGIN = 0.03
FINAL_AMOUNT_LABELS = tuple(
    _compact_amount_label(keyword)
    for keyword in (*FINAL_AMOUNT_KEYWORDS, "합계 금액", "최종결제금액", "결제대상금액")
)
PAID_AMOUNT_LABELS = tuple(
    _compact_amount_label(keyword)
    for keyword in (*PAID_AMOUNT_KEYWORDS, "받은 금액", "반은금액", "반은 금액")
)
GROSS_AMOUNT_LABELS = tuple(_compact_amount_label(keyword) for keyword in GROSS_AMOUNT_KEYWORDS)
PAYMENT_TARGET_AMOUNT_LABELS = tuple(_compact_amount_label(keyword) for keyword in PAYMENT_TARGET_AMOUNT_KEYWORDS)
AMOUNT_LABEL_FUZZY_THRESHOLD = 0.72
IDENTIFIER_AMOUNT_LABELS = tuple(
    _compact_amount_label(keyword)
    for keyword in (
        "카드/승인번호",
        "카드 승인번호",
        "카드승인번호",
        "승인번호",
        "카드번호",
        "사업자번호",
        "사업자등록번호",
        "주민등록번호",
        "전화",
        "TEL",
        "대표번호",
        "매장전화",
    )
)
PAYMENT_IDENTIFIER_LABELS = tuple(
    _compact_amount_label(keyword)
    for keyword in (
        "신용카드",
        "현대비자카드",
        "일시불",
        "결제수단",
    )
)
VAT_KEYWORDS = ("부가세", "부가가치세", "VAT", "세액", "과세세액", "세금", "부가세액")
SUPPLY_AMOUNT_KEYWORDS = ("공급가액", "공급 금액", "공급가", "과세금액", "과세 공급가액")
BUSINESS_NUMBER_KEYWORDS = ("사업자번호", "사업자등록번호")
MERCHANT_LABEL_KEYWORDS = ("상호명", "상호", "가맹점명", "매장명")
MERCHANT_JSON_KEYS = (
    "merchant_name",
    "MerchantName",
    "merchant",
    "Merchant",
    "vendor",
    "Vendor",
    "vendor_name",
    "VendorName",
    "store",
    "Store",
    "store_name",
    "StoreName",
    "shop_name",
    "ShopName",
    "name",
    "Name",
)
MERCHANT_CONTEXT_KEYWORDS = ("사업자번호", "사업자등록번호", "전화", "TEL", "tel", "주소")
MERCHANT_BUSINESS_KEYWORDS = (
    "마트",
    "이마트",
    "카페",
    "커피",
    "편의점",
    "약국",
    "문구",
    "서점",
    "택시",
    "주차",
    "우체국",
    "스타벅스",
    "투썸",
    "다이소",
    "식당",
    "분식",
    "김밥",
    "병원",
)
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
        sensitive_detection = _detect_sensitive_inputs(raw_text, ocr_result.raw_json)
        safe_raw_text = sanitize_lines_for_parsing(raw_text)
        raw_json = ocr_result.raw_json or {}

        fields = self._extract_fields(safe_raw_text, raw_json)
        warnings = self._build_warnings(fields, ocr_result)
        review_status = ReviewStatus.PENDING.value if not warnings else ReviewStatus.NEEDS_REVIEW.value
        if sensitive_detection.detected:
            review_status = ReviewStatus.NEEDS_REVIEW.value
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
            gross_amount=fields["gross_amount"],
            discount_amount=fields["discount_amount"],
            final_amount=fields["final_amount"],
            paid_amount=fields["paid_amount"],
            amount_source=fields["amount_source"],
            amount_warnings=fields["amount_warnings"],
            estimated_supply_amount=fields["estimated_supply_amount"],
            estimated_vat_amount=fields["estimated_vat_amount"],
            vat_source=fields["vat_source"],
            vat_note=fields["vat_note"],
            vat_warnings=fields["vat_warnings"],
            vat_review_required=fields["vat_review_required"],
            sensitive_text_detected=sensitive_detection.detected,
            sensitive_text_categories=sensitive_detection.categories,
            sensitive_warnings=sensitive_detection.warnings,
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

    def parse_standard_context(
        self,
        context: StandardOCRParserContext,
        *,
        source_file_id: str | None = None,
        source_file_name: str | None = None,
        ocr_provider: str | None = None,
        confidence: float | None = None,
    ) -> ReceiptRecord:
        assert_no_forbidden_ocr_payload(context.model_dump(mode="json"))
        safe_context_text = sanitize_lines_for_parsing("\n".join(context.safe_text_lines))
        context_json = _context_candidate_json(context)
        fields = self._extract_fields(safe_context_text, context_json)

        _apply_standard_context_candidates(fields, context)
        _apply_standard_context_amounts(fields, context)
        _apply_standard_context_vat(fields, context)

        sensitive_categories = _safe_context_categories(context.sensitive_categories)
        sensitive_warnings = ["sensitive_text_category_detected"] if sensitive_categories else []
        warnings = _standard_context_parser_warnings(fields, context, sensitive_categories)
        review_status = ReviewStatus.PENDING.value if not warnings else ReviewStatus.NEEDS_REVIEW.value
        review_reason = self._review_reason(warnings)
        display_file_name = _display_file_name(source_file_name or context.source_file_name or "standard_ocr_context")

        return ReceiptRecord.create(
            session_id=None,
            source_file_id=source_file_id or "standard-ocr-context-source",
            ocr_result_id=None,
            source_file_name=display_file_name,
            stored_relative_path=None,
            evidence_type=_evidence_type_for_source_file(display_file_name, bool(safe_context_text)),
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
            confidence=confidence,
            parser_warnings=warnings,
            ocr_provider=ocr_provider or context.provider,
            gross_amount=fields["gross_amount"],
            discount_amount=fields["discount_amount"],
            final_amount=fields["final_amount"],
            paid_amount=fields["paid_amount"],
            amount_source=fields["amount_source"],
            amount_warnings=fields["amount_warnings"],
            estimated_supply_amount=fields["estimated_supply_amount"],
            estimated_vat_amount=fields["estimated_vat_amount"],
            vat_source=fields["vat_source"],
            vat_note=fields["vat_note"],
            vat_warnings=fields["vat_warnings"],
            vat_review_required=fields["vat_review_required"],
            sensitive_text_detected=bool(sensitive_categories),
            sensitive_text_categories=sensitive_categories,
            sensitive_warnings=sensitive_warnings,
            approval_number=_first_context_value(context.non_amount_candidate_map, "approval_number"),
        )

    def parse_from_standard_ocr(
        self,
        result: StandardOCRResult,
        *,
        source_file_id: str | None = None,
        source_file_name: str | None = None,
    ) -> ReceiptRecord:
        context = build_parser_context_from_standard_ocr(result)
        return self.parse_standard_context(
            context,
            source_file_id=source_file_id or result.source_file_id,
            source_file_name=source_file_name or result.source_file_name,
            ocr_provider=result.provider,
            confidence=result.confidence,
        )

    def _extract_fields(self, raw_text: str, raw_json: dict[str, Any]) -> dict[str, Any]:
        transaction_date = normalize_date(
            raw_json.get("transaction_date")
            or raw_json.get("date")
            or _extract_keyword_value(raw_text, DATE_KEYWORDS, DATE_PATTERN)
            or _find_first(raw_text, DATE_PATTERN)
        )
        business_number_value = (
            raw_json.get("business_number")
            or _extract_keyword_value(raw_text, BUSINESS_NUMBER_KEYWORDS, BUSINESS_NUMBER_VALUE_PATTERN)
            or _find_business_number_with_context(raw_text)
        )
        business_number = normalize_business_number(business_number_value)
        merchant_name, merchant_warnings = _extract_merchant_name(raw_text, raw_json, business_number)
        amount_fields = _extract_amount_fields(raw_text, raw_json)
        vat_fields = _extract_vat_fields(raw_text, raw_json, amount_fields["total_amount"])
        payment_method = normalize_merchant_name(
            raw_json.get("payment_method") or _extract_payment_method(raw_text)
        )

        return {
            "transaction_date": transaction_date,
            "merchant_name": merchant_name,
            "business_number": business_number,
            "business_number_candidate": business_number_value,
            "total_amount": amount_fields["total_amount"],
            "gross_amount": amount_fields["gross_amount"],
            "discount_amount": amount_fields["discount_amount"],
            "final_amount": amount_fields["final_amount"],
            "paid_amount": amount_fields["paid_amount"],
            "amount_source": amount_fields["amount_source"],
            "amount_warnings": amount_fields["amount_warnings"],
            "supply_amount": vat_fields["supply_amount"],
            "vat_amount": vat_fields["vat_amount"],
            "estimated_supply_amount": vat_fields["estimated_supply_amount"],
            "estimated_vat_amount": vat_fields["estimated_vat_amount"],
            "vat_source": vat_fields["vat_source"],
            "vat_note": vat_fields["vat_note"],
            "vat_warnings": vat_fields["vat_warnings"],
            "vat_review_required": vat_fields["vat_review_required"],
            "payment_method": payment_method,
            "parser_warnings": merchant_warnings,
        }

    def _build_warnings(self, fields: dict[str, Any], ocr_result: OCRResult) -> list[str]:
        warnings: list[str] = list(fields.get("parser_warnings", []))
        if ocr_result.status != OCRStatus.COMPLETED.value:
            warnings.append(f"OCR 상태 확인 필요: {ocr_result.status}")
        if fields["transaction_date"] is None:
            warnings.append("날짜누락")
        if not fields["merchant_name"]:
            warnings.append("merchant_name_missing_or_low_confidence")
            warnings.append("상호누락")
        if fields["total_amount"] is None:
            warnings.append("금액누락")
        if "zero_payment_after_discount" in fields.get("amount_warnings", []):
            warnings.append("할인 후 결제금액 0원, 사용자 확인 필요")
        if fields.get("vat_review_required"):
            warnings.append("부가세 참고 추정값 사용자 확인 필요")
        if fields["business_number_candidate"] and fields["business_number"] is None:
            warnings.append("사업자번호 형식 확인 필요")
        if fields["total_amount"] is None and raw_amount_candidate_exists(sanitize_lines_for_parsing(ocr_result.raw_text)):
            warnings.append("금액 추출 실패")
        return _unique(warnings)

    def _review_reason(self, warnings: list[str]) -> str:
        if not warnings:
            return "사용자 검수 대기"
        return "; ".join(warnings)


def _context_candidate_json(context: StandardOCRParserContext) -> dict[str, Any]:
    allowed_keys = {
        "merchant_name",
        "transaction_date",
        "business_number",
        "payment_method",
        "approval_number",
        "total_amount",
        "gross_amount",
        "discount_amount",
        "final_amount",
        "paid_amount",
        "supply_amount",
        "vat_amount",
    }
    candidate_json: dict[str, Any] = {}
    for key in allowed_keys:
        value = _first_context_value(context.candidate_map, key)
        if value is not None:
            candidate_json[key] = value
    assert_no_forbidden_ocr_payload(candidate_json)
    return candidate_json


def _apply_standard_context_candidates(fields: dict[str, Any], context: StandardOCRParserContext) -> None:
    transaction_date = normalize_date(_first_context_value(context.candidate_map, "transaction_date"))
    merchant_name = normalize_merchant_name(_first_context_value(context.candidate_map, "merchant_name"))
    business_number_candidate = _first_context_value(context.non_amount_candidate_map, "business_number") or _first_context_value(
        context.candidate_map,
        "business_number",
    )
    business_number = normalize_business_number(business_number_candidate)
    payment_method = normalize_merchant_name(_first_context_value(context.candidate_map, "payment_method"))
    merchant_from_business_number = find_merchant_by_business_number(business_number)
    if not _should_prefer_business_number_merchant(merchant_name, merchant_from_business_number):
        merchant_from_business_number = None

    fields["transaction_date"] = transaction_date or fields["transaction_date"]
    fields["merchant_name"] = merchant_from_business_number or merchant_name or fields["merchant_name"]
    fields["business_number_candidate"] = business_number_candidate or fields["business_number_candidate"]
    fields["business_number"] = business_number or fields["business_number"]
    fields["payment_method"] = payment_method or fields["payment_method"]


def _apply_standard_context_amounts(fields: dict[str, Any], context: StandardOCRParserContext) -> None:
    gross_amount = _context_amount(context, "gross_amount")
    discount_amount = _context_amount(context, "discount_amount", discount=True)
    final_amount = _context_amount(context, "final_amount")
    paid_amount = _context_amount(context, "paid_amount")
    total_amount = _context_amount(context, "total_amount")

    if gross_amount is not None:
        fields["gross_amount"] = gross_amount
    if discount_amount is not None:
        fields["discount_amount"] = discount_amount
    if final_amount is not None:
        fields["final_amount"] = final_amount
    if paid_amount is not None:
        fields["paid_amount"] = paid_amount

    gross_minus_discount = None
    if fields["gross_amount"] is not None and fields["discount_amount"] is not None:
        gross_minus_discount = max(fields["gross_amount"] - fields["discount_amount"], 0)

    amount_warnings: list[str] = list(fields.get("amount_warnings", []))
    if fields["discount_amount"] is not None and fields["discount_amount"] > 0:
        amount_warnings.append("discount_detected")
    if (
        fields["discount_amount"] in (None, 0)
        and fields["final_amount"] is not None
        and fields["paid_amount"] is not None
        and fields["paid_amount"] > fields["final_amount"]
        and fields["paid_amount"] - fields["final_amount"] >= 10000
    ):
        fields["final_amount"] = fields["paid_amount"]
        amount_warnings.append("final_amount_replaced_by_paid_amount_candidate")
    if fields["final_amount"] is not None and fields["paid_amount"] is not None and fields["final_amount"] != fields["paid_amount"]:
        amount_warnings.append("final_paid_amount_mismatch")

    if total_amount is not None:
        fields["total_amount"] = total_amount
        fields["amount_source"] = "total_amount"
        if (
            fields["discount_amount"] in (None, 0)
            and fields["paid_amount"] is not None
            and fields["paid_amount"] > fields["total_amount"]
            and fields["paid_amount"] - fields["total_amount"] >= 10000
        ):
            fields["total_amount"] = fields["paid_amount"]
            fields["amount_source"] = "paid_amount_corrected_total"
            amount_warnings.append("total_amount_replaced_by_paid_amount_candidate")
    else:
        chosen_total, amount_source = _choose_total_amount(
            paid_amount=fields["paid_amount"],
            payment_target_amount=None,
            final_amount=fields["final_amount"],
            gross_minus_discount=gross_minus_discount,
            gross_amount=fields["gross_amount"],
        )
        fields["total_amount"] = chosen_total
        fields["amount_source"] = amount_source
        if chosen_total is None:
            amount_warnings.append("amount_source_low_confidence")
    if (
        fields["discount_amount"] in (None, 0)
        and fields["total_amount"] is not None
        and fields["paid_amount"] is not None
        and fields["total_amount"] > fields["paid_amount"] > 0
        and fields["total_amount"] - fields["paid_amount"] >= 100
        and fields["final_amount"] in (None, fields["total_amount"])
    ):
        fields["discount_amount"] = fields["total_amount"] - fields["paid_amount"]
        fields["final_amount"] = fields["paid_amount"]
        amount_warnings.append("discount_inferred_from_total_paid_difference")
        amount_warnings = [
            warning for warning in amount_warnings if warning != "final_paid_amount_mismatch"
        ]

    if fields["total_amount"] == 0 and fields["discount_amount"] is not None and fields["discount_amount"] > 0:
        amount_warnings.append("zero_payment_after_discount")
    fields["amount_warnings"] = _unique(amount_warnings)


def _apply_standard_context_vat(fields: dict[str, Any], context: StandardOCRParserContext) -> None:
    supply_amount = _context_amount(context, "supply_amount")
    vat_amount = _context_amount(context, "vat_amount")
    vat_review_hint = _context_has_vat_review_hint(context)

    if supply_amount is not None:
        fields["supply_amount"] = supply_amount
    if vat_amount is not None:
        fields["vat_amount"] = vat_amount
        fields["estimated_supply_amount"] = None
        fields["estimated_vat_amount"] = None
        fields["vat_source"] = "explicit"
        fields["vat_note"] = "영수증에 부가세가 명시되어 있음"
        fields["vat_review_required"] = bool(vat_review_hint)
        fields["vat_warnings"] = _unique(list(fields.get("vat_warnings", [])) + (["vat_review_hint"] if vat_review_hint else []))
        if supply_amount is not None and supply_amount > 0:
            explicit_tax_total = supply_amount + vat_amount
            amount_warnings = list(fields.get("amount_warnings", []))
            for field_name in ("total_amount", "final_amount", "paid_amount"):
                current_amount = fields.get(field_name)
                if (
                    current_amount is not None
                    and current_amount != explicit_tax_total
                    and abs(current_amount - explicit_tax_total) <= 1000
                    and fields.get("discount_amount") in (None, 0)
                ):
                    fields[field_name] = explicit_tax_total
                    amount_warnings.append(f"{field_name}_replaced_by_explicit_vat_total")
            if fields.get("final_amount") == fields.get("paid_amount"):
                amount_warnings = [
                    warning for warning in amount_warnings if warning != "final_paid_amount_mismatch"
                ]
            fields["amount_warnings"] = _unique(amount_warnings)
        return

    total_amount = fields["total_amount"]
    vat_warnings = list(fields.get("vat_warnings", []))
    if vat_review_hint:
        vat_warnings.append("vat_review_hint")
        vat_warnings.append("vat_not_explicit")
    if total_amount is not None and total_amount > 0:
        if supply_amount is not None and 0 < supply_amount < total_amount:
            supply_difference = total_amount - supply_amount
            if abs(round(supply_amount / 10) - supply_difference) <= 2:
                estimated_supply = supply_amount
                estimated_vat = supply_difference
                vat_warnings.append("vat_estimated_from_supply_difference")
            else:
                estimated_supply, estimated_vat = calculate_estimated_vat_amounts(total_amount)
                fields["supply_amount"] = None
                vat_warnings.append("supply_amount_inconsistent_with_total_ignored")
        else:
            estimated_supply, estimated_vat = calculate_estimated_vat_amounts(total_amount)
        fields["estimated_supply_amount"] = estimated_supply
        fields["estimated_vat_amount"] = estimated_vat
        fields["vat_source"] = "estimated_reference"
        fields["vat_note"] = "부가세 미표기, 참고용 역산값"
        vat_warnings.append("vat_estimated_reference_only")
        fields["vat_review_required"] = True
    elif total_amount == 0:
        fields["estimated_supply_amount"] = None
        fields["estimated_vat_amount"] = None
        fields["vat_source"] = "zero_amount"
        fields["vat_note"] = "총액 0원으로 부가세 참고 추정 생략"
        vat_warnings.append("vat_estimate_skipped_zero_amount")
        fields["vat_review_required"] = bool(vat_review_hint)
    else:
        fields["vat_review_required"] = True
    fields["vat_amount"] = None
    fields["vat_warnings"] = _unique(vat_warnings)


def _standard_context_parser_warnings(
    fields: dict[str, Any],
    context: StandardOCRParserContext,
    sensitive_categories: list[str],
) -> list[str]:
    warnings: list[str] = list(fields.get("parser_warnings", []))
    if context.status != "completed":
        warnings.append(_safe_warning_text(f"ocr_status:{context.status}"))
    if context.diagnostic_code:
        warnings.append(_safe_warning_text(f"diagnostic_code:{context.diagnostic_code}"))
    if fields["transaction_date"] is None:
        warnings.append("date_missing")
    if not fields["merchant_name"]:
        warnings.append("merchant_name_missing_or_low_confidence")
    if fields["total_amount"] is None:
        warnings.append("amount_missing")
    if fields["business_number_candidate"] and fields["business_number"] is None:
        warnings.append("business_number_format_review_required")
    if fields.get("vat_review_required"):
        warnings.append("vat_review_required")
    warnings.extend(fields.get("amount_warnings", []))
    warnings.extend(fields.get("vat_warnings", []))
    warnings.extend(_safe_warning_text(hint) for hint in context.review_hints)
    if sensitive_categories:
        warnings.append("sensitive_text_category_detected")
    return _unique([_safe_warning_text(warning) for warning in warnings])


def _context_amount(context: StandardOCRParserContext, candidate_type: str, *, discount: bool = False) -> int | None:
    value = _first_context_value(context.amount_candidate_map, candidate_type)
    if value is None:
        return None
    if discount:
        return normalize_discount_amount(value)
    return normalize_amount(value)


def _first_context_value(candidate_map: dict[str, list[str]], *candidate_types: str) -> str | None:
    for candidate_type in candidate_types:
        for value in candidate_map.get(candidate_type, []):
            text = str(value or "").strip()
            if text:
                return text
    return None


def _context_has_vat_review_hint(context: StandardOCRParserContext) -> bool:
    if "vat_missing" in context.non_amount_candidate_map or "vat_review_hint" in context.non_amount_candidate_map:
        return True
    return any(
        hint.startswith("vat_missing") or hint.startswith("vat_review_hint")
        for hint in context.review_hints
    )


def _safe_context_categories(categories: list[str]) -> list[str]:
    return _unique([_safe_warning_text(category) for category in categories])


def _safe_warning_text(value: object) -> str:
    text = str(value or "")
    replacements = {
        "api_key": "api-key",
        "operation_location": "operation-location",
        "endpoint": "service-url",
        "password": "credential",
        "secret": "redacted-secret",
        "token": "redacted-token",
    }
    for source, replacement in replacements.items():
        text = re.sub(source, replacement, text, flags=re.IGNORECASE)
    return text


DATE_PATTERN = r"\d{4}[-./]?\d{2}[-./]?\d{2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"
AMOUNT_PATTERN = r"[\-－−–—]?\s*(?:₩\s*)?(?:(?:\d{1,3}(?:(?:\s*[,\.]\s*|\s+)\d{3})+)|\d+)(?:원)?"
OCR_AMOUNT_PATTERN = r"(?<![A-Za-z가-힣])[\-－−–—]?\s*(?:₩\s*)?(?:(?:[0-9OoIl|BSㅇ]{1,3}(?:(?:\s*[,\.]\s*|\s+)[0-9OoIl|BSㅇ]{3})+)|[0-9OoIl|BSㅇ]+)(?:원)?(?![A-Za-z가-힣])"
BUSINESS_NUMBER_PATTERN = r"(?<!\d)\d{3}-?\d{2}-?\d{5}(?!\d)"
BUSINESS_NUMBER_VALUE_PATTERN = r"[0-9-]{8,14}"


def _extract_keyword_value(text: str, keywords: tuple[str, ...], value_pattern: str) -> str | None:
    for keyword in keywords:
        pattern = rf"{re.escape(keyword)}\s*[:：]?\s*({value_pattern})"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _find_business_number_with_context(text: str) -> str | None:
    lines = [line.strip() for line in str(text or "").splitlines()]
    for index, line in enumerate(lines):
        match = re.search(BUSINESS_NUMBER_PATTERN, line)
        if not match:
            continue
        if not _has_valid_business_number_checksum(match.group(0)):
            continue
        nearby_text = " ".join(lines[max(index - 2, 0) : min(index + 3, len(lines))])
        nearby_compact = re.sub(r"\s+", "", nearby_text).upper()
        has_business_evidence = any(
            token in nearby_compact
            for token in ("사업자", "사업자등록", "고유번호", "NO", "N0")
        ) or "[" in nearby_text or "]" in nearby_text
        has_card_evidence = any(
            token in nearby_compact
            for token in ("카드번호", "카드종류", "카드명", "일시불", "승인번호", "POS")
        )
        if "*" in line or has_card_evidence:
            continue
        if has_business_evidence or index <= 10:
            return match.group(0)
    return None


def _has_valid_business_number_checksum(value: str) -> bool:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 10:
        return False
    numbers = [int(char) for char in digits]
    weights = [1, 3, 7, 1, 3, 7, 1, 3]
    checksum_sum = sum(numbers[index] * weights[index] for index in range(8))
    ninth_product = numbers[8] * 5
    checksum_sum += ninth_product // 10 + ninth_product % 10
    return (10 - (checksum_sum % 10)) % 10 == numbers[9]


def _extract_amount_fields(raw_text: str, raw_json: dict[str, Any]) -> dict[str, Any]:
    discount_source_lines = _discount_source_lines(raw_text, raw_json)
    amount_lines = [str(item.get("line") or "") for item in discount_source_lines]
    paid_amount = _first_not_none(
        _first_labeled_amount(
            amount_lines,
            PAID_AMOUNT_LABELS,
            excluded_label_groups=(DISCOUNT_AMOUNT_LABELS, DISCOUNT_TARGET_AMOUNT_LABELS, GROSS_AMOUNT_LABELS, FINAL_AMOUNT_LABELS),
        ),
        _first_amount(
            raw_json,
            ("paid_amount", "received_amount", "card_paid_amount", "cash_paid_amount"),
            raw_text,
            PAID_AMOUNT_KEYWORDS,
        ),
    )
    payment_target_amount = _first_not_none(
        _first_labeled_amount(
            amount_lines,
            PAYMENT_TARGET_AMOUNT_LABELS,
            excluded_label_groups=(DISCOUNT_AMOUNT_LABELS, DISCOUNT_TARGET_AMOUNT_LABELS, GROSS_AMOUNT_LABELS, PAID_AMOUNT_LABELS),
        ),
        _first_amount(
            raw_json,
            ("payment_target_amount", "amount_due"),
            raw_text,
            PAYMENT_TARGET_AMOUNT_KEYWORDS,
        ),
    )
    final_amount = _first_not_none(
        payment_target_amount,
        _first_labeled_amount(
            amount_lines,
            FINAL_AMOUNT_LABELS,
            excluded_label_groups=(DISCOUNT_AMOUNT_LABELS, DISCOUNT_TARGET_AMOUNT_LABELS, GROSS_AMOUNT_LABELS, PAID_AMOUNT_LABELS),
        ),
        _first_amount(raw_json, ("final_amount", "total_after_discount", "total_amount"), raw_text, FINAL_AMOUNT_KEYWORDS),
    )
    gross_amount = _first_not_none(
        _first_labeled_amount(
            amount_lines,
            GROSS_AMOUNT_LABELS,
            excluded_label_groups=(DISCOUNT_AMOUNT_LABELS, DISCOUNT_TARGET_AMOUNT_LABELS, FINAL_AMOUNT_LABELS, PAID_AMOUNT_LABELS),
        ),
        _first_amount(raw_json, ("gross_amount", "subtotal_amount", "line_item_total"), raw_text, GROSS_AMOUNT_KEYWORDS),
        _extract_discount_target_amount(discount_source_lines),
    )
    discount_amount, discount_warnings = _extract_discount_amount(discount_source_lines, raw_json)

    amount_warnings: list[str] = list(discount_warnings)
    paid_amount = _sanitize_paid_amount_candidate(
        paid_amount=paid_amount,
        final_amount=final_amount,
        payment_target_amount=payment_target_amount,
        warnings=amount_warnings,
    )
    explicit_zero_amount = final_amount == 0 or paid_amount == 0
    discount_amount = _sanitize_discount_amount_candidate(
        discount_amount=discount_amount,
        gross_amount=gross_amount,
        final_amount=final_amount,
        paid_amount=paid_amount,
        warnings=amount_warnings,
    )
    if discount_amount is not None and discount_amount > 0:
        amount_warnings.append("discount_detected")
    if (
        gross_amount is not None
        and gross_amount > 0
        and not discount_amount
        and (paid_amount == 0 or (final_amount == 0 and not _has_unclassified_negative_amount(amount_lines)))
    ):
        discount_amount = gross_amount
        amount_warnings.append("discount_inferred_from_zero_payment")

    gross_minus_discount = None
    if gross_amount is not None and discount_amount is not None:
        gross_minus_discount = max(gross_amount - discount_amount, 0)
        if final_amount is None:
            final_amount = gross_minus_discount
            if not explicit_zero_amount:
                amount_warnings.append("gross_total_not_used_due_to_discount")

    total_amount, amount_source = _choose_total_amount(
        paid_amount=paid_amount,
        payment_target_amount=payment_target_amount,
        final_amount=final_amount,
        gross_minus_discount=gross_minus_discount,
        gross_amount=gross_amount,
    )
    if total_amount is None:
        amount_source = "unknown"
        amount_warnings.append("amount_source_low_confidence")
    if total_amount == 0 and discount_amount is not None and discount_amount > 0:
        amount_warnings.append("zero_payment_after_discount")
    if discount_amount is not None and discount_amount > 0 and paid_amount is None and final_amount is None and total_amount == gross_amount:
        total_amount = None
        amount_source = "unknown"
        amount_warnings.append("gross_total_not_used_due_to_discount")
        amount_warnings.append("amount_source_low_confidence")

    return {
        "gross_amount": gross_amount,
        "discount_amount": discount_amount,
        "final_amount": final_amount,
        "paid_amount": paid_amount,
        "total_amount": total_amount,
        "amount_source": amount_source,
        "amount_warnings": _unique(amount_warnings),
    }


def _sanitize_discount_amount_candidate(
    *,
    discount_amount: int | None,
    gross_amount: int | None,
    final_amount: int | None,
    paid_amount: int | None,
    warnings: list[str],
) -> int | None:
    if discount_amount is None:
        return None
    if 1 <= discount_amount <= 9:
        warnings.append("discount_quantity_candidate_ignored")
        return None
    if gross_amount is not None and gross_amount > 0 and discount_amount > gross_amount:
        recalculated = _discount_from_amount_difference(gross_amount, final_amount, paid_amount)
        warnings.append("discount_amount_suspicious")
        warnings.append("discount_identifier_candidate_ignored")
        if recalculated is not None:
            warnings.append("discount_recalculated_from_gross_and_final")
            return recalculated
        return None
    return discount_amount


def _sanitize_paid_amount_candidate(
    *,
    paid_amount: int | None,
    final_amount: int | None,
    payment_target_amount: int | None,
    warnings: list[str],
) -> int | None:
    if paid_amount is None:
        return None
    if 1 <= abs(paid_amount) <= 9:
        warnings.append("paid_amount_quantity_candidate_ignored")
        return None

    expected_amount = _first_not_none(payment_target_amount, final_amount)
    if expected_amount is None or expected_amount <= 0 or paid_amount == expected_amount:
        return paid_amount

    if paid_amount <= 0:
        warnings.append("paid_amount_mismatch_ignored")
        return None
    if paid_amount < 10000 <= expected_amount:
        warnings.append("paid_amount_low_confidence_ignored")
        return None
    if paid_amount < expected_amount and (expected_amount - paid_amount) >= max(10000, expected_amount // 2):
        warnings.append("paid_amount_low_confidence_ignored")
        return None
    return paid_amount


def _discount_from_amount_difference(
    gross_amount: int,
    final_amount: int | None,
    paid_amount: int | None,
) -> int | None:
    for basis in (final_amount, paid_amount):
        if basis is None:
            continue
        difference = gross_amount - basis
        if 0 < difference <= gross_amount:
            return difference
    return None


def _extract_vat_fields(raw_text: str, raw_json: dict[str, Any], total_amount: int | None) -> dict[str, Any]:
    supply_amount = _first_explicit_amount(raw_json, ("supply_amount",), raw_text, SUPPLY_AMOUNT_KEYWORDS)
    vat_amount = _first_explicit_amount(raw_json, ("vat_amount",), raw_text, VAT_KEYWORDS)

    if vat_amount is not None:
        return {
            "supply_amount": supply_amount,
            "vat_amount": vat_amount,
            "estimated_supply_amount": None,
            "estimated_vat_amount": None,
            "vat_source": "explicit",
            "vat_note": "영수증에 부가세가 명시되어 있음",
            "vat_warnings": [],
            "vat_review_required": False,
        }

    warnings = ["vat_not_explicit"]
    if total_amount is not None and total_amount > 0:
        estimated_supply, estimated_vat = calculate_estimated_vat_amounts(total_amount)
        warnings.append("vat_estimated_reference_only")
        return {
            "supply_amount": supply_amount,
            "vat_amount": None,
            "estimated_supply_amount": estimated_supply,
            "estimated_vat_amount": estimated_vat,
            "vat_source": "estimated_reference",
            "vat_note": "부가세 미표기, 참고용 역산값",
            "vat_warnings": warnings,
            "vat_review_required": True,
        }

    if total_amount == 0:
        warnings.append("vat_estimate_skipped_zero_amount")
        return {
            "supply_amount": supply_amount,
            "vat_amount": None,
            "estimated_supply_amount": None,
            "estimated_vat_amount": None,
            "vat_source": "zero_amount",
            "vat_note": "결제금액 0원으로 참고 추정값 미계산",
            "vat_warnings": warnings,
            "vat_review_required": False,
        }

    return {
        "supply_amount": supply_amount,
        "vat_amount": None,
        "estimated_supply_amount": None,
        "estimated_vat_amount": None,
        "vat_source": "missing",
        "vat_note": "부가세 미표기, 금액 확인 필요",
        "vat_warnings": warnings,
        "vat_review_required": True,
    }


def _first_explicit_amount(
    raw_json: dict[str, Any],
    json_keys: tuple[str, ...],
    raw_text: str,
    text_keywords: tuple[str, ...],
) -> int | None:
    return _first_amount(raw_json, json_keys, raw_text, text_keywords)


def _first_amount(
    raw_json: dict[str, Any],
    json_keys: tuple[str, ...],
    raw_text: str,
    text_keywords: tuple[str, ...],
) -> int | None:
    for key in json_keys:
        amount = normalize_amount(raw_json.get(key))
        if amount is not None:
            return amount
    return normalize_amount(_extract_keyword_value(raw_text, text_keywords, AMOUNT_PATTERN))


def _first_labeled_amount(
    lines: list[str],
    labels: tuple[str, ...],
    *,
    excluded_label_groups: tuple[tuple[str, ...], ...] = (),
) -> int | None:
    for index, line in enumerate(lines):
        if any(_classify_amount_label(line, excluded)["label_match_method"] != "none" for excluded in excluded_label_groups):
            continue
        label_info = _classify_amount_label(line, labels)
        if label_info["label_match_method"] == "none":
            continue
        if _is_amount_reference_label_line(line):
            continue
        amount, _ = _extract_signed_labeled_line_amount(lines, index)
        if amount is not None:
            return amount
    return None


def _classify_amount_label(line: str, labels: tuple[str, ...]) -> dict[str, object]:
    compact = _compact_label_part(line)
    if len(compact) < 2 or not any(character.isalpha() or "가" <= character <= "힣" for character in compact):
        return {"label_match_method": "none", "score": 0.0}
    if any(compact.startswith(label) for label in labels):
        return {"label_match_method": "compact", "score": 1.0}
    score = _best_label_score(compact, labels)
    if score >= AMOUNT_LABEL_FUZZY_THRESHOLD:
        return {"label_match_method": "fuzzy", "score": score}
    return {"label_match_method": "none", "score": score}


def _is_amount_reference_label_line(line: str) -> bool:
    if _find_line_amount_token(line) is not None:
        return False
    compact = _compact_amount_label(line)
    if not compact:
        return False
    reference_markers = ("기준", "안내", "적립", "포인트", "증정")
    return any(label in compact for label in PAID_AMOUNT_LABELS) and any(marker in compact for marker in reference_markers)


def classify_discount_label(line: str) -> dict[str, object]:
    compact = _compact_label_part(line)
    if len(compact) < 3 or not any(character.isalpha() or "가" <= character <= "힣" for character in compact):
        return {"line_type": "unknown", "label_match_method": "none", "score": 0.0}
    if any(compact.startswith(label) for label in NON_DISCOUNT_AMOUNT_LABELS):
        return {"line_type": "unknown", "label_match_method": "none", "score": 0.0}
    if any(compact.startswith(label) for label in DISCOUNT_TARGET_AMOUNT_LABELS):
        return {"line_type": "discount_target", "label_match_method": "compact", "score": 1.0}
    if any(compact.startswith(label) for label in DISCOUNT_SUMMARY_LABELS):
        return {"line_type": "discount_summary", "label_match_method": "compact", "score": 1.0}

    target_score = _best_label_score(compact, DISCOUNT_TARGET_AMOUNT_LABELS)
    summary_score = _best_label_score(compact, DISCOUNT_SUMMARY_LABELS)
    if target_score < DISCOUNT_FUZZY_THRESHOLD and summary_score < DISCOUNT_FUZZY_THRESHOLD:
        return {"line_type": "unknown", "label_match_method": "none", "score": max(target_score, summary_score)}
    if target_score >= summary_score - DISCOUNT_FUZZY_MARGIN:
        return {"line_type": "discount_target", "label_match_method": "fuzzy", "score": target_score}
    return {"line_type": "discount_summary", "label_match_method": "fuzzy", "score": summary_score}


def _best_label_score(value: str, labels: tuple[str, ...]) -> float:
    scores: list[float] = []
    for label in labels:
        if len(value) < 3 or len(label) < 3:
            continue
        prefix = value[: max(len(label), min(len(value), len(label) + 2))]
        scores.append(SequenceMatcher(None, prefix, label).ratio())
    return max(scores, default=0.0)


def _discount_source_lines(raw_text: str, raw_json: dict[str, Any]) -> list[dict[str, Any]]:
    lines = []
    for row in _columnar_amount_rows(raw_text):
        normalized_row = normalize_merchant_name(row)
        if normalized_row:
            lines.append({"source": "text_column_pair", "line": normalized_row})
    lines.extend(
        {"source": "text_line", "line": normalize_merchant_name(line) or ""}
        for line in (raw_text or "").splitlines()
        if normalize_merchant_name(line)
    )
    for row in _raw_json_table_rows(raw_json):
        safe_row = sanitize_lines_for_parsing(row)
        normalized_row = normalize_merchant_name(safe_row)
        if normalized_row:
            lines.append({"source": "raw_json_table", "line": normalized_row})
    return lines


def _columnar_amount_rows(raw_text: str) -> list[str]:
    lines = [normalize_merchant_name(line) or "" for line in (raw_text or "").splitlines()]
    lines = [line for line in lines if line]
    rows: list[str] = []
    index = 0
    while index < len(lines):
        label_lines: list[str] = []
        label_index = index
        while label_index < len(lines) and _is_amount_label_without_inline_amount(lines[label_index]):
            label_lines.append(lines[label_index])
            label_index += 1

        if len(label_lines) < 2:
            index += 1
            continue

        amount_lines: list[str] = []
        amount_index = label_index
        while amount_index < len(lines) and len(amount_lines) < len(label_lines):
            if not _is_amount_only_line(lines[amount_index]):
                break
            amount_lines.append(lines[amount_index])
            amount_index += 1

        if len(amount_lines) >= 2:
            rows.extend(f"{label} {amount}" for label, amount in zip(label_lines, amount_lines))
            index = amount_index
            continue

        index += 1
    return rows


def _is_amount_label_without_inline_amount(line: str) -> bool:
    if _find_line_amount_token(line):
        return False
    return _has_amount_label(line)


def _raw_json_table_rows(raw_json: dict[str, Any]) -> list[str]:
    tables = _collect_table_objects(raw_json)
    rows: list[str] = []
    for table in tables:
        cells = table.get("cells")
        if not isinstance(cells, list):
            continue
        grouped: dict[int, list[tuple[int, str]]] = {}
        for cell in cells:
            if not isinstance(cell, dict):
                continue
            row_index = _int_or_none(_first_present(cell, "rowIndex", "row_index"))
            column_index = _int_or_none(_first_present(cell, "columnIndex", "column_index"))
            text = _raw_json_field_value(cell)
            if row_index is None or column_index is None or not text:
                continue
            grouped.setdefault(row_index, []).append((column_index, text))
        for row_index in sorted(grouped):
            row_parts = [text for _, text in sorted(grouped[row_index], key=lambda item: item[0]) if text]
            if row_parts:
                rows.append(" ".join(row_parts))
    return rows


def _collect_table_objects(value: Any) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if isinstance(value.get("tables"), list):
            tables.extend(item for item in value["tables"] if isinstance(item, dict))
        for nested_value in value.values():
            tables.extend(_collect_table_objects(nested_value))
    elif isinstance(value, list):
        for item in value:
            tables.extend(_collect_table_objects(item))
    return tables


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_present(data: dict[str, Any], *keys: str) -> object:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _extract_discount_amount(source_lines: list[dict[str, Any]], raw_json: dict[str, Any]) -> tuple[int | None, list[str]]:
    summary_amounts: list[int] = []
    item_amounts: list[int] = []
    warnings: list[str] = []
    lines = [str(item.get("line") or "") for item in source_lines]
    has_discount_table_header = _has_discount_table_header(lines)
    if has_discount_table_header:
        warnings.append("discount_table_header_detected")
    seen_summary_amounts: set[int] = set()
    for key in ("discount_amount", "discount", "coupon_amount", "point_used_amount"):
        amount = normalize_discount_amount(raw_json.get(key))
        if amount is not None:
            summary_amounts.append(amount)
            seen_summary_amounts.add(amount)
    for index, normalized_line in enumerate(lines):
        if _is_discount_table_header_line(normalized_line):
            continue
        label_info = classify_discount_label(normalized_line)
        if label_info["line_type"] == "discount_target":
            amount, _ = _extract_labeled_line_amount(lines, index)
            if amount is not None:
                warnings.append("discount_target_amount_not_discount")
            continue
        amount, from_next_line, match_method = _extract_discount_summary_amount(lines, index)
        if amount is not None:
            if amount in seen_summary_amounts:
                warnings.append("discount_candidate_duplicate_ignored")
                continue
            summary_amounts.append(amount)
            seen_summary_amounts.add(amount)
            if from_next_line:
                warnings.append("discount_amount_from_next_line")
            if match_method == "fuzzy":
                warnings.append("discount_label_fuzzy_matched")
            continue
        amount = _extract_discount_item_amount(normalized_line, has_discount_table_header)
        if amount is not None:
            item_amounts.append(amount)
            warnings.append("item_level_discount_detected")

    if summary_amounts:
        if item_amounts:
            warnings.append("discount_summary_preferred")
            warnings.append("discount_candidate_duplicate_ignored")
        return _sum_unique_amounts(summary_amounts), _unique(warnings)
    if item_amounts:
        unique_item_amounts = _unique_numbers(item_amounts)
        if len(unique_item_amounts) < len(item_amounts):
            warnings.append("discount_candidate_duplicate_ignored")
        return sum(unique_item_amounts), _unique(warnings)
    return None, _unique(warnings)


def _extract_discount_target_amount(source_lines: list[dict[str, Any]]) -> int | None:
    lines = [str(item.get("line") or "") for item in source_lines]
    for index, line in enumerate(lines):
        if not _is_discount_target_amount_line(line):
            continue
        amount, _ = _extract_labeled_line_amount(lines, index)
        if amount is not None:
            return amount
    return None


def _is_discount_target_amount_line(line: str) -> bool:
    return classify_discount_label(line)["line_type"] == "discount_target"


def _extract_discount_summary_amount(lines: list[str], index: int) -> tuple[int | None, bool, str]:
    line = lines[index]
    if _is_discount_table_header_line(line):
        return None, False, "none"
    label_info = classify_discount_label(line)
    if label_info["line_type"] != "discount_summary":
        return None, False, "none"
    amount, from_next_line = _extract_labeled_line_amount(lines, index)
    return amount, from_next_line, str(label_info["label_match_method"])


def _extract_discount_item_amount(line: str, discount_table_context: bool = False) -> int | None:
    if classify_discount_label(line)["line_type"] == "discount_summary":
        amount = normalize_discount_amount(_extract_line_amount(line))
        if amount is not None:
            return amount
    for value in _extract_keyword_values(line, DISCOUNT_AMOUNT_KEYWORDS, AMOUNT_PATTERN):
        amount = normalize_discount_amount(value)
        if amount is not None:
            return amount
    amount = normalize_amount(_extract_line_amount(line))
    if amount is not None and amount < 0 and any(keyword in line for keyword in DISCOUNT_LINE_HINT_KEYWORDS):
        return abs(amount)
    if (
        discount_table_context
        and amount is not None
        and amount > 0
        and any(keyword in line for keyword in DISCOUNT_LINE_HINT_KEYWORDS)
    ):
        return amount
    return None


def _has_discount_table_header(lines: list[str]) -> bool:
    return any(
        _is_discount_table_header_line(line)
        for line in lines
    )


def _is_discount_table_header_line(line: str) -> bool:
    text = str(line or "").strip()
    compact = _compact_amount_label(text)
    if not compact:
        return False
    if "할인내역" in compact:
        return True
    if "제품명" in compact and "수량" in compact and "금액" in compact:
        return True
    if "수량" in compact and "금액" in compact and "할인금액" in compact:
        return True
    if "금액" in compact and "할인금액" in compact and _has_parenthesized_discount_label(text):
        return True
    if compact == "할인금액" and _has_parenthesized_discount_label(text):
        return True
    return False


def _has_parenthesized_discount_label(line: str) -> bool:
    return bool(re.search(r"[\(\[]\s*할\s*인\s*금\s*액\s*[\)\]]", line or ""))


def _has_unclassified_negative_amount(lines: list[str]) -> bool:
    for line in lines:
        amount = normalize_amount(_extract_line_amount(line))
        if amount is None or amount >= 0:
            continue
        label_type = classify_discount_label(line)["line_type"]
        if label_type in {"discount_summary", "discount_target"}:
            continue
        if any(keyword in line for keyword in DISCOUNT_LINE_HINT_KEYWORDS):
            continue
        return True
    return False


def _extract_labeled_line_amount(lines: list[str], index: int) -> tuple[int | None, bool]:
    amount = normalize_discount_amount(_extract_line_amount(lines[index]))
    if amount is not None:
        return amount, False
    for next_index in range(index + 1, min(index + 3, len(lines))):
        next_line = lines[next_index]
        if _is_amount_only_line(next_line):
            return normalize_discount_amount(next_line), True
        if _has_amount_label(next_line):
            break
    return None, False


def _extract_signed_labeled_line_amount(lines: list[str], index: int) -> tuple[int | None, bool]:
    amount = normalize_amount(_extract_line_amount(lines[index]))
    if amount is not None:
        return amount, False
    for next_index in range(index + 1, min(index + 3, len(lines))):
        next_line = lines[next_index]
        if _is_amount_only_line(next_line):
            return normalize_amount(_extract_line_amount(next_line)), True
        if _has_amount_label(next_line):
            break
    return None, False


def _is_amount_only_line(line: str) -> bool:
    if normalize_amount(line) is None:
        amount = normalize_amount(_extract_line_amount(line))
        if amount is None:
            return False
    return bool(re.fullmatch(rf"\s*{OCR_AMOUNT_PATTERN}\s*", line or "", flags=re.IGNORECASE))


def _has_amount_label(line: str) -> bool:
    label_groups = (
        DISCOUNT_AMOUNT_LABELS,
        DISCOUNT_TARGET_AMOUNT_LABELS,
        GROSS_AMOUNT_LABELS,
        FINAL_AMOUNT_LABELS,
        PAID_AMOUNT_LABELS,
        PAYMENT_TARGET_AMOUNT_LABELS,
    )
    return any(_starts_with_compact_label(line, labels) for labels in label_groups)


def _starts_with_compact_label(line: str, labels: tuple[str, ...]) -> bool:
    compact = _compact_label_part(line)
    return any(compact.startswith(label) for label in labels)


def _extract_line_amount(line: str) -> str | None:
    token = _find_line_amount_token(line)
    if not token:
        return None
    return _normalize_ocr_amount_token(token)


def _find_line_amount_token(line: str) -> str | None:
    matches = list(re.finditer(OCR_AMOUNT_PATTERN, line or "", flags=re.IGNORECASE))
    if not matches:
        return None
    for match in reversed(matches):
        token = _normalize_ocr_amount_token(match.group(0))
        amount = normalize_amount(token)
        if token is None or amount is None:
            continue
        if _amount_candidate_ignored_reason(line, match.group(0), match.start(), amount) != "none":
            continue
        return token
    return None


def _amount_candidate_ignored_reason(line: str, token: str | None, start: int | None = None, amount: int | None = None) -> str:
    normalized_token = _normalize_ocr_amount_token(token)
    normalized_amount = normalize_amount(normalized_token) if amount is None else amount
    if normalized_token is None or normalized_amount is None:
        return "no_amount"
    compact = _compact_amount_label(line)
    digits = re.sub(r"\D", "", normalized_token)
    stripped = str(token or "").strip()
    has_group_separator = bool(re.search(r"\d\s*[,\.]\s*\d|\d\s+\d", stripped))
    label_groups = (
        DISCOUNT_AMOUNT_LABELS,
        DISCOUNT_TARGET_AMOUNT_LABELS,
        GROSS_AMOUNT_LABELS,
        FINAL_AMOUNT_LABELS,
        PAID_AMOUNT_LABELS,
        PAYMENT_TARGET_AMOUNT_LABELS,
    )
    has_amount_label = any(any(compact.startswith(label) for label in labels) for labels in label_groups)
    has_discount_label = any(label and label in compact for label in DISCOUNT_SUMMARY_LABELS)
    if 1 <= abs(normalized_amount) <= 9:
        return "quantity_candidate"
    if _is_identifier_amount_line(compact):
        if has_discount_label and start is not None and start > _discount_label_start(line):
            return "none"
        return "approval_number_candidate"
    if any(compact.startswith(label) for label in PAYMENT_IDENTIFIER_LABELS) and not has_amount_label:
        return "approval_number_candidate"
    if len(digits) >= 8 and not has_group_separator:
        return "long_number_candidate"
    return "none"


def _is_identifier_amount_line(compact_line: str) -> bool:
    return any(label and label in compact_line for label in IDENTIFIER_AMOUNT_LABELS)


def _discount_label_start(line: str) -> int:
    compact_line = _compact_amount_label(line)
    positions = [compact_line.find(label) for label in DISCOUNT_SUMMARY_LABELS if label and label in compact_line]
    return min(positions) if positions else len(compact_line)


def _find_any_line_amount_token(line: str) -> str | None:
    matches = re.findall(OCR_AMOUNT_PATTERN, line or "", flags=re.IGNORECASE)
    if not matches:
        return None
    return matches[-1].strip()


def _normalize_ocr_amount_token(value: object) -> str | None:
    text = str(value or "").strip()
    if not text or len(text) > 32:
        return None
    if not re.fullmatch(r"[\s\-－−–—₩원,.()0-9OoIl|BSㅇ]+", text):
        return None
    translate = str.maketrans({"O": "0", "o": "0", "ㅇ": "0", "I": "1", "l": "1", "|": "1", "B": "8", "S": "5"})
    return text.translate(translate)


def _compact_label_part(line: str) -> str:
    amount_token = _find_line_amount_token(line)
    label_part = line
    if amount_token:
        match = re.search(OCR_AMOUNT_PATTERN, line or "", flags=re.IGNORECASE)
        if match:
            label_part = line[: match.start()]
    return _compact_amount_label(label_part)


def diagnose_discount_lines(raw_text: str, raw_json: dict[str, Any] | None = None) -> list[dict[str, object]]:
    return build_receipt_amount_diagnostics(raw_text, raw_json)


def build_receipt_amount_diagnostics(raw_text: str, raw_json: dict[str, Any] | None = None) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    source_lines = _discount_source_lines(sanitize_lines_for_parsing(raw_text), raw_json or {})
    for index, item in enumerate(source_lines):
        line = str(item.get("line") or "")
        label_info = classify_discount_label(line)
        amount_token = _find_any_line_amount_token(line)
        amount = normalize_discount_amount(_extract_line_amount(line))
        line_type = _diagnostic_line_type(line, str(label_info["line_type"]))
        ignored_reason = "none"
        used_for_discount = False
        used_for_total = False
        if line_type == "discount_target":
            ignored_reason = "target_amount"
        elif line_type in {"discount_summary", "item_level_discount"} and amount is not None:
            used_for_discount = True
        elif line_type in {"final_amount", "paid_amount"} and amount is not None:
            used_for_total = True
        elif amount is None:
            ignored_reason = _amount_candidate_ignored_reason(line, amount_token)
        diagnostics.append(
            {
                "source": item.get("source") or "text_line",
                "line_index": index,
                "line_type": line_type,
                "label_matched": line_type in {"discount_summary", "discount_target"},
                "label_match_method": label_info["label_match_method"],
                "amount_detected": amount is not None,
                "amount_shape": _amount_shape(amount_token),
                "used_for_discount": used_for_discount,
                "used_for_total": used_for_total,
                "ignored_reason": ignored_reason,
            }
        )
    return diagnostics


def _diagnostic_line_type(line: str, discount_line_type: str) -> str:
    if _is_discount_table_header_line(line):
        return "discount_table_header"
    if discount_line_type in {"discount_summary", "discount_target"}:
        return discount_line_type
    if _classify_amount_label(line, GROSS_AMOUNT_LABELS)["label_match_method"] != "none":
        return "gross_amount"
    if _classify_amount_label(line, FINAL_AMOUNT_LABELS)["label_match_method"] != "none":
        return "final_amount"
    if _classify_amount_label(line, PAID_AMOUNT_LABELS)["label_match_method"] != "none":
        return "paid_amount"
    amount = normalize_amount(_extract_line_amount(line))
    if amount is not None and any(keyword in line for keyword in DISCOUNT_LINE_HINT_KEYWORDS):
        return "item_level_discount"
    if amount is not None:
        return "amount_candidate"
    return "unknown"


def _amount_shape(token: str | None) -> str:
    if not token:
        return "none"
    normalized = normalize_amount(_normalize_ocr_amount_token(token))
    if normalized == 0 and re.search(r"[Ooㅇ]", token):
        return "zero_ocr_corrected"
    if normalized == 0:
        return "zero"
    if token.strip().startswith(("-", "－", "−", "–", "—")):
        return "negative_amount"
    if re.search(r"[OoIl|BS]", token):
        return "ocr_corrected_amount"
    if "." in token:
        return "dot_amount"
    if re.search(r"\d,\s+\d", token) or re.search(r"\d\s+\d", token):
        return "spaced_amount"
    if "," in token:
        return "comma_amount"
    return "plain_amount"


def _sum_unique_amounts(amounts: list[int]) -> int | None:
    unique_amounts = _unique_numbers(amounts)
    return sum(unique_amounts) if unique_amounts else None


def _unique_numbers(values: list[int]) -> list[int]:
    result: list[int] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _extract_keyword_values(text: str, keywords: tuple[str, ...], value_pattern: str) -> list[str]:
    values: list[str] = []
    for line in (text or "").splitlines():
        for keyword in keywords:
            pattern = rf"{re.escape(keyword)}\s*[:：]?\s*({value_pattern})"
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                values.append(match.group(1).strip())
                break
    return values


def _choose_total_amount(
    *,
    paid_amount: int | None,
    payment_target_amount: int | None,
    final_amount: int | None,
    gross_minus_discount: int | None,
    gross_amount: int | None,
) -> tuple[int | None, str]:
    if paid_amount is not None:
        return paid_amount, "paid_amount"
    if payment_target_amount is not None:
        return payment_target_amount, "payment_target_amount"
    if final_amount is not None:
        return final_amount, "final_amount"
    if gross_minus_discount is not None:
        return gross_minus_discount, "gross_minus_discount"
    if gross_amount is not None:
        return gross_amount, "line_item_total"
    return None, "unknown"


def _first_not_none(*values: int | None) -> int | None:
    for value in values:
        if value is not None:
            return value
    return None


def _find_first(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(0).strip()


def _detect_sensitive_inputs(raw_text: str, raw_json: dict[str, Any] | None):
    text_detection = detect_sensitive_text(raw_text)
    json_detection = detect_sensitive_text(_json_scalar_text(raw_json or {}))
    categories = _unique([*text_detection.categories, *json_detection.categories])
    warnings = _unique([*text_detection.warnings, *json_detection.warnings])
    return type(text_detection)(detected=bool(categories), categories=categories, warnings=warnings)


def _json_scalar_text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(_json_scalar_text(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(_json_scalar_text(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _extract_merchant_name(
    raw_text: str,
    raw_json: dict[str, Any],
    business_number: str | None,
) -> tuple[str | None, list[str]]:
    merchant_from_json = _merchant_from_json(raw_json)
    if _is_usable_merchant_candidate(merchant_from_json):
        return normalize_merchant_name(merchant_from_json), []

    merchant_from_business_number = find_merchant_by_business_number(business_number)
    if merchant_from_business_number:
        return merchant_from_business_number, []

    merchant_from_labeled_text = _merchant_from_labeled_text(raw_text)
    if _is_usable_merchant_candidate(merchant_from_labeled_text):
        return normalize_merchant_name(merchant_from_labeled_text), []

    merchant_from_context, context_warning = _merchant_from_receipt_context(raw_text)
    if _is_usable_merchant_candidate(merchant_from_context):
        warnings = [context_warning] if context_warning else []
        return normalize_merchant_name(merchant_from_context), warnings

    return None, []


def _should_prefer_business_number_merchant(
    current_merchant: str | None,
    business_number_merchant: str | None,
) -> bool:
    if not business_number_merchant:
        return False
    if not current_merchant:
        return True
    current_compact = re.sub(r"[^0-9A-Za-z가-힣]", "", current_merchant).lower()
    dictionary_compact = re.sub(r"[^0-9A-Za-z가-힣]", "", business_number_merchant).lower()
    if not current_compact:
        return True
    if not re.search(r"[가-힣]", current_merchant):
        return True
    return current_compact in dictionary_compact or dictionary_compact in current_compact


def _merchant_from_json(raw_json: dict[str, Any]) -> str | None:
    return _find_merchant_value_in_json(raw_json)


def _find_merchant_value_in_json(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in MERCHANT_JSON_KEYS:
            if key in value:
                candidate = _raw_json_field_value(value[key])
                if candidate:
                    return candidate
        for nested_value in value.values():
            candidate = _find_merchant_value_in_json(nested_value)
            if candidate:
                return candidate
    if isinstance(value, list):
        for item in value:
            candidate = _find_merchant_value_in_json(item)
            if candidate:
                return candidate
    return None


def _raw_json_field_value(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("value", "valueString", "content", "text"):
            if value.get(key):
                return str(value[key])
        value_currency = value.get("valueCurrency")
        if isinstance(value_currency, dict) and value_currency.get("amount") is not None:
            return str(value_currency["amount"])
        return None
    if value is not None and value != "":
        return str(value)
    return None


def _merchant_from_labeled_text(raw_text: str) -> str | None:
    for line in raw_text.splitlines():
        candidate = normalize_merchant_name(line)
        labeled = _merchant_from_labeled_line(candidate or "")
        if _is_usable_merchant_candidate(labeled):
            return labeled
    return None


def _merchant_from_receipt_context(raw_text: str) -> tuple[str | None, str | None]:
    lines = [normalize_merchant_name(line) for line in raw_text.splitlines()]
    clean_lines = [line for line in lines if line]
    for index, line in enumerate(clean_lines):
        if not any(keyword in line for keyword in MERCHANT_CONTEXT_KEYWORDS):
            continue
        for neighbor_index in (index - 2, index - 1, index + 1):
            if neighbor_index < 0 or neighbor_index >= len(clean_lines):
                continue
            candidate = clean_lines[neighbor_index]
            if not _is_usable_merchant_candidate(candidate):
                continue
            if _has_business_keyword(candidate):
                return candidate, None
            return candidate, "merchant_name_low_confidence"

    for line in clean_lines[:8]:
        if not _is_usable_merchant_candidate(line):
            continue
        if _has_business_keyword(line):
            return line, None
    return None, None


def _merchant_from_labeled_line(line: str) -> str | None:
    match = re.match(rf"(?:{'|'.join(MERCHANT_LABEL_KEYWORDS)})\s*[:：]\s*(.+)", line)
    if not match:
        return None
    return normalize_merchant_name(match.group(1))


def _is_usable_merchant_candidate(value: str | None) -> bool:
    candidate = normalize_merchant_name(value)
    if not candidate:
        return False
    if detect_sensitive_text(candidate).detected:
        return False
    if is_overlay_text(candidate):
        return False
    if is_product_line_text(candidate):
        return False
    if is_receipt_metadata_line(candidate):
        return False
    compact = re.sub(r"\s+", "", candidate)
    if compact.startswith(("대표", "대표자", "주소", "TEL", "Tel", "tel", "전화")):
        return False
    return True


def is_valid_merchant_candidate(value: str | None) -> bool:
    return _is_usable_merchant_candidate(value)


def _has_business_keyword(value: str) -> bool:
    normalized = normalize_merchant_name(value) or ""
    return any(keyword.lower() in normalized.lower() for keyword in MERCHANT_BUSINESS_KEYWORDS)


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


def _evidence_type_for_source_file(source_file_name: str, has_text: bool) -> str:
    suffix = Path(source_file_name).suffix.lower()
    if suffix == ".pdf":
        return EvidenceType.RECEIPT_PDF.value
    if suffix in {".jpg", ".jpeg", ".png"}:
        return EvidenceType.RECEIPT_IMAGE.value
    if has_text:
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


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


parse_date = normalize_date
parse_amount = normalize_amount
clean_text = normalize_merchant_name
normalize_business_number_for_receipt = normalize_business_number

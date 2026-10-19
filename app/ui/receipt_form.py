"""One receipt review form; OCR/provider metadata stays outside editable fields."""

from dataclasses import replace
import re
from typing import Any

import streamlit as st

from app.core.receipt_models import ReceiptRecord
from app.parser.normalizers import normalize_business_number, normalize_date, normalize_optional_text
from app.ui.review_utils import (
    REVIEW_STATUS_OPTIONS, format_display_amount, map_review_label_to_status, map_review_status_to_label,
)


AMOUNT_FIELDS = (
    ("discount_amount", "할인금액"), ("total_amount", "최종결제금액"),
    ("supply_amount", "공급가액"), ("vat_amount", "부가세"),
)


def parse_review_amount(value: object) -> int | None:
    text = "" if value is None else str(value).strip()
    if text in {"", "—"}:
        return None
    if not re.fullmatch(r"-?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)", text):
        raise ValueError("금액은 정수와 천 단위 콤마로 입력해 주세요.")
    amount = int(text.replace(",", ""))
    if abs(amount) > 2**53 - 1:
        raise ValueError("금액이 안전하게 입력할 수 있는 범위를 넘었습니다.")
    return amount


def receipt_form_values(record: ReceiptRecord) -> dict[str, Any]:
    return {
        "transaction_date": record.transaction_date,
        "merchant_name": record.merchant_name or "",
        "business_number": record.business_number or "",
        "payment_method": record.payment_method or "",
        "expense_category": record.expense_category or "",
        "review_status": map_review_status_to_label(record.review_status),
        "user_note": record.user_note or "",
        **{field: format_display_amount(getattr(record, field), suffix="", missing="") for field, _ in AMOUNT_FIELDS},
    }


def _remember_input(receipt_id: str, field: str, key: str) -> None:
    value = st.session_state[key]
    if field in dict(AMOUNT_FIELDS):
        try:
            value = format_display_amount(parse_review_amount(value), suffix="", missing="")
            st.session_state[key] = value
        except ValueError:
            pass  # Keep invalid input visible; saving will reject it.
    st.session_state["receipt_review_drafts"][receipt_id][field] = value


def clear_receipt_draft(receipt_id: str) -> None:
    st.session_state.get("receipt_review_drafts", {}).pop(receipt_id, None)
    st.session_state["receipt_review_reset_draft"] = receipt_id


def apply_receipt_form(record: ReceiptRecord, values: dict[str, Any]) -> ReceiptRecord:
    """Change only reviewed fields, preserving identity and other receipts' metadata."""
    status = map_review_label_to_status(values["review_status"])
    updated = replace(
        record,
        transaction_date=normalize_date(values["transaction_date"]),
        merchant_name=normalize_optional_text(values["merchant_name"]),
        business_number=normalize_business_number(values["business_number"]),
        discount_amount=parse_review_amount(values["discount_amount"]),
        supply_amount=parse_review_amount(values["supply_amount"]),
        vat_amount=parse_review_amount(values["vat_amount"]),
        total_amount=parse_review_amount(values["total_amount"]),
        payment_method=normalize_optional_text(values["payment_method"]),
        expense_category=normalize_optional_text(values.get("expense_category", record.expense_category)),
        user_note=normalize_optional_text(values["user_note"]),
        review_status=status,
        export_included=status != "excluded",
        estimated_supply_amount=None,
        estimated_vat_amount=None,
    )
    if updated.total_amount != record.total_amount:
        updated = replace(updated, final_amount=updated.total_amount)
    if (updated.supply_amount, updated.vat_amount) != (record.supply_amount, record.vat_amount):
        updated = replace(
            updated, vat_source="reviewed" if updated.vat_amount is not None else "missing",
            vat_review_required=updated.vat_amount is None,
            vat_warnings=[] if updated.vat_amount is not None else ["vat_not_explicit"],
            vat_note=None,
        )
    return updated


def render_receipt_form(record: ReceiptRecord) -> dict[str, Any]:
    st.caption("표준 영수증 · 원본과 비교하여 확인해 주세요")
    st.caption("빈칸은 확인되지 않은 값입니다. 공급가액·부가세를 자동 계산하지 않습니다.")
    duplicate = bool(record.duplicate_group_id or record.duplicate_candidate_ids or record.duplicate_reason)
    st.caption("중복의심: " + ("Y · 비교 후 포함 여부를 선택해 주세요" if duplicate else "—"))
    drafts = st.session_state.setdefault("receipt_review_drafts", {})
    draft = drafts.setdefault(record.id, receipt_form_values(record))
    if st.session_state.get("receipt_review_form_active_id") != record.id or st.session_state.get("receipt_review_reset_draft") == record.id:
        for field in draft:
            st.session_state[f"receipt_input_{record.id}_{field}"] = draft[field]
        st.session_state["receipt_review_form_active_id"] = record.id
        st.session_state.pop("receipt_review_reset_draft", None)
    fields = (
        ("transaction_date", "사용일자"), ("merchant_name", "상호"),
        ("business_number", "사업자번호"), ("payment_method", "결제수단"),
        *AMOUNT_FIELDS, ("expense_category", "비용항목 (추천 · 선택)"), ("review_status", "검수상태"),
    )
    for offset in range(0, len(fields), 2):
        columns = st.columns(2)
        for column, (field, label) in zip(columns, fields[offset:offset + 2]):
            key = f"receipt_input_{record.id}_{field}"
            st.session_state.setdefault(key, draft[field])
            kwargs = dict(key=key, on_change=_remember_input, args=(record.id, field, key))
            with column:
                if field == "transaction_date":
                    st.date_input(label, **kwargs)
                elif field == "review_status":
                    st.selectbox(label, REVIEW_STATUS_OPTIONS, **kwargs)
                else:
                    st.text_input(label, placeholder="미표기 / 확인 필요" if field in dict(AMOUNT_FIELDS) else "", **kwargs)
                if field in dict(AMOUNT_FIELDS):
                    try:
                        parse_review_amount(draft[field])
                    except ValueError:
                        st.error(f"{label}: 금액 형식과 입력 범위를 확인해 주세요.")
    key = f"receipt_input_{record.id}_user_note"
    st.session_state.setdefault(key, draft["user_note"])
    st.text_input("비고", key=key, on_change=_remember_input, args=(record.id, "user_note", key))
    st.caption("입력 중인 내용은 이번 작업 세션에서 유지됩니다. 저장한 값만 표와 엑셀에 반영됩니다.")
    return dict(draft)

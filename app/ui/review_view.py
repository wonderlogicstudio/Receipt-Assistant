from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.core.receipt_models import ReceiptRecord
from app.ui.review_utils import (
    COL_CARD_MATCH_REASON,
    COL_CARD_MATCH_STATUS,
    COL_DATE,
    COL_DUPLICATE_SUSPECTED,
    COL_EXPENSE_CATEGORY,
    COL_INCLUDED,
    COL_MERCHANT,
    COL_PAYMENT,
    COL_RECOMMENDED_CATEGORY,
    COL_REVIEW_REASON,
    COL_REVIEW_STATUS,
    COL_SOURCE_FILE_NAME,
    COL_SUPPLY,
    COL_TOTAL,
    COL_USER_NOTE,
    COL_VAT,
    REVIEW_FILTER_ALL,
    REVIEW_FILTER_OPTIONS,
    REVIEW_ISSUE_OPTIONS,
    REVIEW_DISPLAY_COLUMNS,
    REVIEW_READ_ONLY_COLUMNS,
    REVIEW_STATUS_OPTIONS,
    build_review_issue_summary,
    filter_receipt_records_for_review,
    merge_reviewed_records,
    receipt_records_to_review_dataframe,
    review_issue_labels,
    review_dataframe_to_receipt_records,
    tracking_columns,
)
from app.ui.summary_view import render_review_summary


def render_review_view(records: list[ReceiptRecord]) -> list[ReceiptRecord]:
    if not records:
        st.info("먼저 파일을 업로드하고 처리해 주세요.")
        return []

    st.session_state["receipt_records"] = records
    render_review_summary(records)

    st.subheader("영수증 검수")
    st.caption("추천값과 검토사유를 확인한 뒤 필요한 항목만 직접 수정해 주세요.")

    status_filter, issue_filters = _render_review_filters(records)
    filtered_records = filter_receipt_records_for_review(
        records,
        status_filter=status_filter,
        issue_filters=issue_filters,
    )
    st.caption(f"표시 중: {len(filtered_records):,}건 / 전체 {len(records):,}건")

    if not filtered_records:
        st.info("현재 필터에 해당하는 영수증이 없습니다.")
        return records

    _render_review_detail_panel(filtered_records)

    dataframe = receipt_records_to_review_dataframe(filtered_records)
    edited_dataframe = st.data_editor(
        dataframe,
        key="receipt_review_editor",
        use_container_width=True,
        hide_index=True,
        column_order=REVIEW_DISPLAY_COLUMNS,
        disabled=REVIEW_READ_ONLY_COLUMNS,
        column_config=_column_config(),
    )

    reviewed_subset = review_dataframe_to_receipt_records(edited_dataframe, filtered_records)
    reviewed_records = merge_reviewed_records(records, reviewed_subset)
    st.session_state["reviewed_receipt_records"] = reviewed_records
    st.session_state["receipt_records"] = reviewed_records
    return reviewed_records


def _render_review_filters(records: list[ReceiptRecord]) -> tuple[str, list[str]]:
    issue_summary = build_review_issue_summary(records)
    filter_columns = st.columns([1, 2])
    status_filter = filter_columns[0].selectbox(
        "검수상태 필터",
        options=REVIEW_FILTER_OPTIONS,
        index=REVIEW_FILTER_OPTIONS.index(REVIEW_FILTER_ALL),
        key="receipt_review_status_filter",
    )
    issue_options = [
        f"{issue} ({issue_summary.get(issue, 0):,})"
        for issue in REVIEW_ISSUE_OPTIONS
        if issue_summary.get(issue, 0) > 0
    ]
    selected_issue_labels = filter_columns[1].multiselect(
        "검토 항목 필터",
        options=issue_options,
        key="receipt_review_issue_filter",
    )
    selected_issues = [label.split(" (", 1)[0] for label in selected_issue_labels]
    return status_filter, selected_issues


def _render_review_detail_panel(records: list[ReceiptRecord]) -> None:
    detail_options = [
        (_record_detail_label(record, index), record.id)
        for index, record in enumerate(records, start=1)
    ]
    if not detail_options:
        return
    option_by_label = dict(detail_options)
    selected_label = st.selectbox(
        "상세 확인",
        options=[label for label, _ in detail_options],
        key="receipt_review_detail_selector",
    )
    selected_id = option_by_label[selected_label]
    selected_record = next((record for record in records if record.id == selected_id), None)
    if selected_record is None:
        return
    detail_rows = [
        {"항목": "파일명", "값": _safe_file_name(selected_record.source_file_name)},
        {"항목": "상호", "값": selected_record.merchant_name or "-"},
        {"항목": "거래일자", "값": selected_record.transaction_date or "-"},
        {"항목": "사업자번호", "값": selected_record.business_number or "-"},
        {"항목": "총액", "값": selected_record.total_amount if selected_record.total_amount is not None else "-"},
        {"항목": "결제수단", "값": selected_record.payment_method or "-"},
        {"항목": "검토 항목", "값": "; ".join(review_issue_labels(selected_record)) or "-"},
        {"항목": "검토 사유", "값": selected_record.review_reason or "-"},
    ]
    with st.expander("선택한 영수증 상세", expanded=False):
        st.table(detail_rows)


def _record_detail_label(record: ReceiptRecord, index: int) -> str:
    merchant = record.merchant_name or "상호 미확인"
    amount = f"{record.total_amount:,}원" if record.total_amount is not None else "금액 미확인"
    date = record.transaction_date.isoformat() if record.transaction_date else "날짜 미확인"
    file_name = record.source_file_name or "파일명 없음"
    return f"{index}. {date} | {merchant} | {amount} | {_safe_file_name(file_name)}"


def _safe_file_name(value: str | None) -> str:
    if not value:
        return "파일명 없음"
    return Path(str(value).replace("\\", "/")).name or "파일명 없음"


def _column_config() -> dict[str, object]:
    hidden_columns = {column: None for column in tracking_columns()}
    visible_columns: dict[str, object] = {
        COL_INCLUDED: st.column_config.CheckboxColumn(COL_INCLUDED),
        COL_DATE: st.column_config.DateColumn(COL_DATE, format="YYYY-MM-DD"),
        COL_TOTAL: st.column_config.NumberColumn(COL_TOTAL, step=1, format="%d"),
        COL_SUPPLY: st.column_config.NumberColumn(COL_SUPPLY, step=1, format="%d"),
        COL_VAT: st.column_config.NumberColumn(COL_VAT, step=1, format="%d"),
        COL_REVIEW_STATUS: st.column_config.SelectboxColumn(
            COL_REVIEW_STATUS,
            options=REVIEW_STATUS_OPTIONS,
            required=True,
        ),
        COL_DUPLICATE_SUSPECTED: st.column_config.CheckboxColumn(COL_DUPLICATE_SUSPECTED),
        COL_MERCHANT: st.column_config.TextColumn(COL_MERCHANT),
        COL_PAYMENT: st.column_config.TextColumn(COL_PAYMENT),
        COL_EXPENSE_CATEGORY: st.column_config.TextColumn(COL_EXPENSE_CATEGORY),
        COL_USER_NOTE: st.column_config.TextColumn(COL_USER_NOTE),
        COL_RECOMMENDED_CATEGORY: st.column_config.TextColumn(COL_RECOMMENDED_CATEGORY),
        COL_REVIEW_REASON: st.column_config.TextColumn(COL_REVIEW_REASON),
        COL_CARD_MATCH_STATUS: st.column_config.TextColumn(COL_CARD_MATCH_STATUS),
        COL_CARD_MATCH_REASON: st.column_config.TextColumn(COL_CARD_MATCH_REASON),
        COL_SOURCE_FILE_NAME: st.column_config.TextColumn(COL_SOURCE_FILE_NAME),
    }
    return {**visible_columns, **hidden_columns}

from __future__ import annotations

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
    REVIEW_DISPLAY_COLUMNS,
    REVIEW_READ_ONLY_COLUMNS,
    REVIEW_STATUS_OPTIONS,
    receipt_records_to_review_dataframe,
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

    dataframe = receipt_records_to_review_dataframe(records)
    edited_dataframe = st.data_editor(
        dataframe,
        key="receipt_review_editor",
        use_container_width=True,
        hide_index=True,
        column_order=REVIEW_DISPLAY_COLUMNS,
        disabled=REVIEW_READ_ONLY_COLUMNS,
        column_config=_column_config(),
    )

    reviewed_records = review_dataframe_to_receipt_records(edited_dataframe, records)
    st.session_state["reviewed_receipt_records"] = reviewed_records
    st.session_state["receipt_records"] = reviewed_records
    return reviewed_records


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

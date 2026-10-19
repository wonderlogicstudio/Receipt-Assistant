from __future__ import annotations

import streamlit as st

from app.core.receipt_models import ReceiptRecord
from app.ui.review_utils import build_review_summary


def render_review_summary(records: list[ReceiptRecord]) -> None:
    summary = build_review_summary(records)

    st.subheader("검수 요약")
    reviewed_count = summary["approved_count"] + summary["excluded_count"]
    st.progress(reviewed_count / max(summary["total_count"], 1), text=f"검수 진행 {reviewed_count:,} / {summary['total_count']:,}건 · 확인 또는 제외한 건수")
    first_row = st.columns(4)
    first_row[0].metric("전체 건수", f"{summary['total_count']:,}")
    first_row[1].metric("확인완료", f"{summary['approved_count']:,}")
    first_row[2].metric("검토필요", f"{summary['needs_review_count']:,}")
    first_row[3].metric("제외", f"{summary['excluded_count']:,}")

    st.metric("중복의심", f"{summary['duplicate_suspected_count']:,}")

    third_row = st.columns(2)
    third_row[0].metric("총금액 합계", f"{summary['total_amount_sum']:,}원")
    third_row[1].metric("제외 후 총금액 합계", f"{summary['included_total_amount_sum']:,}원")

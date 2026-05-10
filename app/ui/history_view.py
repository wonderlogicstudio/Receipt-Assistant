from __future__ import annotations

import streamlit as st

from app.core.exceptions import ReceiptAssistantError
from app.history.job_service import JobHistoryService
from app.ui.history_detail_view import render_history_detail_view
from app.ui.history_utils import build_history_summary, format_amount, jobs_to_history_dataframe


def render_history_view(service: JobHistoryService | None = None) -> None:
    st.title("처리 이력")
    st.caption("최근 처리 작업의 요약 목록입니다.")

    try:
        history_service = service or JobHistoryService()
        jobs = history_service.list_processing_jobs(limit=50, offset=0)
    except ReceiptAssistantError:
        st.error("처리 이력을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
        return
    except Exception:
        st.error("처리 이력을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
        return

    if not jobs:
        st.info("아직 처리 이력이 없습니다.")
        return

    summary = build_history_summary(jobs)
    columns = st.columns(5)
    columns[0].metric("전체 작업 수", f"{summary['total_jobs']:,}")
    columns[1].metric("총 영수증 건수", f"{summary['total_receipts']:,}")
    columns[2].metric("총 카드내역 건수", f"{summary['total_card_transactions']:,}")
    columns[3].metric("총 검토필요 건수", f"{summary['total_needs_review']:,}")
    columns[4].metric("총금액 합계", format_amount(summary["total_amount"]))

    dataframe = jobs_to_history_dataframe(jobs)
    st.dataframe(dataframe, use_container_width=True, hide_index=True)

    job_options = [""] + [str(job.get("id")) for job in jobs if job.get("id")]
    selected_job_id = st.selectbox(
        "상세 확인 작업",
        job_options,
        format_func=lambda value: "선택 안 함" if not value else str(value)[:8],
    )
    if selected_job_id:
        render_history_detail_view(selected_job_id, service=history_service)

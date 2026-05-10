from __future__ import annotations

import streamlit as st

from app.core.config import get_config
from app.core.exceptions import ReceiptAssistantError
from app.history.job_service import JobHistoryService
from app.ui.history_utils import (
    card_transactions_to_history_detail_dataframe,
    export_files_to_display_dataframe,
    job_detail_to_summary_dict,
    read_export_file_bytes,
    receipt_records_to_history_detail_dataframe,
    select_latest_export_file,
)

EXPORT_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def render_history_detail_view(job_id: str, service: JobHistoryService | None = None) -> None:
    if not job_id:
        return

    st.subheader("작업 상세")
    try:
        history_service = service or JobHistoryService()
        detail = history_service.get_processing_job_detail(job_id)
    except ReceiptAssistantError:
        st.error("작업 상세 정보를 불러오지 못했습니다.")
        return
    except Exception:
        st.error("작업 상세 정보를 불러오지 못했습니다.")
        return

    if detail is None:
        st.info("선택한 작업을 찾을 수 없습니다.")
        return

    summary = job_detail_to_summary_dict(detail)
    st.table({"항목": list(summary.keys()), "내용": list(summary.values())})

    receipt_records = detail.get("receipt_records") or []
    st.markdown("#### 영수증 요약")
    if receipt_records:
        st.dataframe(receipt_records_to_history_detail_dataframe(receipt_records), use_container_width=True, hide_index=True)
    else:
        st.info("저장된 영수증 요약이 없습니다.")

    card_transactions = detail.get("card_transactions") or []
    st.markdown("#### 카드내역 요약")
    if card_transactions:
        st.dataframe(card_transactions_to_history_detail_dataframe(card_transactions), use_container_width=True, hide_index=True)
    else:
        st.info("저장된 카드내역 요약이 없습니다.")

    export_files = detail.get("export_files") or []
    st.markdown("#### 엑셀 파일")
    if export_files:
        st.dataframe(export_files_to_display_dataframe(export_files), use_container_width=True, hide_index=True)
        _render_export_download(export_files)
    else:
        st.info("저장된 엑셀 파일이 없습니다.")


def _render_export_download(export_files: list[dict[str, object]]) -> None:
    latest_export = select_latest_export_file(export_files)
    if latest_export is None:
        st.info("다운로드할 엑셀 파일이 없습니다.")
        return

    export_file_name = str(latest_export.get("export_file_name") or "receipt_summary.xlsx")
    try:
        file_bytes = read_export_file_bytes(get_config().output_root, latest_export.get("export_relative_path"))
    except ValueError:
        st.warning("엑셀 파일 경로를 확인해야 합니다.")
        return
    except OSError:
        st.warning("엑셀 파일을 읽지 못했습니다.")
        return

    if file_bytes is None:
        st.info("파일을 찾을 수 없습니다. 다시 생성이 필요합니다.")
        return

    st.download_button(
        "엑셀 다시 다운로드",
        data=file_bytes,
        file_name=export_file_name,
        mime=EXPORT_MIME_TYPE,
    )

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.core.config import get_config
from app.history.job_service import JobHistoryService
from app.storage.cleanup import cleanup_old_output_files, cleanup_old_upload_files
from app.ui.settings_utils import (
    build_db_summary,
    build_history_connection_summary,
    build_ocr_settings_summary,
    build_retention_settings_summary,
    build_storage_summary,
    sanitize_cleanup_summary,
    sanitize_settings_display,
)


def render_settings_view() -> None:
    st.title("설정")
    st.caption("현재 실행 환경과 저장소 상태를 안전하게 확인하는 읽기 전용 화면입니다.")

    config = get_config()

    st.subheader("기본 설정")
    _render_mapping(
        {
            "앱 모드": "로컬 MVP",
            "설정 변경": "화면에서 변경하지 않음",
            "원본 파일 장기 보관": "하지 않음",
        }
    )

    st.subheader("OCR 설정")
    _render_mapping(build_ocr_settings_summary(config))

    st.subheader("파일 보관 설정")
    _render_mapping(build_retention_settings_summary(config))

    st.subheader("저장소 상태")
    try:
        _render_mapping(build_storage_summary(upload_root=config.upload_root, output_root=config.output_root))
    except Exception:
        st.warning("저장소 상태를 확인하지 못했습니다.")

    st.subheader("DB 상태")
    try:
        history_service = JobHistoryService(config=config)
        _render_mapping(build_db_summary(history_service))
    except Exception:
        st.warning("DB 상태를 확인하지 못했습니다.")
        history_service = None

    st.subheader("처리 이력 연결 상태")
    if history_service is None:
        st.warning("처리 이력 연결 상태를 확인하지 못했습니다.")
    else:
        _render_mapping(build_history_connection_summary(history_service))

    st.subheader("Cleanup dry-run")
    st.caption("실제 삭제 없이 보관기간 기준 삭제 대상 수와 예상 용량만 확인합니다.")
    if st.button("Cleanup dry-run 확인", type="secondary"):
        try:
            upload_summary = sanitize_cleanup_summary(cleanup_old_upload_files(config=config, dry_run=True))
            output_summary = sanitize_cleanup_summary(cleanup_old_output_files(config=config, dry_run=True))
            st.write("업로드 저장소")
            _render_mapping(upload_summary)
            st.write("출력 저장소")
            _render_mapping(output_summary)
        except Exception:
            st.warning("Cleanup dry-run 결과를 확인하지 못했습니다.")

    st.subheader("주의사항")
    st.info(
        "이 화면에서는 API key, endpoint 전체 URL, 전체 로컬 경로, 파일명 목록, OCR 원문, 카드내역 원문을 표시하지 않습니다. "
        "실제 삭제, Provider 변경, DB 초기화 기능도 제공하지 않습니다."
    )


def _render_mapping(values: dict[str, object]) -> None:
    safe_values = sanitize_settings_display(values)
    rows = [{"항목": key, "값": value} for key, value in dict(safe_values).items()]
    st.table(pd.DataFrame(rows))

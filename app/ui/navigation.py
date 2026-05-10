from __future__ import annotations

import streamlit as st


NEW_JOB_PAGE = "new_job"
HISTORY_PAGE = "history"
SETTINGS_PAGE = "settings"

PAGE_LABELS = {
    NEW_JOB_PAGE: "새 작업",
    HISTORY_PAGE: "처리 이력",
    SETTINGS_PAGE: "설정",
}


def page_options() -> list[str]:
    return [NEW_JOB_PAGE, HISTORY_PAGE, SETTINGS_PAGE]


def page_label(page_key: str) -> str:
    return PAGE_LABELS.get(page_key, PAGE_LABELS[NEW_JOB_PAGE])


def render_navigation(default_page: str = NEW_JOB_PAGE) -> str:
    options = page_options()
    default_index = options.index(default_page) if default_page in options else 0
    return st.sidebar.radio(
        "메뉴",
        options,
        index=default_index,
        format_func=page_label,
        key="selected_page",
    )

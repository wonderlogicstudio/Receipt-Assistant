import streamlit as st

from app.ui.history_view import render_history_view
from app.ui.navigation import HISTORY_PAGE, NEW_JOB_PAGE, SETTINGS_PAGE, render_navigation
from app.ui.settings_view import render_settings_view
from app.ui.streamlit_app import (
    build_export_filename,
    prepare_export_bytes,
    process_card_statement_files,
    process_receipt_files_with_mock_ocr,
    render_new_job_view,
    route_uploaded_files_by_extension,
    run,
)


if __name__ == "__main__":
    st.set_page_config(page_title="영수증 OCR 엑셀 비서", layout="wide")
    selected_page = render_navigation(default_page=NEW_JOB_PAGE)
    if selected_page == HISTORY_PAGE:
        render_history_view()
    elif selected_page == SETTINGS_PAGE:
        render_settings_view()
    else:
        render_new_job_view()

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from app.core.exceptions import FileStoreError
from app.core.enums import OCRStatus
from app.core.receipt_models import ReceiptRecord
from app.exporter.excel_exporter import ExcelExporter
from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser, parse_amount, parse_date
from app.storage.file_store import FileStore, StoredFileMetadata
from app.validator.receipt_validator import ReceiptValidator


PREVIEW_COLUMNS = [
    "receipt_id",
    "source_file_name",
    "transaction_date",
    "merchant_name",
    "business_number",
    "total_amount",
    "supply_amount",
    "vat_amount",
    "payment_method",
    "expense_category",
    "confidence",
    "review_status",
    "review_reason",
]


def run() -> None:
    st.set_page_config(page_title="영수증 OCR 엑셀 비서", layout="wide")
    st.title("영수증 OCR 엑셀 비서 MVP")
    st.caption("OCR 결과는 검수 대상이며, 비용항목은 추천값으로만 표시됩니다.")

    file_store = FileStore()
    session_id = ensure_session_id(file_store)

    uploaded_files = st.file_uploader(
        "영수증 이미지/PDF 또는 카드 사용내역 엑셀/CSV 업로드",
        type=["jpg", "jpeg", "png", "pdf", "xlsx", "csv"],
        accept_multiple_files=True,
    )

    if st.button("업로드 저장 및 Mock OCR 실행", type="primary", disabled=not uploaded_files):
        provider = MockOCRProvider()
        parser = ReceiptParser()
        validator = ReceiptValidator()
        ocr_results = []
        receipts = []
        stored_files = []

        for uploaded_file in uploaded_files or []:
            try:
                metadata = file_store.save_uploaded_file(uploaded_file, session_id=session_id)
            except FileStoreError as exc:
                st.error(f"{uploaded_file.name}: {exc}")
                continue

            stored_files.append(metadata)
            ocr_result = provider.extract(metadata)
            ocr_results.append(ocr_result)
            if ocr_result.status == OCRStatus.COMPLETED.value:
                receipts.append(validator.validate(parser.parse(ocr_result)))

        st.session_state["stored_files"] = stored_files
        st.session_state["ocr_results"] = ocr_results
        st.session_state["receipts"] = receipts

    stored_files = st.session_state.get("stored_files", [])
    receipts = st.session_state.get("receipts", [])
    ocr_results = st.session_state.get("ocr_results", [])

    if stored_files:
        st.subheader("저장 메타데이터")
        st.dataframe(stored_files_to_dataframe(stored_files), use_container_width=True, hide_index=True)

    if not receipts:
        st.info("영수증 파일을 업로드한 뒤 저장 및 Mock OCR을 실행하세요.")
        return

    st.subheader("결과 미리보기")
    edited_df = st.data_editor(
        receipts_to_preview_dataframe(receipts),
        use_container_width=True,
        hide_index=True,
        disabled=["receipt_id", "source_file_name", "confidence"],
    )

    edited_receipts = _records_from_dataframe(edited_df, receipts)
    exporter = ExcelExporter()
    excel_bytes = exporter.export_to_bytes(edited_receipts, ocr_results)

    st.download_button(
        "엑셀 다운로드",
        data=excel_bytes,
        file_name=exporter.make_filename(),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def ensure_session_id(file_store: FileStore) -> str:
    session_id = st.session_state.get("session_id")
    session_id = file_store.get_or_create_session_id(session_id)
    st.session_state["session_id"] = session_id
    return session_id


def stored_files_to_dataframe(stored_files: list[StoredFileMetadata]) -> pd.DataFrame:
    rows = []
    for metadata in stored_files:
        row = metadata.to_dict()
        row["original_file_name"] = _display_file_name(str(row["original_file_name"]))
        rows.append(row)
    return pd.DataFrame(rows)


def receipts_to_preview_dataframe(receipts: list[ReceiptRecord]) -> pd.DataFrame:
    rows = []
    for receipt in receipts:
        row = receipt.to_dict()
        rows.append({column: row.get(column) for column in PREVIEW_COLUMNS})
    return pd.DataFrame(rows, columns=PREVIEW_COLUMNS)


def _records_from_dataframe(df: pd.DataFrame, fallback_records: list[ReceiptRecord]) -> list[ReceiptRecord]:
    records: list[ReceiptRecord] = []
    fallback_by_id = {record.receipt_id: record for record in fallback_records}

    for row in df.to_dict(orient="records"):
        original = fallback_by_id.get(row.get("receipt_id"))
        if original is None:
            continue
        records.append(
            replace(
                original,
                transaction_date=_as_date(row.get("transaction_date")),
                merchant_name=_as_optional_text(row.get("merchant_name")),
                business_number=_as_optional_text(row.get("business_number")),
                total_amount=parse_amount(row.get("total_amount")),
                supply_amount=parse_amount(row.get("supply_amount")),
                vat_amount=parse_amount(row.get("vat_amount")),
                payment_method=_as_optional_text(row.get("payment_method")),
                expense_category=_as_optional_text(row.get("expense_category")),
                review_status=str(row.get("review_status") or original.review_status),
                review_reason=str(row.get("review_reason") or ""),
            )
        )
    return records


def _as_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _as_date(value: object) -> date | None:
    return parse_date(value)


def _display_file_name(file_name: str) -> str:
    return Path(file_name.replace("\\", "/")).name

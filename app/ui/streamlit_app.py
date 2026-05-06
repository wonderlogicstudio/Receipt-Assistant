from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app.exporter.excel_exporter import ExcelExporter
from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser, ReceiptRecord, parse_amount, parse_date
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

    uploaded_files = st.file_uploader(
        "영수증 이미지 또는 PDF 업로드",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
    )

    if st.button("Mock OCR 실행", type="primary", disabled=not uploaded_files):
        provider = MockOCRProvider()
        parser = ReceiptParser()
        validator = ReceiptValidator()
        ocr_results = []
        receipts = []

        for uploaded_file in uploaded_files or []:
            ocr_result = provider.extract(uploaded_file.name)
            ocr_results.append(ocr_result)
            if ocr_result.status == "success":
                receipts.append(validator.validate(parser.parse(ocr_result)))

        st.session_state["ocr_results"] = ocr_results
        st.session_state["receipts"] = receipts

    receipts = st.session_state.get("receipts", [])
    ocr_results = st.session_state.get("ocr_results", [])

    if not receipts:
        st.info("샘플 영수증 파일을 업로드한 뒤 Mock OCR을 실행하세요.")
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
            ReceiptRecord(
                receipt_id=str(row.get("receipt_id") or original.receipt_id),
                source_file_name=str(row.get("source_file_name") or original.source_file_name),
                transaction_date=_as_date(row.get("transaction_date")),
                merchant_name=_as_optional_text(row.get("merchant_name")),
                business_number=_as_optional_text(row.get("business_number")),
                total_amount=parse_amount(row.get("total_amount")),
                supply_amount=parse_amount(row.get("supply_amount")),
                vat_amount=parse_amount(row.get("vat_amount")),
                payment_method=str(row.get("payment_method") or "미확인"),
                expense_category=str(row.get("expense_category") or "미분류"),
                confidence=original.confidence,
                review_status=str(row.get("review_status") or original.review_status),
                review_reason=str(row.get("review_reason") or ""),
                evidence_type=str(row.get("evidence_type") or original.evidence_type),
                ocr_provider=original.ocr_provider,
                ocr_raw_text=original.ocr_raw_text,
                raw_json=original.raw_json,
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

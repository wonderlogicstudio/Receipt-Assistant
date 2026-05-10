from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
import streamlit as st

from app.core.config import get_config
from app.core.card_models import CardParseResult, CardTransaction
from app.core.exceptions import ConfigurationError, FileStoreError, MissingRequiredColumnsError
from app.core.enums import OCRStatus
from app.core.ocr_models import OCRResult
from app.core.receipt_models import ReceiptRecord
from app.exporter.excel_exporter import ExcelExporter
from app.ocr.base import OCRProvider
from app.ocr.provider_factory import get_ocr_provider
from app.parser.card_statement_parser import CardStatementParser
from app.parser.receipt_parser import ReceiptParser, parse_amount, parse_date
from app.storage.file_store import FileStore, StoredFileMetadata
from app.ui.review_view import render_review_view
from app.ui.review_utils import build_review_summary
from app.validator.card_matcher import CardMatcher
from app.validator.duplicate_checker import DuplicateChecker
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

RECEIPT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
CARD_STATEMENT_EXTENSIONS = {".xlsx", ".csv"}
EXPORT_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True)
class RoutedUploadedFiles:
    receipt_files: list[StoredFileMetadata]
    card_statement_files: list[StoredFileMetadata]
    unsupported_files: list[StoredFileMetadata]


@dataclass(frozen=True)
class ReceiptProcessingResult:
    receipt_records: list[ReceiptRecord]
    ocr_results: list[OCRResult]
    errors: list[str]


@dataclass(frozen=True)
class CardStatementProcessingResult:
    card_transactions: list[CardTransaction]
    parse_results: list[CardParseResult]
    errors: list[str]


@dataclass(frozen=True)
class ProcessingPipelineResult:
    uploaded_file_metadata: list[StoredFileMetadata]
    receipt_records: list[ReceiptRecord]
    card_transactions: list[CardTransaction]
    ocr_results: list[OCRResult]
    card_parse_results: list[CardParseResult]
    errors: list[str]


def run() -> None:
    st.set_page_config(page_title="영수증 OCR 엑셀 비서", layout="wide")
    st.title("영수증 OCR 엑셀 비서 MVP")
    st.caption("업로드한 증빙을 설정된 OCR provider와 규칙 기반 파서로 정리한 뒤, 사용자가 검수해 표준 엑셀 정리 파일을 만듭니다.")
    st.caption(f"현재 OCR provider: {get_config().ocr_provider}")

    file_store = FileStore()
    session_id = ensure_session_id(file_store)

    st.subheader("1단계: 파일 업로드")
    uploaded_files = st.file_uploader(
        "영수증 이미지/PDF 또는 카드 사용내역 엑셀/CSV 업로드",
        type=["jpg", "jpeg", "png", "pdf", "xlsx", "csv"],
        accept_multiple_files=True,
    )

    st.subheader("2단계: 파일 처리")
    if st.button("파일 저장 및 처리", type="primary", disabled=not uploaded_files):
        result = save_and_process_uploaded_files(uploaded_files or [], file_store=file_store, session_id=session_id)
        st.session_state["uploaded_file_metadata"] = result.uploaded_file_metadata
        st.session_state["stored_files"] = result.uploaded_file_metadata
        st.session_state["ocr_results"] = result.ocr_results
        st.session_state["card_parse_results"] = result.card_parse_results
        st.session_state["card_transactions"] = result.card_transactions
        st.session_state["receipt_records"] = result.receipt_records
        st.session_state["reviewed_receipt_records"] = result.receipt_records
        st.session_state["export_file_bytes"] = None
        st.session_state["export_file_name"] = None

        for message in result.errors:
            st.warning(message)

    uploaded_metadata = st.session_state.get("uploaded_file_metadata", st.session_state.get("stored_files", []))
    receipt_records: list[ReceiptRecord] = (
        st.session_state.get("reviewed_receipt_records")
        or st.session_state.get("receipt_records")
        or st.session_state.get("receipts", [])
    )
    card_transactions: list[CardTransaction] = st.session_state.get("card_transactions", [])

    if uploaded_metadata:
        st.subheader("저장 메타데이터")
        st.dataframe(stored_files_to_dataframe(uploaded_metadata), use_container_width=True, hide_index=True)

    render_processing_summary(uploaded_metadata, receipt_records, card_transactions)

    st.subheader("3단계: 검수")
    if not receipt_records:
        st.info("먼저 파일을 업로드하고 처리해 주세요.")
        return

    reviewed_records = render_review_view(receipt_records)
    st.session_state["reviewed_receipt_records"] = reviewed_records

    st.subheader("4단계: 엑셀 다운로드")
    if st.button("표준 엑셀 생성", type="secondary"):
        try:
            st.session_state["export_file_bytes"] = prepare_export_bytes(reviewed_records, card_transactions)
            st.session_state["export_file_name"] = build_export_filename()
            st.success("엑셀 파일이 생성되었습니다.")
        except Exception as exc:  # pragma: no cover - Streamlit error guard
            st.error(f"엑셀 파일을 생성하지 못했습니다: {exc.__class__.__name__}")

    if st.session_state.get("export_file_bytes"):
        st.download_button(
            "엑셀 다운로드",
            data=st.session_state["export_file_bytes"],
            file_name=st.session_state.get("export_file_name") or build_export_filename(),
            mime=EXPORT_MIME_TYPE,
        )


def ensure_session_id(file_store: FileStore) -> str:
    session_id = st.session_state.get("session_id")
    session_id = file_store.get_or_create_session_id(session_id)
    st.session_state["session_id"] = session_id
    return session_id


def save_and_process_uploaded_files(
    uploaded_files: Sequence[object],
    *,
    file_store: FileStore,
    session_id: str,
) -> ProcessingPipelineResult:
    uploaded_metadata: list[StoredFileMetadata] = []
    errors: list[str] = []

    for uploaded_file in uploaded_files:
        try:
            uploaded_metadata.append(file_store.save_uploaded_file(uploaded_file, session_id=session_id))
        except FileStoreError as exc:
            errors.append(f"{_display_file_name(str(getattr(uploaded_file, 'name', 'uploaded_file')))}: {exc}")

    processed = process_uploaded_file_metadata(uploaded_metadata, file_store=file_store)
    return ProcessingPipelineResult(
        uploaded_file_metadata=uploaded_metadata,
        receipt_records=processed.receipt_records,
        card_transactions=processed.card_transactions,
        ocr_results=processed.ocr_results,
        card_parse_results=processed.card_parse_results,
        errors=[*errors, *processed.errors],
    )


def process_uploaded_file_metadata(
    uploaded_metadata: Iterable[StoredFileMetadata],
    *,
    file_store: FileStore | None = None,
) -> ProcessingPipelineResult:
    metadata_list = list(uploaded_metadata)
    routed = route_uploaded_files_by_extension(metadata_list)
    receipt_result = process_receipt_files_with_mock_ocr(routed.receipt_files, file_store=file_store)
    card_result = process_card_statement_files(routed.card_statement_files, file_store=file_store)

    receipt_records = DuplicateChecker().check(receipt_result.receipt_records)
    if card_result.card_transactions:
        receipt_records = CardMatcher().match(receipt_records, card_result.card_transactions)

    unsupported_errors = [
        f"{_display_file_name(metadata.original_file_name)}: 지원하지 않는 파일 형식입니다."
        for metadata in routed.unsupported_files
    ]

    return ProcessingPipelineResult(
        uploaded_file_metadata=metadata_list,
        receipt_records=receipt_records,
        card_transactions=card_result.card_transactions,
        ocr_results=receipt_result.ocr_results,
        card_parse_results=card_result.parse_results,
        errors=[*receipt_result.errors, *card_result.errors, *unsupported_errors],
    )


def route_uploaded_files_by_extension(uploaded_metadata: Iterable[StoredFileMetadata]) -> RoutedUploadedFiles:
    receipt_files: list[StoredFileMetadata] = []
    card_statement_files: list[StoredFileMetadata] = []
    unsupported_files: list[StoredFileMetadata] = []

    for metadata in uploaded_metadata:
        extension = metadata.file_extension.lower()
        if extension in RECEIPT_EXTENSIONS:
            receipt_files.append(metadata)
        elif extension in CARD_STATEMENT_EXTENSIONS:
            card_statement_files.append(metadata)
        else:
            unsupported_files.append(metadata)

    return RoutedUploadedFiles(
        receipt_files=receipt_files,
        card_statement_files=card_statement_files,
        unsupported_files=unsupported_files,
    )


def process_receipt_files_with_mock_ocr(
    receipt_files: Iterable[StoredFileMetadata],
    *,
    file_store: FileStore | None = None,
    ocr_provider: OCRProvider | None = None,
) -> ReceiptProcessingResult:
    parser = ReceiptParser()
    validator = ReceiptValidator()
    receipt_records: list[ReceiptRecord] = []
    ocr_results: list[OCRResult] = []
    errors: list[str] = []
    try:
        provider = ocr_provider or get_ocr_provider()
    except ConfigurationError as exc:
        return ReceiptProcessingResult(receipt_records=[], ocr_results=[], errors=[str(exc)])

    for metadata in receipt_files:
        source = file_store.resolve_stored_path(metadata) if file_store else metadata
        ocr_result = _copy_ocr_result_metadata(provider.extract(source), metadata)
        ocr_results.append(ocr_result)
        if ocr_result.status != OCRStatus.COMPLETED.value:
            errors.append(f"{_display_file_name(metadata.original_file_name)}: OCR 처리 상태를 확인해 주세요.")
            continue
        receipt_records.append(validator.validate(parser.parse(ocr_result)))

    return ReceiptProcessingResult(receipt_records=receipt_records, ocr_results=ocr_results, errors=errors)


def process_card_statement_files(
    card_statement_files: Iterable[StoredFileMetadata],
    *,
    file_store: FileStore | None = None,
) -> CardStatementProcessingResult:
    parser = CardStatementParser()
    card_transactions: list[CardTransaction] = []
    parse_results: list[CardParseResult] = []
    errors: list[str] = []

    for metadata in card_statement_files:
        try:
            source = file_store.resolve_stored_path(metadata) if file_store else metadata
            parse_result = parser.parse(source)
        except MissingRequiredColumnsError as exc:
            errors.append(f"{_display_file_name(metadata.original_file_name)}: {exc}")
            continue

        parse_result = _copy_card_parse_result_metadata(parse_result, metadata)
        parse_results.append(parse_result)
        card_transactions.extend(parse_result.transactions)
        if parse_result.warning_messages:
            errors.append(f"{_display_file_name(metadata.original_file_name)}: 카드 사용내역 확인이 필요합니다.")

    return CardStatementProcessingResult(
        card_transactions=card_transactions,
        parse_results=parse_results,
        errors=errors,
    )


def prepare_export_bytes(
    reviewed_receipt_records: Iterable[ReceiptRecord],
    card_transactions: Iterable[CardTransaction] | None = None,
) -> bytes:
    return ExcelExporter().export_to_bytes(list(reviewed_receipt_records), list(card_transactions or []))


def build_export_filename(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"receipt_summary_{timestamp}.xlsx"


def render_processing_summary(
    uploaded_metadata: list[StoredFileMetadata],
    receipt_records: list[ReceiptRecord],
    card_transactions: list[CardTransaction],
) -> None:
    if not uploaded_metadata and not receipt_records and not card_transactions:
        return

    summary = build_review_summary(receipt_records)
    columns = st.columns(6)
    columns[0].metric("업로드 파일 수", f"{len(uploaded_metadata):,}")
    columns[1].metric("영수증 처리 건수", f"{len(receipt_records):,}")
    columns[2].metric("카드 사용내역 건수", f"{len(card_transactions):,}")
    columns[3].metric("검토필요 건수", f"{summary['needs_review_count']:,}")
    columns[4].metric("카드매칭 완료", f"{summary['card_matched_count']:,}")
    columns[5].metric(
        "카드 후보/미매칭",
        f"{summary['card_candidate_count']:,}/{summary['card_unmatched_count']:,}",
    )


def stored_files_to_dataframe(stored_files: list[StoredFileMetadata]) -> pd.DataFrame:
    rows = []
    for metadata in stored_files:
        row = metadata.to_dict()
        row["original_file_name"] = _display_file_name(str(row["original_file_name"]))
        row.pop("stored_relative_path", None)
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


def _copy_card_parse_result_metadata(parse_result: CardParseResult, metadata: StoredFileMetadata) -> CardParseResult:
    source_file_id = _source_file_id(metadata)
    transactions = [
        replace(
            transaction,
            session_id=metadata.session_id,
            source_file_id=source_file_id,
            source_file_name=metadata.original_file_name,
            stored_relative_path=metadata.stored_relative_path,
        )
        for transaction in parse_result.transactions
    ]
    return replace(
        parse_result,
        session_id=metadata.session_id,
        source_file_id=source_file_id,
        source_file_name=metadata.original_file_name,
        transactions=transactions,
        parsed_rows=len(transactions),
    )


def _copy_ocr_result_metadata(ocr_result: OCRResult, metadata: StoredFileMetadata) -> OCRResult:
    source_file_id = _source_file_id(metadata)
    return replace(
        ocr_result,
        source_file_id=source_file_id,
        source_file_name=metadata.original_file_name,
        stored_relative_path=metadata.stored_relative_path,
    )


def _source_file_id(metadata: StoredFileMetadata) -> str:
    return sha256(metadata.stored_relative_path.encode("utf-8")).hexdigest()


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

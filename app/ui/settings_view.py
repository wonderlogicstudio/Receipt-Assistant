from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from app.classifier.merchant_candidate import MerchantCandidateMatcher
from app.classifier.merchant_diagnostics import (
    build_candidate_diagnostic_rows,
    build_merchant_dictionary_summary,
    build_saved_receipt_candidate_diagnostic,
    collect_recent_receipt_records,
)
from app.classifier.merchant_importer import MerchantImportResult, PublicMerchantCsvImporter
from app.core.config import AppConfig, get_config
from app.core.standard_ocr import StandardOCRResult
from app.db.merchant_repository import MerchantRepository
from app.history.job_service import JobHistoryService
from app.history.safe_diagnostics import build_processing_history_safety_diagnostic
from app.ocr.azure_provider import AzureDocumentIntelligenceProvider
from app.ocr.paddle_provider import PaddleOCRProvider
from app.storage.cleanup import cleanup_old_output_files, cleanup_old_upload_files
from app.ui.ocr_comparison_report_utils import (
    build_diagnostic_standard_ocr_result,
    build_side_by_side_report,
    build_standard_ocr_from_safe_azure_ocr_result,
    comparison_report_to_field_rows,
    comparison_report_to_match_summary,
    comparison_report_to_summary_rows,
)
from app.ui.ocr_preview_utils import build_safe_ocr_preview
from app.ui.settings_utils import (
    build_db_summary,
    build_history_connection_summary,
    build_merchant_category_summary_rows,
    build_merchant_dictionary_summary_rows,
    build_merchant_import_batch_summary_rows,
    build_merchant_import_result_rows,
    build_merchant_search_result_rows,
    build_ocr_settings_summary,
    build_paddle_smoke_result_summary,
    build_processing_history_safety_rows,
    build_retention_settings_summary,
    build_saved_receipt_diagnostic_sample_rows,
    build_saved_receipt_diagnostic_summary_rows,
    build_storage_summary,
    sanitize_cleanup_summary,
    sanitize_settings_display,
)

MERCHANT_CSV_MAX_UPLOAD_SIZE_MB = 400
MERCHANT_CSV_MAX_UPLOAD_SIZE_BYTES = MERCHANT_CSV_MAX_UPLOAD_SIZE_MB * 1024 * 1024


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
    render_paddle_smoke_test_box()
    render_ocr_side_by_side_comparison_box(config)

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
        render_processing_history_safety_box(config)

    render_merchant_dictionary_import_box(config)
    render_merchant_dictionary_search_box(config)
    render_merchant_dictionary_diagnostics_box(config, history_service=history_service)

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


def render_paddle_smoke_test_box() -> None:
    st.subheader("PaddleOCR Local smoke test")
    st.caption("PaddleOCR 실제 실행 경로만 확인합니다. 기본 provider와 업로드 처리 흐름은 변경하지 않습니다.")
    uploaded_image = st.file_uploader(
        "PaddleOCR smoke test 이미지",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        key="paddle_smoke_test_image",
    )
    if st.button("PaddleOCR smoke test 실행", type="secondary"):
        if uploaded_image is None:
            st.info("비민감 샘플 이미지를 선택한 뒤 다시 실행해 주세요.")
            return
        try:
            result_or_summary = run_paddle_smoke_test_from_uploaded_file(uploaded_image)
        except Exception:
            st.warning("PaddleOCR smoke test 실행 경로를 확인하지 못했습니다.")
            return
        if isinstance(result_or_summary, StandardOCRResult):
            _render_mapping(build_paddle_smoke_result_summary(result_or_summary))
            _render_safe_ocr_preview(result_or_summary)
        else:
            _render_mapping(result_or_summary)


def render_processing_history_safety_box(config: AppConfig) -> None:
    st.subheader("Processing History 안전 진단")
    st.caption(
        "기존 Processing History schema는 변경하지 않고, 저장된 컬럼/값의 안전 요약만 확인합니다. "
        "raw OCR, provider raw JSON, 전체 경로 값은 표시하지 않습니다."
    )
    if not st.button("Processing History 안전 진단 실행", type="secondary"):
        return
    started_at = time.perf_counter()
    try:
        diagnostic = build_processing_history_safety_diagnostic(config=config)
    except Exception:
        st.warning("Processing History 안전 진단을 완료하지 못했습니다.")
        return
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    st.table(pd.DataFrame(build_processing_history_safety_rows(diagnostic)))
    _render_mapping({"diagnostic_elapsed_ms": elapsed_ms})


def render_merchant_dictionary_import_box(config: AppConfig) -> None:
    st.subheader("상호 사전 관리")
    st.caption(
        "공공 상가정보 CSV에서 허용 컬럼만 읽어 상호 후보 DB에 누적합니다. "
        "CSV 원본은 장기 보관하지 않고, 같은 파일 내용은 중복 import로 건너뜁니다. "
        f"파일당 업로드 한도는 {MERCHANT_CSV_MAX_UPLOAD_SIZE_MB}MB입니다. "
        "수백 MB 이상 파일은 브라우저 업로드보다 CLI import가 더 안정적입니다."
    )
    uploaded_files = st.file_uploader(
        "공공 상가정보 CSV",
        type=["csv"],
        accept_multiple_files=True,
        key="merchant_dictionary_csv_import",
    )
    encoding = st.selectbox(
        "CSV 인코딩",
        options=["utf-8-sig", "cp949"],
        index=0,
        key="merchant_dictionary_csv_encoding",
    )
    oversize_files = _merchant_csv_files_over_limit(uploaded_files or [])
    if oversize_files:
        st.warning(
            f"{MERCHANT_CSV_MAX_UPLOAD_SIZE_MB}MB를 초과한 CSV는 import하지 않습니다: "
            + ", ".join(oversize_files)
        )
    if st.button("상호 사전 CSV import", type="secondary"):
        if not uploaded_files:
            st.info("CSV 파일을 하나 이상 선택한 뒤 다시 실행해 주세요.")
            return
        if oversize_files:
            st.warning("용량 제한을 초과한 파일을 제거한 뒤 다시 실행해 주세요.")
            return
        try:
            results = import_merchant_dictionary_uploaded_files(uploaded_files, config=config, encoding=encoding)
        except Exception:
            st.warning("상호 사전 CSV import를 안전하게 완료하지 못했습니다.")
            return
        rows = build_merchant_import_result_rows(results)
        st.session_state.pop("merchant_candidate_cache", None)
        st.table(pd.DataFrame(rows))


def render_merchant_dictionary_search_box(config: AppConfig) -> None:
    st.subheader("상호 사전 검색")
    st.caption(
        "상호명 prefix 또는 도로명+건물번호로 merchant DB를 안전하게 조회합니다. "
        "대용량 DB 보호를 위해 입력 없는 전체 조회와 전체 주소/경로 노출은 하지 않습니다."
    )
    merchant_name = st.text_input(
        "상호명",
        value="",
        key="merchant_dictionary_search_merchant_name",
    )
    road_name = st.text_input(
        "도로명",
        value="",
        key="merchant_dictionary_search_road_name",
    )
    building_main_number = st.text_input(
        "건물본번지",
        value="",
        key="merchant_dictionary_search_building_main_number",
    )
    branch_name = st.text_input(
        "지점명 필터",
        value="",
        key="merchant_dictionary_search_branch_name",
    )
    category = st.text_input(
        "업종 필터",
        value="",
        key="merchant_dictionary_search_category",
    )
    limit = st.slider(
        "검색 결과 수",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
        key="merchant_dictionary_search_limit",
    )
    if not st.button("상호 사전 검색", type="secondary"):
        return
    has_name_query = bool(merchant_name.strip())
    has_address_query = bool(road_name.strip() and building_main_number.strip())
    if not (has_name_query or has_address_query):
        st.info("상호명 또는 도로명+건물본번지를 입력한 뒤 검색해 주세요.")
        return
    started_at = time.perf_counter()
    try:
        repository = MerchantRepository(config=config)
        rows = build_merchant_search_result_rows(
            repository.search_masters(
                merchant_name=merchant_name,
                road_name=road_name,
                building_main_number=building_main_number,
                branch_name=branch_name,
                category=category,
                limit=limit,
            )
        )
    except Exception:
        st.warning("상호 사전 검색을 안전하게 완료하지 못했습니다.")
        return
    if rows:
        st.table(pd.DataFrame(rows))
    else:
        st.info("검색 조건에 맞는 상호 사전 항목이 없습니다.")


    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    _render_mapping({"query_elapsed_ms": elapsed_ms, "result_count": len(rows), "limit": int(limit)})


def render_merchant_dictionary_diagnostics_box(
    config: AppConfig,
    *,
    history_service: JobHistoryService | None,
) -> None:
    st.subheader("상호 사전 진단")
    st.caption(
        "저장된 상호 사전과 matcher 후보 품질을 안전한 요약으로만 확인합니다. "
        "후보는 자동 확정하지 않으며 사업자번호는 마스킹해서 표시합니다."
    )
    merchant_name = st.text_input(
        "테스트 상호명",
        value="",
        key="merchant_dictionary_diagnostic_merchant_name",
    )
    business_number = st.text_input(
        "테스트 사업자번호",
        value="",
        key="merchant_dictionary_diagnostic_business_number",
    )
    address_hint = st.text_input(
        "테스트 주소 힌트",
        value="",
        key="merchant_dictionary_diagnostic_address_hint",
    )
    include_saved_records = st.checkbox(
        "최근 처리 이력 집계 포함",
        value=False,
        key="merchant_dictionary_diagnostic_include_history",
    )
    if not st.button("상호 사전 진단 실행", type="secondary"):
        return

    try:
        repository = MerchantRepository(config=config)
        matcher = MerchantCandidateMatcher(repository)
        summary = build_merchant_dictionary_summary(repository)
    except Exception:
        st.warning("상호 사전 진단 요약을 안전하게 준비하지 못했습니다.")
        return

    st.write("상호 사전 요약")
    st.table(pd.DataFrame(build_merchant_dictionary_summary_rows(summary)))

    category_rows = build_merchant_category_summary_rows(summary)
    if category_rows:
        st.write("상위 업종 요약")
        st.table(pd.DataFrame(category_rows))

    batch_rows = build_merchant_import_batch_summary_rows(summary)
    if batch_rows:
        st.write("최근 import batch")
        st.table(pd.DataFrame(batch_rows))

    if merchant_name.strip() or business_number.strip() or address_hint.strip():
        try:
            rows = build_candidate_diagnostic_rows(
                matcher,
                merchant_name=merchant_name,
                business_number=business_number,
                address_hint=address_hint,
            )
        except Exception:
            st.warning("상호 후보 진단을 안전하게 실행하지 못했습니다.")
            rows = []
        st.write("테스트 후보 결과")
        if rows:
            st.table(pd.DataFrame(rows))
        else:
            st.info("표시할 상호 후보가 없습니다.")

    if include_saved_records:
        if history_service is None:
            st.warning("처리 이력 DB 연결을 확인하지 못해 집계를 건너뜁니다.")
            return
        try:
            records = collect_recent_receipt_records(history_service, job_limit=20, record_limit=100)
            diagnostic = build_saved_receipt_candidate_diagnostic(records, matcher, max_records=100, sample_limit=10)
        except Exception:
            st.warning("저장된 처리 이력 후보 집계를 안전하게 실행하지 못했습니다.")
            return
        st.write("저장된 처리 이력 후보 집계")
        st.table(pd.DataFrame(build_saved_receipt_diagnostic_summary_rows(diagnostic)))
        sample_rows = build_saved_receipt_diagnostic_sample_rows(diagnostic)
        if sample_rows:
            st.write("안전 샘플")
            st.table(pd.DataFrame(sample_rows))


def import_merchant_dictionary_uploaded_files(
    uploaded_files: list[object],
    *,
    config: AppConfig,
    encoding: str = "utf-8-sig",
) -> list[MerchantImportResult]:
    repository = MerchantRepository(config=config)
    importer = PublicMerchantCsvImporter(repository)
    results: list[MerchantImportResult] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for index, uploaded_file in enumerate(uploaded_files, start=1):
            safe_name = _safe_file_name(str(getattr(uploaded_file, "name", f"merchant_{index}.csv")))
            if _uploaded_file_size(uploaded_file) > MERCHANT_CSV_MAX_UPLOAD_SIZE_BYTES:
                raise ValueError("merchant_csv_upload_too_large")
            temp_path = temp_root / f"merchant_{index}.csv"
            _write_uploaded_file_to_temp(uploaded_file, temp_path)
            if temp_path.stat().st_size > MERCHANT_CSV_MAX_UPLOAD_SIZE_BYTES:
                raise ValueError("merchant_csv_upload_too_large")
            result = importer.import_csv(temp_path, encoding=encoding, source_file_name=safe_name)
            results.append(
                MerchantImportResult(
                    source_batch_id=result.source_batch_id,
                    imported_row_count=result.imported_row_count,
                    skipped_row_count=result.skipped_row_count,
                    duplicate_file=result.duplicate_file,
                    source_file_name=safe_name,
                    source_file_hash=result.source_file_hash,
                    scanned_row_count=result.scanned_row_count,
                    skipped_duplicate_row_count=result.skipped_duplicate_row_count,
                    skipped_invalid_row_count=result.skipped_invalid_row_count,
                    elapsed_seconds=result.elapsed_seconds,
                    rows_per_second=result.rows_per_second,
                )
            )
    return results


def _merchant_csv_files_over_limit(uploaded_files: list[object]) -> list[str]:
    return [
        _safe_file_name(str(getattr(uploaded_file, "name", "merchant.csv")))
        for uploaded_file in uploaded_files
        if _uploaded_file_size(uploaded_file) > MERCHANT_CSV_MAX_UPLOAD_SIZE_BYTES
    ]


def _uploaded_file_size(uploaded_file: object) -> int:
    size = getattr(uploaded_file, "size", None)
    if size is not None:
        try:
            return int(size)
        except (TypeError, ValueError):
            return 0
    if hasattr(uploaded_file, "getbuffer"):
        try:
            return len(uploaded_file.getbuffer())
        except Exception:
            return 0
    if hasattr(uploaded_file, "getvalue"):
        try:
            return len(uploaded_file.getvalue())
        except Exception:
            return 0
    return 0


def _write_uploaded_file_to_temp(uploaded_file: object, temp_path: Path) -> None:
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    if hasattr(uploaded_file, "read"):
        with temp_path.open("wb") as output:
            while True:
                chunk = uploaded_file.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        return
    payload = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else b""
    temp_path.write_bytes(payload)


def run_paddle_smoke_test_from_uploaded_file(
    uploaded_image: object,
) -> StandardOCRResult | dict[str, object]:
    safe_name = _safe_file_name(str(getattr(uploaded_image, "name", "paddle_smoke_input.png")))
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        return {"status": "skipped", "diagnostic_code": "unsupported_input_type", "file_name": safe_name}

    payload = uploaded_image.getvalue() if hasattr(uploaded_image, "getvalue") else b""
    with tempfile.TemporaryDirectory() as temp_dir:
        smoke_path = Path(temp_dir) / f"paddle_smoke{suffix}"
        smoke_path.write_bytes(payload)
        result = PaddleOCRProvider().extract(smoke_path, source_file_name=safe_name)
    return result


def render_ocr_side_by_side_comparison_box(config: AppConfig) -> None:
    st.subheader("Azure vs PaddleOCR side-by-side comparison")
    st.caption(
        "Non-sensitive sample image only. Azure and PaddleOCR run only after this explicit action, "
        "then StandardOCRResult and parser output are compared without raw OCR text or raw JSON."
    )
    uploaded_image = st.file_uploader(
        "Side-by-side comparison image",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        key="ocr_side_by_side_comparison_image",
    )
    if st.button("Run Azure vs PaddleOCR comparison", type="secondary"):
        if uploaded_image is None:
            st.info("Select one non-sensitive sample image before running the comparison.")
            return
        try:
            report = run_side_by_side_comparison_from_uploaded_file(uploaded_image, config)
        except Exception:
            st.warning("Side-by-side comparison could not be prepared safely.")
            return
        if isinstance(report, dict):
            _render_mapping(report)
            return
        st.write("Provider summary")
        st.table(pd.DataFrame(comparison_report_to_summary_rows(report)))
        st.write("Field match summary")
        _render_mapping(comparison_report_to_match_summary(report))
        for provider_result in (report.azure, report.paddle):
            if provider_result.provider_status != "completed":
                detail = provider_result.diagnostic_detail_code or "-"
                st.warning(
                    f"{provider_result.provider} did not complete: "
                    f"{provider_result.diagnostic_code or provider_result.provider_status}"
                    f" (detail={detail})"
                )
        st.write("Core field comparison")
        st.table(pd.DataFrame(comparison_report_to_field_rows(report)))


def run_side_by_side_comparison_from_uploaded_file(
    uploaded_image: object,
    config: AppConfig,
):
    safe_name = _safe_file_name(str(getattr(uploaded_image, "name", "ocr_comparison_input.png")))
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        return {"status": "skipped", "diagnostic_code": "unsupported_input_type", "file_name": safe_name}

    payload = uploaded_image.getvalue() if hasattr(uploaded_image, "getvalue") else b""
    with tempfile.TemporaryDirectory() as temp_dir:
        comparison_path = Path(temp_dir) / f"ocr_comparison_input{suffix}"
        comparison_path.write_bytes(payload)
        azure_result, azure_elapsed_ms = _run_azure_comparison_provider(
            comparison_path,
            safe_name=safe_name,
            config=config,
        )
        paddle_result, paddle_elapsed_ms = _run_paddle_comparison_provider(
            comparison_path,
            safe_name=safe_name,
        )

    return build_side_by_side_report(
        sample_id=Path(safe_name).stem,
        source_file_name=safe_name,
        azure_result=azure_result,
        paddle_result=paddle_result,
        azure_elapsed_ms=azure_elapsed_ms,
        paddle_elapsed_ms=paddle_elapsed_ms,
    )


def _run_azure_comparison_provider(
    source_path: Path,
    *,
    safe_name: str,
    config: AppConfig,
) -> tuple[StandardOCRResult, int | None]:
    if not config.azure_document_intelligence_endpoint or not config.azure_document_intelligence_key:
        return (
            build_diagnostic_standard_ocr_result(
                provider="azure",
                source_file_name=safe_name,
                status="skipped",
                diagnostic_code="azure_configuration_missing",
                engine_runtime="server",
            ),
            None,
        )
    started_at = time.perf_counter()
    try:
        ocr_result = AzureDocumentIntelligenceProvider(config=config).extract(source_path)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return build_standard_ocr_from_safe_azure_ocr_result(ocr_result, source_file_name=safe_name), elapsed_ms
    except Exception:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return (
            build_diagnostic_standard_ocr_result(
                provider="azure",
                source_file_name=safe_name,
                status="failed",
                diagnostic_code="azure_runtime_error",
                engine_runtime="server",
            ),
            elapsed_ms,
        )


def _run_paddle_comparison_provider(
    source_path: Path,
    *,
    safe_name: str,
) -> tuple[StandardOCRResult, int | None]:
    started_at = time.perf_counter()
    try:
        result = PaddleOCRProvider().extract(source_path, source_file_name=safe_name)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return result, elapsed_ms
    except Exception:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return (
            build_diagnostic_standard_ocr_result(
                provider="paddleocr",
                source_file_name=safe_name,
                status="failed",
                diagnostic_code="paddle_runtime_error",
                engine_runtime="pc_local",
            ),
            elapsed_ms,
        )


def _safe_file_name(value: str) -> str:
    return Path(str(value).replace("\\", "/")).name or "paddle_smoke_input.png"


def _render_mapping(values: dict[str, object]) -> None:
    safe_values = sanitize_settings_display(values)
    rows = [{"항목": key, "값": value} for key, value in dict(safe_values).items()]
    st.table(pd.DataFrame(rows))


def _render_safe_ocr_preview(result: StandardOCRResult) -> None:
    preview = build_safe_ocr_preview(result)
    st.write("Safe OCR preview")
    _render_mapping(preview.summary.as_display_dict())
    if not preview.rows:
        st.info("No safe OCR preview lines are available.")
        return
    rows = [row.as_display_dict() for row in preview.rows]
    st.table(pd.DataFrame(rows))

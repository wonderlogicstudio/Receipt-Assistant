from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from app.core.config import AppConfig, get_config
from app.core.standard_ocr import StandardOCRResult
from app.history.job_service import JobHistoryService
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
    build_ocr_settings_summary,
    build_paddle_smoke_result_summary,
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

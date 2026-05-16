from __future__ import annotations

from pathlib import Path

from app.core.config import AppConfig
from app.db.repository import JobHistoryRepository
from app.history.job_service import JobHistoryService
from app.ui.settings_utils import (
    build_db_summary,
    build_history_connection_summary,
    build_ocr_settings_summary,
    build_paddle_smoke_result_summary,
    build_retention_settings_summary,
    build_storage_summary,
    format_bytes,
    mask_sensitive_value,
    sanitize_cleanup_summary,
    sanitize_settings_display,
)
from app.core.standard_ocr import StandardOCRResult


def make_service(tmp_path: Path) -> JobHistoryService:
    config = AppConfig(
        app_db_path=tmp_path / "history.db",
        output_root=tmp_path / "data" / "outputs",
    )
    return JobHistoryService(repository=JobHistoryRepository(config=config), config=config)


def test_mask_sensitive_value_never_returns_secret():
    assert mask_sensitive_value("sk-test-secret") == "설정됨"
    assert "sk-test-secret" not in mask_sensitive_value("sk-test-secret")
    assert mask_sensitive_value(None) == "미설정"


def test_build_ocr_settings_summary_displays_mock_safely():
    config = AppConfig(ocr_provider="mock")

    summary = build_ocr_settings_summary(config)

    assert summary["OCR Provider"] == "mock"
    assert summary["Azure key"] == "미설정"
    assert summary["Azure endpoint"] == "미설정"
    assert summary["Azure ignore env proxy"] is False


def test_build_ocr_settings_summary_masks_azure_secret_values():
    config = AppConfig(
        ocr_provider="azure",
        azure_document_intelligence_key="real-secret-key",
        azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com",
    )

    summary = build_ocr_settings_summary(config)
    serialized = str(summary)

    assert summary["OCR Provider"] == "azure"
    assert summary["Azure key"] == "설정됨"
    assert summary["Azure endpoint"] == "설정됨"
    assert "real-secret-key" not in serialized
    assert "https://example" not in serialized


def test_build_paddle_smoke_result_summary_is_count_and_status_only():
    result = StandardOCRResult(
        id="paddle-smoke-result",
        source_file_id="source",
        source_file_name="sample.png",
        provider="paddleocr",
        provider_version="optional",
        engine_runtime="pc_local",
        status="failed",
        provider_fields={
            "provider_family": "paddleocr",
            "input_type": "image",
            "adapter_version": "paddle-standard-adapter-v1",
            "diagnostic_detail_code": "runtime_error",
        },
        warnings=["paddle_not_installed", "detail:runtime_error"],
        diagnostic_code="paddle_not_installed",
        created_at=__import__("datetime").datetime.now(),
    )

    summary = build_paddle_smoke_result_summary(result)
    serialized = str(summary)

    assert summary["provider"] == "paddleocr"
    assert summary["diagnostic_code"] == "paddle_not_installed"
    assert summary["diagnostic_detail_code"] == "runtime_error"
    assert summary["warning_codes"] == "paddle_not_installed, detail:runtime_error"
    assert summary["text_block_count"] == 0
    assert "sample.png" not in serialized
    assert "provider_fields" not in serialized


def test_build_retention_settings_summary_returns_safe_values():
    config = AppConfig(upload_retention_days=7, output_retention_days=14, cleanup_dry_run_default=True)

    summary = build_retention_settings_summary(config)

    assert summary["업로드 보관기간"] == "7일"
    assert summary["출력 보관기간"] == "14일"
    assert summary["cleanup dry-run 기본값"] is True
    assert "data/uploads" not in str(summary)


def test_format_bytes_uses_human_readable_units():
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"
    assert format_bytes("bad") == "0 B"


def test_build_storage_summary_returns_counts_without_file_names_or_paths(tmp_path):
    upload_root = tmp_path / "uploads"
    output_root = tmp_path / "outputs"
    upload_root.mkdir()
    output_root.mkdir()
    (upload_root / "input.bin").write_bytes(b"123")
    (output_root / "export.xlsx").write_bytes(b"12345")

    summary = build_storage_summary(upload_root=upload_root, output_root=output_root)
    serialized = str(summary)

    assert summary["업로드 파일 수"] == 1
    assert summary["출력 파일 수"] == 1
    assert summary["업로드 총 용량"] == "3 B"
    assert summary["출력 총 용량"] == "5 B"
    assert "input.bin" not in serialized
    assert "export.xlsx" not in serialized
    assert str(tmp_path) not in serialized


def test_build_db_summary_returns_job_count_and_recent_datetime(tmp_path):
    service = make_service(tmp_path)
    service.save_job_result(session_id="session-a", receipt_records=[], card_transactions=[])

    summary = build_db_summary(service)

    assert summary["DB 접근 가능 여부"] == "가능"
    assert summary["처리 이력 건수"] == 1
    assert summary["최근 처리일시"] != "-"
    assert str(tmp_path) not in str(summary)


def test_build_history_connection_summary_reports_repository_status(tmp_path):
    service = make_service(tmp_path)
    job = service.save_job_result(
        session_id="session-a",
        receipt_records=[],
        card_transactions=[],
        export_file={"export_file_name": "result.xlsx", "export_bytes": b"excel"},
    )

    summary = build_history_connection_summary(service)

    assert job["id"]
    assert summary["DB 접근 가능"] is True
    assert summary["processing_jobs 조회 가능"] is True
    assert summary["export_files 조회 가능"] is True
    assert summary["최근 job 존재"] is True


def test_sanitize_settings_display_hides_paths_and_sensitive_keys():
    value = {
        "api_key": "real-key",
        "token": "real-token",
        "raw_text": "ocr source",
        "path": r"C:\private\data\secret.txt",
        "safe": "mock",
    }

    sanitized = sanitize_settings_display(value)
    serialized = str(sanitized)

    assert sanitized["api_key"] == "설정됨"
    assert sanitized["token"] == "설정됨"
    assert sanitized["raw_text"] == "설정됨"
    assert sanitized["path"] == "[숨김]"
    assert sanitized["safe"] == "mock"
    assert "real-key" not in serialized
    assert "real-token" not in serialized
    assert "C:\\private" not in serialized


def test_sanitize_cleanup_summary_keeps_only_safe_summary_values():
    summary = sanitize_cleanup_summary(
        {
            "scanned_count": 2,
            "eligible_count": 1,
            "deleted_count": 0,
            "skipped_count": 1,
            "failed_count": 0,
            "deleted_bytes": 100,
            "dry_run": True,
            "status": "dry_run",
            "file_name": "input.bin",
            "path": r"C:\private\input.bin",
        }
    )

    serialized = str(summary)

    assert summary["dry_run"] is True
    assert summary["deleted_count"] == 0
    assert "input.bin" not in serialized
    assert "C:\\private" not in serialized

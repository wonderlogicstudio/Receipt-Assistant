from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

from app.core.config import AppConfig
from app.history.job_service import JobHistoryService
from app.ui.history_utils import format_history_datetime


SENSITIVE_KEY_PARTS = ("key", "secret", "token", "password", "endpoint", "raw_text", "raw_json")
HIDDEN_VALUE = "[숨김]"


def mask_sensitive_value(value: object) -> str:
    if value in {None, ""}:
        return "미설정"
    return "설정됨"


def build_ocr_settings_summary(config: AppConfig) -> dict[str, object]:
    return {
        "OCR Provider": config.ocr_provider or "mock",
        "Azure key": mask_sensitive_value(config.azure_document_intelligence_key),
        "Azure endpoint": mask_sensitive_value(config.azure_document_intelligence_endpoint),
        "Azure model": config.azure_document_intelligence_model_id,
        "API version": config.azure_document_intelligence_api_version,
    }


def build_retention_settings_summary(config: AppConfig) -> dict[str, object]:
    return {
        "업로드 보관기간": f"{config.upload_retention_days}일",
        "출력 보관기간": f"{config.output_retention_days}일",
        "cleanup dry-run 기본값": bool(config.cleanup_dry_run_default),
        "업로드 저장소": "설정됨",
        "출력 저장소": "설정됨",
    }


def build_storage_summary(*, upload_root: Path | str, output_root: Path | str) -> dict[str, object]:
    upload = _directory_summary(Path(upload_root))
    output = _directory_summary(Path(output_root))
    return {
        "업로드 파일 수": upload["file_count"],
        "업로드 총 용량": format_bytes(upload["total_bytes"]),
        "출력 파일 수": output["file_count"],
        "출력 총 용량": format_bytes(output["total_bytes"]),
        "업로드 저장소 상태": upload["status"],
        "출력 저장소 상태": output["status"],
    }


def build_db_summary(service: JobHistoryService) -> dict[str, object]:
    try:
        jobs = service.list_processing_jobs(limit=50, offset=0)
    except Exception:
        return {
            "DB 사용 여부": "사용",
            "DB 접근 가능 여부": "불가",
            "처리 이력 건수": 0,
            "최근 처리일시": "-",
        }

    latest = jobs[0] if jobs else {}
    return {
        "DB 사용 여부": "사용",
        "DB 접근 가능 여부": "가능",
        "처리 이력 건수": len(jobs),
        "최근 처리일시": format_history_datetime(latest.get("created_at") or latest.get("updated_at")),
    }


def build_history_connection_summary(service: JobHistoryService) -> dict[str, object]:
    summary = {
        "DB 접근 가능": False,
        "processing_jobs 조회 가능": False,
        "export_files 조회 가능": False,
        "최근 job 존재": False,
    }
    try:
        jobs = service.list_processing_jobs(limit=1, offset=0)
        summary["DB 접근 가능"] = True
        summary["processing_jobs 조회 가능"] = True
        if jobs:
            summary["최근 job 존재"] = True
            detail = service.get_processing_job_detail(str(jobs[0].get("id") or ""))
            summary["export_files 조회 가능"] = isinstance((detail or {}).get("export_files"), list)
        else:
            summary["export_files 조회 가능"] = True
    except Exception:
        return summary
    return summary


def format_bytes(value: object) -> str:
    try:
        size = int(value or 0)
    except (TypeError, ValueError):
        size = 0
    if size <= 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB")
    amount = float(size)
    unit_index = 0
    while amount >= 1024 and unit_index < len(units) - 1:
        amount /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(amount)} {units[unit_index]}"
    return f"{amount:.1f} {units[unit_index]}"


def sanitize_settings_display(value: object) -> object:
    if isinstance(value, Mapping):
        clean: dict[str, object] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                clean[key_text] = item if item in {"설정됨", "미설정"} else mask_sensitive_value(item)
            else:
                clean[key_text] = sanitize_settings_display(item)
        return clean
    if isinstance(value, list):
        return [sanitize_settings_display(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_settings_display(item) for item in value)
    if _looks_like_sensitive_text(value):
        return HIDDEN_VALUE
    return value


def sanitize_cleanup_summary(summary: Mapping[str, object]) -> dict[str, object]:
    allowed = {
        "scanned_count",
        "eligible_count",
        "deleted_count",
        "skipped_count",
        "failed_count",
        "deleted_bytes",
        "dry_run",
        "status",
    }
    return {key: sanitize_settings_display(summary.get(key)) for key in allowed if key in summary}


def _directory_summary(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"file_count": 0, "total_bytes": 0, "status": "아직 생성되지 않음"}
    if not path.is_dir():
        return {"file_count": 0, "total_bytes": 0, "status": "확인 필요"}

    file_count = 0
    total_bytes = 0
    for candidate in _safe_files(path):
        file_count += 1
        try:
            total_bytes += candidate.stat().st_size
        except OSError:
            continue
    return {"file_count": file_count, "total_bytes": total_bytes, "status": "파일 없음" if file_count == 0 else "사용 중"}


def _safe_files(path: Path) -> Iterable[Path]:
    try:
        candidates = path.rglob("*")
        for candidate in candidates:
            if candidate.is_file() and not candidate.is_symlink():
                yield candidate
    except OSError:
        return


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _looks_like_sensitive_text(value: object) -> bool:
    if value in {None, ""}:
        return False
    text = str(value)
    lowered = text.lower()
    if any(part in lowered for part in ("raw_text", "raw_json", "api_key", "secret", "token")):
        return True
    if "://" in text:
        return True
    if "\\" in text or "/" in text:
        if ":" in text[:4] or text.startswith("/") or "data/uploads" in lowered or "data/outputs" in lowered:
            return True
    return False

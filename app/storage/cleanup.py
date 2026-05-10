from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from app.core.config import AppConfig, get_config
from app.core.exceptions import InvalidSessionIdError
from app.storage.file_store import SESSION_ID_PATTERN


CleanupSummary = dict[str, int | bool | str]
UnlinkFile = Callable[[Path], None]


def cleanup_old_upload_files(
    *,
    config: AppConfig | None = None,
    dry_run: bool = True,
    now: float | None = None,
    remove_empty_dirs: bool = True,
) -> CleanupSummary:
    safe_config = config or get_config()
    return cleanup_old_files_in_dir(
        safe_config.upload_root,
        retention_days=safe_config.upload_retention_days,
        dry_run=dry_run,
        now=now,
        remove_empty_dirs=remove_empty_dirs,
    )


def cleanup_old_output_files(
    *,
    config: AppConfig | None = None,
    dry_run: bool = True,
    now: float | None = None,
    remove_empty_dirs: bool = True,
) -> CleanupSummary:
    safe_config = config or get_config()
    return cleanup_old_files_in_dir(
        safe_config.output_root,
        retention_days=safe_config.output_retention_days,
        dry_run=dry_run,
        now=now,
        remove_empty_dirs=remove_empty_dirs,
    )


def cleanup_old_files_in_dir(
    base_dir: str | Path,
    *,
    retention_days: int,
    dry_run: bool = True,
    now: float | None = None,
    remove_empty_dirs: bool = False,
    unlink_file: UnlinkFile | None = None,
) -> CleanupSummary:
    if retention_days <= 0:
        raise ValueError("retention_days must be greater than 0")

    base_path = Path(base_dir)
    resolved_base = base_path.resolve()
    if not base_path.exists():
        return _summary(dry_run=dry_run, status="completed", message="Cleanup completed.")
    if not base_path.is_dir():
        return _summary(dry_run=dry_run, status="failed", message="Cleanup base is not a directory.", failed_count=1)

    threshold = (now if now is not None else time.time()) - (retention_days * 24 * 60 * 60)
    unlink = unlink_file or _unlink_file
    result = _summary(dry_run=dry_run, status="dry_run" if dry_run else "completed", message=_message(dry_run))

    for candidate in sorted(base_path.rglob("*")):
        if candidate.is_dir():
            continue

        result["scanned_count"] = int(result["scanned_count"]) + 1

        if not _is_candidate_file(candidate, resolved_base):
            result["skipped_count"] = int(result["skipped_count"]) + 1
            continue

        try:
            stat = candidate.stat()
        except FileNotFoundError:
            result["skipped_count"] = int(result["skipped_count"]) + 1
            continue
        except OSError:
            result["failed_count"] = int(result["failed_count"]) + 1
            continue

        if stat.st_mtime >= threshold:
            result["skipped_count"] = int(result["skipped_count"]) + 1
            continue

        result["eligible_count"] = int(result["eligible_count"]) + 1
        result["deleted_bytes"] = int(result["deleted_bytes"]) + int(stat.st_size)
        if dry_run:
            continue

        try:
            unlink(candidate)
            result["deleted_count"] = int(result["deleted_count"]) + 1
        except FileNotFoundError:
            result["skipped_count"] = int(result["skipped_count"]) + 1
        except (PermissionError, OSError):
            result["failed_count"] = int(result["failed_count"]) + 1

    if remove_empty_dirs and not dry_run:
        _remove_empty_child_dirs(base_path, resolved_base)

    if int(result["failed_count"]):
        result["status"] = "completed_with_failures"
        result["message"] = "Cleanup completed with failures."
    return result


def cleanup_session_files(
    session_id: str,
    *,
    config: AppConfig | None = None,
    dry_run: bool = True,
    remove_empty_dirs: bool = True,
) -> CleanupSummary:
    safe_config = config or get_config()
    _validate_session_id(session_id)

    upload_root = safe_config.upload_root.resolve()
    session_dir = (safe_config.upload_root / session_id).resolve()
    if not is_safe_child_path(session_dir, upload_root):
        raise InvalidSessionIdError("session_id가 업로드 폴더 밖을 가리킬 수 없습니다.")

    return cleanup_old_files_in_dir(
        session_dir,
        retention_days=1,
        dry_run=dry_run,
        now=float("inf"),
        remove_empty_dirs=remove_empty_dirs,
    )


def is_safe_child_path(path: str | Path, base_dir: str | Path) -> bool:
    resolved_path = Path(path).resolve()
    resolved_base = Path(base_dir).resolve()
    return resolved_path == resolved_base or resolved_base in resolved_path.parents


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise InvalidSessionIdError("session_id 형식이 올바르지 않습니다.")


def _is_candidate_file(path: Path, resolved_base: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    if not is_safe_child_path(resolved, resolved_base):
        return False
    if path.is_symlink():
        return False
    return not _is_hidden_or_system_name(path)


def _is_hidden_or_system_name(path: Path) -> bool:
    return any(part.startswith(".") or part.startswith("~$") for part in path.parts)


def _unlink_file(path: Path) -> None:
    path.unlink()


def _remove_empty_child_dirs(base_path: Path, resolved_base: Path) -> None:
    for directory in sorted((path for path in base_path.rglob("*") if path.is_dir()), reverse=True):
        if not is_safe_child_path(directory, resolved_base):
            continue
        try:
            directory.rmdir()
        except OSError:
            pass


def _summary(
    *,
    dry_run: bool,
    status: str,
    message: str,
    scanned_count: int = 0,
    eligible_count: int = 0,
    deleted_count: int = 0,
    skipped_count: int = 0,
    failed_count: int = 0,
    deleted_bytes: int = 0,
) -> CleanupSummary:
    return {
        "scanned_count": scanned_count,
        "eligible_count": eligible_count,
        "deleted_count": deleted_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "deleted_bytes": deleted_bytes,
        "dry_run": dry_run,
        "status": status,
        "message": message,
    }


def _message(dry_run: bool) -> str:
    if dry_run:
        return "Cleanup dry run completed."
    return "Cleanup completed."

from __future__ import annotations

from pathlib import Path

from app.core.config import AppConfig, get_config
from app.core.exceptions import InvalidSessionIdError
from app.storage.file_store import SESSION_ID_PATTERN


def cleanup_session_files(
    session_id: str,
    *,
    config: AppConfig | None = None,
    dry_run: bool = True,
) -> list[str]:
    safe_config = config or get_config()
    _validate_session_id(session_id)

    upload_root = safe_config.upload_root.resolve()
    session_dir = (upload_root / session_id).resolve()
    if not _is_within_directory(session_dir, upload_root):
        raise InvalidSessionIdError("session_id가 업로드 폴더 밖을 가리킬 수 없습니다.")

    if not session_dir.exists():
        return []

    file_paths = sorted(path for path in session_dir.rglob("*") if path.is_file())
    relative_candidates = [_safe_relative_upload_path(path, upload_root, safe_config.upload_relative_root) for path in file_paths]

    if dry_run:
        return relative_candidates

    for path in file_paths:
        resolved_path = path.resolve()
        if _is_within_directory(resolved_path, upload_root):
            resolved_path.unlink()

    for directory in sorted((path for path in session_dir.rglob("*") if path.is_dir()), reverse=True):
        if _is_within_directory(directory.resolve(), upload_root):
            try:
                directory.rmdir()
            except OSError:
                pass
    try:
        session_dir.rmdir()
    except OSError:
        pass

    return relative_candidates


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise InvalidSessionIdError("session_id 형식이 올바르지 않습니다.")


def _is_within_directory(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _safe_relative_upload_path(path: Path, upload_root: Path, upload_relative_root: Path) -> str:
    relative_to_root = path.relative_to(upload_root)
    return (upload_relative_root / relative_to_root).as_posix()

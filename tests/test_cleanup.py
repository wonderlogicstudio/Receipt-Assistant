from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from app.core.config import (
    DEFAULT_OUTPUT_RETENTION_DAYS,
    DEFAULT_UPLOAD_RETENTION_DAYS,
    AppConfig,
    get_config,
)
from app.core.exceptions import InvalidSessionIdError
from app.storage.cleanup import (
    cleanup_old_files_in_dir,
    cleanup_old_output_files,
    cleanup_old_upload_files,
    cleanup_session_files,
    is_safe_child_path,
)


NOW = 2_000_000_000.0
DAY = 24 * 60 * 60


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        upload_root=tmp_path / "data" / "uploads",
        upload_relative_root=Path("data/uploads"),
        output_root=tmp_path / "data" / "outputs",
        upload_retention_days=7,
        output_retention_days=7,
        cleanup_dry_run_default=True,
    )


def write_file(path: Path, content: bytes = b"sample", *, age_days: int = 0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    timestamp = NOW - (age_days * DAY)
    os.utime(path, (timestamp, timestamp))
    return path


def assert_private_details_not_exposed(summary: dict[str, object], *private_values: str) -> None:
    serialized = str(summary)
    for value in private_values:
        assert value not in serialized


def test_old_upload_files_dry_run_does_not_delete(tmp_path):
    config = make_config(tmp_path)
    old_file = write_file(config.upload_root / "session-a" / "receipt.jpg", age_days=9)

    summary = cleanup_old_upload_files(config=config, dry_run=True, now=NOW)

    assert old_file.exists()
    assert summary["dry_run"] is True
    assert summary["scanned_count"] == 1
    assert summary["eligible_count"] == 1
    assert summary["deleted_count"] == 0
    assert summary["deleted_bytes"] == 6
    assert_private_details_not_exposed(summary, "receipt.jpg", str(tmp_path))


def test_old_upload_files_delete_when_dry_run_false(tmp_path):
    config = make_config(tmp_path)
    old_file = write_file(config.upload_root / "session-a" / "receipt.jpg", age_days=9)

    summary = cleanup_old_upload_files(config=config, dry_run=False, now=NOW)

    assert not old_file.exists()
    assert summary["dry_run"] is False
    assert summary["eligible_count"] == 1
    assert summary["deleted_count"] == 1
    assert summary["failed_count"] == 0


def test_recent_upload_files_are_kept(tmp_path):
    config = make_config(tmp_path)
    recent_file = write_file(config.upload_root / "session-a" / "receipt.jpg", age_days=2)

    summary = cleanup_old_upload_files(config=config, dry_run=False, now=NOW)

    assert recent_file.exists()
    assert summary["eligible_count"] == 0
    assert summary["deleted_count"] == 0
    assert summary["skipped_count"] == 1


def test_old_output_files_delete_when_dry_run_false(tmp_path):
    config = make_config(tmp_path)
    old_file = write_file(config.output_root / "receipt_summary.xlsx", age_days=8)

    summary = cleanup_old_output_files(config=config, dry_run=False, now=NOW)

    assert not old_file.exists()
    assert summary["scanned_count"] == 1
    assert summary["eligible_count"] == 1
    assert summary["deleted_count"] == 1


def test_recent_output_files_are_kept(tmp_path):
    config = make_config(tmp_path)
    recent_file = write_file(config.output_root / "receipt_summary.xlsx", age_days=1)

    summary = cleanup_old_output_files(config=config, dry_run=False, now=NOW)

    assert recent_file.exists()
    assert summary["eligible_count"] == 0
    assert summary["deleted_count"] == 0


def test_paths_outside_upload_and_output_dirs_are_not_safe(tmp_path):
    config = make_config(tmp_path)
    outside = tmp_path / "outside" / "file.txt"

    assert not is_safe_child_path(outside, config.upload_root)
    assert not is_safe_child_path(outside, config.output_root)


def test_session_cleanup_rejects_path_traversal(tmp_path):
    config = make_config(tmp_path)

    with pytest.raises(InvalidSessionIdError):
        cleanup_session_files("../outside", config=config)


def test_session_cleanup_rejects_absolute_path(tmp_path):
    config = make_config(tmp_path)

    with pytest.raises(InvalidSessionIdError):
        cleanup_session_files(str(tmp_path.resolve()), config=config)


def test_session_cleanup_returns_summary_without_paths_or_names(tmp_path):
    config = make_config(tmp_path)
    target = write_file(config.upload_root / "session-a" / "receipt.jpg", age_days=0)

    summary = cleanup_session_files("session-a", config=config, dry_run=True)

    assert target.exists()
    assert set(summary) == {
        "scanned_count",
        "eligible_count",
        "deleted_count",
        "skipped_count",
        "failed_count",
        "deleted_bytes",
        "dry_run",
        "status",
        "message",
    }
    assert summary["eligible_count"] == 1
    assert_private_details_not_exposed(summary, "receipt.jpg", "session-a", str(tmp_path))


def test_missing_file_during_delete_is_handled_safely(tmp_path):
    config = make_config(tmp_path)
    old_file = write_file(config.upload_root / "session-a" / "receipt.jpg", age_days=9)

    def remove_before_unlink(path: Path) -> None:
        path.unlink()
        raise FileNotFoundError

    summary = cleanup_old_files_in_dir(
        config.upload_root,
        retention_days=7,
        dry_run=False,
        now=NOW,
        unlink_file=remove_before_unlink,
    )

    assert not old_file.exists()
    assert summary["eligible_count"] == 1
    assert summary["deleted_count"] == 0
    assert summary["skipped_count"] == 1
    assert summary["failed_count"] == 0


def test_permission_error_is_counted_without_stopping_cleanup(tmp_path):
    config = make_config(tmp_path)
    first = write_file(config.upload_root / "session-a" / "first.jpg", age_days=9)
    second = write_file(config.upload_root / "session-a" / "second.jpg", age_days=9)

    def fail_one(path: Path) -> None:
        if path.name == "first.jpg":
            raise PermissionError
        path.unlink()

    summary = cleanup_old_files_in_dir(
        config.upload_root,
        retention_days=7,
        dry_run=False,
        now=NOW,
        unlink_file=fail_one,
    )

    assert first.exists()
    assert not second.exists()
    assert summary["eligible_count"] == 2
    assert summary["deleted_count"] == 1
    assert summary["failed_count"] == 1
    assert summary["status"] == "completed_with_failures"


def test_symlink_is_skipped_when_supported(tmp_path):
    config = make_config(tmp_path)
    outside = write_file(tmp_path / "outside" / "secret.txt", age_days=9)
    link = config.upload_root / "session-a" / "linked.txt"
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is not available in this environment")

    summary = cleanup_old_upload_files(config=config, dry_run=False, now=NOW)

    assert link.exists()
    assert outside.exists()
    assert summary["skipped_count"] == 1


def test_hidden_and_system_like_files_are_skipped(tmp_path):
    config = make_config(tmp_path)
    hidden = write_file(config.upload_root / "session-a" / ".hidden", age_days=9)
    office_temp = write_file(config.upload_root / "session-a" / "~$receipt.xlsx", age_days=9)

    summary = cleanup_old_upload_files(config=config, dry_run=False, now=NOW)

    assert hidden.exists()
    assert office_temp.exists()
    assert summary["eligible_count"] == 0
    assert summary["skipped_count"] == 2


def test_config_reads_cleanup_environment_and_defaults_invalid_retention(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UPLOAD_DIR", "custom/uploads")
    monkeypatch.setenv("OUTPUT_DIR", "custom/outputs")
    monkeypatch.setenv("UPLOAD_RETENTION_DAYS", "invalid")
    monkeypatch.setenv("OUTPUT_RETENTION_DAYS", "0")
    monkeypatch.setenv("CLEANUP_DRY_RUN_DEFAULT", "false")

    config = get_config()

    assert config.upload_root == Path("custom/uploads")
    assert config.output_root == Path("custom/outputs")
    assert config.upload_retention_days == DEFAULT_UPLOAD_RETENTION_DAYS
    assert config.output_retention_days == DEFAULT_OUTPUT_RETENTION_DAYS
    assert config.cleanup_dry_run_default is False


def test_cleanup_omitted_dry_run_stays_safe_even_if_config_is_false(tmp_path):
    config = AppConfig(
        upload_root=tmp_path / "data" / "uploads",
        upload_relative_root=Path("data/uploads"),
        output_root=tmp_path / "data" / "outputs",
        upload_retention_days=7,
        output_retention_days=7,
        cleanup_dry_run_default=False,
    )
    write_file(config.upload_root / "session-a" / "receipt.jpg", age_days=9)

    summary = cleanup_old_upload_files(config=config, now=NOW)

    assert summary["dry_run"] is True
    assert summary["deleted_count"] == 0

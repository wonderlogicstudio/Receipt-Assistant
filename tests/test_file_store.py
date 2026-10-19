from __future__ import annotations

import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.config import AppConfig
from app.core.exceptions import FileStoreError, InvalidSessionIdError, UnsupportedFileTypeError, UploadFileTooLargeError
from dataclasses import replace
from app.storage.file_store import FileStore, sanitize_filename


class FakeUploadedFile(BytesIO):
    def __init__(self, name: str, content: bytes = b"sample") -> None:
        super().__init__(content)
        self.name = name
        self.size = len(content)


def make_store(tmp_path: Path, max_upload_size_bytes: int = 1024) -> FileStore:
    return FileStore(
        AppConfig(
            upload_root=tmp_path / "uploads",
            upload_relative_root=Path("data/uploads"),
            max_upload_size_bytes=max_upload_size_bytes,
        )
    )


def test_sanitize_filename_keeps_safe_name_readable():
    assert sanitize_filename("  receipt  01.JPG ") == "receipt_01.jpg"


def test_sanitize_filename_removes_dangerous_path_parts_and_characters():
    safe_name = sanitize_filename(r"..\..\C:\private folder\영수증 ../bad!? name.pdf")

    assert safe_name.endswith(".pdf")
    assert "/" not in safe_name
    assert "\\" not in safe_name
    assert ".." not in safe_name
    assert " " not in safe_name
    assert "!" not in safe_name
    assert "?" not in safe_name


@pytest.mark.parametrize("file_name", ["receipt.jpg", "receipt.jpeg", "receipt.png", "receipt.pdf", "card.xlsx", "card.csv"])
def test_save_uploaded_file_allows_configured_extensions(tmp_path, file_name):
    store = make_store(tmp_path)

    metadata = store.save_uploaded_file(FakeUploadedFile(file_name), session_id="session-a")

    assert metadata.original_file_name == file_name
    assert metadata.file_extension == Path(file_name).suffix
    assert metadata.session_id == "session-a"
    assert (tmp_path / "uploads" / "session-a" / metadata.stored_file_name).exists()


def test_save_uploaded_file_rejects_unsupported_extension(tmp_path):
    store = make_store(tmp_path)

    with pytest.raises(UnsupportedFileTypeError):
        store.save_uploaded_file(FakeUploadedFile("receipt.exe"), session_id="session-a")


def test_save_uploaded_file_rejects_unsafe_session_id(tmp_path):
    store = make_store(tmp_path)

    with pytest.raises(InvalidSessionIdError):
        store.save_uploaded_file(FakeUploadedFile("receipt.pdf"), session_id="../unsafe")


def test_save_uploaded_file_rejects_file_over_size_limit(tmp_path):
    store = make_store(tmp_path, max_upload_size_bytes=3)

    with pytest.raises(UploadFileTooLargeError):
        store.save_uploaded_file(FakeUploadedFile("receipt.pdf", b"1234"), session_id="session-a")


def test_session_id_folders_are_separated(tmp_path):
    store = make_store(tmp_path)

    first = store.save_uploaded_file(FakeUploadedFile("receipt.pdf", b"first"), session_id="session-a")
    second = store.save_uploaded_file(FakeUploadedFile("receipt.pdf", b"second"), session_id="session-b")

    assert first.session_id == "session-a"
    assert second.session_id == "session-b"
    assert store.resolve_stored_path(first).parent.name == "session-a"
    assert store.resolve_stored_path(second).parent.name == "session-b"


def test_same_original_file_name_does_not_overwrite_existing_file(tmp_path):
    store = make_store(tmp_path)

    first = store.save_uploaded_file(FakeUploadedFile("receipt.pdf", b"first"), session_id="session-a")
    second = store.save_uploaded_file(FakeUploadedFile("receipt.pdf", b"second"), session_id="session-a")

    assert first.stored_file_name != second.stored_file_name
    assert store.resolve_stored_path(first).read_bytes() == b"first"
    assert store.resolve_stored_path(second).read_bytes() == b"second"


def test_stored_file_resolution_cannot_leave_upload_root(tmp_path):
    store = make_store(tmp_path)
    metadata = store.save_uploaded_file(FakeUploadedFile("receipt.jpg"), "session-a")
    for stored_name in ("../../private.jpg", "../session-b/private.jpg", str((tmp_path / "private.jpg").resolve())):
        with pytest.raises(FileStoreError):
            store.resolve_stored_path(replace(metadata, stored_file_name=stored_name))


def test_original_filename_metadata_does_not_retain_client_directory(tmp_path):
    metadata = make_store(tmp_path).save_uploaded_file(FakeUploadedFile(r"C:\private\receipt.jpg"), "session-a")
    assert metadata.original_file_name == "receipt.jpg"


def test_saved_metadata_contains_required_fields_and_relative_path(tmp_path):
    store = make_store(tmp_path)

    metadata = store.save_uploaded_file(FakeUploadedFile(r"C:\private\receipt.pdf", b"data"), session_id="session-a")
    metadata_dict = metadata.to_dict()

    assert metadata_dict["original_file_name"] == "receipt.pdf"
    assert metadata_dict["stored_file_name"].endswith(".pdf")
    assert metadata_dict["stored_relative_path"].startswith("data/uploads/session-a/")
    assert metadata_dict["file_size_bytes"] == 4
    assert metadata_dict["session_id"] == "session-a"
    assert not Path(metadata.stored_relative_path).is_absolute()
    assert str(tmp_path) not in metadata.stored_relative_path


def test_missing_session_id_creates_uuid_based_session(tmp_path):
    store = make_store(tmp_path)

    metadata = store.save_uploaded_file(FakeUploadedFile("receipt.pdf"))

    assert len(metadata.session_id) == 32
    assert metadata.session_id.isalnum()
    assert store.resolve_stored_path(metadata).exists()


def test_default_data_upload_file_is_ignored_by_git_status():
    store = FileStore()
    session_id = f"pytest-{uuid4().hex}"
    metadata = store.save_uploaded_file(FakeUploadedFile("receipt.pdf", b"data"), session_id=session_id)
    session_dir = Path("data/uploads") / session_id

    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", metadata.stored_relative_path],
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ""
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)

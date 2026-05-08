from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from app.core.config import AppConfig, get_config
from app.core.exceptions import InvalidSessionIdError, UnsupportedFileTypeError, UploadFileTooLargeError


SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class StoredFileMetadata:
    original_file_name: str
    stored_file_name: str
    stored_relative_path: str
    file_extension: str
    file_size_bytes: int
    session_id: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class FileStore:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or get_config()

    def create_session_id(self) -> str:
        return uuid4().hex

    def get_or_create_session_id(self, session_id: str | None = None) -> str:
        if not session_id:
            return self.create_session_id()
        self._validate_session_id(session_id)
        return session_id

    def save_uploaded_file(self, uploaded_file, session_id: str | None = None) -> StoredFileMetadata:
        safe_session_id = self.get_or_create_session_id(session_id)
        original_file_name = str(getattr(uploaded_file, "name", "uploaded_file")).strip() or "uploaded_file"
        safe_file_name = sanitize_filename(original_file_name)
        file_extension = Path(safe_file_name).suffix.lower()

        if file_extension not in self.config.allowed_upload_extensions:
            raise UnsupportedFileTypeError(f"지원하지 않는 파일 형식입니다: {file_extension or '확장자 없음'}")

        data = self._read_uploaded_file(uploaded_file)
        file_size_bytes = len(data)
        if file_size_bytes > self.config.max_upload_size_bytes:
            raise UploadFileTooLargeError("업로드 파일 크기가 설정된 제한을 초과했습니다.")

        stored_file_name = self._build_unique_file_name(safe_file_name)
        session_dir = self._session_dir(safe_session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        stored_path = session_dir / stored_file_name
        stored_path.write_bytes(data)

        stored_relative_path = self.config.upload_relative_root / safe_session_id / stored_file_name
        return StoredFileMetadata(
            original_file_name=original_file_name,
            stored_file_name=stored_file_name,
            stored_relative_path=_as_posix(stored_relative_path),
            file_extension=file_extension,
            file_size_bytes=file_size_bytes,
            session_id=safe_session_id,
        )

    def resolve_stored_path(self, metadata: StoredFileMetadata) -> Path:
        self._validate_session_id(metadata.session_id)
        return self._session_dir(metadata.session_id) / metadata.stored_file_name

    def _session_dir(self, session_id: str) -> Path:
        root = self.config.upload_root
        target = root / session_id
        self._validate_session_id(session_id)
        return target

    def _validate_session_id(self, session_id: str) -> None:
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            raise InvalidSessionIdError("session_id는 영문, 숫자, 하이픈, 언더스코어만 사용할 수 있습니다.")

    def _read_uploaded_file(self, uploaded_file) -> bytes:
        if hasattr(uploaded_file, "getbuffer"):
            return bytes(uploaded_file.getbuffer())
        if hasattr(uploaded_file, "getvalue"):
            return bytes(uploaded_file.getvalue())
        if hasattr(uploaded_file, "read"):
            position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else None
            data = uploaded_file.read()
            if position is not None and hasattr(uploaded_file, "seek"):
                uploaded_file.seek(position)
            return bytes(data)
        raise TypeError("uploaded_file은 bytes를 읽을 수 있는 객체여야 합니다.")

    def _build_unique_file_name(self, safe_file_name: str) -> str:
        path = Path(safe_file_name)
        token = uuid4().hex
        return f"{path.stem}_{token}{path.suffix.lower()}"


def sanitize_filename(file_name: str) -> str:
    candidate = str(file_name).replace("\\", "/").strip()
    base_name = candidate.split("/")[-1].strip()
    if re.match(r"^[A-Za-z]:", base_name):
        base_name = base_name[2:].strip()

    stem = Path(base_name).stem
    suffix = Path(base_name).suffix.lower()
    safe_stem = unicodedata.normalize("NFKC", stem)
    safe_stem = re.sub(r"\s+", "_", safe_stem)
    safe_stem = re.sub(r"[^0-9A-Za-z._\-\uAC00-\uD7A3]+", "_", safe_stem)
    safe_stem = safe_stem.strip("._-")

    if not safe_stem:
        safe_stem = "uploaded"

    return f"{safe_stem[:80]}{suffix}"


def _as_posix(path: Path) -> str:
    return path.as_posix()

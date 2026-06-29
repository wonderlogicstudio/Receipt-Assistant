from __future__ import annotations

import csv
import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from app.classifier.merchant_normalizer import normalize_merchant_name, normalize_road_address, sanitize_optional_text
from app.db.merchant_repository import MerchantMasterInput, MerchantRepository


PUBLIC_MERCHANT_SOURCE = "public_store_data"

MERCHANT_NAME_COLUMN = "상호명"
BRANCH_COLUMN = "지점명"
CATEGORY_LARGE_COLUMN = "상권업종대분류명"
CATEGORY_MEDIUM_COLUMN = "상권업종중분류명"
CATEGORY_SMALL_COLUMN = "상권업종소분류명"
ROAD_NAME_COLUMN = "도로명"
BUILDING_MAIN_NUMBER_COLUMN = "건물본번지"
BUILDING_SUB_NUMBER_COLUMN = "건물부번지"
BUILDING_NAME_COLUMN = "건물명"
ROAD_ADDRESS_COLUMN = "도로명주소"

ALLOWED_PUBLIC_STORE_COLUMNS = (
    MERCHANT_NAME_COLUMN,
    BRANCH_COLUMN,
    CATEGORY_LARGE_COLUMN,
    CATEGORY_MEDIUM_COLUMN,
    CATEGORY_SMALL_COLUMN,
    ROAD_NAME_COLUMN,
    BUILDING_MAIN_NUMBER_COLUMN,
    BUILDING_SUB_NUMBER_COLUMN,
    BUILDING_NAME_COLUMN,
    ROAD_ADDRESS_COLUMN,
)

BLOCKED_COLUMN_TOKENS = (
    "전화",
    "tel",
    "phone",
    "대표",
    "대표자",
    "owner",
    "성명",
    "휴대",
    "mobile",
)


@dataclass(frozen=True)
class MerchantImportResult:
    source_batch_id: str
    imported_row_count: int
    skipped_row_count: int
    duplicate_file: bool = False
    source_file_name: str | None = None
    source_file_hash: str | None = None
    scanned_row_count: int = 0
    skipped_duplicate_row_count: int = 0
    skipped_invalid_row_count: int = 0
    elapsed_seconds: float = 0.0
    rows_per_second: float = 0.0


@dataclass(frozen=True)
class MerchantCsvScanResult:
    source_file_hash: str
    row_count: int
    valid_row_count: int
    skipped_row_count: int


class PublicMerchantCsvImporter:
    def __init__(self, repository: MerchantRepository) -> None:
        self.repository = repository

    def import_csv(
        self,
        csv_path: Path | str,
        *,
        encoding: str = "utf-8-sig",
        source_batch_id: str | None = None,
        source_file_name: str | None = None,
        batch_size: int = 5000,
    ) -> MerchantImportResult:
        started_at = time.perf_counter()
        path = Path(csv_path)
        safe_file_name = Path(source_file_name or path.name).name
        batch_id = source_batch_id or str(uuid4())
        scan = self.scan_csv(csv_path, encoding=encoding)

        if self.repository.has_source_file_hash(PUBLIC_MERCHANT_SOURCE, scan.source_file_hash):
            self.repository.log_source_import(
                source_name=PUBLIC_MERCHANT_SOURCE,
                source_file_name=safe_file_name,
                source_file_hash=scan.source_file_hash,
                source_batch_id=batch_id,
                imported_row_count=0,
                skipped_row_count=scan.row_count,
                skipped_invalid_row_count=scan.skipped_row_count,
                duplicate_file=True,
                note="duplicate_file",
            )
            elapsed_seconds = _elapsed_seconds(started_at)
            return MerchantImportResult(
                source_batch_id=batch_id,
                imported_row_count=0,
                skipped_row_count=scan.row_count,
                skipped_duplicate_row_count=scan.valid_row_count,
                skipped_invalid_row_count=scan.skipped_row_count,
                duplicate_file=True,
                source_file_name=safe_file_name,
                source_file_hash=scan.source_file_hash,
                scanned_row_count=scan.row_count,
                elapsed_seconds=elapsed_seconds,
                rows_per_second=_rows_per_second(scan.row_count, elapsed_seconds),
            )

        imported = self.repository.add_masters_stream(
            self._iter_valid_items(path, encoding=encoding, source_batch_id=batch_id),
            chunk_size=batch_size,
        )
        skipped_duplicate = max(0, scan.valid_row_count - imported)
        skipped = skipped_duplicate + scan.skipped_row_count
        elapsed_seconds = _elapsed_seconds(started_at)

        self.repository.log_source_import(
            source_name=PUBLIC_MERCHANT_SOURCE,
            source_file_name=safe_file_name,
            source_file_hash=scan.source_file_hash,
            source_batch_id=batch_id,
            imported_row_count=imported,
            skipped_row_count=skipped,
            skipped_invalid_row_count=scan.skipped_row_count,
        )
        return MerchantImportResult(
            source_batch_id=batch_id,
            imported_row_count=imported,
            skipped_row_count=skipped,
            skipped_duplicate_row_count=skipped_duplicate,
            skipped_invalid_row_count=scan.skipped_row_count,
            duplicate_file=False,
            source_file_name=safe_file_name,
            source_file_hash=scan.source_file_hash,
            scanned_row_count=scan.row_count,
            elapsed_seconds=elapsed_seconds,
            rows_per_second=_rows_per_second(scan.row_count, elapsed_seconds),
        )

    def scan_csv(
        self,
        csv_path: Path | str,
        *,
        encoding: str = "utf-8-sig",
    ) -> MerchantCsvScanResult:
        hasher = hashlib.sha256()
        row_count = 0
        valid_row_count = 0
        skipped_row_count = 0
        with Path(csv_path).open("r", encoding=encoding, newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                row_count += 1
                item = self._row_to_item(row, source_batch_id="scan")
                if item is None:
                    skipped_row_count += 1
                    hasher.update(b"invalid\n")
                    continue
                valid_row_count += 1
                hasher.update(item.source_row_hash.encode("utf-8"))
                hasher.update(b"\n")
        return MerchantCsvScanResult(
            source_file_hash=hasher.hexdigest(),
            row_count=row_count,
            valid_row_count=valid_row_count,
            skipped_row_count=skipped_row_count,
        )

    def _row_to_item(self, row: dict[str, str], *, source_batch_id: str) -> MerchantMasterInput | None:
        allowed_values = _allowed_values(row)
        merchant_name = allowed_values[MERCHANT_NAME_COLUMN]
        if not merchant_name:
            return None
        source_hash = _safe_row_hash(allowed_values)
        return MerchantMasterInput(
            merchant_name=merchant_name,
            branch_name=allowed_values[BRANCH_COLUMN],
            area_hint=_area_hint_from_road_address(allowed_values[ROAD_ADDRESS_COLUMN]),
            category_large=allowed_values[CATEGORY_LARGE_COLUMN],
            category_medium=allowed_values[CATEGORY_MEDIUM_COLUMN],
            category_small=allowed_values[CATEGORY_SMALL_COLUMN],
            road_name=allowed_values[ROAD_NAME_COLUMN],
            building_main_number=allowed_values[BUILDING_MAIN_NUMBER_COLUMN],
            building_sub_number=allowed_values[BUILDING_SUB_NUMBER_COLUMN],
            building_name=allowed_values[BUILDING_NAME_COLUMN],
            road_address=allowed_values[ROAD_ADDRESS_COLUMN],
            source=PUBLIC_MERCHANT_SOURCE,
            source_row_hash=source_hash,
            source_batch_id=source_batch_id,
        )

    def _iter_valid_items(
        self,
        csv_path: Path,
        *,
        encoding: str,
        source_batch_id: str,
    ) -> Iterator[MerchantMasterInput]:
        with csv_path.open("r", encoding=encoding, newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                item = self._row_to_item(row, source_batch_id=source_batch_id)
                if item is not None:
                    yield item


def _allowed_values(row: dict[str, str]) -> dict[str, str | None]:
    blocked_columns = _blocked_columns(row)
    values: dict[str, str | None] = {}
    for column in ALLOWED_PUBLIC_STORE_COLUMNS:
        values[column] = None if column in blocked_columns else sanitize_optional_text(row.get(column), max_length=220)
    return values


def _area_hint_from_road_address(road_address: str | None) -> str | None:
    address = sanitize_optional_text(road_address, max_length=220)
    if not address:
        return None
    parts = address.split()
    if len(parts) >= 2:
        return " ".join(parts[:2])
    return parts[0] if parts else None


def _safe_row_hash(values: dict[str, str | None]) -> str:
    merchant_name = normalize_merchant_name(values.get(MERCHANT_NAME_COLUMN))
    normalized_road_address = normalize_road_address(values.get(ROAD_ADDRESS_COLUMN))
    payload_values = {
        "normalized_merchant_name": merchant_name,
        "branch_name": values.get(BRANCH_COLUMN) or "",
        "category_large": values.get(CATEGORY_LARGE_COLUMN) or "",
        "category_medium": values.get(CATEGORY_MEDIUM_COLUMN) or "",
        "category_small": values.get(CATEGORY_SMALL_COLUMN) or "",
        "road_name": values.get(ROAD_NAME_COLUMN) or "",
        "building_main_number": values.get(BUILDING_MAIN_NUMBER_COLUMN) or "",
        "building_sub_number": values.get(BUILDING_SUB_NUMBER_COLUMN) or "",
        "building_name": values.get(BUILDING_NAME_COLUMN) or "",
        "normalized_road_address": normalized_road_address,
    }
    payload = "|".join(f"{key}={payload_values[key]}" for key in sorted(payload_values))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _blocked_columns(row: dict[str, str]) -> set[str]:
    result: set[str] = set()
    for column in row:
        normalized = str(column).strip().lower()
        if any(token in normalized for token in BLOCKED_COLUMN_TOKENS):
            result.add(column)
    return result


def _elapsed_seconds(started_at: float) -> float:
    return max(0.0, round(time.perf_counter() - started_at, 3))


def _rows_per_second(row_count: int, elapsed_seconds: float) -> float:
    if row_count <= 0 or elapsed_seconds <= 0:
        return 0.0
    return round(row_count / elapsed_seconds, 2)

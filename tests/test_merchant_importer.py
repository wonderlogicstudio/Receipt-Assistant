from __future__ import annotations

import csv
import sqlite3

import pytest

from app.classifier.merchant_importer import (
    BRANCH_COLUMN,
    BUILDING_MAIN_NUMBER_COLUMN,
    BUILDING_NAME_COLUMN,
    BUILDING_SUB_NUMBER_COLUMN,
    CATEGORY_LARGE_COLUMN,
    CATEGORY_MEDIUM_COLUMN,
    CATEGORY_SMALL_COLUMN,
    MERCHANT_NAME_COLUMN,
    ROAD_ADDRESS_COLUMN,
    ROAD_NAME_COLUMN,
    PublicMerchantCsvImporter,
)
from app.db.merchant_repository import MerchantMasterInput, MerchantRepository
from scripts.import_public_merchants import format_import_summary


OWNER_COLUMN = "owner_name"
PHONE_COLUMN = "phone_number"
RAW_COLUMN = "raw_text"
FIELDNAMES = [
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
    OWNER_COLUMN,
    PHONE_COLUMN,
    RAW_COLUMN,
]


def test_public_merchant_csv_import_stores_only_allowed_columns_and_address_hints(tmp_path):
    csv_path = tmp_path / "public_stores.csv"
    _write_csv(
        csv_path,
        [
            {
                MERCHANT_NAME_COLUMN: "Green Cafe",
                BRANCH_COLUMN: "Ewha",
                CATEGORY_LARGE_COLUMN: "food",
                CATEGORY_MEDIUM_COLUMN: "cafe",
                CATEGORY_SMALL_COLUMN: "coffee",
                ROAD_NAME_COLUMN: "Ewha Road",
                BUILDING_MAIN_NUMBER_COLUMN: "52",
                BUILDING_SUB_NUMBER_COLUMN: "31",
                BUILDING_NAME_COLUMN: "Safe Building",
                ROAD_ADDRESS_COLUMN: "Seoul Seodaemun Ewha Road 52-31",
                OWNER_COLUMN: "owner name",
                PHONE_COLUMN: "02-1234-5678",
                RAW_COLUMN: "full raw csv row should not be stored",
            }
        ],
    )

    db_path = tmp_path / "merchant.db"
    repository = MerchantRepository(db_path=db_path)
    result = PublicMerchantCsvImporter(repository).import_csv(csv_path, source_batch_id="batch-1")

    assert result.imported_row_count == 1
    assert result.skipped_row_count == 0
    assert result.duplicate_file is False
    assert result.scanned_row_count == 1
    assert result.skipped_duplicate_row_count == 0
    assert result.skipped_invalid_row_count == 0
    assert result.elapsed_seconds >= 0
    assert result.rows_per_second >= 0

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT merchant_name, branch_name, category_large, category_medium,
                   category_small, road_name, building_main_number,
                   building_sub_number, building_name, road_address,
                   normalized_road_address, area_hint
            FROM merchant_master
            """
        ).fetchone()
        log = connection.execute(
            "SELECT source_file_name, source_file_hash, duplicate_file, note FROM merchant_source_log"
        ).fetchone()

    assert row == (
        "Green Cafe",
        "Ewha",
        "food",
        "cafe",
        "coffee",
        "Ewha Road",
        "52",
        "31",
        "Safe Building",
        "Seoul Seodaemun Ewha Road 52-31",
        "seoulseodaemunewharoad5231",
        "Seoul Seodaemun",
    )
    assert log[0] == "public_stores.csv"
    assert len(log[1]) == 64
    assert log[2] == 0
    assert log[3] is None

    serialized = " ".join(str(value) for value in [*row, *log] if value is not None)
    assert "owner name" not in serialized
    assert "02-1234-5678" not in serialized
    assert "full raw csv row" not in serialized
    assert str(tmp_path) not in serialized


def test_public_merchant_csv_import_skips_duplicate_rows_by_allowed_column_hash(tmp_path):
    csv_path = tmp_path / "public_stores.csv"
    row = {
        MERCHANT_NAME_COLUMN: "Test Store",
        BRANCH_COLUMN: "",
        CATEGORY_LARGE_COLUMN: "food",
        CATEGORY_MEDIUM_COLUMN: "restaurant",
        CATEGORY_SMALL_COLUMN: "general",
        ROAD_NAME_COLUMN: "Jongro",
        BUILDING_MAIN_NUMBER_COLUMN: "1",
        BUILDING_SUB_NUMBER_COLUMN: "0",
        BUILDING_NAME_COLUMN: "",
        ROAD_ADDRESS_COLUMN: "Seoul Jongro 1",
        OWNER_COLUMN: "A",
        PHONE_COLUMN: "02-1111-1111",
        RAW_COLUMN: "ignored",
    }
    _write_csv(csv_path, [row, {**row, OWNER_COLUMN: "B", PHONE_COLUMN: "02-2222-2222"}])

    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    result = PublicMerchantCsvImporter(repository).import_csv(csv_path, source_batch_id="batch-1")

    assert result.imported_row_count == 1
    assert result.skipped_row_count == 1
    assert result.scanned_row_count == 2
    assert result.skipped_duplicate_row_count == 1
    assert result.skipped_invalid_row_count == 0


def test_public_merchant_csv_import_skips_same_file_hash(tmp_path):
    csv_path = tmp_path / "public_stores.csv"
    _write_csv(
        csv_path,
        [
            {
                MERCHANT_NAME_COLUMN: "Test Store",
                ROAD_NAME_COLUMN: "Jongro",
                BUILDING_MAIN_NUMBER_COLUMN: "1",
                BUILDING_SUB_NUMBER_COLUMN: "0",
                ROAD_ADDRESS_COLUMN: "Seoul Jongro 1",
            }
        ],
    )

    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    importer = PublicMerchantCsvImporter(repository)
    first = importer.import_csv(csv_path, source_batch_id="batch-1")
    second = importer.import_csv(csv_path, source_batch_id="batch-2")

    assert first.imported_row_count == 1
    assert second.imported_row_count == 0
    assert second.skipped_row_count == 1
    assert second.scanned_row_count == 1
    assert second.skipped_duplicate_row_count == 1
    assert second.duplicate_file is True


def test_public_merchant_csv_import_allows_same_file_name_with_different_content(tmp_path):
    csv_path = tmp_path / "public_stores.csv"
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    importer = PublicMerchantCsvImporter(repository)

    _write_csv(csv_path, [{MERCHANT_NAME_COLUMN: "First Store", ROAD_ADDRESS_COLUMN: "Seoul Jongro 1"}])
    first = importer.import_csv(csv_path, source_batch_id="batch-1")
    _write_csv(csv_path, [{MERCHANT_NAME_COLUMN: "Second Store", ROAD_ADDRESS_COLUMN: "Seoul Junggu 2"}])
    second = importer.import_csv(csv_path, source_batch_id="batch-2")

    assert first.imported_row_count == 1
    assert second.imported_row_count == 1
    assert second.duplicate_file is False


def test_public_merchant_csv_import_skips_rows_without_merchant_name(tmp_path):
    csv_path = tmp_path / "public_stores.csv"
    _write_csv(csv_path, [{MERCHANT_NAME_COLUMN: "", ROAD_ADDRESS_COLUMN: "Seoul Jongro 1"}])

    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    result = PublicMerchantCsvImporter(repository).import_csv(csv_path, source_batch_id="batch-1")

    assert result.imported_row_count == 0
    assert result.skipped_row_count == 1
    assert result.scanned_row_count == 1
    assert result.skipped_invalid_row_count == 1


def test_public_merchant_csv_import_summary_is_safe_for_cli_output(tmp_path):
    csv_path = tmp_path / "public_stores.csv"
    _write_csv(
        csv_path,
        [
            {
                MERCHANT_NAME_COLUMN: "Safe Merchant",
                ROAD_ADDRESS_COLUMN: "Safe Road 1",
                OWNER_COLUMN: "owner name",
                PHONE_COLUMN: "02-1234-5678",
                RAW_COLUMN: "raw csv row should not appear",
            }
        ],
    )
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    result = PublicMerchantCsvImporter(repository).import_csv(
        csv_path,
        source_batch_id="batch-safe",
        source_file_name=r"C:\private\public_stores.csv",
    )

    summary = format_import_summary(result)

    assert "file=public_stores.csv" in summary
    assert "batch=batch-safe" in summary
    assert "scanned=1" in summary
    assert "imported=1" in summary
    assert "elapsed_seconds=" in summary
    assert "rows_per_second=" in summary
    assert "C:" not in summary
    assert "private" not in summary
    assert "owner name" not in summary
    assert "02-1234-5678" not in summary
    assert "raw csv row" not in summary


def test_bulk_import_rolls_back_when_stream_fails(tmp_path):
    db_path = tmp_path / "merchant.db"
    repository = MerchantRepository(db_path=db_path)

    def broken_items():
        yield MerchantMasterInput(
            merchant_name="Normal Store",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
        )
        raise RuntimeError("stream_failed_without_raw_row")

    with pytest.raises(RuntimeError, match="stream_failed_without_raw_row"):
        repository.add_masters_stream(broken_items(), chunk_size=1)

    with sqlite3.connect(db_path) as connection:
        master_count = connection.execute("SELECT COUNT(*) FROM merchant_master").fetchone()[0]
        source_log_count = connection.execute("SELECT COUNT(*) FROM merchant_source_log").fetchone()[0]

    assert master_count == 0
    assert source_log_count == 0


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDNAMES})

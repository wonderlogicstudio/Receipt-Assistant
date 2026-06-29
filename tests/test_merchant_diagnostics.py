from __future__ import annotations

import sqlite3

from app.classifier.merchant_candidate import MerchantCandidateMatcher
from app.classifier.merchant_diagnostics import (
    build_candidate_diagnostic_rows,
    build_merchant_dictionary_summary,
    build_saved_receipt_candidate_diagnostic,
    collect_recent_receipt_records,
    mask_business_number,
)
from app.core.config import AppConfig
from app.db.merchant_repository import MerchantAliasInput, MerchantMasterInput, MerchantRepository
from app.db.repository import JobHistoryRepository
from app.history.job_service import JobHistoryService
from app.ui.settings_utils import (
    build_merchant_category_summary_rows,
    build_merchant_dictionary_summary_rows,
    build_merchant_import_batch_summary_rows,
    build_saved_receipt_diagnostic_sample_rows,
    build_saved_receipt_diagnostic_summary_rows,
)


def test_merchant_dictionary_summary_returns_safe_counts_and_file_name(tmp_path):
    db_path = tmp_path / "merchant.db"
    repository = MerchantRepository(db_path=db_path)
    repository.add_master(
        MerchantMasterInput(
            merchant_name="Alpha Store",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
            category_large="Food",
        )
    )
    repository.add_master(
        MerchantMasterInput(
            merchant_name="Beta Store",
            source="public_store_data",
            source_row_hash="row-2",
            source_batch_id="batch-1",
            category_large="Food",
        )
    )
    repository.add_alias(MerchantAliasInput(alias_name="Alpha Receipt", source="review"))
    repository.log_source_import(
        source_name="public_store_data",
        source_file_name=r"C:\private\public_stores.csv",
        source_file_hash="hash-1",
        source_batch_id="batch-1",
        imported_row_count=2,
        skipped_row_count=0,
    )
    repository.log_source_import(
        source_name="public_store_data",
        source_file_name=r"C:\private\public_stores.csv",
        source_file_hash="hash-1",
        source_batch_id="batch-duplicate",
        imported_row_count=0,
        skipped_row_count=2,
        duplicate_file=True,
    )

    summary = build_merchant_dictionary_summary(repository)
    serialized = str(summary)

    assert summary.merchant_master_row_count == 2
    assert summary.merchant_alias_row_count == 1
    assert summary.source_import_batch_count == 2
    assert summary.duplicate_file_count == 1
    assert summary.latest_source_file_name == "public_stores.csv"
    assert summary.top_categories[0].category_large == "Food"
    assert summary.top_categories[0].row_count == 2
    assert "C:" not in serialized
    assert "private" not in serialized
    assert "hash-1" not in serialized


def test_business_number_masking_never_returns_full_value():
    assert mask_business_number("1234567890") == "123-**-*****"
    assert mask_business_number("123-45-67890") == "123-**-*****"
    assert mask_business_number("not-a-number") is None


def test_candidate_diagnostic_rows_mask_business_number_and_keep_review_required(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="Alpha Store",
            business_number="1234567890",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
            road_name="Main Road",
            building_main_number="52",
            road_address="Seoul Main Road 52",
        )
    )

    rows = build_candidate_diagnostic_rows(
        MerchantCandidateMatcher(repository),
        merchant_name="Other Store",
        business_number="123-45-67890",
        address_hint="Seoul Main Road 52",
    )
    serialized = str(rows)

    assert rows[0]["candidate_merchant_name"] == "Alpha Store"
    assert rows[0]["candidate_business_number_masked"] == "123-**-*****"
    assert rows[0]["candidate_business_number_present"] is True
    assert rows[0]["review_required"] is True
    assert "123-45-67890" not in serialized
    assert "raw_text" not in serialized
    assert "raw_json" not in serialized


def test_diagnostic_output_ignores_disallowed_record_fields(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="Alpha Store",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
        )
    )
    records = [
        {
            "merchant_name": "Alpha Store",
            "business_number": None,
            "source_file_name": r"C:\private\receipt.jpg",
            "review_status": "needs_review",
            "raw_text": "FULL OCR RAW TEXT",
            "provider_raw_json": '{"secret": true}',
            "phone": "010-1234-5678",
            "representative_name": "Representative Person",
        }
    ]

    summary = build_saved_receipt_candidate_diagnostic(records, MerchantCandidateMatcher(repository))
    serialized = str(summary)

    assert summary.candidate_present_count == 1
    assert summary.sample_rows[0]["file_name"] == "receipt.jpg"
    assert "C:" not in serialized
    assert "private" not in serialized
    assert "FULL OCR RAW TEXT" not in serialized
    assert "provider_raw_json" not in serialized
    assert "010-1234-5678" not in serialized
    assert "Representative Person" not in serialized


def test_saved_receipt_aggregate_counts_exact_fuzzy_alias_and_missing(tmp_path):
    db_path = tmp_path / "merchant.db"
    repository = MerchantRepository(db_path=db_path)
    repository.add_master(
        MerchantMasterInput(
            merchant_name="Alpha Store",
            business_number="1234567890",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
        )
    )
    repository.add_master(
        MerchantMasterInput(
            merchant_name="Gamma Market",
            source="public_store_data",
            source_row_hash="row-2",
            source_batch_id="batch-1",
        )
    )
    repository.add_alias(
        MerchantAliasInput(
            merchant_master_id=_first_master_id(db_path),
            alias_name="Alpha Receipt",
            source="review",
        )
    )
    records = [
        {"merchant_name": "Wrong Name", "business_number": "123-45-67890", "source_file_name": "a.jpg"},
        {"merchant_name": "Gamma Mkt", "business_number": None, "source_file_name": "b.jpg"},
        {"merchant_name": "Alpha Receipt", "business_number": None, "source_file_name": "c.jpg"},
        {"merchant_name": "No Candidate", "business_number": None, "source_file_name": "d.jpg"},
    ]

    summary = build_saved_receipt_candidate_diagnostic(records, MerchantCandidateMatcher(repository))

    assert summary.scanned_record_count == 4
    assert summary.candidate_present_count == 3
    assert summary.candidate_missing_count == 1
    assert summary.exact_match_count >= 2
    assert summary.fuzzy_match_count >= 1
    assert summary.alias_match_count >= 1
    assert summary.review_required_count == 3
    assert summary.score_buckets["missing"] == 1


def test_collect_recent_receipt_records_uses_safe_fields_only(tmp_path):
    config = AppConfig(app_db_path=tmp_path / "history.db", output_root=tmp_path / "outputs")
    service = JobHistoryService(repository=JobHistoryRepository(config=config), config=config)
    service.save_job_result(
        session_id="session-a",
        receipt_records=[
            {
                "id": "receipt-1",
                "merchant_name": "Alpha Store",
                "business_number": "123-45-67890",
                "source_file_name": r"C:\private\receipt.jpg",
                "review_status": "needs_review",
                "raw_text": "SHOULD NOT BE STORED",
            }
        ],
        card_transactions=[],
    )

    records = collect_recent_receipt_records(service)
    serialized = str(records)

    assert records == [
        {
            "merchant_name": "Alpha Store",
            "business_number": "123-45-67890",
            "source_file_name": "receipt.jpg",
            "review_status": "needs_review",
        }
    ]
    assert "C:" not in serialized
    assert "private" not in serialized
    assert "SHOULD NOT BE STORED" not in serialized


def test_settings_utility_rows_for_diagnostics_are_safe(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="Alpha Store",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
            category_large="Food",
        )
    )
    repository.log_source_import(
        source_name="public_store_data",
        source_file_name=r"C:\private\public_stores.csv",
        source_file_hash="secret-hash",
        source_batch_id="batch-1",
        imported_row_count=1,
        skipped_row_count=0,
    )
    dictionary_summary = build_merchant_dictionary_summary(repository)
    receipt_summary = build_saved_receipt_candidate_diagnostic(
        [{"merchant_name": "Alpha Store", "source_file_name": r"C:\private\receipt.jpg"}],
        MerchantCandidateMatcher(repository),
    )

    rows = [
        *build_merchant_dictionary_summary_rows(dictionary_summary),
        *build_merchant_category_summary_rows(dictionary_summary),
        *build_merchant_import_batch_summary_rows(dictionary_summary),
        *build_saved_receipt_diagnostic_summary_rows(receipt_summary),
        *build_saved_receipt_diagnostic_sample_rows(receipt_summary),
    ]
    serialized = str(rows)

    assert "public_stores.csv" in serialized
    assert "receipt.jpg" in serialized
    assert "C:" not in serialized
    assert "private" not in serialized
    assert "secret-hash" not in serialized


def _first_master_id(db_path) -> str:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT id FROM merchant_master LIMIT 1").fetchone()
    return str(row[0])

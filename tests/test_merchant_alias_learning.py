from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import date

from app.classifier.merchant_alias_learning import MerchantAliasLearningService, is_safe_review_alias_name
from app.core.enums import CardMatchStatus, EvidenceType, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.db.merchant_repository import MerchantMasterInput, MerchantRepository


def make_receipt(
    *,
    merchant_name: str | None,
    business_number: str | None = None,
    review_status: str = ReviewStatus.APPROVED.value,
    export_included: bool = True,
) -> ReceiptRecord:
    return ReceiptRecord.create(
        session_id="session-1",
        source_file_id="source-file-1",
        ocr_result_id="ocr-result-1",
        source_file_name=r"C:\private\receipt.jpg",
        stored_relative_path="data/uploads/session-1/receipt.jpg",
        evidence_type=EvidenceType.RECEIPT_IMAGE.value,
        transaction_date=date(2026, 6, 18),
        merchant_name=merchant_name,
        business_number=business_number,
        total_amount=12000,
        supply_amount=None,
        vat_amount=None,
        payment_method="card",
        expense_category="office",
        review_status=review_status,
        review_reason="",
        card_match_status=CardMatchStatus.MATCHED.value,
        confidence=0.9,
        parser_warnings=[],
        export_included=export_included,
    )


def test_review_merchant_edit_saves_final_and_original_alias(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    service = MerchantAliasLearningService(repository)
    original = make_receipt(merchant_name="스타커피 OCR")
    reviewed = replace(original, merchant_name="스타커피 이대점")

    result = service.learn_from_review(original_records=[original], reviewed_records=[reviewed])

    rows = _alias_rows(tmp_path / "merchant.db")
    alias_names = {row["alias_name"] for row in rows}

    assert result.saved_count == 2
    assert "스타커피 이대점" in alias_names
    assert "스타커피 OCR" in alias_names
    assert {row["source"] for row in rows} == {"review"}


def test_invalid_alias_values_are_not_saved(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    service = MerchantAliasLearningService(repository)
    invalid_values = [
        "",
        "A",
        "1234567890",
        "02-1234-5678",
        "대표자 홍길동",
        "50,000원",
        "2026-05-01",
    ]

    for index, value in enumerate(invalid_values):
        original = make_receipt(merchant_name=None)
        reviewed = replace(original, merchant_name=value, source_file_id=f"source-{index}")
        service.learn_from_review(original_records=[original], reviewed_records=[reviewed])

    assert _alias_rows(tmp_path / "merchant.db") == []
    assert is_safe_review_alias_name("GS25 이대점") is True


def test_repeated_review_save_does_not_duplicate_alias(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    service = MerchantAliasLearningService(repository)
    original = make_receipt(merchant_name="모쿠")
    reviewed = replace(original, merchant_name="모쿠")

    first = service.learn_from_review(original_records=[original], reviewed_records=[reviewed])
    second = service.learn_from_review(original_records=[original], reviewed_records=[reviewed])

    assert first.saved_count == 1
    assert second.saved_count == 0
    assert len(_alias_rows(tmp_path / "merchant.db")) == 1


def test_business_number_exact_match_links_alias_to_master_first(tmp_path):
    db_path = tmp_path / "merchant.db"
    repository = MerchantRepository(db_path=db_path)
    repository.add_master(
        MerchantMasterInput(
            merchant_name="정식상호",
            business_number="1234567890",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
        )
    )
    service = MerchantAliasLearningService(repository)
    original = make_receipt(merchant_name="오씨알상호", business_number="123-45-67890")
    reviewed = replace(original, merchant_name="검수상호", business_number="123-45-67890")

    service.learn_from_review(original_records=[original], reviewed_records=[reviewed])

    master_id = _first_master_id(db_path)
    rows = _alias_rows(db_path)

    assert rows
    assert {row["merchant_master_id"] for row in rows} == {master_id}
    assert {row["business_number"] for row in rows} == {"123-45-67890"}


def test_uncertain_master_link_saves_alias_without_master_id(tmp_path):
    db_path = tmp_path / "merchant.db"
    repository = MerchantRepository(db_path=db_path)
    service = MerchantAliasLearningService(repository)
    original = make_receipt(merchant_name="새로운가게")

    result = service.learn_from_review(original_records=[original], reviewed_records=[original])

    rows = _alias_rows(db_path)

    assert result.saved_count == 1
    assert rows[0]["alias_name"] == "새로운가게"
    assert rows[0]["merchant_master_id"] is None


def test_excel_generation_does_not_learn_merchant_aliases(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from app.ui import streamlit_app
    from app.classifier.merchant_alias_learning import MerchantAliasLearningResult

    calls = []
    monkeypatch.setattr(MerchantAliasLearningService, "learn_from_review", lambda *a, **kw: calls.append(kw) or MerchantAliasLearningResult(saved_count=1))
    monkeypatch.setattr(streamlit_app, "MerchantRepository", lambda **kw: object(), raising=False)
    monkeypatch.setattr(streamlit_app, "render_runtime_ocr_provider_selector", lambda _: "mock")
    monkeypatch.setattr(streamlit_app, "render_runtime_paddle_gpu_option", lambda _: (False, False))
    monkeypatch.setattr(streamlit_app, "render_review_view", lambda records, **kw: records)
    monkeypatch.setattr(streamlit_app, "save_export_history_once", lambda **kw: {})

    def page():
        from app.ui.streamlit_app import render_new_job_view
        render_new_job_view()

    app = AppTest.from_function(page)
    app.session_state["receipt_records"] = [make_receipt(merchant_name="안전상호")]
    app.run()
    next(button for button in app.button if button.label == "표준 엑셀 생성").click().run()
    assert not app.exception
    assert app.session_state["export_file_bytes"].startswith(b"PK")
    assert calls == []


def test_alias_db_does_not_store_raw_paths_or_sensitive_context(tmp_path):
    db_path = tmp_path / "merchant.db"
    repository = MerchantRepository(db_path=db_path)
    service = MerchantAliasLearningService(repository)
    original = make_receipt(merchant_name="안전상호", business_number="123-45-67890")
    original = replace(
        original,
        source_file_name=r"C:\private\대표자_홍길동_02-1234-5678.jpg",
        stored_relative_path=r"C:\private\receipt.jpg",
        user_note="provider raw JSON full OCR text",
    )

    service.learn_from_review(original_records=[original], reviewed_records=[original])

    serialized = str([dict(row) for row in _alias_rows(db_path)])

    assert "안전상호" in serialized
    assert "C:" not in serialized
    assert "private" not in serialized
    assert "홍길동" not in serialized
    assert "02-1234-5678" not in serialized
    assert "raw JSON" not in serialized
    assert "full OCR text" not in serialized


def _alias_rows(db_path) -> list[sqlite3.Row]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        return list(
            connection.execute(
                """
                SELECT alias_name, normalized_alias_name, business_number, source, merchant_master_id
                FROM merchant_alias
                ORDER BY alias_name
                """
            ).fetchall()
        )


def _first_master_id(db_path) -> str:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT id FROM merchant_master LIMIT 1").fetchone()
    return str(row[0])

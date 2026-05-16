from __future__ import annotations

import json
from pathlib import Path

from app.classifier.category_rules import CategoryRules
from app.core.config import AppConfig
from app.db.repository import JobHistoryRepository
from app.exporter.excel_exporter import ExcelExporter
from app.history.job_service import JobHistoryService
from app.validator.card_matcher import CardMatcher
from app.validator.receipt_validator import ReceiptValidator
from tests.standard_parser_regression_helpers import (
    assert_no_forbidden_text,
    assert_no_forbidden_workbook_values,
    assert_no_raw_metadata,
    matching_card_transaction,
    paddleocr_candidate_record,
    workbook_cell_values,
    workbook_from_bytes,
)


def test_downstream_services_accept_paddleocr_provider_string_as_receipt_metadata(tmp_path) -> None:
    receipt = paddleocr_candidate_record()
    validated = ReceiptValidator().validate(receipt)
    category = CategoryRules().recommend(validated.merchant_name)
    matched = CardMatcher().match([validated], [matching_card_transaction(validated)])[0]
    workbook = workbook_from_bytes(ExcelExporter().export([matched]))

    config = AppConfig(
        upload_root=tmp_path / "data" / "uploads",
        upload_relative_root=Path("data/uploads"),
        output_root=tmp_path / "data" / "outputs",
        app_db_path=tmp_path / "history.db",
    )
    service = JobHistoryService(repository=JobHistoryRepository(config=config), config=config)
    job = service.save_job_result(session_id="session-provider-independent", receipt_records=[matched])
    detail = service.get_processing_job_detail(str(job["id"]))

    assert validated.ocr_provider == "paddleocr"
    assert matched.ocr_provider == "paddleocr"
    assert category == "복리후생비"
    assert detail["receipt_records"][0]["merchant_name"] == matched.merchant_name
    assert_no_forbidden_text(matched)
    assert_no_forbidden_text(detail)
    assert_no_forbidden_workbook_values(workbook_cell_values(workbook))


def test_downstream_receipt_record_does_not_carry_provider_fields_raw_metadata() -> None:
    receipt = paddleocr_candidate_record()
    validated = ReceiptValidator().validate(receipt)
    matched = CardMatcher().match([validated], [matching_card_transaction(validated)])[0]

    assert_no_raw_metadata(receipt)
    assert_no_raw_metadata(validated)
    assert_no_raw_metadata(matched)
    assert "provider_fields" not in json.dumps(matched.to_dict(), ensure_ascii=False, default=str)


def test_downstream_code_does_not_import_provider_specific_ocr_sdks() -> None:
    paths = [
        *Path("app/validator").rglob("*.py"),
        *Path("app/classifier").rglob("*.py"),
        *Path("app/exporter").rglob("*.py"),
        *Path("app/db").rglob("*.py"),
        *Path("app/history").rglob("*.py"),
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    forbidden_import_markers = [
        "azure.ai",
        "DocumentAnalysisClient",
        "DocumentIntelligenceClient",
        "paddleocr",
        "pytesseract",
        "mlkit",
        "VNRecognizeTextRequest",
    ]

    for marker in forbidden_import_markers:
        assert marker not in source


def test_requirements_do_not_add_paddleocr_dependency_for_downstream_regression() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()

    assert "paddleocr" not in requirements
    assert "pytesseract" not in requirements

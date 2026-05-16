from __future__ import annotations

import json
import re
from pathlib import Path

from app.core.ocr_models import OCRResult
from app.ocr.adapters.azure_standard_adapter import AzureStandardOCRAdapter
from app.ocr.adapters.paddle_standard_adapter import PaddleStandardOCRAdapter
from app.parser.standard_ocr_context import build_parser_context_from_standard_ocr
from app.ui.ocr_comparison_report_utils import (
    CORE_COMPARISON_FIELDS,
    build_diagnostic_standard_ocr_result,
    build_provider_comparison_result,
    build_side_by_side_report,
    build_standard_ocr_from_safe_azure_ocr_result,
    comparison_report_to_field_rows,
    comparison_report_to_match_summary,
    comparison_report_to_summary_rows,
)


AZURE_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "azure"
PADDLE_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "paddle"
FORBIDDEN_REPORT_PATTERNS = [
    r"raw_json",
    r"raw_text",
    r"provider_raw_response",
    r"provider_fields",
    r"full_ocr_text",
    r"operation_location",
    r"endpoint",
    r"api_key",
    r"secret",
    r"token",
    r"password",
    r"https?://",
    r"[A-Za-z]:\\",
    r"/Users/",
    r"/home/",
    r"/var/",
    r"/tmp/",
    r"\b\d{13,19}\b",
    r"\b\d{6}-\d{7}\b",
]


def load_azure_result(name: str = "azure_receipt_sanitized_response.json"):
    payload = json.loads((AZURE_FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return AzureStandardOCRAdapter().convert(
        payload,
        source_file_id=f"source-{name}",
        source_file_name="sample_receipt.png",
    )


def load_paddle_result(name: str = "paddle_receipt_sanitized_result.json"):
    payload = json.loads((PADDLE_FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return PaddleStandardOCRAdapter().convert(
        payload,
        source_file_id=f"source-{name}",
        source_file_name="sample_receipt.png",
    )


def test_build_side_by_side_report_from_sanitized_fixtures() -> None:
    report = build_side_by_side_report(
        sample_id="receipt-001",
        source_file_name="sample_receipt.png",
        azure_result=load_azure_result(),
        paddle_result=load_paddle_result(),
        azure_elapsed_ms=1200,
        paddle_elapsed_ms=3400,
    )

    assert report.sample_id == "receipt-001"
    assert report.source_file_name == "sample_receipt.png"
    assert report.azure.provider == "azure"
    assert report.paddle.provider == "paddleocr"
    assert report.azure.receipt_record is not None
    assert report.paddle.receipt_record is not None
    assert {row.field_name for row in report.field_rows} == set(CORE_COMPARISON_FIELDS)


def test_report_uses_parser_context_and_receipt_parser_result() -> None:
    azure_result = load_azure_result()
    paddle_result = load_paddle_result()
    azure_context = build_parser_context_from_standard_ocr(azure_result)
    paddle_context = build_parser_context_from_standard_ocr(paddle_result)

    report = build_side_by_side_report(
        sample_id="receipt-001",
        source_file_name="sample_receipt.png",
        azure_result=azure_result,
        paddle_result=paddle_result,
    )

    assert report.azure.parser_safe_text_line_count == len(azure_context.safe_text_lines)
    assert report.paddle.parser_safe_text_line_count == len(paddle_context.safe_text_lines)
    assert report.azure.receipt_record is not None
    assert report.paddle.receipt_record is not None
    assert report.azure.receipt_record.total_amount == 12000
    assert report.paddle.receipt_record.total_amount == 12000


def test_field_rows_compute_present_and_same_flags() -> None:
    report = build_side_by_side_report(
        sample_id="receipt-001",
        source_file_name="sample_receipt.png",
        azure_result=load_azure_result(),
        paddle_result=load_paddle_result(),
    )
    rows = {row["field_name"]: row for row in comparison_report_to_field_rows(report)}

    assert rows["merchant_name"]["azure_present"] is True
    assert rows["merchant_name"]["paddle_present"] is True
    assert rows["merchant_name"]["is_same"] is True
    assert rows["merchant_name"]["match_status"] == "matched"
    assert rows["total_amount"]["is_same"] is True
    assert rows["transaction_date"]["is_same"] is False
    assert rows["transaction_date"]["match_status"] == "mismatched"


def test_elapsed_ms_and_provider_metrics_are_kept_per_provider() -> None:
    report = build_side_by_side_report(
        sample_id="receipt-001",
        source_file_name="sample_receipt.png",
        azure_result=load_azure_result(),
        paddle_result=load_paddle_result(),
        azure_elapsed_ms=11,
        paddle_elapsed_ms=22,
    )
    rows = {row["provider"]: row for row in comparison_report_to_summary_rows(report)}

    assert rows["azure"]["elapsed_ms"] == 11
    assert rows["paddleocr"]["elapsed_ms"] == 22
    assert "diagnostic_detail_code" in rows["paddleocr"]
    assert rows["azure"]["standard_text_block_count"] == 6
    assert rows["paddleocr"]["standard_candidate_count"] == 6
    assert rows["azure"]["review_reason_count"] >= 0
    assert rows["paddleocr"]["parser_warning_count"] >= 0


def test_total_low_confidence_and_redacted_counts_use_full_standard_result() -> None:
    result = PaddleStandardOCRAdapter().convert(
        {
            "engine": "paddleocr",
            "engine_version": "test",
            "status": "succeeded",
            "input_type": "image",
            "image_count": 1,
            "lines": [
                {"block_id": "line-1", "text": "merchant", "confidence": 0.90},
                {"block_id": "line-2", "text": "low", "confidence": 0.50},
                {
                    "block_id": "line-3",
                    "text": "sensitive",
                    "confidence": 0.40,
                    "sensitive_category": "wifi_credential",
                },
            ],
        },
        source_file_name="sample_receipt.png",
    )

    provider_result = build_provider_comparison_result(result)

    assert provider_result.low_confidence_total_count == 2
    assert provider_result.redacted_total_count == 1


def test_failed_or_skipped_provider_result_still_builds_safe_report() -> None:
    azure_result = build_diagnostic_standard_ocr_result(
        provider="azure",
        source_file_name="sample_receipt.png",
        status="skipped",
        diagnostic_code="azure_configuration_missing",
        engine_runtime="server",
    )
    paddle_result = load_paddle_result("paddle_receipt_empty_sanitized_result.json")

    report = build_side_by_side_report(
        sample_id="receipt-001",
        source_file_name="sample_receipt.png",
        azure_result=azure_result,
        paddle_result=paddle_result,
    )

    assert report.azure.provider_status == "skipped"
    assert report.azure.diagnostic_code == "azure_configuration_missing"
    assert report.azure.receipt_record is None
    assert report.azure.parse_error_code == "azure_configuration_missing"
    assert report.paddle.provider_status == "failed"
    assert report.paddle.diagnostic_code == "paddle_no_text_detected"
    assert report.paddle.receipt_record is None


def test_provider_summary_exposes_only_safe_diagnostic_detail_code() -> None:
    paddle_result = build_diagnostic_standard_ocr_result(
        provider="paddleocr",
        source_file_name="sample_receipt.png",
        status="failed",
        diagnostic_code="paddle_runtime_error",
        engine_runtime="pc_local",
    )
    paddle_result.provider_fields["diagnostic_detail_code"] = "runtime_error"
    report = build_side_by_side_report(
        sample_id="receipt-001",
        source_file_name="sample_receipt.png",
        azure_result=load_azure_result(),
        paddle_result=paddle_result,
    )
    rows = {row["provider"]: row for row in comparison_report_to_summary_rows(report)}

    assert rows["paddleocr"]["diagnostic_detail_code"] == "runtime_error"


def test_failed_azure_detail_code_is_carried_to_comparison_report() -> None:
    azure_ocr_result = OCRResult.failed(
        source_file_id="azure-source",
        source_file_name="receipt.jpg",
        stored_relative_path=None,
        provider="azure",
        error_message="OCR request failed",
        diagnostic_code="analyze_http_403",
        diagnostic_detail_code="quota_or_rate_limit",
    )
    azure_result = build_standard_ocr_from_safe_azure_ocr_result(azure_ocr_result)
    report = build_side_by_side_report(
        sample_id="receipt-001",
        source_file_name="receipt.jpg",
        azure_result=azure_result,
        paddle_result=load_paddle_result(),
    )
    rows = {row["provider"]: row for row in comparison_report_to_summary_rows(report)}

    assert rows["azure"]["diagnostic_code"] == "analyze_http_403"
    assert rows["azure"]["diagnostic_detail_code"] == "quota_or_rate_limit"


def test_match_summary_counts_per_sample_field_states() -> None:
    report = build_side_by_side_report(
        sample_id="receipt-001",
        source_file_name="sample_receipt.png",
        azure_result=load_azure_result(),
        paddle_result=load_paddle_result(),
    )
    summary = comparison_report_to_match_summary(report)

    assert summary["field_count"] == len(CORE_COMPARISON_FIELDS)
    assert summary["matched_field_count"] >= 1
    assert summary["mismatched_field_count"] >= 1
    assert summary["both_missing_field_count"] >= 1


def test_report_serialization_does_not_copy_raw_or_sensitive_payload() -> None:
    report = build_side_by_side_report(
        sample_id=r"C:\private\receipt-001",
        source_file_name=r"C:\private\sample_receipt.png",
        azure_result=load_azure_result(),
        paddle_result=load_paddle_result(),
    )
    serialized = json.dumps(report.as_safe_dict(), ensure_ascii=False, default=str)

    assert "sample_receipt.png" in serialized
    for pattern in FORBIDDEN_REPORT_PATTERNS:
        assert not re.search(pattern, serialized, flags=re.IGNORECASE), pattern


def test_safe_azure_ocr_result_bridge_handles_failed_result_without_raw_details() -> None:
    ocr_result = OCRResult.failed(
        source_file_id="azure-source",
        source_file_name=r"C:\private\receipt.png",
        stored_relative_path=r"C:\private\receipt.png",
        provider="azure",
        error_message="do not expose this stack detail",
        diagnostic_code="timeout",
    )

    standard_result = build_standard_ocr_from_safe_azure_ocr_result(ocr_result)
    serialized = json.dumps(standard_result.model_dump(mode="json"), ensure_ascii=False, default=str)

    assert standard_result.provider == "azure"
    assert standard_result.status == "failed"
    assert standard_result.source_file_name == "receipt.png"
    assert standard_result.diagnostic_code == "timeout"
    assert "do not expose" not in serialized
    assert "C:\\private" not in serialized

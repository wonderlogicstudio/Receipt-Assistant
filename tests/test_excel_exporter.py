from io import BytesIO
from dataclasses import replace

from openpyxl import load_workbook

from app.core.enums import ReviewStatus
from app.exporter.excel_exporter import ExcelExporter
from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.validator.receipt_validator import ReceiptValidator


def make_ocr_result(tmp_path):
    receipt_path = tmp_path / "sample_receipt.pdf"
    receipt_path.write_bytes(b"sample")
    return MockOCRProvider().extract(receipt_path)


def test_excel_exporter_creates_required_sheets(tmp_path):
    ocr_result = make_ocr_result(tmp_path)
    receipt = ReceiptValidator().validate(ReceiptParser().parse(ocr_result))

    excel_bytes = ExcelExporter().export_to_bytes([receipt], [ocr_result])
    workbook = load_workbook(BytesIO(excel_bytes))

    assert {"정리내역", "월별요약", "검수필요", "원본OCR"}.issubset(set(workbook.sheetnames))


def test_excel_exporter_writes_summary_and_monthly_totals(tmp_path):
    ocr_result = make_ocr_result(tmp_path)
    receipt = ReceiptValidator().validate(ReceiptParser().parse(ocr_result))

    workbook = load_workbook(BytesIO(ExcelExporter().export_to_bytes([receipt], [ocr_result])))

    summary = workbook["정리내역"]
    headers = [cell.value for cell in summary[1]]
    assert headers[:13] == ExcelExporter.summary_headers
    assert summary["F2"].value == 33000

    monthly = workbook["월별요약"]
    assert monthly["A2"].value == "2026-05"
    assert monthly["C2"].value == 33000


def test_excel_exporter_puts_review_needed_records_on_review_sheet(tmp_path):
    ocr_result = make_ocr_result(tmp_path)
    receipt = replace(
        ReceiptParser().parse(ocr_result),
        review_status=ReviewStatus.NEEDS_REVIEW.value,
        parser_warnings=["금액누락"],
        review_reason="금액누락",
    )

    workbook = load_workbook(BytesIO(ExcelExporter().export_to_bytes([receipt], [ocr_result])))

    review_sheet = workbook["검수필요"]
    assert review_sheet.max_row == 2
    assert review_sheet["A2"].value == receipt.receipt_id

from io import BytesIO

from openpyxl import load_workbook

from app.exporter.excel_exporter import ExcelExporter
from app.ocr.mock_provider import MockOCRProvider
from app.parser.receipt_parser import ReceiptParser
from app.validator.receipt_validator import ReceiptValidator


def test_excel_exporter_creates_required_sheets():
    ocr_result = MockOCRProvider().extract("sample_receipt.pdf")
    receipt = ReceiptValidator().validate(ReceiptParser().parse(ocr_result))

    excel_bytes = ExcelExporter().export_to_bytes([receipt], [ocr_result])
    workbook = load_workbook(BytesIO(excel_bytes))

    assert {"정리내역", "월별요약", "검수필요", "원본OCR"}.issubset(set(workbook.sheetnames))


def test_excel_exporter_writes_summary_and_monthly_totals():
    ocr_result = MockOCRProvider().extract("sample_receipt.pdf")
    receipt = ReceiptValidator().validate(ReceiptParser().parse(ocr_result))

    workbook = load_workbook(BytesIO(ExcelExporter().export_to_bytes([receipt], [ocr_result])))

    summary = workbook["정리내역"]
    headers = [cell.value for cell in summary[1]]
    assert headers[:13] == ExcelExporter.summary_headers
    assert summary["F2"].value == 33000

    monthly = workbook["월별요약"]
    assert monthly["A2"].value == "2026-05"
    assert monthly["C2"].value == 33000


def test_excel_exporter_puts_review_needed_records_on_review_sheet():
    ocr_result = MockOCRProvider().extract("sample_receipt.pdf")
    receipt = ReceiptValidator().validate(ReceiptParser().parse(ocr_result))

    workbook = load_workbook(BytesIO(ExcelExporter().export_to_bytes([receipt], [ocr_result])))

    review_sheet = workbook["검수필요"]
    assert review_sheet.max_row == 2
    assert review_sheet["A2"].value == receipt.receipt_id


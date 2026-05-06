from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from app.ocr.base import OCRResult
from app.parser.receipt_parser import ReceiptRecord


class ExcelExporter:
    summary_sheet_name = "정리내역"
    monthly_sheet_name = "월별요약"
    review_sheet_name = "검수필요"
    raw_ocr_sheet_name = "원본OCR"

    summary_headers = [
        "receipt_id",
        "source_file_name",
        "transaction_date",
        "merchant_name",
        "business_number",
        "total_amount",
        "supply_amount",
        "vat_amount",
        "payment_method",
        "expense_category",
        "confidence",
        "review_status",
        "review_reason",
    ]

    def build_workbook(
        self,
        receipts: Iterable[ReceiptRecord],
        ocr_results: Iterable[OCRResult] | None = None,
    ) -> Workbook:
        receipt_list = list(receipts)
        ocr_result_list = list(ocr_results or [])

        workbook = Workbook()
        default_sheet = workbook.active
        workbook.remove(default_sheet)

        self._add_summary_sheet(workbook, receipt_list)
        self._add_monthly_sheet(workbook, receipt_list)
        self._add_review_sheet(workbook, receipt_list)
        self._add_raw_ocr_sheet(workbook, ocr_result_list, receipt_list)
        return workbook

    def export_to_bytes(
        self,
        receipts: Iterable[ReceiptRecord],
        ocr_results: Iterable[OCRResult] | None = None,
    ) -> bytes:
        workbook = self.build_workbook(receipts, ocr_results)
        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    def export(
        self,
        receipts: Iterable[ReceiptRecord],
        output_path: str | Path,
        ocr_results: Iterable[OCRResult] | None = None,
    ) -> Path:
        workbook = self.build_workbook(receipts, ocr_results)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(path)
        return path

    def make_filename(self, now: datetime | None = None) -> str:
        timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
        return f"receipt_summary_{timestamp}.xlsx"

    def _add_summary_sheet(self, workbook: Workbook, receipts: list[ReceiptRecord]) -> None:
        sheet = workbook.create_sheet(self.summary_sheet_name)
        sheet.append(self.summary_headers)
        for receipt in receipts:
            sheet.append([self._cell_value(getattr(receipt, header)) for header in self.summary_headers])
        self._format_sheet(sheet)

    def _add_monthly_sheet(self, workbook: Workbook, receipts: list[ReceiptRecord]) -> None:
        sheet = workbook.create_sheet(self.monthly_sheet_name)
        sheet.append(["month", "receipt_count", "total_amount", "supply_amount", "vat_amount"])

        totals: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "total": 0, "supply": 0, "vat": 0})
        for receipt in receipts:
            month = receipt.transaction_date.strftime("%Y-%m") if receipt.transaction_date else "날짜미확인"
            totals[month]["count"] += 1
            totals[month]["total"] += receipt.total_amount or 0
            totals[month]["supply"] += receipt.supply_amount or 0
            totals[month]["vat"] += receipt.vat_amount or 0

        for month in sorted(totals):
            item = totals[month]
            sheet.append([month, item["count"], item["total"], item["supply"], item["vat"]])
        self._format_sheet(sheet)

    def _add_review_sheet(self, workbook: Workbook, receipts: list[ReceiptRecord]) -> None:
        sheet = workbook.create_sheet(self.review_sheet_name)
        sheet.append(self.summary_headers)
        for receipt in receipts:
            if receipt.review_status == "검토필요" or receipt.review_reason:
                sheet.append([self._cell_value(getattr(receipt, header)) for header in self.summary_headers])
        self._format_sheet(sheet)

    def _add_raw_ocr_sheet(
        self,
        workbook: Workbook,
        ocr_results: list[OCRResult],
        receipts: list[ReceiptRecord],
    ) -> None:
        sheet = workbook.create_sheet(self.raw_ocr_sheet_name)
        sheet.append(["ocr_result_id", "source_file_name", "provider", "confidence", "status", "raw_text"])

        if ocr_results:
            for result in ocr_results:
                sheet.append(
                    [
                        result.id,
                        Path(result.source_file_name).name,
                        result.provider,
                        result.confidence,
                        result.status,
                        result.raw_text,
                    ]
                )
        else:
            for receipt in receipts:
                sheet.append(
                    [
                        receipt.receipt_id,
                        Path(receipt.source_file_name).name,
                        receipt.ocr_provider,
                        receipt.confidence,
                        "success",
                        receipt.ocr_raw_text,
                    ]
                )
        self._format_sheet(sheet)

    def _format_sheet(self, sheet) -> None:
        header_fill = PatternFill("solid", fgColor="D9EAF7")
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
        sheet.freeze_panes = "A2"

        for column_cells in sheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            column_letter = get_column_letter(column_cells[0].column)
            sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 48)

        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                header = sheet.cell(row=1, column=cell.column).value
                if header in {"total_amount", "supply_amount", "vat_amount"}:
                    cell.number_format = '#,##0'
                if header == "transaction_date":
                    cell.number_format = "yyyy-mm-dd"

    def _cell_value(self, value):
        if isinstance(value, date):
            return value
        if isinstance(value, Path):
            return value.name
        return value


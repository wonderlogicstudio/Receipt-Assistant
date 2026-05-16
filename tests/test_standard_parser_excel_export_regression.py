from __future__ import annotations

from app.exporter.excel_exporter import ExcelExporter
from tests.standard_parser_regression_helpers import (
    assert_no_forbidden_workbook_values,
    matching_card_transaction,
    parse_azure_adapter_fixture,
    parse_standard_fixture,
    standard_parser_records,
    workbook_cell_values,
    workbook_from_bytes,
)


def _header_map(sheet) -> dict[str, int]:
    return {cell.value: index for index, cell in enumerate(sheet[1], start=1)}


def test_standard_parser_records_export_with_existing_sheet_and_header_structure() -> None:
    records = standard_parser_records()
    excel_bytes = ExcelExporter().export(records)
    workbook = workbook_from_bytes(excel_bytes)

    assert set(ExcelExporter.sheet_names).issubset(set(workbook.sheetnames))
    assert [cell.value for cell in workbook[ExcelExporter.summary_sheet_name][1]] == ExcelExporter.summary_headers
    assert [cell.value for cell in workbook[ExcelExporter.review_sheet_name][1]] == ExcelExporter.review_headers
    assert_no_forbidden_workbook_values(workbook_cell_values(workbook))


def test_standard_parser_amount_columns_preserve_discount_and_paid_amounts() -> None:
    edge = parse_azure_adapter_fixture("azure_receipt_edge_sanitized_response.json")
    workbook = workbook_from_bytes(ExcelExporter().export([edge]))
    summary = workbook[ExcelExporter.summary_sheet_name]
    columns = _header_map(summary)

    assert summary.cell(row=2, column=columns["총금액"]).value == 0
    assert summary.cell(row=2, column=columns["할인전금액"]).value == 18000
    assert summary.cell(row=2, column=columns["할인금액"]).value == 3000
    assert summary.cell(row=2, column=columns["최종결제금액"]).value == 15000
    assert summary.cell(row=2, column=columns["실제결제금액"]).value == 0
    assert "final_paid_amount_mismatch" in summary.cell(row=2, column=columns["금액검토사유"]).value


def test_standard_parser_vat_reference_columns_do_not_replace_explicit_vat() -> None:
    receipt = parse_standard_fixture("azure_like_receipt_standard.json")
    workbook = workbook_from_bytes(ExcelExporter().export([receipt]))
    summary = workbook[ExcelExporter.summary_sheet_name]
    columns = _header_map(summary)

    assert summary.cell(row=2, column=columns["공급가액"]).value is None
    assert summary.cell(row=2, column=columns["부가세"]).value is None
    assert summary.cell(row=2, column=columns["추정공급가액"]).value == receipt.estimated_supply_amount
    assert summary.cell(row=2, column=columns["추정부가세"]).value == receipt.estimated_vat_amount
    assert summary.cell(row=2, column=columns["부가세출처"]).value == "estimated_reference"
    assert "vat_estimated_reference_only" in summary.cell(row=2, column=columns["부가세검토사유"]).value


def test_standard_parser_sensitive_categories_are_exported_without_sensitive_values() -> None:
    receipt = parse_standard_fixture("azure_like_receipt_standard.json")
    workbook = workbook_from_bytes(ExcelExporter().export([receipt]))
    summary = workbook[ExcelExporter.summary_sheet_name]
    columns = _header_map(summary)
    values = workbook_cell_values(workbook)

    assert summary.cell(row=2, column=columns["민감문구감지"]).value == "Y"
    assert summary.cell(row=2, column=columns["민감문구유형"]).value == "wifi_credential"
    assert "[REDACTED]" not in "\n".join(str(value) for value in values)
    assert_no_forbidden_workbook_values(values)


def test_standard_parser_card_match_and_source_file_sheets_do_not_expose_paths_or_raw_metadata() -> None:
    receipt = parse_azure_adapter_fixture("azure_receipt_sanitized_response.json")
    transaction = matching_card_transaction(receipt)
    workbook = workbook_from_bytes(ExcelExporter().export([receipt], [transaction]))
    card_sheet = workbook[ExcelExporter.sheet_names[4]]
    source_sheet = workbook[ExcelExporter.sheet_names[5]]
    values = workbook_cell_values(workbook)

    assert card_sheet.max_row == 2
    assert source_sheet.max_row >= 2
    assert "sample_azure_receipt.pdf" in {cell.value for cell in source_sheet["B"] if cell.value}
    assert_no_forbidden_workbook_values(values)


def test_standard_parser_export_keeps_non_amount_candidates_out_of_amount_columns() -> None:
    receipt = parse_standard_fixture("edge_case_receipt_standard.json")
    workbook = workbook_from_bytes(ExcelExporter().export([receipt]))
    summary = workbook[ExcelExporter.summary_sheet_name]
    columns = _header_map(summary)
    amount_values = {
        summary.cell(row=2, column=columns["총금액"]).value,
        summary.cell(row=2, column=columns["할인전금액"]).value,
        summary.cell(row=2, column=columns["할인금액"]).value,
        summary.cell(row=2, column=columns["최종결제금액"]).value,
        summary.cell(row=2, column=columns["실제결제금액"]).value,
        summary.cell(row=2, column=columns["공급가액"]).value,
        summary.cell(row=2, column=columns["부가세"]).value,
    }

    assert "APPROVAL-TEST-42" not in amount_values
    assert 1 not in amount_values
    assert 3 not in amount_values
    assert 10 not in amount_values
    assert 88 not in amount_values
    assert_no_forbidden_workbook_values(workbook_cell_values(workbook))

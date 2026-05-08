from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4
import shutil

import pandas as pd
import pytest

from app.core.enums import CardParseResultStatus, CardParseStatus
from app.core.exceptions import MissingRequiredColumnsError
from app.parser.card_statement_parser import CardStatementParser
from app.parser.normalizers import normalize_amount, normalize_approval_number, normalize_date
from app.storage.file_store import FileStore


class UploadedFile(BytesIO):
    def __init__(self, name: str, content: bytes) -> None:
        super().__init__(content)
        self.name = name


def write_csv(path: Path, rows: list[dict[str, object]]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def write_xlsx(path: Path, rows: list[dict[str, object]]) -> Path:
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


def sample_rows() -> list[dict[str, object]]:
    return [
        {
            "사용일자": "2026.05.07",
            "가맹점명": "샘플카페",
            "이용금액": "12,000원",
            "카드명": "테스트카드",
            "승인번호": "001234",
        },
        {
            "사용일자": "20260507",
            "가맹점명": "샘플문구",
            "이용금액": "₩12,000",
            "카드명": "테스트카드",
            "승인번호": "000777",
        },
    ]


def test_parse_csv_card_statement_to_result(tmp_path):
    path = write_csv(tmp_path / "card_statement.csv", sample_rows())

    result = CardStatementParser().parse(path)

    assert result.status == CardParseResultStatus.COMPLETED.value
    assert result.total_rows == 2
    assert result.parsed_rows == 2
    assert result.failed_rows == 0
    assert result.transactions[0].merchant_name == "샘플카페"


def test_parse_xlsx_card_statement_to_result(tmp_path):
    path = write_xlsx(tmp_path / "card_statement.xlsx", sample_rows())

    result = CardStatementParser().parse(path)

    assert result.status == CardParseResultStatus.COMPLETED.value
    assert result.total_rows == 2
    assert result.transactions[1].merchant_name == "샘플문구"


def test_csv_rows_are_converted_to_standard_card_transactions(tmp_path):
    path = write_csv(tmp_path / "card_statement.csv", sample_rows())

    transactions = CardStatementParser().parse(path).transactions

    assert transactions[0].transaction_date.isoformat() == "2026-05-07"
    assert transactions[0].total_amount == 12000
    assert transactions[0].card_name == "테스트카드"
    assert transactions[0].approval_number == "001234"
    assert transactions[0].parse_status == CardParseStatus.PARSED.value


def test_xlsx_rows_are_converted_to_standard_card_transactions(tmp_path):
    path = write_xlsx(tmp_path / "card_statement.xlsx", sample_rows())

    transactions = CardStatementParser().parse(path).transactions

    assert transactions[1].transaction_date.isoformat() == "2026-05-07"
    assert transactions[1].total_amount == 12000
    assert transactions[1].approval_number == "000777"


def test_normalize_amount_handles_won_suffix_and_currency_symbol():
    assert normalize_amount("12,000원") == 12000
    assert normalize_amount("₩12,000") == 12000
    assert normalize_amount(" 12,000 ") == 12000


def test_normalize_date_handles_supported_formats():
    assert normalize_date("2026.05.07").isoformat() == "2026-05-07"
    assert normalize_date("20260507").isoformat() == "2026-05-07"
    assert normalize_date("2026/05/07").isoformat() == "2026-05-07"
    assert normalize_date("2026-05-07 13:20:00").isoformat() == "2026-05-07"


def test_normalize_approval_number_preserves_leading_zeroes():
    assert normalize_approval_number("001234") == "001234"


def test_card_name_is_optional(tmp_path):
    path = write_csv(
        tmp_path / "card_statement.csv",
        [{"거래일자": "2026-05-07", "상호": "샘플상점", "금액": "12000", "승인번호": "001234"}],
    )

    transaction = CardStatementParser().parse(path).transactions[0]

    assert transaction.card_name is None
    assert transaction.parse_status == CardParseStatus.PARSED.value


def test_approval_number_is_optional(tmp_path):
    path = write_csv(
        tmp_path / "card_statement.csv",
        [{"거래일자": "2026-05-07", "상호": "샘플상점", "금액": "12000", "카드": "테스트카드"}],
    )

    transaction = CardStatementParser().parse(path).transactions[0]

    assert transaction.approval_number is None
    assert transaction.parse_status == CardParseStatus.PARSED.value


@pytest.mark.parametrize(
    ("rows", "missing_column"),
    [
        ([{"상호": "샘플상점", "금액": "12000"}], "transaction_date"),
        ([{"거래일자": "2026-05-07", "금액": "12000"}], "merchant_name"),
        ([{"거래일자": "2026-05-07", "상호": "샘플상점"}], "total_amount"),
    ],
)
def test_missing_required_columns_raise_clear_exception(tmp_path, rows, missing_column):
    path = write_csv(tmp_path / "card_statement.csv", rows)

    with pytest.raises(MissingRequiredColumnsError, match=missing_column):
        CardStatementParser().parse(path)


def test_file_store_metadata_is_reflected_in_transactions():
    session_id = f"card-{uuid4().hex}"
    dataframe = pd.DataFrame(sample_rows())
    buffer = BytesIO()
    dataframe.to_csv(buffer, index=False, encoding="utf-8-sig")
    metadata = FileStore().save_uploaded_file(UploadedFile("metadata_card.csv", buffer.getvalue()), session_id=session_id)

    try:
        result = CardStatementParser().parse(metadata)
    finally:
        shutil.rmtree(Path("data/uploads") / session_id, ignore_errors=True)

    transaction = result.transactions[0]
    assert transaction.session_id == session_id
    assert transaction.source_file_name == "metadata_card.csv"
    assert transaction.stored_relative_path == metadata.stored_relative_path
    assert transaction.source_file_id
    assert result.source_file_id == transaction.source_file_id


def test_negative_amount_needs_review_with_warning(tmp_path):
    path = write_csv(
        tmp_path / "card_statement.csv",
        [{"사용일자": "2026-05-07", "가맹점명": "샘플환불", "이용금액": "-12,000"}],
    )

    result = CardStatementParser().parse(path)
    transaction = result.transactions[0]

    assert result.status == CardParseResultStatus.COMPLETED_WITH_WARNINGS.value
    assert transaction.parse_status == CardParseStatus.NEEDS_REVIEW.value
    assert any("음수 금액" in message for message in transaction.warning_messages)


@pytest.mark.parametrize("file_name", ["receipt.jpg", "receipt.png", "receipt.pdf"])
def test_image_and_pdf_files_are_not_card_statement_targets(tmp_path, file_name):
    path = tmp_path / file_name
    path.write_bytes(b"sample")

    result = CardStatementParser().parse(path)

    assert result.status == CardParseResultStatus.FAILED.value
    assert result.warning_messages

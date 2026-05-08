from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.card_models import CardParseResult, CardTransaction
from app.core.enums import CardParseResultStatus
from app.core.exceptions import MissingRequiredColumnsError
from app.parser.normalizers import (
    normalize_amount,
    normalize_approval_number,
    normalize_column_name,
    normalize_date,
    normalize_optional_text,
)
from app.storage.file_store import StoredFileMetadata


ParserInput = str | Path | StoredFileMetadata


class CardStatementParser:
    supported_extensions = {".xlsx", ".csv"}
    non_card_extensions = {".jpg", ".jpeg", ".png", ".pdf"}
    required_columns = {"transaction_date", "merchant_name", "total_amount"}
    optional_columns = {"card_name", "approval_number"}
    column_aliases = {
        "transaction_date": {
            "사용일자",
            "이용일자",
            "거래일자",
            "승인일자",
            "결제일자",
            "일자",
            "date",
            "transaction_date",
        },
        "merchant_name": {
            "가맹점명",
            "상호",
            "사용처",
            "이용가맹점",
            "거래처",
            "merchant",
            "merchant_name",
        },
        "total_amount": {
            "이용금액",
            "사용금액",
            "승인금액",
            "결제금액",
            "금액",
            "amount",
            "total_amount",
        },
        "card_name": {"카드명", "카드", "결제카드", "card", "card_name"},
        "approval_number": {"승인번호", "승인No", "승인 No", "approval_no", "approval_number"},
    }

    def __init__(self) -> None:
        self._alias_lookup = self._build_alias_lookup()

    def parse(self, source: ParserInput, sheet_name: int | str = 0) -> CardParseResult:
        source_info = self._source_info(source)
        extension = source_info["file_extension"]

        if extension not in self.supported_extensions:
            message = f"카드 사용내역 Parser 대상 파일이 아닙니다: {extension or '확장자 없음'}"
            return CardParseResult(
                id=self._new_id(),
                session_id=source_info["session_id"],
                source_file_id=source_info["source_file_id"],
                source_file_name=source_info["source_file_name"],
                total_rows=0,
                parsed_rows=0,
                failed_rows=0,
                transactions=[],
                warning_messages=[message],
                missing_required_columns=[],
                status=CardParseResultStatus.FAILED.value,
            )

        try:
            dataframe = self._read_dataframe(source_info["file_path"], extension, sheet_name)
        except (OSError, ValueError, FileNotFoundError) as exc:
            return CardParseResult(
                id=self._new_id(),
                session_id=source_info["session_id"],
                source_file_id=source_info["source_file_id"],
                source_file_name=source_info["source_file_name"],
                total_rows=0,
                parsed_rows=0,
                failed_rows=0,
                transactions=[],
                missing_required_columns=[],
                warning_messages=[f"카드 사용내역 파일을 읽을 수 없습니다: {exc.__class__.__name__}"],
                status=CardParseResultStatus.FAILED.value,
            )

        column_map = self.map_columns(dataframe.columns)
        self.validate_required_columns(column_map)

        transactions: list[CardTransaction] = []
        result_warnings: list[str] = []
        for index, row in dataframe.iterrows():
            transaction = self._parse_row(row, index + 2, column_map, source_info)
            transactions.append(transaction)
            result_warnings.extend(transaction.warning_messages)

        return CardParseResult.create(
            session_id=source_info["session_id"],
            source_file_id=source_info["source_file_id"],
            source_file_name=source_info["source_file_name"],
            total_rows=len(dataframe),
            transactions=transactions,
            warning_messages=result_warnings,
        )

    def map_columns(self, columns) -> dict[str, str]:
        mapped: dict[str, str] = {}
        for column in columns:
            standard_name = self._alias_lookup.get(normalize_column_name(column))
            if standard_name and standard_name not in mapped:
                mapped[standard_name] = column
        return mapped

    def validate_required_columns(self, column_map: dict[str, str]) -> None:
        missing = sorted(self.required_columns - set(column_map))
        if missing:
            raise MissingRequiredColumnsError(f"필수 카드 사용내역 컬럼이 없습니다: {', '.join(missing)}")

    def _parse_row(
        self,
        row: pd.Series,
        row_number: int,
        column_map: dict[str, str],
        source_info: dict[str, Any],
    ) -> CardTransaction:
        warnings: list[str] = []
        transaction_date = normalize_date(row.get(column_map["transaction_date"]))
        merchant_name = normalize_optional_text(row.get(column_map["merchant_name"]))
        total_amount = normalize_amount(row.get(column_map["total_amount"]))
        card_name = normalize_optional_text(row.get(column_map["card_name"])) if "card_name" in column_map else None
        approval_number = (
            normalize_approval_number(row.get(column_map["approval_number"])) if "approval_number" in column_map else None
        )

        if transaction_date is None:
            warnings.append("거래일자 확인 필요")
        if not merchant_name:
            warnings.append("가맹점명 확인 필요")
        if total_amount is None or total_amount == 0:
            warnings.append("금액 확인 필요")
        elif total_amount < 0:
            warnings.append("음수 금액 확인 필요")

        return CardTransaction.create(
            session_id=source_info["session_id"],
            source_file_id=source_info["source_file_id"],
            source_file_name=source_info["source_file_name"],
            stored_relative_path=source_info["stored_relative_path"],
            row_number=row_number,
            transaction_date=transaction_date,
            merchant_name=merchant_name,
            total_amount=total_amount,
            card_name=card_name,
            approval_number=approval_number,
            currency="KRW",
            warning_messages=warnings,
        )

    def _read_dataframe(self, path: Path, extension: str, sheet_name: int | str) -> pd.DataFrame:
        if extension == ".csv":
            return pd.read_csv(path, dtype=str, keep_default_na=False)
        return pd.read_excel(path, sheet_name=sheet_name, dtype=str, engine="openpyxl", keep_default_na=False)

    def _source_info(self, source: ParserInput) -> dict[str, Any]:
        if isinstance(source, StoredFileMetadata):
            stored_relative_path = source.stored_relative_path
            source_file_id = getattr(source, "file_id", None) or _source_file_id(stored_relative_path)
            return {
                "session_id": source.session_id,
                "source_file_id": source_file_id,
                "source_file_name": source.original_file_name,
                "stored_relative_path": stored_relative_path,
                "file_extension": source.file_extension.lower(),
                "file_path": Path(stored_relative_path),
            }

        path = Path(source)
        stored_relative_path = path.as_posix() if not path.is_absolute() else path.name
        return {
            "session_id": None,
            "source_file_id": _source_file_id(stored_relative_path),
            "source_file_name": path.name,
            "stored_relative_path": stored_relative_path,
            "file_extension": path.suffix.lower(),
            "file_path": path,
        }

    def _build_alias_lookup(self) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for standard_name, aliases in self.column_aliases.items():
            lookup[normalize_column_name(standard_name)] = standard_name
            for alias in aliases:
                lookup[normalize_column_name(alias)] = standard_name
        return lookup

    def _new_id(self) -> str:
        from uuid import uuid4

        return str(uuid4())


def _source_file_id(value: str | None) -> str:
    return sha256((value or "unknown").encode("utf-8")).hexdigest()

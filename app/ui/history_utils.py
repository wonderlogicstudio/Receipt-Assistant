from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


HISTORY_COLUMNS = [
    "처리일시",
    "상태",
    "영수증건수",
    "카드내역건수",
    "검토필요건수",
    "제외건수",
    "총금액",
    "엑셀파일명",
    "작업ID",
]

JOB_DETAIL_SUMMARY_KEYS = [
    "작업ID",
    "처리일시",
    "상태",
    "영수증 건수",
    "카드내역 건수",
    "검토필요 건수",
    "제외 건수",
    "총금액",
    "엑셀파일명",
]

RECEIPT_DETAIL_COLUMNS = [
    "사용일자",
    "상호",
    "총금액",
    "공급가액",
    "부가세",
    "최종비용항목",
    "추천비용항목",
    "검수상태",
    "검토사유",
    "카드매칭상태",
    "카드매칭사유",
    "중복의심여부",
    "원본파일명",
]

CARD_DETAIL_COLUMNS = [
    "사용일자",
    "가맹점명",
    "금액",
    "카드명",
    "승인번호",
    "파싱상태",
    "원본파일명",
]

EXPORT_FILE_COLUMNS = [
    "엑셀파일명",
    "생성일시",
    "파일크기",
]

HIDDEN_KEYS = {
    "stored_relative_path",
    "export_relative_path",
    "raw_text",
    "raw_json",
    "ocr_raw_text",
    "card_raw_text",
}


def jobs_to_history_dataframe(jobs: Iterable[object]) -> pd.DataFrame:
    rows = [sanitize_history_display_row(_as_dict(job)) for job in jobs]
    return pd.DataFrame(rows, columns=HISTORY_COLUMNS)


def sanitize_history_display_row(job: dict[str, object]) -> dict[str, object]:
    return {
        "처리일시": format_history_datetime(job.get("created_at") or job.get("updated_at")),
        "상태": str(job.get("status") or "-"),
        "영수증건수": _safe_int(job.get("receipt_count")),
        "카드내역건수": _safe_int(job.get("card_transaction_count")),
        "검토필요건수": _safe_int(job.get("needs_review_count")),
        "제외건수": _safe_int(job.get("excluded_count")),
        "총금액": format_amount(job.get("total_amount")),
        "엑셀파일명": _display_file_name(job.get("export_file_name")) or "-",
        "작업ID": _short_job_id(job.get("id")),
    }


def format_history_datetime(value: object) -> str:
    if value in {None, ""}:
        return "-"
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return "-"
    return parsed.strftime("%Y-%m-%d %H:%M")


def format_amount(value: object) -> str:
    if value in {None, ""}:
        return "-"
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return "-"
    return f"{amount:,}"


def build_history_summary(jobs: Iterable[object]) -> dict[str, int]:
    rows = [_as_dict(job) for job in jobs]
    return {
        "total_jobs": len(rows),
        "total_receipts": sum(_safe_int(row.get("receipt_count")) for row in rows),
        "total_card_transactions": sum(_safe_int(row.get("card_transaction_count")) for row in rows),
        "total_needs_review": sum(_safe_int(row.get("needs_review_count")) for row in rows),
        "total_amount": sum(_safe_int(row.get("total_amount")) for row in rows),
    }


def job_detail_to_summary_dict(detail: dict[str, object] | None) -> dict[str, object]:
    job = _job_from_detail(detail)
    return {
        "작업ID": str(job.get("id") or "-"),
        "처리일시": format_history_datetime(job.get("created_at") or job.get("updated_at")),
        "상태": str(job.get("status") or "-"),
        "영수증 건수": _safe_int(job.get("receipt_count")),
        "카드내역 건수": _safe_int(job.get("card_transaction_count")),
        "검토필요 건수": _safe_int(job.get("needs_review_count")),
        "제외 건수": _safe_int(job.get("excluded_count")),
        "총금액": format_amount(job.get("total_amount")),
        "엑셀파일명": _display_file_name(job.get("export_file_name")) or "-",
    }


def receipt_records_to_history_detail_dataframe(receipt_records: Iterable[object]) -> pd.DataFrame:
    rows = []
    for item in receipt_records:
        row = _as_dict(item)
        rows.append(
            {
                "사용일자": _date_display(row.get("transaction_date")),
                "상호": row.get("merchant_name") or "-",
                "총금액": format_amount(row.get("total_amount")),
                "공급가액": format_amount(row.get("supply_amount")),
                "부가세": format_amount(row.get("vat_amount")),
                "최종비용항목": row.get("expense_category") or "-",
                "추천비용항목": row.get("recommended_expense_category") or "-",
                "검수상태": row.get("review_status") or "-",
                "검토사유": _review_reason_display(row),
                "카드매칭상태": row.get("card_match_status") or "-",
                "카드매칭사유": row.get("card_match_reason") or "-",
                "중복의심여부": "예" if _safe_int(row.get("duplicate_suspected")) else "아니오",
                "원본파일명": _display_file_name(row.get("source_file_name")) or "-",
            }
        )
    return pd.DataFrame(rows, columns=RECEIPT_DETAIL_COLUMNS)


def card_transactions_to_history_detail_dataframe(card_transactions: Iterable[object]) -> pd.DataFrame:
    rows = []
    for item in card_transactions:
        row = _as_dict(item)
        rows.append(
            {
                "사용일자": _date_display(row.get("transaction_date")),
                "가맹점명": row.get("merchant_name") or "-",
                "금액": format_amount(row.get("total_amount")),
                "카드명": row.get("card_name") or "-",
                "승인번호": _mask_long_number(row.get("approval_number")) or "-",
                "파싱상태": row.get("parse_status") or "-",
                "원본파일명": _display_file_name(row.get("source_file_name")) or "-",
            }
        )
    return pd.DataFrame(rows, columns=CARD_DETAIL_COLUMNS)


def export_files_to_display_dataframe(export_files: Iterable[object]) -> pd.DataFrame:
    rows = []
    for item in export_files:
        row = _as_dict(item)
        rows.append(
            {
                "엑셀파일명": _display_file_name(row.get("export_file_name")) or "-",
                "생성일시": format_history_datetime(row.get("created_at")),
                "파일크기": format_file_size(row.get("file_size_bytes")),
            }
        )
    return pd.DataFrame(rows, columns=EXPORT_FILE_COLUMNS)


def select_latest_export_file(export_files: Iterable[object]) -> dict[str, object] | None:
    rows = [_as_dict(item) for item in export_files]
    if not rows:
        return None
    return max(rows, key=lambda row: str(row.get("created_at") or ""))


def build_safe_download_path(output_root: Path | str, export_relative_path: object) -> Path:
    if export_relative_path in {None, ""}:
        raise ValueError("missing export path")
    text = str(export_relative_path).replace("\\", "/").strip()
    relative = Path(text)
    if relative.is_absolute() or ".." in relative.parts or ":" in text.split("/")[0]:
        raise ValueError("unsafe export path")

    parts = list(relative.parts)
    if len(parts) >= 2 and parts[0] == "data" and parts[1] == "outputs":
        relative = Path(*parts[2:]) if len(parts) > 2 else Path()

    base = Path(output_root).resolve()
    candidate = (base / relative).resolve()
    if not _is_relative_to(candidate, base):
        raise ValueError("unsafe export path")
    return candidate


def read_export_file_bytes(output_root: Path | str, export_relative_path: object) -> bytes | None:
    path = build_safe_download_path(output_root, export_relative_path)
    if not path.exists() or not path.is_file():
        return None
    return path.read_bytes()


def format_file_size(value: object) -> str:
    size = _safe_int(value)
    if size <= 0:
        return "-"
    if size < 1024:
        return f"{size} B"
    return f"{size / 1024:.1f} KB"


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _job_from_detail(detail: dict[str, object] | None) -> dict[str, object]:
    if not detail:
        return {}
    data = _as_dict(detail)
    if isinstance(data.get("job"), dict):
        return dict(data["job"])
    return data


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _display_file_name(value: object) -> str | None:
    if value in {None, ""}:
        return None
    return Path(str(value).replace("\\", "/")).name


def _short_job_id(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    return text[:8]


def _date_display(value: object) -> str:
    if value in {None, ""}:
        return "-"
    text = str(value)
    if "T" in text:
        return format_history_datetime(text)
    return text[:10] if len(text) >= 10 else text


def _review_reason_display(row: dict[str, object]) -> str:
    for key in ("review_reasons_json", "parser_warnings_json", "validation_warnings_json"):
        value = row.get(key)
        if value:
            text = str(value).strip()
            return text if text else "-"
    return row.get("review_reason") or "-"


def _mask_long_number(value: object) -> str | None:
    if value in {None, ""}:
        return None
    text = str(value)
    digits = "".join(character for character in text if character.isdigit())
    if len(digits) >= 12:
        return f"***{digits[-4:]}"
    return text


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.enums import CardMatchStatus, ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.parser.normalizers import normalize_amount, normalize_date, normalize_optional_text


STATUS_LABEL_APPROVED = "확인완료"
STATUS_LABEL_NEEDS_REVIEW = "검토필요"
STATUS_LABEL_EXCLUDED = "제외"

REVIEW_STATUS_OPTIONS = [
    STATUS_LABEL_APPROVED,
    STATUS_LABEL_NEEDS_REVIEW,
    STATUS_LABEL_EXCLUDED,
]

COL_INCLUDED = "포함"
COL_DATE = "사용일자"
COL_MERCHANT = "상호"
COL_TOTAL = "총금액"
COL_GROSS_AMOUNT = "할인전금액"
COL_DISCOUNT_AMOUNT = "할인금액"
COL_FINAL_AMOUNT = "최종결제금액"
COL_PAID_AMOUNT = "실제결제금액"
COL_AMOUNT_SOURCE = "금액판단기준"
COL_AMOUNT_WARNINGS = "금액검토사유"
COL_SUPPLY = "공급가액"
COL_VAT = "부가세"
COL_ESTIMATED_SUPPLY = "추정공급가액"
COL_ESTIMATED_VAT = "추정부가세"
COL_VAT_SOURCE = "부가세출처"
COL_VAT_WARNINGS = "부가세검토사유"
COL_SENSITIVE_DETECTED = "민감문구감지"
COL_SENSITIVE_CATEGORIES = "민감문구유형"
COL_PAYMENT = "결제수단"
COL_RECOMMENDED_CATEGORY = "시스템 추천 비용항목"
COL_EXPENSE_CATEGORY = "최종 비용항목"
COL_REVIEW_STATUS = "검수상태"
COL_REVIEW_REASON = "검토사유"
COL_CARD_MATCH_STATUS = "카드매칭상태"
COL_CARD_MATCH_REASON = "카드매칭사유"
COL_DUPLICATE_SUSPECTED = "중복의심여부"
COL_SOURCE_FILE_NAME = "원본파일명"
COL_USER_NOTE = "비고"

INTERNAL_RECEIPT_ID = "__receipt_id"
INTERNAL_SOURCE_FILE_ID = "__source_file_id"
INTERNAL_OCR_RESULT_ID = "__ocr_result_id"

REVIEW_DISPLAY_COLUMNS = [
    COL_INCLUDED,
    COL_DATE,
    COL_MERCHANT,
    COL_TOTAL,
    COL_GROSS_AMOUNT,
    COL_DISCOUNT_AMOUNT,
    COL_FINAL_AMOUNT,
    COL_PAID_AMOUNT,
    COL_AMOUNT_SOURCE,
    COL_AMOUNT_WARNINGS,
    COL_SUPPLY,
    COL_VAT,
    COL_ESTIMATED_SUPPLY,
    COL_ESTIMATED_VAT,
    COL_VAT_SOURCE,
    COL_VAT_WARNINGS,
    COL_SENSITIVE_DETECTED,
    COL_SENSITIVE_CATEGORIES,
    COL_PAYMENT,
    COL_RECOMMENDED_CATEGORY,
    COL_EXPENSE_CATEGORY,
    COL_REVIEW_STATUS,
    COL_REVIEW_REASON,
    COL_CARD_MATCH_STATUS,
    COL_CARD_MATCH_REASON,
    COL_DUPLICATE_SUSPECTED,
    COL_SOURCE_FILE_NAME,
    COL_USER_NOTE,
]

REVIEW_EDITABLE_COLUMNS = [
    COL_INCLUDED,
    COL_DATE,
    COL_MERCHANT,
    COL_TOTAL,
    COL_SUPPLY,
    COL_VAT,
    COL_PAYMENT,
    COL_EXPENSE_CATEGORY,
    COL_REVIEW_STATUS,
    COL_USER_NOTE,
]

REVIEW_READ_ONLY_COLUMNS = [
    COL_RECOMMENDED_CATEGORY,
    COL_GROSS_AMOUNT,
    COL_DISCOUNT_AMOUNT,
    COL_FINAL_AMOUNT,
    COL_PAID_AMOUNT,
    COL_AMOUNT_SOURCE,
    COL_AMOUNT_WARNINGS,
    COL_ESTIMATED_SUPPLY,
    COL_ESTIMATED_VAT,
    COL_VAT_SOURCE,
    COL_VAT_WARNINGS,
    COL_SENSITIVE_DETECTED,
    COL_SENSITIVE_CATEGORIES,
    COL_REVIEW_REASON,
    COL_CARD_MATCH_STATUS,
    COL_CARD_MATCH_REASON,
    COL_DUPLICATE_SUSPECTED,
    COL_SOURCE_FILE_NAME,
]


def receipt_records_to_review_dataframe(records: list[ReceiptRecord]) -> pd.DataFrame:
    rows = [_record_to_review_row(record) for record in records]
    return pd.DataFrame(rows, columns=[*REVIEW_DISPLAY_COLUMNS, *tracking_columns()])


def review_dataframe_to_receipt_records(
    dataframe: pd.DataFrame,
    original_records: list[ReceiptRecord],
) -> list[ReceiptRecord]:
    records: list[ReceiptRecord] = []
    original_by_id = {record.id: record for record in original_records}
    originals_by_position = list(original_records)

    for index, row in enumerate(dataframe.to_dict(orient="records")):
        record_id = _clean_text(row.get(INTERNAL_RECEIPT_ID))
        original = original_by_id.get(record_id or "")
        if original is None and index < len(originals_by_position):
            original = originals_by_position[index]
        if original is None:
            continue

        status_label = _clean_text(row.get(COL_REVIEW_STATUS)) or map_review_status_to_label(original.review_status)
        included = _as_bool(row.get(COL_INCLUDED), default=not is_excluded_record(original))
        review_status = map_review_label_to_status(status_label)
        if not included or review_status == ReviewStatus.EXCLUDED.value:
            review_status = ReviewStatus.EXCLUDED.value
            included = False
        else:
            included = True

        records.append(
            replace(
                original,
                transaction_date=normalize_date(row.get(COL_DATE)),
                merchant_name=normalize_optional_text(row.get(COL_MERCHANT)),
                total_amount=normalize_amount(row.get(COL_TOTAL)),
                supply_amount=normalize_amount(row.get(COL_SUPPLY)),
                vat_amount=normalize_amount(row.get(COL_VAT)),
                payment_method=normalize_optional_text(row.get(COL_PAYMENT)),
                expense_category=normalize_optional_text(row.get(COL_EXPENSE_CATEGORY)),
                review_status=review_status,
                export_included=included,
                user_note=normalize_optional_text(row.get(COL_USER_NOTE)),
            )
        )

    return records


def map_review_status_to_label(status: str | ReviewStatus | None) -> str:
    status_value = _enum_value(status)
    if status_value == ReviewStatus.APPROVED.value:
        return STATUS_LABEL_APPROVED
    if status_value in {ReviewStatus.EXCLUDED.value, ReviewStatus.REJECTED.value}:
        return STATUS_LABEL_EXCLUDED
    return STATUS_LABEL_NEEDS_REVIEW


def map_review_label_to_status(label: str | None) -> str:
    if label == STATUS_LABEL_APPROVED:
        return ReviewStatus.APPROVED.value
    if label == STATUS_LABEL_EXCLUDED:
        return ReviewStatus.EXCLUDED.value
    return ReviewStatus.NEEDS_REVIEW.value


def is_excluded_record(record: ReceiptRecord) -> bool:
    if getattr(record, "export_included", True) is False:
        return True
    return record.review_status in {ReviewStatus.EXCLUDED.value, ReviewStatus.REJECTED.value}


def build_review_summary(records: list[ReceiptRecord]) -> dict[str, int]:
    total_amount_sum = sum(record.total_amount or 0 for record in records)
    included_records = [record for record in records if not is_excluded_record(record)]

    return {
        "total_count": len(records),
        "approved_count": sum(
            1
            for record in records
            if not is_excluded_record(record) and record.review_status == ReviewStatus.APPROVED.value
        ),
        "needs_review_count": sum(
            1
            for record in records
            if not is_excluded_record(record) and record.review_status != ReviewStatus.APPROVED.value
        ),
        "excluded_count": sum(1 for record in records if is_excluded_record(record)),
        "card_matched_count": sum(1 for record in records if record.card_match_status == CardMatchStatus.MATCHED.value),
        "card_candidate_count": sum(
            1 for record in records if record.card_match_status == CardMatchStatus.CANDIDATE.value
        ),
        "card_unmatched_count": sum(
            1
            for record in records
            if record.card_match_status not in {CardMatchStatus.MATCHED.value, CardMatchStatus.CANDIDATE.value}
        ),
        "duplicate_suspected_count": sum(1 for record in records if _has_duplicate_signal(record)),
        "total_amount_sum": total_amount_sum,
        "included_total_amount_sum": sum(record.total_amount or 0 for record in included_records),
    }


def tracking_columns() -> list[str]:
    return [INTERNAL_RECEIPT_ID, INTERNAL_SOURCE_FILE_ID, INTERNAL_OCR_RESULT_ID]


def _record_to_review_row(record: ReceiptRecord) -> dict[str, Any]:
    return {
        COL_INCLUDED: not is_excluded_record(record),
        COL_DATE: record.transaction_date,
        COL_MERCHANT: record.merchant_name,
        COL_TOTAL: record.total_amount,
        COL_GROSS_AMOUNT: record.gross_amount,
        COL_DISCOUNT_AMOUNT: record.discount_amount,
        COL_FINAL_AMOUNT: record.final_amount,
        COL_PAID_AMOUNT: record.paid_amount,
        COL_AMOUNT_SOURCE: record.amount_source,
        COL_AMOUNT_WARNINGS: "; ".join(record.amount_warnings),
        COL_SUPPLY: record.supply_amount,
        COL_VAT: record.vat_amount,
        COL_ESTIMATED_SUPPLY: record.estimated_supply_amount,
        COL_ESTIMATED_VAT: record.estimated_vat_amount,
        COL_VAT_SOURCE: record.vat_source,
        COL_VAT_WARNINGS: _joined_vat_reasons(record),
        COL_SENSITIVE_DETECTED: record.sensitive_text_detected,
        COL_SENSITIVE_CATEGORIES: "; ".join(record.sensitive_text_categories),
        COL_PAYMENT: record.payment_method,
        COL_RECOMMENDED_CATEGORY: record.recommended_expense_category,
        COL_EXPENSE_CATEGORY: record.expense_category,
        COL_REVIEW_STATUS: map_review_status_to_label(record.review_status),
        COL_REVIEW_REASON: _joined_reasons(record),
        COL_CARD_MATCH_STATUS: record.card_match_status,
        COL_CARD_MATCH_REASON: record.card_match_reason,
        COL_DUPLICATE_SUSPECTED: _has_duplicate_signal(record),
        COL_SOURCE_FILE_NAME: _display_file_name(record.source_file_name),
        COL_USER_NOTE: record.user_note,
        INTERNAL_RECEIPT_ID: record.id,
        INTERNAL_SOURCE_FILE_ID: record.source_file_id,
        INTERNAL_OCR_RESULT_ID: record.ocr_result_id,
    }


def _joined_reasons(record: ReceiptRecord) -> str:
    values = [
        *_split_reason_text(record.review_reason),
        *record.review_reasons,
        *record.parser_warnings,
        *record.validation_warnings,
        *record.vat_warnings,
        *record.sensitive_warnings,
    ]
    return "; ".join(_unique(values))


def _joined_vat_reasons(record: ReceiptRecord) -> str:
    values = [*record.vat_warnings]
    if record.vat_note:
        values.append(record.vat_note)
    return "; ".join(_unique(values))


def _has_duplicate_signal(record: ReceiptRecord) -> bool:
    return bool(record.duplicate_group_id or record.duplicate_candidate_ids or record.duplicate_reason)


def _display_file_name(file_name: str | None) -> str | None:
    if not file_name:
        return None
    return Path(str(file_name).replace("\\", "/")).name


def _split_reason_text(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _enum_value(value: object) -> str | None:
    if value is None:
        return None
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None


def _as_bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "no", "n", "off", ""}
    return bool(value)

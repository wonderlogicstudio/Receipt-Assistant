from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol

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
COL_MERCHANT_CANDIDATE = "상호 후보"
COL_MERCHANT_CANDIDATE_SCORE = "후보 점수"
COL_BUSINESS_STATUS = "사업자번호 상태조회"
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
COL_REVIEW_PRIORITY = "검토우선순위"
COL_MISSING_FIELDS = "누락필드"
COL_QUALITY_FLAGS = "검토사유요약"
COL_SOURCE_PREVIEW = "원본보기"

REVIEW_FILTER_ALL = "전체"
REVIEW_FILTER_NEEDS_REVIEW = "검토필요"
REVIEW_FILTER_APPROVED = "확인완료"
REVIEW_FILTER_EXCLUDED = "제외"

ISSUE_MERCHANT_MISSING = "상호 누락"
ISSUE_DATE_MISSING = "날짜 누락"
ISSUE_BUSINESS_NUMBER_MISSING = "사업자번호 누락"
ISSUE_TOTAL_MISSING = "총액 누락"
ISSUE_PAYMENT_MISSING = "결제수단 누락"
ISSUE_VAT_REVIEW = "부가세 확인"
ISSUE_DISCOUNT_ZERO_PAYMENT = "할인/0원 결제"
ISSUE_SENSITIVE_TEXT = "민감문구 감지"
ISSUE_CARD_UNMATCHED = "카드 미매칭"

REVIEW_FILTER_OPTIONS = [
    REVIEW_FILTER_ALL,
    REVIEW_FILTER_NEEDS_REVIEW,
    REVIEW_FILTER_APPROVED,
    REVIEW_FILTER_EXCLUDED,
]

REVIEW_ISSUE_OPTIONS = [
    ISSUE_MERCHANT_MISSING,
    ISSUE_DATE_MISSING,
    ISSUE_BUSINESS_NUMBER_MISSING,
    ISSUE_TOTAL_MISSING,
    ISSUE_PAYMENT_MISSING,
    ISSUE_VAT_REVIEW,
    ISSUE_DISCOUNT_ZERO_PAYMENT,
    ISSUE_SENSITIVE_TEXT,
    ISSUE_CARD_UNMATCHED,
]

INTERNAL_RECEIPT_ID = "__receipt_id"
INTERNAL_SOURCE_FILE_ID = "__source_file_id"
INTERNAL_OCR_RESULT_ID = "__ocr_result_id"

PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"
PRIORITY_SORT_ORDER = {
    PRIORITY_HIGH: 0,
    PRIORITY_MEDIUM: 1,
    PRIORITY_LOW: 2,
}

PREVIEW_KIND_IMAGE = "image"
PREVIEW_KIND_PDF = "pdf"
PREVIEW_KIND_UNAVAILABLE = "unavailable"
PREVIEW_KIND_BLOCKED = "blocked"
PREVIEW_KIND_MISSING = "missing"
PREVIEW_KIND_UNSUPPORTED = "unsupported"
IMAGE_PREVIEW_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_PREVIEW_EXTENSIONS = {".pdf"}

REVIEW_DISPLAY_COLUMNS = [
    COL_REVIEW_PRIORITY,
    COL_MISSING_FIELDS,
    COL_QUALITY_FLAGS,
    COL_SOURCE_FILE_NAME,
    COL_SOURCE_PREVIEW,
    COL_INCLUDED,
    COL_DATE,
    COL_MERCHANT,
    COL_MERCHANT_CANDIDATE,
    COL_MERCHANT_CANDIDATE_SCORE,
    COL_BUSINESS_STATUS,
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
    COL_REVIEW_PRIORITY,
    COL_MISSING_FIELDS,
    COL_QUALITY_FLAGS,
    COL_SOURCE_PREVIEW,
    COL_MERCHANT_CANDIDATE,
    COL_MERCHANT_CANDIDATE_SCORE,
    COL_BUSINESS_STATUS,
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


@dataclass(frozen=True)
class ReceiptSourcePreview:
    kind: str
    source_file_name: str
    path: Path | None = None
    message: str = ""

    @property
    def is_image(self) -> bool:
        return self.kind == PREVIEW_KIND_IMAGE and self.path is not None

    @property
    def is_pdf(self) -> bool:
        return self.kind == PREVIEW_KIND_PDF


class MerchantMatcherProtocol(Protocol):
    def find_candidates(
        self,
        *,
        merchant_name: object = None,
        business_number: object = None,
        address_hint: object = None,
    ) -> list[Any]:
        ...


def receipt_records_to_review_dataframe(
    records: list[ReceiptRecord],
    *,
    merchant_matcher: MerchantMatcherProtocol | None = None,
    merchant_address_hints: dict[str, object] | None = None,
) -> pd.DataFrame:
    rows = [
        _record_to_review_row(
            record,
            merchant_matcher=merchant_matcher,
            address_hint=(merchant_address_hints or {}).get(record.id),
        )
        for record in sort_receipt_records_for_review(records)
    ]
    return pd.DataFrame(rows, columns=[*REVIEW_DISPLAY_COLUMNS, *tracking_columns()])


def sort_receipt_records_for_review(records: list[ReceiptRecord]) -> list[ReceiptRecord]:
    sorted_items = sorted(
        enumerate(records),
        key=lambda item: (PRIORITY_SORT_ORDER.get(review_priority_label(item[1]), 99), item[0]),
    )
    return [record for _, record in sorted_items]


def filter_receipt_records_for_review(
    records: list[ReceiptRecord],
    *,
    status_filter: str = REVIEW_FILTER_ALL,
    issue_filters: list[str] | tuple[str, ...] | None = None,
) -> list[ReceiptRecord]:
    selected_issues = set(issue_filters or [])
    return [
        record
        for record in records
        if _matches_review_status_filter(record, status_filter)
        and _matches_issue_filters(record, selected_issues)
    ]


def merge_reviewed_records(
    original_records: list[ReceiptRecord],
    reviewed_subset: list[ReceiptRecord],
) -> list[ReceiptRecord]:
    reviewed_by_id = {record.id: record for record in reviewed_subset}
    return [reviewed_by_id.get(record.id, record) for record in original_records]


def build_review_issue_summary(records: list[ReceiptRecord]) -> dict[str, int]:
    summary = {issue: 0 for issue in REVIEW_ISSUE_OPTIONS}
    for record in records:
        for issue in review_issue_labels(record):
            if issue in summary:
                summary[issue] += 1
    return summary


def review_issue_labels(record: ReceiptRecord) -> list[str]:
    issues: list[str] = []
    if not record.merchant_name:
        issues.append(ISSUE_MERCHANT_MISSING)
    if record.transaction_date is None:
        issues.append(ISSUE_DATE_MISSING)
    if not record.business_number:
        issues.append(ISSUE_BUSINESS_NUMBER_MISSING)
    if record.total_amount is None:
        issues.append(ISSUE_TOTAL_MISSING)
    if not record.payment_method:
        issues.append(ISSUE_PAYMENT_MISSING)
    if record.vat_review_required or record.vat_warnings:
        issues.append(ISSUE_VAT_REVIEW)
    if "zero_payment_after_discount" in record.amount_warnings:
        issues.append(ISSUE_DISCOUNT_ZERO_PAYMENT)
    if record.sensitive_text_detected or record.sensitive_text_categories:
        issues.append(ISSUE_SENSITIVE_TEXT)
    if record.card_match_status not in {CardMatchStatus.MATCHED.value, CardMatchStatus.CANDIDATE.value}:
        issues.append(ISSUE_CARD_UNMATCHED)
    return _unique(issues)


def review_priority_label(record: ReceiptRecord) -> str:
    if (
        record.transaction_date is None
        or not record.merchant_name
        or record.total_amount is None
        or bool(record.amount_warnings)
        or bool(record.vat_warnings)
        or bool(record.vat_review_required)
        or bool(record.sensitive_text_detected)
        or bool(record.sensitive_text_categories)
        or record.card_match_status in {
            CardMatchStatus.NEEDS_REVIEW.value,
            CardMatchStatus.CANDIDATE.value,
            CardMatchStatus.MISMATCH.value,
        }
    ):
        return PRIORITY_HIGH
    if _is_uncategorized_recommendation(record.recommended_expense_category) or record.review_status == ReviewStatus.PENDING.value:
        return PRIORITY_MEDIUM
    if record.review_status == ReviewStatus.APPROVED.value and not _joined_reasons(record):
        return PRIORITY_LOW
    return PRIORITY_MEDIUM


def missing_field_labels(record: ReceiptRecord) -> list[str]:
    missing_fields: list[str] = []
    if record.transaction_date is None:
        missing_fields.append("transaction_date")
    if not record.merchant_name:
        missing_fields.append("merchant_name")
    if record.total_amount is None:
        missing_fields.append("total_amount")
    if not record.expense_category:
        missing_fields.append("expense_category")
    return missing_fields


def resolve_receipt_source_preview(
    record: ReceiptRecord,
    *,
    upload_root: Path | str = Path("data/uploads"),
    upload_relative_root: Path | str = Path("data/uploads"),
) -> ReceiptSourcePreview:
    file_name = _display_file_name(record.source_file_name) or "receipt"
    if not record.stored_relative_path:
        return ReceiptSourcePreview(
            kind=PREVIEW_KIND_UNAVAILABLE,
            source_file_name=file_name,
            message="원본 파일 위치 정보가 없습니다.",
        )

    safe_path = _resolve_safe_upload_path(
        record.stored_relative_path,
        upload_root=Path(upload_root),
        upload_relative_root=Path(upload_relative_root),
    )
    if safe_path is None:
        return ReceiptSourcePreview(
            kind=PREVIEW_KIND_BLOCKED,
            source_file_name=file_name,
            message="안전한 업로드 경로의 파일만 미리볼 수 있습니다.",
        )
    if not safe_path.exists():
        return ReceiptSourcePreview(
            kind=PREVIEW_KIND_MISSING,
            source_file_name=file_name,
            message="원본 파일을 찾을 수 없습니다.",
        )

    extension = safe_path.suffix.lower()
    if extension in IMAGE_PREVIEW_EXTENSIONS:
        return ReceiptSourcePreview(kind=PREVIEW_KIND_IMAGE, source_file_name=file_name, path=safe_path)
    if extension in PDF_PREVIEW_EXTENSIONS:
        return ReceiptSourcePreview(
            kind=PREVIEW_KIND_PDF,
            source_file_name=file_name,
            path=safe_path,
            message="PDF 원본 파일입니다. 다운로드 또는 별도 열기 대상입니다.",
        )
    return ReceiptSourcePreview(
        kind=PREVIEW_KIND_UNSUPPORTED,
        source_file_name=file_name,
        message="미리보기를 지원하지 않는 파일 형식입니다.",
    )


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


def format_display_amount(value: object, *, suffix: str = "원", missing: str = "-") -> str:
    if value is None:
        return missing
    try:
        amount = int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return missing
    return f"{amount:,}{suffix}"


def tracking_columns() -> list[str]:
    return [INTERNAL_RECEIPT_ID, INTERNAL_SOURCE_FILE_ID, INTERNAL_OCR_RESULT_ID]


def _record_to_review_row(
    record: ReceiptRecord,
    *,
    merchant_matcher: MerchantMatcherProtocol | None = None,
    address_hint: object = None,
) -> dict[str, Any]:
    candidate_label, candidate_score = _merchant_candidate_display(record, merchant_matcher, address_hint=address_hint)
    return {
        COL_REVIEW_PRIORITY: review_priority_label(record),
        COL_MISSING_FIELDS: _joined_missing_fields(record),
        COL_QUALITY_FLAGS: "; ".join(review_issue_labels(record)) or "-",
        COL_SOURCE_PREVIEW: _source_preview_label(record),
        COL_INCLUDED: not is_excluded_record(record),
        COL_DATE: record.transaction_date,
        COL_MERCHANT: record.merchant_name,
        COL_MERCHANT_CANDIDATE: candidate_label,
        COL_MERCHANT_CANDIDATE_SCORE: candidate_score,
        COL_BUSINESS_STATUS: _business_status_hint(record),
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


def _merchant_candidate_display(
    record: ReceiptRecord,
    merchant_matcher: MerchantMatcherProtocol | None,
    *,
    address_hint: object = None,
) -> tuple[str, str]:
    if merchant_matcher is None:
        return "-", "-"
    try:
        candidates = merchant_matcher.find_candidates(
            merchant_name=record.merchant_name,
            business_number=record.business_number,
            address_hint=address_hint,
        )
    except Exception:
        return "-", "-"
    if not candidates:
        return "-", "-"
    candidate = candidates[0]
    name = getattr(candidate, "candidate_merchant_name", None) or "-"
    match_type = getattr(candidate, "match_type", None) or "candidate"
    score = getattr(candidate, "score", None)
    business_number = getattr(candidate, "candidate_business_number", None)
    number_suffix = f" / {business_number}" if business_number else ""
    address_summary = getattr(candidate, "address_summary", None)
    address_suffix = f" / {address_summary}" if address_summary else ""
    return f"{name}{number_suffix}{address_suffix} ({match_type})", "-" if score is None else str(score)


def _business_status_hint(record: ReceiptRecord) -> str:
    if not record.business_number:
        return "-"
    return "not_checked"


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


def _joined_missing_fields(record: ReceiptRecord) -> str:
    return ", ".join(missing_field_labels(record)) or "-"


def _matches_review_status_filter(record: ReceiptRecord, status_filter: str) -> bool:
    if status_filter == REVIEW_FILTER_NEEDS_REVIEW:
        return not is_excluded_record(record) and record.review_status != ReviewStatus.APPROVED.value
    if status_filter == REVIEW_FILTER_APPROVED:
        return not is_excluded_record(record) and record.review_status == ReviewStatus.APPROVED.value
    if status_filter == REVIEW_FILTER_EXCLUDED:
        return is_excluded_record(record)
    return True


def _matches_issue_filters(record: ReceiptRecord, issue_filters: set[str]) -> bool:
    if not issue_filters:
        return True
    record_issues = set(review_issue_labels(record))
    return bool(record_issues & issue_filters)


def _has_duplicate_signal(record: ReceiptRecord) -> bool:
    return bool(record.duplicate_group_id or record.duplicate_candidate_ids or record.duplicate_reason)


def _display_file_name(file_name: str | None) -> str | None:
    if not file_name:
        return None
    return Path(str(file_name).replace("\\", "/")).name


def _source_preview_label(record: ReceiptRecord) -> str:
    path_text = str(record.stored_relative_path or record.source_file_name or "")
    extension = Path(path_text.replace("\\", "/")).suffix.lower()
    if extension in IMAGE_PREVIEW_EXTENSIONS:
        return "이미지"
    if extension in PDF_PREVIEW_EXTENSIONS:
        return "PDF"
    return "-"


def _is_uncategorized_recommendation(value: str | None) -> bool:
    if not value:
        return True
    normalized = str(value).strip().lower()
    return normalized in {"-", "uncategorized", "unknown", "none", "미분류"}


def _resolve_safe_upload_path(
    stored_relative_path: str,
    *,
    upload_root: Path,
    upload_relative_root: Path,
) -> Path | None:
    normalized_text = str(stored_relative_path).replace("\\", "/").strip()
    if not normalized_text:
        return None
    relative_path = Path(normalized_text)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None
    try:
        upload_subpath = relative_path.relative_to(upload_relative_root)
    except ValueError:
        return None
    if ".." in upload_subpath.parts:
        return None
    upload_root_resolved = upload_root.resolve(strict=False)
    candidate = (upload_root_resolved / upload_subpath).resolve(strict=False)
    try:
        candidate.relative_to(upload_root_resolved)
    except ValueError:
        return None
    return candidate


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

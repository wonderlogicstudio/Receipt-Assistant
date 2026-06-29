from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from app.classifier.merchant_candidate import MerchantCandidate, MerchantCandidateMatcher
from app.classifier.merchant_normalizer import (
    normalize_business_number,
    sanitize_optional_text,
)
from app.db.database import get_connection
from app.db.merchant_repository import MerchantRepository


SCORE_BUCKETS = ("90_100", "80_89", "70_79", "below_70", "missing")


@dataclass(frozen=True)
class MerchantCategorySummary:
    category_large: str
    row_count: int


@dataclass(frozen=True)
class MerchantImportBatchSummary:
    source_batch_id: str
    source_file_name: str | None
    imported_row_count: int
    skipped_row_count: int
    duplicate_file: bool
    created_at: str | None


@dataclass(frozen=True)
class MerchantDictionarySummary:
    merchant_master_row_count: int
    merchant_alias_row_count: int
    source_import_batch_count: int
    duplicate_file_count: int
    latest_import_date: str | None
    latest_source_file_name: str | None
    top_categories: tuple[MerchantCategorySummary, ...]
    recent_import_batches: tuple[MerchantImportBatchSummary, ...]

    def as_display_dict(self) -> dict[str, object]:
        return {
            "merchant_master_row_count": self.merchant_master_row_count,
            "merchant_alias_row_count": self.merchant_alias_row_count,
            "source_import_batch_count": self.source_import_batch_count,
            "duplicate_file_count": self.duplicate_file_count,
            "latest_import_date": self.latest_import_date or "-",
            "latest_source_file_name": self.latest_source_file_name or "-",
        }


@dataclass(frozen=True)
class SavedReceiptDiagnosticSummary:
    scanned_record_count: int
    candidate_present_count: int
    candidate_missing_count: int
    exact_match_count: int
    fuzzy_match_count: int
    alias_match_count: int
    review_required_count: int
    score_buckets: dict[str, int]
    sample_rows: tuple[dict[str, object], ...]

    def as_display_dict(self) -> dict[str, object]:
        return {
            "scanned_record_count": self.scanned_record_count,
            "candidate_present_count": self.candidate_present_count,
            "candidate_missing_count": self.candidate_missing_count,
            "exact_match_count": self.exact_match_count,
            "fuzzy_match_count": self.fuzzy_match_count,
            "alias_match_count": self.alias_match_count,
            "review_required_count": self.review_required_count,
            **{f"score_bucket_{key}": self.score_buckets.get(key, 0) for key in SCORE_BUCKETS},
        }


def build_merchant_dictionary_summary(
    repository: MerchantRepository,
    *,
    top_category_limit: int = 5,
    recent_batch_limit: int = 5,
) -> MerchantDictionarySummary:
    with get_connection(config=repository.config, db_path=repository.db_path) as connection:
        master_count = _fetch_count(connection, "SELECT COUNT(*) FROM merchant_master")
        alias_count = _fetch_count(connection, "SELECT COUNT(*) FROM merchant_alias")
        batch_count = _fetch_count(
            connection,
            """
            SELECT COUNT(DISTINCT source_batch_id)
            FROM merchant_source_log
            WHERE COALESCE(source_batch_id, '') <> ''
            """,
        )
        duplicate_file_count = _fetch_count(
            connection,
            "SELECT COUNT(*) FROM merchant_source_log WHERE duplicate_file = 1",
        )
        latest = connection.execute(
            """
            SELECT source_file_name, created_at
            FROM merchant_source_log
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
        category_rows = connection.execute(
            """
            SELECT category_large, COUNT(*) AS row_count
            FROM merchant_master
            WHERE COALESCE(category_large, '') <> ''
            GROUP BY category_large
            ORDER BY row_count DESC, category_large ASC
            LIMIT ?
            """,
            (top_category_limit,),
        ).fetchall()
        recent_rows = connection.execute(
            """
            SELECT source_batch_id, source_file_name, imported_row_count,
                   skipped_row_count, duplicate_file, created_at
            FROM merchant_source_log
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (recent_batch_limit,),
        ).fetchall()

    return MerchantDictionarySummary(
        merchant_master_row_count=master_count,
        merchant_alias_row_count=alias_count,
        source_import_batch_count=batch_count,
        duplicate_file_count=duplicate_file_count,
        latest_import_date=str(latest["created_at"]) if latest else None,
        latest_source_file_name=_safe_file_name(latest["source_file_name"]) if latest else None,
        top_categories=tuple(
            MerchantCategorySummary(
                category_large=sanitize_optional_text(row["category_large"], max_length=80) or "-",
                row_count=int(row["row_count"] or 0),
            )
            for row in category_rows
        ),
        recent_import_batches=tuple(
            MerchantImportBatchSummary(
                source_batch_id=sanitize_optional_text(row["source_batch_id"], max_length=80) or "-",
                source_file_name=_safe_file_name(row["source_file_name"]),
                imported_row_count=int(row["imported_row_count"] or 0),
                skipped_row_count=int(row["skipped_row_count"] or 0),
                duplicate_file=bool(row["duplicate_file"]),
                created_at=str(row["created_at"]) if row["created_at"] else None,
            )
            for row in recent_rows
        ),
    )


def build_candidate_diagnostic_rows(
    matcher: MerchantCandidateMatcher,
    *,
    merchant_name: object = None,
    business_number: object = None,
    address_hint: object = None,
) -> list[dict[str, object]]:
    candidates = matcher.find_candidates(
        merchant_name=merchant_name,
        business_number=business_number,
        address_hint=address_hint,
    )
    return [candidate_to_diagnostic_row(candidate) for candidate in candidates]


def candidate_to_diagnostic_row(candidate: MerchantCandidate) -> dict[str, object]:
    return {
        "candidate_merchant_name": sanitize_optional_text(candidate.candidate_merchant_name, max_length=160) or "-",
        "candidate_business_number_masked": mask_business_number(candidate.candidate_business_number) or "-",
        "candidate_business_number_present": bool(normalize_business_number(candidate.candidate_business_number)),
        "score": int(candidate.score),
        "match_type": sanitize_optional_text(candidate.match_type, max_length=80) or "-",
        "source": sanitize_optional_text(candidate.source, max_length=80) or "-",
        "review_required": bool(candidate.review_required),
        "address_summary": sanitize_optional_text(candidate.address_summary, max_length=80) or "-",
    }


def mask_business_number(value: object) -> str | None:
    normalized = normalize_business_number(value)
    if not normalized:
        return None
    return f"{normalized[:3]}-**-*****"


def build_saved_receipt_candidate_diagnostic(
    records: Iterable[Mapping[str, object]],
    matcher: MerchantCandidateMatcher,
    *,
    max_records: int = 100,
    sample_limit: int = 10,
) -> SavedReceiptDiagnosticSummary:
    score_buckets = {key: 0 for key in SCORE_BUCKETS}
    scanned = 0
    present = 0
    missing = 0
    exact = 0
    fuzzy = 0
    alias = 0
    review_required = 0
    sample_rows: list[dict[str, object]] = []

    for record in records:
        if scanned >= max_records:
            break
        scanned += 1
        merchant_name = record.get("merchant_name")
        business_number = record.get("business_number")
        candidates = matcher.find_candidates(merchant_name=merchant_name, business_number=business_number)
        top = candidates[0] if candidates else None
        if top is None:
            missing += 1
            score_buckets["missing"] += 1
        else:
            present += 1
            bucket = _score_bucket(top.score)
            score_buckets[bucket] += 1
            if "exact" in top.match_type:
                exact += 1
            if "fuzzy" in top.match_type:
                fuzzy += 1
            if top.match_type.startswith("alias"):
                alias += 1
            if top.review_required:
                review_required += 1

        if len(sample_rows) < sample_limit:
            sample_rows.append(
                {
                    "file_name": _safe_file_name(record.get("source_file_name")) or "-",
                    "merchant_summary": _safe_merchant_summary(merchant_name),
                    "review_status": sanitize_optional_text(record.get("review_status"), max_length=80) or "-",
                    "candidate_count": len(candidates),
                    "top_score": int(top.score) if top else None,
                    "top_match_type": sanitize_optional_text(top.match_type, max_length=80) if top else "-",
                }
            )

    return SavedReceiptDiagnosticSummary(
        scanned_record_count=scanned,
        candidate_present_count=present,
        candidate_missing_count=missing,
        exact_match_count=exact,
        fuzzy_match_count=fuzzy,
        alias_match_count=alias,
        review_required_count=review_required,
        score_buckets=score_buckets,
        sample_rows=tuple(sample_rows),
    )


def collect_recent_receipt_records(
    history_service: object,
    *,
    job_limit: int = 20,
    record_limit: int = 100,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    jobs = history_service.list_processing_jobs(limit=job_limit, offset=0)
    for job in jobs:
        if len(records) >= record_limit:
            break
        job_id = str(job.get("id") or "")
        if not job_id:
            continue
        detail = history_service.get_processing_job_detail(job_id) or {}
        for row in detail.get("receipt_records") or []:
            if len(records) >= record_limit:
                break
            if not isinstance(row, Mapping):
                continue
            records.append(
                {
                    "merchant_name": row.get("merchant_name"),
                    "business_number": row.get("business_number"),
                    "source_file_name": _safe_file_name(row.get("source_file_name")),
                    "review_status": row.get("review_status"),
                }
            )
    return records


def _fetch_count(connection: object, sql: str) -> int:
    row = connection.execute(sql).fetchone()
    if row is None:
        return 0
    return int(row[0] or 0)


def _score_bucket(score: object) -> str:
    try:
        value = int(score)
    except (TypeError, ValueError):
        return "missing"
    if value >= 90:
        return "90_100"
    if value >= 80:
        return "80_89"
    if value >= 70:
        return "70_79"
    return "below_70"


def _safe_file_name(value: object) -> str | None:
    if value in {None, ""}:
        return None
    return Path(str(value).replace("\\", "/")).name


def _safe_merchant_summary(value: object) -> str:
    text = sanitize_optional_text(value, max_length=40)
    if not text:
        return "-"
    return text

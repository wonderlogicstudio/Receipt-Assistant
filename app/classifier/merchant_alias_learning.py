from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.classifier.merchant_normalizer import (
    business_number_digits,
    normalize_business_number,
    normalize_merchant_name,
    sanitize_optional_text,
)
from app.core.enums import ReviewStatus
from app.core.receipt_models import ReceiptRecord
from app.db.merchant_repository import MerchantAliasInput, MerchantRepository, MerchantSearchRow


ALIAS_SOURCE_REVIEW = "review"
DEFAULT_MASTER_LINK_SCORE = 92


@dataclass(frozen=True)
class MerchantAliasLearningResult:
    saved_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0


class MerchantAliasLearningService:
    def __init__(
        self,
        repository: MerchantRepository,
        *,
        master_link_score: int = DEFAULT_MASTER_LINK_SCORE,
    ) -> None:
        self.repository = repository
        self.master_link_score = master_link_score

    def learn_from_review(
        self,
        *,
        original_records: list[ReceiptRecord],
        reviewed_records: list[ReceiptRecord],
    ) -> MerchantAliasLearningResult:
        original_by_id = {record.id: record for record in original_records}
        saved_count = 0
        skipped_count = 0
        failed_count = 0
        seen_inputs: set[tuple[str, str | None]] = set()

        for reviewed in reviewed_records:
            if _is_excluded(reviewed):
                skipped_count += 1
                continue
            final_name = reviewed.merchant_name
            business_number = normalize_business_number(reviewed.business_number)
            master_id = self._resolve_master_id(final_name, business_number)
            names_to_save = [final_name]

            original = original_by_id.get(reviewed.id)
            if original is not None and _normalized_or_empty(original.merchant_name) != _normalized_or_empty(final_name):
                names_to_save.append(original.merchant_name)

            for alias_name in names_to_save:
                normalized_alias = normalize_merchant_name(alias_name)
                dedupe_key = (normalized_alias, business_number)
                if not normalized_alias or dedupe_key in seen_inputs:
                    skipped_count += 1
                    continue
                seen_inputs.add(dedupe_key)
                if not is_safe_review_alias_name(alias_name):
                    skipped_count += 1
                    continue
                try:
                    if self.repository.add_alias(
                        MerchantAliasInput(
                            alias_name=sanitize_optional_text(alias_name, max_length=160) or "",
                            merchant_master_id=master_id,
                            business_number=business_number,
                            source=ALIAS_SOURCE_REVIEW,
                        )
                    ):
                        saved_count += 1
                    else:
                        skipped_count += 1
                except Exception:
                    failed_count += 1

        return MerchantAliasLearningResult(
            saved_count=saved_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
        )

    def _resolve_master_id(self, merchant_name: object, business_number: object) -> str | None:
        normalized_business_number = normalize_business_number(business_number)
        if normalized_business_number:
            rows = self.repository.find_master_by_business_number(normalized_business_number, limit=1)
            if rows:
                return rows[0].id

        normalized_name = normalize_merchant_name(merchant_name)
        if not normalized_name:
            return None

        exact_rows = self.repository.find_master_by_normalized_name(normalized_name, limit=1)
        if exact_rows:
            return exact_rows[0].id

        best_row: MerchantSearchRow | None = None
        best_score = 0
        for row in self.repository.list_master_name_candidates(normalized_name):
            score = _similarity_score(normalized_name, row.normalized_name)
            if score > best_score:
                best_score = score
                best_row = row
        if best_row is not None and best_score >= self.master_link_score:
            return best_row.id
        return None


def is_safe_review_alias_name(value: object) -> bool:
    text = sanitize_optional_text(value, max_length=160)
    if not text:
        return False
    normalized = normalize_merchant_name(text)
    if len(normalized) < 2:
        return False
    if business_number_digits(text) is not None:
        return False
    if _looks_like_phone_number(text):
        return False
    if _looks_like_date(text):
        return False
    if _looks_like_amount_or_identifier(text):
        return False
    if _looks_like_representative_or_metadata(text):
        return False

    letter_count = sum(1 for character in normalized if character.isalpha() or _is_hangul(character))
    digit_count = sum(1 for character in normalized if character.isdigit())
    if letter_count < 2:
        return False
    if digit_count > max(2, letter_count * 2):
        return False
    return True


def _is_excluded(record: ReceiptRecord) -> bool:
    return record.export_included is False or record.review_status in {
        ReviewStatus.EXCLUDED.value,
        ReviewStatus.REJECTED.value,
    }


def _normalized_or_empty(value: object) -> str:
    return normalize_merchant_name(value) or ""


def _looks_like_phone_number(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) in {10, 11} and digits.startswith("0"):
        return True
    return bool(re.search(r"(?:\(?0\d{1,3}\)?[-.\s]?)?\d{3,4}[-.\s]\d{4}", value))


def _looks_like_date(value: str) -> bool:
    return bool(
        re.fullmatch(r"\s*\d{4}[-./]?\d{1,2}[-./]?\d{1,2}\s*", value)
        or re.fullmatch(r"\s*\d{8}\s*", value)
    )


def _looks_like_amount_or_identifier(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    digits = re.sub(r"\D", "", value)
    if re.fullmatch(r"[\W_0-9]+", compact):
        return True
    if re.search(r"(?:원|₩|합계|총액|금액|결제|승인|카드|고유번호|영수증|pos)", value, flags=re.IGNORECASE):
        return True
    if len(digits) >= 8 and len(digits) >= len(compact) - 2:
        return True
    return False


def _looks_like_representative_or_metadata(value: str) -> bool:
    lowered = value.lower()
    keywords = (
        "대표",
        "대표자",
        "성명",
        "사업자",
        "등록번호",
        "전화",
        "tel",
        "phone",
        "owner",
        "ceo",
        "주소",
        "도로명",
    )
    return any(keyword in lowered for keyword in keywords)


def _similarity_score(left: str, right: str) -> int:
    if not left or not right:
        return 0
    if left == right:
        return 100
    if left in right or right in left:
        shorter = min(len(left), len(right))
        longer = max(len(left), len(right))
        return max(80, int(shorter / longer * 100))
    return int(SequenceMatcher(None, left, right).ratio() * 100)


def _is_hangul(character: str) -> bool:
    return "\uac00" <= character <= "\ud7a3"

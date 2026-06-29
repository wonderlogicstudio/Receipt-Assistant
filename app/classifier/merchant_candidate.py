from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.classifier.merchant_normalizer import normalize_business_number, normalize_merchant_name, normalize_road_address
from app.db.merchant_repository import MerchantRepository, MerchantSearchRow
from app.parser.address_hint import address_hint_to_search_text, extract_address_hint_from_safe_line


MATCH_TYPE_BUSINESS_NUMBER_EXACT = "business_number_exact"
MATCH_TYPE_ALIAS_EXACT = "alias_exact"
MATCH_TYPE_ALIAS_FUZZY = "alias_fuzzy"
MATCH_TYPE_MASTER_EXACT = "master_exact"
MATCH_TYPE_MASTER_FUZZY = "master_fuzzy"
MATCH_TYPE_ADDRESS_HINT = "address_hint"

DEFAULT_FUZZY_THRESHOLD = 72


@dataclass(frozen=True)
class MerchantCandidate:
    candidate_merchant_name: str
    candidate_business_number: str | None
    score: int
    match_type: str
    source: str
    review_required: bool = True
    address_summary: str | None = None


class MerchantCandidateMatcher:
    def __init__(
        self,
        repository: MerchantRepository,
        *,
        fuzzy_threshold: int = DEFAULT_FUZZY_THRESHOLD,
        max_candidates: int = 5,
    ) -> None:
        self.repository = repository
        self.fuzzy_threshold = fuzzy_threshold
        self.max_candidates = max_candidates

    def find_candidates(
        self,
        *,
        merchant_name: object = None,
        business_number: object = None,
        address_hint: object = None,
    ) -> list[MerchantCandidate]:
        normalized_business_number = normalize_business_number(business_number)
        if normalized_business_number:
            exact_rows = self.repository.find_by_business_number(normalized_business_number, limit=self.max_candidates)
            if exact_rows:
                return self._dedupe(
                    [
                        self._candidate_from_row(
                            row,
                            score=100,
                            match_type=MATCH_TYPE_BUSINESS_NUMBER_EXACT,
                        )
                        for row in exact_rows
                    ]
                )

        normalized_name = normalize_merchant_name(merchant_name)
        if not normalized_name:
            return self._address_only_candidates(address_hint)

        exact_name_rows = self.repository.find_by_normalized_name(normalized_name, limit=self.max_candidates)
        if exact_name_rows:
            normalized_address = normalize_road_address(address_hint_to_search_text(address_hint))
            return self._dedupe(
                [
                    self._candidate_from_row(
                        row,
                        score=(95 if row.match_source == "alias" else 90) + _address_bonus(normalized_address, row),
                        match_type=MATCH_TYPE_ALIAS_EXACT if row.match_source == "alias" else MATCH_TYPE_MASTER_EXACT,
                    )
                    for row in exact_name_rows
                ]
            )

        fuzzy_candidates: list[MerchantCandidate] = []
        normalized_address = normalize_road_address(address_hint_to_search_text(address_hint))
        for row in self.repository.list_name_candidates(normalized_name):
            score = _similarity_score(normalized_name, row.normalized_name)
            score += _address_bonus(normalized_address, row)
            if score < self.fuzzy_threshold:
                continue
            fuzzy_candidates.append(
                self._candidate_from_row(
                    row,
                    score=score + (1 if row.match_source == "alias" and score < 99 else 0),
                    match_type=MATCH_TYPE_ALIAS_FUZZY if row.match_source == "alias" else MATCH_TYPE_MASTER_FUZZY,
                )
            )
        fuzzy_candidates.sort(key=lambda candidate: (-candidate.score, _match_type_rank(candidate.match_type)))
        return self._dedupe(fuzzy_candidates)

    def _address_only_candidates(self, address_hint: object) -> list[MerchantCandidate]:
        address_parts = _address_hint_parts(address_hint)
        if not address_parts:
            return []
        rows = self.repository.list_master_address_candidates(
            road_name=address_parts.get("road_name"),
            building_main_number=address_parts.get("building_main_number"),
            building_sub_number=address_parts.get("building_sub_number"),
            normalized_road_address=normalize_road_address(address_parts.get("road_address_hint")),
            limit=self.max_candidates,
        )
        return self._dedupe(
            [
                self._candidate_from_row(
                    row,
                    score=68,
                    match_type=MATCH_TYPE_ADDRESS_HINT,
                )
                for row in rows
            ]
        )

    def _candidate_from_row(self, row: MerchantSearchRow, *, score: int, match_type: str) -> MerchantCandidate:
        return MerchantCandidate(
            candidate_merchant_name=row.merchant_name,
            candidate_business_number=row.business_number,
            score=min(100, max(0, int(score))),
            match_type=match_type,
            source=row.source,
            review_required=True,
            address_summary=row.address_summary,
        )

    def _dedupe(self, candidates: list[MerchantCandidate]) -> list[MerchantCandidate]:
        result: list[MerchantCandidate] = []
        seen: set[tuple[str, str | None]] = set()
        for candidate in candidates:
            key = (candidate.candidate_merchant_name, candidate.candidate_business_number)
            if key in seen:
                continue
            seen.add(key)
            result.append(candidate)
            if len(result) >= self.max_candidates:
                break
        return result


def _similarity_score(left: str, right: str) -> int:
    if not left or not right:
        return 0
    if left == right:
        return 100
    if left in right or right in left:
        shorter = min(len(left), len(right))
        longer = max(len(left), len(right))
        ratio_score = int(shorter / longer * 100)
        if shorter <= 3 and ratio_score < 60:
            return 70
        return max(80, ratio_score)
    return int(SequenceMatcher(None, left, right).ratio() * 100)


def _match_type_rank(match_type: str) -> int:
    if match_type.startswith("alias"):
        return 0
    return 1


def _address_bonus(normalized_address: str, row: MerchantSearchRow) -> int:
    if not normalized_address:
        return 0
    row_address = row.normalized_road_address or normalize_road_address(row.road_address)
    if row_address and (row_address in normalized_address or normalized_address in row_address):
        return 12
    row_road = normalize_road_address(row.road_name)
    if row_road and row_road in normalized_address:
        main_number = str(row.building_main_number or "").strip()
        sub_number = str(row.building_sub_number or "").strip()
        main_match = bool(main_number and main_number in normalized_address)
        sub_match = bool(sub_number and sub_number != "0" and sub_number in normalized_address)
        if main_match and (sub_match or not sub_number or sub_number == "0"):
            return 12
        if main_match:
            return 10
        return 6
    return 0


def _address_hint_parts(address_hint: object) -> dict[str, str | None]:
    if address_hint is None:
        return {}
    if isinstance(address_hint, dict):
        return {
            "road_address_hint": address_hint.get("road_address_hint") or address_hint.get("road_address"),
            "road_name": address_hint.get("road_name"),
            "building_main_number": address_hint.get("building_main_number"),
            "building_sub_number": address_hint.get("building_sub_number"),
        }
    parsed = extract_address_hint_from_safe_line(address_hint)
    if parsed is None:
        return {}
    return parsed.as_dict()

from __future__ import annotations

import sqlite3

from app.classifier.merchant_candidate import (
    MATCH_TYPE_ALIAS_EXACT,
    MATCH_TYPE_ADDRESS_HINT,
    MATCH_TYPE_BUSINESS_NUMBER_EXACT,
    MATCH_TYPE_MASTER_FUZZY,
    MerchantCandidateMatcher,
)
from app.db.merchant_repository import MerchantAliasInput, MerchantMasterInput, MerchantRepository


def test_business_number_exact_match_takes_priority_over_fuzzy_name(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="정확상호",
            business_number="1234567890",
            source="manual",
            source_row_hash="row-1",
            source_batch_id="batch-1",
        )
    )
    repository.add_master(
        MerchantMasterInput(
            merchant_name="비슷한상호",
            source="manual",
            source_row_hash="row-2",
            source_batch_id="batch-1",
        )
    )

    candidates = MerchantCandidateMatcher(repository).find_candidates(
        merchant_name="비슷한상호",
        business_number="123-45-67890",
    )

    assert candidates[0].candidate_merchant_name == "정확상호"
    assert candidates[0].candidate_business_number == "123-45-67890"
    assert candidates[0].score == 100
    assert candidates[0].match_type == MATCH_TYPE_BUSINESS_NUMBER_EXACT
    assert candidates[0].review_required is True


def test_without_business_number_returns_fuzzy_candidate_only(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="롯데 유스컬처빌 파주점",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
        )
    )

    candidates = MerchantCandidateMatcher(repository).find_candidates(
        merchant_name="롯데유스컬처빌파주",
        business_number=None,
    )

    assert candidates
    assert candidates[0].candidate_merchant_name == "롯데 유스컬처빌 파주점"
    assert candidates[0].candidate_business_number is None
    assert candidates[0].match_type == MATCH_TYPE_MASTER_FUZZY
    assert candidates[0].review_required is True


def test_alias_match_is_returned_before_master_fuzzy_candidate(tmp_path):
    db_path = tmp_path / "merchant.db"
    repository = MerchantRepository(db_path=db_path)
    repository.add_master(
        MerchantMasterInput(
            merchant_name="현대오일뱅크 프라자주유소",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
        )
    )
    master_id = _first_master_id(db_path)
    repository.add_alias(
        MerchantAliasInput(
            merchant_master_id=master_id,
            alias_name="프라자주유소",
            source="user_review",
        )
    )

    candidates = MerchantCandidateMatcher(repository).find_candidates(merchant_name="프라자 주유소")

    assert candidates[0].candidate_merchant_name == "현대오일뱅크 프라자주유소"
    assert candidates[0].match_type == MATCH_TYPE_ALIAS_EXACT
    assert candidates[0].source == "user_review"


def test_fuzzy_name_with_address_hint_boosts_matching_score(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="크린에이드 이대역서희스타힐스점",
            source="public_store_data",
            source_row_hash="row-1",
            source_batch_id="batch-1",
            road_name="이화여대길",
            building_main_number="52",
            building_sub_number="31",
            road_address="서울특별시 서대문구 이화여대길 52-31",
        )
    )

    matcher = MerchantCandidateMatcher(repository)
    without_address = matcher.find_candidates(merchant_name="크린에이드")
    with_address = matcher.find_candidates(
        merchant_name="크린에이드",
        address_hint="서울특별시 서대문구 이화여대길 52-31",
    )

    assert with_address[0].score > without_address[0].score
    assert with_address[0].address_summary == "이화여대길 52-31"
    assert with_address[0].review_required is True


def test_fuzzy_name_with_structured_address_hint_boosts_without_auto_confirm(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="강남테스트상점",
            source="public_store_data",
            source_row_hash="row-structured-address",
            source_batch_id="batch-1",
            road_name="강남대로",
            building_main_number="123",
            road_address="서울특별시 강남구 강남대로 123",
        )
    )

    matcher = MerchantCandidateMatcher(repository)
    without_address = matcher.find_candidates(merchant_name="강남테스트")
    with_address = matcher.find_candidates(
        merchant_name="강남테스트",
        address_hint={
            "road_address_hint": "서울특별시 강남구 강남대로 123",
            "road_name": "강남대로",
            "building_main_number": "123",
            "building_sub_number": None,
        },
    )

    assert with_address[0].score > without_address[0].score
    assert with_address[0].review_required is True
    assert with_address[0].match_type == MATCH_TYPE_MASTER_FUZZY


def test_address_hint_only_returns_review_candidate_without_auto_confirm(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="Address Matched Store",
            source="public_store_data",
            source_row_hash="row-address-only",
            source_batch_id="batch-1",
            road_name="Jongno",
            building_main_number="19",
            road_address="Seoul Jongno 19",
        )
    )

    candidates = MerchantCandidateMatcher(repository).find_candidates(
        merchant_name=None,
        business_number=None,
        address_hint={
            "road_address_hint": "Seoul Jongno 19",
            "road_name": "Jongno",
            "building_main_number": "19",
            "building_sub_number": None,
        },
    )

    assert candidates
    assert candidates[0].candidate_merchant_name == "Address Matched Store"
    assert candidates[0].match_type == MATCH_TYPE_ADDRESS_HINT
    assert candidates[0].score < 72
    assert candidates[0].review_required is True


def test_short_containment_candidate_needs_address_support(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="데일리",
            source="public_store_data",
            source_row_hash="row-short-name",
            source_batch_id="batch-1",
        )
    )

    candidates = MerchantCandidateMatcher(repository).find_candidates(merchant_name="데일리픽스 을지로")

    assert candidates == []


def test_short_containment_candidate_survives_with_address_support(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="모쿠",
            source="public_store_data",
            source_row_hash="row-short-address",
            source_batch_id="batch-1",
            road_name="서울특별시 강남구 봉은사로44길",
            building_main_number="70",
            road_address="서울특별시 강남구 봉은사로44길 70",
        )
    )

    candidates = MerchantCandidateMatcher(repository).find_candidates(
        merchant_name="모쿠카츠",
        address_hint={
            "road_address_hint": "서울특별시 강남구 봉은사로44길 70",
            "road_name": "봉은사로44길",
            "building_main_number": "70",
            "building_sub_number": None,
        },
    )

    assert candidates
    assert candidates[0].candidate_merchant_name == "모쿠"
    assert candidates[0].score >= 72
    assert candidates[0].review_required is True


def test_repository_search_masters_requires_filter_and_uses_safe_limited_results(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    repository.add_master(
        MerchantMasterInput(
            merchant_name="총각김밥",
            source="public_store_data",
            source_row_hash="row-search-1",
            source_batch_id="batch-1",
            road_name="서울특별시 종로구 종로",
            building_main_number="19",
            road_address="서울특별시 종로구 종로 19",
        )
    )
    repository.add_master(
        MerchantMasterInput(
            merchant_name="다른가게",
            source="public_store_data",
            source_row_hash="row-search-2",
            source_batch_id="batch-1",
            road_name="종로",
            building_main_number="20",
            road_address="서울특별시 종로구 종로 20",
        )
    )

    assert repository.search_masters() == []

    by_name = repository.search_masters(merchant_name="총각", limit=10)
    by_address = repository.search_masters(road_name="종로", building_main_number="19", limit=10)

    assert [row.merchant_name for row in by_name] == ["총각김밥"]
    assert [row.merchant_name for row in by_address] == ["총각김밥"]
    assert by_address[0].address_summary == "서울특별시 종로구 종로 19"


def test_repository_search_masters_applies_limit_branch_and_category_filters(tmp_path):
    repository = MerchantRepository(db_path=tmp_path / "merchant.db")
    for index in range(3):
        repository.add_master(
            MerchantMasterInput(
                merchant_name=f"Test Store {index}",
                branch_name="Main Branch" if index < 2 else "Other Branch",
                category_large="Food" if index < 2 else "Retail",
                source="public_store_data",
                source_row_hash=f"row-filter-{index}",
                source_batch_id="batch-filter",
                road_name="Main Road",
                building_main_number=str(10 + index),
                road_address=f"Seoul Main Road {10 + index}",
            )
        )

    limited = repository.search_masters(merchant_name="Test", limit=2)
    filtered = repository.search_masters(merchant_name="Test", branch_name="Main", category="Food", limit=10)

    assert len(limited) == 2
    assert len(filtered) == 2
    assert {row.branch_name for row in filtered} == {"Main Branch"}
    assert {row.category_large for row in filtered} == {"Food"}
    assert {row.source_batch_id for row in filtered} == {"batch-filter"}


def _first_master_id(db_path) -> str:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT id FROM merchant_master LIMIT 1").fetchone()
    return str(row[0])

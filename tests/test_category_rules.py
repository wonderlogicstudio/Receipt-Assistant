from pathlib import Path

from app.classifier.category_rules import CategoryRules


def test_category_rules_recommends_for_starbucks():
    assert CategoryRules().recommend("스타벅스 강남점") == "복리후생비"


def test_category_rules_recommends_for_kakao_taxi():
    assert CategoryRules().recommend("카카오택시") == "여비교통비"


def test_category_rules_recommends_for_kyobo_bookstore():
    assert CategoryRules().recommend("교보문고 광화문점") == "도서인쇄비"


def test_category_rules_uses_uncategorized_for_unknown_merchant():
    assert CategoryRules().recommend("알수없는상점") == "미분류"


def test_category_recommendation_includes_short_reason():
    recommendation = CategoryRules().recommend_with_reason("다이소 사무용품")

    assert recommendation.category == "사무용품비"
    assert recommendation.reason == "merchant_keyword: 다이소"


def test_app_and_test_code_do_not_include_blocked_phrases():
    blocked_phrases = [
        "\ubd80\uac00\uc138 " + "\uacf5\uc81c \uac00\ub2a5",
        "\uc808\uc138 " + "\ucd94\ucc9c",
        "\ube44\uc6a9 \uc778\uc815 \uc5ec\ubd80 " + "\ud310\ub2e8",
    ]
    paths = [*Path("app").rglob("*.py"), *Path("tests").rglob("*.py")]
    contents = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    for phrase in blocked_phrases:
        assert phrase not in contents

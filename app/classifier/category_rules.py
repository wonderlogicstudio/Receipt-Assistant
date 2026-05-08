from __future__ import annotations

from dataclasses import dataclass
import re

from app.classifier.merchant_dictionary import MERCHANT_CATEGORY_RULES, UNCATEGORIZED


@dataclass(frozen=True)
class CategoryRecommendation:
    category: str
    reason: str | None


class CategoryRules:
    def __init__(self, rules: list[dict[str, object]] | None = None) -> None:
        self.rules = rules or MERCHANT_CATEGORY_RULES

    def recommend(self, merchant_name: str | None, raw_text: str | None = None) -> str:
        return self.recommend_with_reason(merchant_name, raw_text).category

    def recommend_with_reason(self, merchant_name: str | None, raw_text: str | None = None) -> CategoryRecommendation:
        haystack = self._normalize(" ".join(value for value in [merchant_name, raw_text] if value))
        if not haystack:
            return CategoryRecommendation(UNCATEGORIZED, None)

        for rule in self.rules:
            category = str(rule["category"])
            for keyword in rule["keywords"]:
                normalized_keyword = self._normalize(str(keyword))
                if normalized_keyword and normalized_keyword in haystack:
                    return CategoryRecommendation(category, f"merchant_keyword: {keyword}")

        return CategoryRecommendation(UNCATEGORIZED, None)

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", "", value).lower()

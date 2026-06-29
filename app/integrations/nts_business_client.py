from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from app.classifier.merchant_normalizer import business_number_digits, normalize_business_number


DEFAULT_NTS_BUSINESS_STATUS_API_URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"


@dataclass(frozen=True)
class BusinessStatusResult:
    business_number: str | None
    status: str
    status_category: str | None = None
    tax_type_category: str | None = None
    closed_date: str | None = None
    diagnostic_code: str | None = None


class NTSBusinessStatusClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        api_url: str = DEFAULT_NTS_BUSINESS_STATUS_API_URL,
        timeout_seconds: int = 10,
        session: Any | None = None,
    ) -> None:
        self.api_key = api_key.strip() if api_key else None
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def check_status(self, business_number: object) -> BusinessStatusResult:
        normalized = normalize_business_number(business_number)
        digits = business_number_digits(business_number)
        if not normalized or not digits:
            return BusinessStatusResult(
                business_number=None,
                status="failed",
                diagnostic_code="invalid_business_number",
            )
        if not self.api_key:
            return BusinessStatusResult(
                business_number=normalized,
                status="skipped",
                diagnostic_code="nts_api_key_missing",
            )
        try:
            response = self.session.post(
                self.api_url,
                params={"serviceKey": self.api_key},
                json={"b_no": [digits]},
                timeout=self.timeout_seconds,
            )
        except requests.RequestException:
            return BusinessStatusResult(
                business_number=normalized,
                status="failed",
                diagnostic_code="nts_request_failed",
            )
        if getattr(response, "status_code", 0) >= 400:
            return BusinessStatusResult(
                business_number=normalized,
                status="failed",
                diagnostic_code="nts_http_error",
            )
        try:
            payload = response.json()
        except ValueError:
            return BusinessStatusResult(
                business_number=normalized,
                status="failed",
                diagnostic_code="nts_invalid_response",
            )
        return _result_from_payload(payload, normalized)


def _result_from_payload(payload: dict[str, Any], business_number: str) -> BusinessStatusResult:
    data = payload.get("data")
    first_item = data[0] if isinstance(data, list) and data else {}
    if not isinstance(first_item, dict):
        return BusinessStatusResult(
            business_number=business_number,
            status="failed",
            diagnostic_code="nts_empty_response",
        )
    return BusinessStatusResult(
        business_number=business_number,
        status="checked",
        status_category=_safe_category(first_item.get("b_stt") or first_item.get("b_stt_cd")),
        tax_type_category=_safe_category(first_item.get("tax_type") or first_item.get("tax_type_cd")),
        closed_date=_safe_date(first_item.get("end_dt")),
        diagnostic_code=_safe_category(first_item.get("b_no_match_msg")),
    )


def _safe_category(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:80]


def _safe_date(value: object) -> str | None:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(text) != 8:
        return None
    return f"{text[:4]}-{text[4:6]}-{text[6:]}"

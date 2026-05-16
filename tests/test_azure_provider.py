from __future__ import annotations

from pathlib import Path

import pytest
import requests

from app.core.config import AppConfig
from app.core.enums import OCRStatus
from app.ocr.azure_provider import AzureDocumentIntelligenceProvider
from app.parser.receipt_parser import ReceiptParser


class FakeResponse:
    def __init__(self, *, status_code=200, headers=None, payload=None, json_error: Exception | None = None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload or {}
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload


class FakeSession:
    def __init__(
        self,
        *,
        post_response=None,
        post_responses=None,
        get_responses=None,
        post_exception: Exception | None = None,
    ):
        self.post_responses = list(post_responses or [])
        self.post_response = post_response or FakeResponse()
        self.get_responses = list(get_responses or [])
        self.post_exception = post_exception
        self.post_calls = []
        self.get_calls = []

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        if self.post_exception:
            raise self.post_exception
        if self.post_responses:
            return self.post_responses.pop(0)
        return self.post_response

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        if not self.get_responses:
            return FakeResponse(payload={"status": "succeeded", "analyzeResult": {"documents": []}})
        response = self.get_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_config() -> AppConfig:
    return AppConfig(
        ocr_provider="azure",
        azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com/",
        azure_document_intelligence_key="not-a-real-credential",
        ocr_request_timeout_seconds=5,
    )


def make_provider(
    session: FakeSession,
    *,
    sleep_calls: list[float] | None = None,
    poll_interval_seconds: float = 1,
    max_poll_attempts: int = 2,
    max_retries: int = 3,
) -> AzureDocumentIntelligenceProvider:
    return AzureDocumentIntelligenceProvider(
        make_config(),
        session=session,
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
        max_retries=max_retries,
        sleep_func=(sleep_calls.append if sleep_calls is not None else (lambda seconds: None)),
    )


def make_sample_file(tmp_path: Path, name: str = "receipt.jpg") -> Path:
    path = tmp_path / name
    path.write_bytes(b"sample")
    return path


def test_azure_provider_can_ignore_environment_proxy_settings() -> None:
    session = requests.Session()
    config = AppConfig(
        ocr_provider="azure",
        azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com/",
        azure_document_intelligence_key="not-a-real-credential",
        azure_ocr_ignore_env_proxy=True,
    )

    provider = AzureDocumentIntelligenceProvider(config, session=session)

    assert provider.session.trust_env is False


def success_payload():
    return {
        "status": "succeeded",
        "analyzeResult": {
            "documents": [
                {
                    "fields": {
                        "MerchantName": {"valueString": "테스트카페", "confidence": 0.95},
                        "TransactionDate": {"valueDate": "2026-05-08", "confidence": 0.93},
                        "Total": {"valueCurrency": {"amount": 12000, "currencyCode": "KRW"}, "confidence": 0.94},
                        "TotalTax": {"valueCurrency": {"amount": 1091, "currencyCode": "KRW"}, "confidence": 0.91},
                        "PaymentMethod": {"content": "신용카드", "confidence": 0.8},
                    }
                }
            ]
        },
    }


def test_azure_provider_success_returns_completed_result(tmp_path):
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[FakeResponse(payload=success_payload())],
    )
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.COMPLETED.value
    assert result.provider == "azure"
    assert result.raw_json["merchant_name"] == "테스트카페"
    assert result.raw_json["total_amount"] == 12000
    assert 0 <= result.confidence <= 1
    assert session.post_calls
    assert session.get_calls


def test_azure_provider_keeps_safe_amount_context_lines_for_parser_without_sensitive_values(tmp_path):
    payload = success_payload()
    payload["analyzeResult"]["pages"] = [
        {
            "lines": [
                {"content": "WIFI PW: sample-password-1234"},
                {"content": "사업자번호 123-45-67890"},
                {"content": "TEL 02-1234-5678"},
                {"content": "총매출액"},
                {"content": "할인금액"},
                {"content": "합계금액"},
                {"content": "받은금액"},
                {"content": "10,800"},
                {"content": "10,800"},
                {"content": "0"},
                {"content": "0"},
            ]
        }
    ]
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[FakeResponse(payload=payload)],
    )
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.raw_json["amount_context_lines"] == [
        "사업자번호 123-45-67890",
        "TEL [REDACTED]",
        "총매출액",
        "할인금액",
        "합계금액",
        "받은금액",
        "10,800",
        "10,800",
        "0",
        "0",
    ]
    assert "할인금액" in result.raw_text
    assert "사업자번호 123-45-67890" in result.raw_text
    assert "sample-password-1234" not in result.raw_text
    assert "02-1234-5678" not in result.raw_text
    assert "sample-password-1234" not in str(result.raw_json)

    receipt = ReceiptParser().parse(result)
    assert receipt.business_number == "123-45-67890"
    assert receipt.gross_amount == 10800
    assert receipt.discount_amount == 10800
    assert receipt.final_amount == 0
    assert receipt.paid_amount == 0
    assert receipt.total_amount == 0


def test_azure_provider_keeps_card_payment_context_line_for_parser(tmp_path):
    payload = success_payload()
    payload["analyzeResult"]["pages"] = [
        {
            "lines": [
                {"content": "결제대상금액 105,720"},
                {"content": "카드결제(IC) 일시불 / 105,720"},
                {"content": "※ 해당카드 결제금액 기준"},
                {"content": "캐셔:063453 김00"},
                {"content": "1520"},
            ]
        }
    ]
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[FakeResponse(payload=payload)],
    )
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert "카드결제(IC) 일시불 / 105,720" in result.raw_json["amount_context_lines"]
    assert "카드결제(IC) 일시불 / 105,720" in result.raw_text

    receipt = ReceiptParser().parse(result)
    assert receipt.final_amount == 105720
    assert receipt.paid_amount == 105720
    assert receipt.total_amount == 105720
    assert receipt.amount_source == "paid_amount"


def test_azure_provider_http_failure_returns_failed_result(tmp_path):
    session = FakeSession(post_response=FakeResponse(status_code=500))
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.error_message == "OCR 요청에 실패했습니다."
    assert result.diagnostic_code == "analyze_http_500"


def test_azure_provider_timeout_returns_failed_result(tmp_path):
    session = FakeSession(post_exception=requests.Timeout("timeout"))
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.error_message == "OCR 요청 시간이 초과되었습니다."


def test_azure_provider_json_error_returns_failed_result(tmp_path):
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[FakeResponse(json_error=ValueError("bad json"))],
    )
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.error_message == "OCR 응답을 해석할 수 없습니다."


@pytest.mark.parametrize("file_name", ["statement.xlsx", "statement.csv"])
def test_azure_provider_skips_card_statement_files(tmp_path, file_name):
    provider = make_provider(FakeSession())

    result = provider.extract(make_sample_file(tmp_path, file_name))

    assert result.status == OCRStatus.SKIPPED.value


def test_azure_provider_missing_file_returns_failed_result(tmp_path):
    provider = make_provider(FakeSession())
    missing_path = tmp_path / "missing.jpg"

    result = provider.extract(missing_path)

    assert result.status == OCRStatus.FAILED.value
    assert result.error_message == "OCR 대상 파일에 접근할 수 없습니다."


def test_azure_provider_does_not_expose_key_endpoint_or_full_path(tmp_path):
    session = FakeSession(post_response=FakeResponse(status_code=500))
    provider = make_provider(session)
    path = make_sample_file(tmp_path)

    result = provider.extract(path)
    serialized = f"{result.source_file_name} {result.stored_relative_path} {result.error_message} {result.raw_text} {result.raw_json}"

    assert "not-a-real-credential" not in serialized
    assert "cognitiveservices.azure.com" not in serialized
    assert str(tmp_path) not in serialized
    assert result.source_file_name == "receipt.jpg"


def test_azure_provider_proxy_error_returns_diagnostic_code(tmp_path):
    session = FakeSession(post_exception=requests.exceptions.ProxyError("proxy"))
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.error_message == "OCR 요청에 실패했습니다."
    assert result.diagnostic_code == "proxy_error"


def test_azure_provider_operation_failed_returns_diagnostic_code(tmp_path):
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[FakeResponse(payload={"status": "failed"})],
    )
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.diagnostic_code == "operation_failed"


def test_azure_provider_respects_retry_after_for_running_poll(tmp_path):
    sleep_calls: list[float] = []
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[
            FakeResponse(headers={"Retry-After": "4"}, payload={"status": "running"}),
            FakeResponse(headers={"Retry-After": "3"}, payload={"status": "running"}),
            FakeResponse(headers={"Retry-After": "2"}, payload={"status": "running"}),
            FakeResponse(payload=success_payload()),
        ],
    )
    provider = make_provider(session, sleep_calls=sleep_calls, max_poll_attempts=5)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.COMPLETED.value
    assert sleep_calls == [4.0, 3.0, 2.0]


def test_azure_provider_uses_default_poll_interval_when_retry_after_missing(tmp_path):
    sleep_calls: list[float] = []
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[
            FakeResponse(payload={"status": "running"}),
            FakeResponse(payload=success_payload()),
        ],
    )
    provider = make_provider(session, sleep_calls=sleep_calls, poll_interval_seconds=2, max_poll_attempts=3)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.COMPLETED.value
    assert sleep_calls == [2.0]


def test_azure_provider_uses_default_poll_interval_for_invalid_retry_after(tmp_path):
    sleep_calls: list[float] = []
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[
            FakeResponse(headers={"Retry-After": "later"}, payload={"status": "running"}),
            FakeResponse(payload=success_payload()),
        ],
    )
    provider = make_provider(session, sleep_calls=sleep_calls, poll_interval_seconds=2, max_poll_attempts=3)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.COMPLETED.value
    assert sleep_calls == [2.0]


def test_azure_provider_retries_analyze_429_then_completes(tmp_path):
    sleep_calls: list[float] = []
    session = FakeSession(
        post_responses=[
            FakeResponse(status_code=429, headers={"Retry-After": "2"}),
            FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        ],
        get_responses=[FakeResponse(payload=success_payload())],
    )
    provider = make_provider(session, sleep_calls=sleep_calls)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.COMPLETED.value
    assert len(session.post_calls) == 2
    assert sleep_calls == [2.0]


def test_azure_provider_retries_poll_429_then_completes(tmp_path):
    sleep_calls: list[float] = []
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[
            FakeResponse(status_code=429, headers={"Retry-After": "3"}),
            FakeResponse(payload=success_payload()),
        ],
    )
    provider = make_provider(session, sleep_calls=sleep_calls)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.COMPLETED.value
    assert len(session.get_calls) == 2
    assert sleep_calls == [3.0]


def test_azure_provider_repeated_analyze_500_returns_status_code_reason(tmp_path):
    sleep_calls: list[float] = []
    session = FakeSession(post_response=FakeResponse(status_code=500))
    provider = make_provider(session, sleep_calls=sleep_calls, max_retries=2)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.diagnostic_code == "analyze_http_500"
    assert len(session.post_calls) == 3


def test_azure_provider_repeated_poll_503_returns_status_code_reason(tmp_path):
    sleep_calls: list[float] = []
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[
            FakeResponse(status_code=503),
            FakeResponse(status_code=503),
            FakeResponse(status_code=503),
        ],
    )
    provider = make_provider(session, sleep_calls=sleep_calls, max_retries=2)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.diagnostic_code == "poll_http_503"
    assert len(session.get_calls) == 3


@pytest.mark.parametrize("status_code", [401, 403])
def test_azure_provider_auth_errors_are_not_retried(tmp_path, status_code):
    session = FakeSession(post_response=FakeResponse(status_code=status_code))
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.diagnostic_code == f"analyze_http_{status_code}"
    assert len(session.post_calls) == 1


def test_azure_provider_reports_safe_quota_detail_for_403(tmp_path):
    session = FakeSession(
        post_response=FakeResponse(
            status_code=403,
            payload={"error": {"code": "403", "message": "Quota limit exceeded."}},
        )
    )
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.diagnostic_code == "analyze_http_403"
    assert result.diagnostic_detail_code == "quota_or_rate_limit"
    serialized = f"{result.error_message} {result.diagnostic_code} {result.diagnostic_detail_code}"
    assert "Quota limit exceeded" not in serialized


def test_azure_provider_poll_attempt_limit_returns_failed_result(tmp_path):
    sleep_calls: list[float] = []
    session = FakeSession(
        post_response=FakeResponse(status_code=202, headers={"Operation-Location": "https://poll.example/result"}),
        get_responses=[
            FakeResponse(payload={"status": "running"}),
            FakeResponse(payload={"status": "running"}),
        ],
    )
    provider = make_provider(session, sleep_calls=sleep_calls, max_poll_attempts=2)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.diagnostic_code == "timeout"
    assert len(session.get_calls) == 2
    assert sleep_calls == [1.0]

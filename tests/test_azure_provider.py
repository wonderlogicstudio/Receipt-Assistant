from __future__ import annotations

from pathlib import Path

import pytest
import requests

from app.core.config import AppConfig
from app.core.enums import OCRStatus
from app.ocr.azure_provider import AzureDocumentIntelligenceProvider


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
    def __init__(self, *, post_response=None, get_responses=None, post_exception: Exception | None = None):
        self.post_response = post_response or FakeResponse()
        self.get_responses = list(get_responses or [])
        self.post_exception = post_exception
        self.post_calls = []
        self.get_calls = []

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        if self.post_exception:
            raise self.post_exception
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


def make_provider(session: FakeSession) -> AzureDocumentIntelligenceProvider:
    return AzureDocumentIntelligenceProvider(
        make_config(),
        session=session,
        poll_interval_seconds=0,
        max_poll_attempts=2,
    )


def make_sample_file(tmp_path: Path, name: str = "receipt.jpg") -> Path:
    path = tmp_path / name
    path.write_bytes(b"sample")
    return path


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


def test_azure_provider_http_failure_returns_failed_result(tmp_path):
    session = FakeSession(post_response=FakeResponse(status_code=500))
    provider = make_provider(session)

    result = provider.extract(make_sample_file(tmp_path))

    assert result.status == OCRStatus.FAILED.value
    assert result.error_message == "OCR 요청에 실패했습니다."


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

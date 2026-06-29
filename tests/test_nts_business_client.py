from __future__ import annotations

from app.integrations.nts_business_client import NTSBusinessStatusClient


class FakeResponse:
    def __init__(self, payload, *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def test_nts_client_returns_safe_skipped_result_without_api_key():
    result = NTSBusinessStatusClient(api_key=None).check_status("123-45-67890")

    assert result.business_number == "123-45-67890"
    assert result.status == "skipped"
    assert result.diagnostic_code == "nts_api_key_missing"


def test_nts_client_rejects_invalid_business_number_without_request():
    result = NTSBusinessStatusClient(api_key="secret").check_status("123")

    assert result.business_number is None
    assert result.status == "failed"
    assert result.diagnostic_code == "invalid_business_number"


def test_nts_client_maps_only_safe_summary_fields():
    session = FakeSession(
        FakeResponse(
            {
                "request_cnt": 1,
                "data": [
                    {
                        "b_no": "1234567890",
                        "b_stt": "계속사업자",
                        "tax_type": "부가가치세 일반과세자",
                        "end_dt": "20260531",
                        "raw_private_field": "do-not-store",
                    }
                ],
                "trace_id": "trace-secret",
            }
        )
    )
    client = NTSBusinessStatusClient(api_key="secret-key", session=session)

    result = client.check_status("123-45-67890")

    assert result.business_number == "123-45-67890"
    assert result.status == "checked"
    assert result.status_category == "계속사업자"
    assert result.tax_type_category == "부가가치세 일반과세자"
    assert result.closed_date == "2026-05-31"
    serialized = str(result)
    assert "secret-key" not in serialized
    assert "trace-secret" not in serialized
    assert "do-not-store" not in serialized
    assert session.calls[0][1]["json"] == {"b_no": ["1234567890"]}

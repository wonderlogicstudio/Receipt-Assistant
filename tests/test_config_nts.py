from __future__ import annotations

from app.core.config import DEFAULT_NTS_BUSINESS_STATUS_API_URL, get_config


def test_get_config_reads_nts_business_api_key_from_env(monkeypatch):
    monkeypatch.setenv("NTS_BUSINESS_API_KEY", "secret-key")
    monkeypatch.setenv("NTS_BUSINESS_STATUS_API_URL", "https://example.test/status")

    config = get_config()

    assert config.nts_business_api_key == "secret-key"
    assert config.nts_business_status_api_url == "https://example.test/status"


def test_get_config_uses_default_nts_business_status_url(monkeypatch):
    monkeypatch.setenv("NTS_BUSINESS_STATUS_API_URL", "")

    config = get_config()

    assert config.nts_business_status_api_url == DEFAULT_NTS_BUSINESS_STATUS_API_URL

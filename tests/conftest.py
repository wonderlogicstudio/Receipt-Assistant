from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def default_to_mock_ocr_provider(monkeypatch):
    if os.getenv("RUN_LIVE_OCR_TESTS") != "true":
        monkeypatch.setenv("OCR_PROVIDER", "mock")

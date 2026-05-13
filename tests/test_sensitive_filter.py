from __future__ import annotations

from app.security.sensitive_filter import (
    detect_sensitive_text,
    sanitize_lines_for_parsing,
    sanitize_text_for_display,
    sanitize_text_for_storage,
)


def test_wifi_password_is_detected_and_redacted():
    text = "WIFI ID: TEST_STORE\nWIFI PW: sample-password-1234"

    detection = detect_sensitive_text(text)
    sanitized = sanitize_text_for_display(text)

    assert detection.detected is True
    assert "wifi_password" in detection.categories
    assert "sample-password-1234" not in sanitized


def test_password_label_is_detected_and_redacted():
    text = "password: abc12345"

    detection = detect_sensitive_text(text)
    sanitized = sanitize_text_for_storage(text)

    assert "password" in detection.categories
    assert "abc12345" not in sanitized


def test_full_card_number_is_detected_and_redacted():
    text = "카드번호 1234-5678-9012-3456"

    detection = detect_sensitive_text(text)
    sanitized = sanitize_text_for_display(text)

    assert "card_number" in detection.categories
    assert "1234-5678-9012-3456" not in sanitized


def test_masked_card_number_is_allowed_without_full_card_category():
    text = "카드번호 1234-****-****-5678"

    detection = detect_sensitive_text(text)
    sanitized = sanitize_text_for_display(text)

    assert "card_number" not in detection.categories
    assert "1234-****-****-5678" in sanitized


def test_resident_number_email_and_phone_are_redacted():
    text = "900101-1234567 test@example.com 010-1234-5678"

    detection = detect_sensitive_text(text)
    sanitized = sanitize_text_for_storage(text)

    assert {"resident_number", "email", "phone_number"}.issubset(set(detection.categories))
    assert "900101-1234567" not in sanitized
    assert "test@example.com" not in sanitized
    assert "010-1234-5678" not in sanitized


def test_business_number_is_not_removed_as_sensitive_text():
    text = "사업자번호: 123-45-67890"

    detection = detect_sensitive_text(text)
    sanitized = sanitize_lines_for_parsing(text)

    assert detection.detected is False
    assert "123-45-67890" in sanitized


def test_sensitive_credential_lines_are_removed_from_parsing_text():
    text = "\n".join(["테스트카페", "WIFI PW: sample-password-1234", "합계: 5,100원"])

    sanitized = sanitize_lines_for_parsing(text)

    assert "테스트카페" in sanitized
    assert "합계: 5,100원" in sanitized
    assert "sample-password-1234" not in sanitized

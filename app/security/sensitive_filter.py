from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable


MASK = "[REDACTED]"


@dataclass(frozen=True)
class SensitiveTextDetection:
    detected: bool
    categories: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SensitiveTextFilter:
    wifi_line_pattern = re.compile(
        r"\b(?:wi[-\s]?fi|wifi|ssid)\b|와이파이|무선랜",
        re.IGNORECASE,
    )
    password_line_pattern = re.compile(
        r"\b(?:password|passwd|pwd|pw|pass)\b|비밀번호|패스워드|암호",
        re.IGNORECASE,
    )
    security_token_line_pattern = re.compile(
        r"\b(?:token|secret|api\s*key|access\s*key)\b|인증키",
        re.IGNORECASE,
    )
    resident_number_pattern = re.compile(r"\b\d{6}-\d{7}\b")
    masked_card_pattern = re.compile(r"\b\d{4}[-\s][*xX]{4}[-\s][*xX]{4}[-\s]\d{4}\b")
    grouped_card_pattern = re.compile(r"\b(?:\d{4}[-\s]){3}\d{4}\b")
    continuous_card_pattern = re.compile(r"\b\d{13,19}\b")
    email_pattern = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    phone_pattern = re.compile(
        r"\b(?:01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}|0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})\b"
    )

    warning_by_category = {
        "wifi_id": "sensitive_text_redacted",
        "wifi_password": "wifi_password_detected",
        "password": "password_detected",
        "card_number": "full_card_number_masked",
        "resident_number": "resident_number_masked",
        "email": "email_masked",
        "phone_number": "phone_number_masked",
        "security_token": "security_token_detected",
    }

    def detect_sensitive_text(self, value: object) -> SensitiveTextDetection:
        text = _text(value)
        categories: list[str] = []
        for line in text.splitlines() or [text]:
            categories.extend(self._line_categories(line))
        categories = _unique(categories)
        warnings = _unique([self.warning_by_category[category] for category in categories if category in self.warning_by_category])
        return SensitiveTextDetection(detected=bool(categories), categories=categories, warnings=warnings)

    def redact_sensitive_text(self, value: object) -> str:
        text = _text(value)
        if not text:
            return ""
        redacted_lines = []
        for line in text.splitlines():
            if self._is_credential_line(line):
                redacted_lines.append(MASK)
            else:
                redacted_lines.append(self._redact_inline(line))
        if redacted_lines:
            return "\n".join(redacted_lines)
        return self._redact_inline(text)

    def sanitize_text_for_display(self, value: object) -> str:
        return self.redact_sensitive_text(value)

    def sanitize_text_for_storage(self, value: object) -> str:
        return self.redact_sensitive_text(value)

    def sanitize_lines_for_parsing(self, value: object) -> str:
        text = _text(value)
        safe_lines = []
        for line in text.splitlines():
            if self._is_credential_line(line):
                continue
            safe_lines.append(self._redact_inline(line))
        return "\n".join(safe_lines)

    def summarize_sensitive_categories(self, value: object) -> list[str]:
        if isinstance(value, SensitiveTextDetection):
            return list(value.categories)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
            return _unique([str(item) for item in value if item])
        return self.detect_sensitive_text(value).categories

    def _line_categories(self, line: str) -> list[str]:
        categories: list[str] = []
        has_wifi = bool(self.wifi_line_pattern.search(line))
        has_password = bool(self.password_line_pattern.search(line))
        if has_wifi and has_password:
            categories.append("wifi_password")
        elif has_wifi:
            categories.append("wifi_id")
        elif has_password:
            categories.append("password")
        if self.security_token_line_pattern.search(line):
            categories.append("security_token")
        if self.resident_number_pattern.search(line):
            categories.append("resident_number")
        if self._has_unmasked_card_number(line):
            categories.append("card_number")
        if self.email_pattern.search(line):
            categories.append("email")
        if self.phone_pattern.search(line):
            categories.append("phone_number")
        return categories

    def _is_credential_line(self, line: str) -> bool:
        categories = set(self._line_categories(line))
        return bool(categories.intersection({"wifi_id", "wifi_password", "password", "security_token"}))

    def _redact_inline(self, text: str) -> str:
        result = self.resident_number_pattern.sub(MASK, text)
        result = self.email_pattern.sub(MASK, result)
        result = self.phone_pattern.sub(MASK, result)
        result = self.grouped_card_pattern.sub(lambda match: match.group(0) if self.masked_card_pattern.fullmatch(match.group(0)) else MASK, result)
        result = self.continuous_card_pattern.sub(MASK, result)
        return result

    def _has_unmasked_card_number(self, line: str) -> bool:
        for match in self.grouped_card_pattern.finditer(line):
            if not self.masked_card_pattern.fullmatch(match.group(0)):
                return True
        return bool(self.continuous_card_pattern.search(line))


_DEFAULT_FILTER = SensitiveTextFilter()


def detect_sensitive_text(value: object) -> SensitiveTextDetection:
    return _DEFAULT_FILTER.detect_sensitive_text(value)


def redact_sensitive_text(value: object) -> str:
    return _DEFAULT_FILTER.redact_sensitive_text(value)


def sanitize_text_for_display(value: object) -> str:
    return _DEFAULT_FILTER.sanitize_text_for_display(value)


def sanitize_text_for_storage(value: object) -> str:
    return _DEFAULT_FILTER.sanitize_text_for_storage(value)


def sanitize_lines_for_parsing(value: object) -> str:
    return _DEFAULT_FILTER.sanitize_lines_for_parsing(value)


def summarize_sensitive_categories(value: object) -> list[str]:
    return _DEFAULT_FILTER.summarize_sensitive_categories(value)


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

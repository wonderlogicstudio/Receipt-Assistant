from __future__ import annotations

import time
import re
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

import requests

from app.core.config import AppConfig, get_config
from app.core.enums import OCRProviderName, OCRStatus
from app.core.exceptions import ConfigurationError
from app.core.ocr_models import OCRResult
from app.ocr.base import OCRInput, OCRProvider
from app.security.sensitive_filter import sanitize_lines_for_parsing
from app.storage.file_store import StoredFileMetadata


RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
MIN_POLL_INTERVAL_SECONDS = 1.0
_HTTP_DIAGNOSTIC_PATTERN = re.compile(r"(?P<stage>analyze|poll)_http_(?P<status>\d{3})")
_AMOUNT_CONTEXT_PATTERN = re.compile(
    r"[\-－−–—]?\s*(?:(?:[0-9OoIl|BSㅇ]{1,3}(?:(?:\s*[,\.]\s*|\s+)[0-9OoIl|BSㅇ]{3})+)|[0-9OoIl|BSㅇ]+)"
)
_AMOUNT_CONTEXT_KEYWORDS = (
    "사업자번호",
    "사업자등록번호",
    "등록번호",
    "전화",
    "tel",
    "대표번호",
    "매장전화",
    "상호",
    "상호명",
    "가맹점명",
    "매장명",
    "총매출액",
    "총 매출액",
    "상품금액",
    "상품 금액",
    "할인",
    "할인금액",
    "할인 금액",
    "할인내역",
    "할인 내역",
    "합계",
    "합계금액",
    "합계 금액",
    "받은금액",
    "받은 금액",
    "반은금액",
    "결제금액",
    "결제 금액",
    "카드결제",
    "카드 결제",
    "현금결제",
    "현금 결제",
    "최종결제금액",
    "결제대상금액",
    "멤버십",
    "쿠폰",
    "포인트",
    "차감",
    "프로모션",
    "초이스",
    "vvip",
    "vip",
    "kt",
)


class AzureDocumentIntelligenceProvider(OCRProvider):
    provider_name = OCRProviderName.AZURE.value
    ocr_extensions = {".jpg", ".jpeg", ".png", ".pdf"}
    skipped_extensions = {".xlsx", ".csv"}
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".pdf": "application/pdf",
    }

    def __init__(
        self,
        config: AppConfig | None = None,
        *,
        session: requests.Session | None = None,
        poll_interval_seconds: float | None = None,
        max_poll_attempts: int | None = None,
        max_retries: int | None = None,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config or get_config()
        self._validate_config()
        self.session = session or requests.Session()
        if self.config.azure_ocr_ignore_env_proxy:
            self.session.trust_env = False
        self.poll_interval_seconds = _positive_float(
            poll_interval_seconds,
            float(self.config.azure_ocr_default_poll_interval_seconds),
        )
        self.max_poll_interval_seconds = max(
            MIN_POLL_INTERVAL_SECONDS,
            float(self.config.azure_ocr_max_poll_interval_seconds),
        )
        self.max_poll_attempts = max_poll_attempts or self.config.azure_ocr_max_poll_attempts
        self.max_retries = max_retries if max_retries is not None else self.config.azure_ocr_max_retries
        self.sleep_func = sleep_func or time.sleep

    def extract(self, source: OCRInput) -> OCRResult:
        source_info = self._source_info(source)
        suffix = source_info["file_extension"]

        if suffix in self.skipped_extensions:
            return OCRResult.skipped(
                source_file_id=source_info["source_file_id"],
                source_file_name=source_info["source_file_name"],
                stored_relative_path=source_info["stored_relative_path"],
                provider=self.provider_name,
                error_message="카드 사용내역 파일은 OCR 대상이 아닙니다.",
            )

        if suffix not in self.ocr_extensions:
            return self._failed(source_info, "지원하지 않는 OCR 파일 형식입니다.", "unsupported_file_type")

        path = source_info["file_path"]
        if not isinstance(path, Path) or not path.exists():
            return self._failed(source_info, "OCR 대상 파일에 접근할 수 없습니다.", "source_not_accessible")

        try:
            result_payload = self._analyze_file(path, suffix)
        except requests.Timeout:
            return self._failed(source_info, "OCR 요청 시간이 초과되었습니다.", "timeout")
        except requests.exceptions.ProxyError:
            return self._failed(source_info, "OCR 요청에 실패했습니다.", "proxy_error")
        except requests.RequestException as exc:
            return self._failed(
                source_info,
                "OCR 요청에 실패했습니다.",
                _request_diagnostic_code(exc),
                diagnostic_detail_code=_request_diagnostic_detail_code(exc),
            )
        except ValueError:
            return self._failed(source_info, "OCR 응답을 해석할 수 없습니다.", "bad_response")
        except KeyError:
            return self._failed(source_info, "OCR 응답 구조를 확인해야 합니다.", "unexpected_response")

        sanitized = self._sanitize_result(result_payload)
        return OCRResult.completed(
            source_file_id=source_info["source_file_id"],
            source_file_name=source_info["source_file_name"],
            stored_relative_path=source_info["stored_relative_path"],
            provider=self.provider_name,
            raw_text=self._safe_parser_text(sanitized),
            raw_json=sanitized,
            confidence=sanitized.get("confidence") or 0.0,
        )

    def _analyze_file(self, path: Path, suffix: str) -> dict[str, Any]:
        analyze_url = self._analyze_url()
        headers = {
            "Ocp-Apim-Subscription-Key": self.config.azure_document_intelligence_key or "",
            "Content-Type": self.content_types[suffix],
        }
        data = path.read_bytes()
        response = self._request_with_retries(
            "analyze",
            lambda: self.session.post(
                analyze_url,
                headers=headers,
                data=data,
                timeout=self.config.ocr_request_timeout_seconds,
            ),
        )
        if response.status_code >= 400:
            raise _http_error("analyze", response)

        operation_location = response.headers.get("Operation-Location")
        if not operation_location:
            return response.json()

        return self._poll_result(operation_location)

    def _poll_result(self, operation_location: str) -> dict[str, Any]:
        headers = {"Ocp-Apim-Subscription-Key": self.config.azure_document_intelligence_key or ""}
        last_payload: dict[str, Any] | None = None
        for attempt in range(self.max_poll_attempts):
            response = self._request_with_retries(
                "poll",
                lambda: self.session.get(
                    operation_location,
                    headers=headers,
                    timeout=self.config.ocr_request_timeout_seconds,
                ),
            )
            if response.status_code >= 400:
                raise _http_error("poll", response)
            payload = response.json()
            last_payload = payload
            status = str(payload.get("status", "")).lower()
            if status == "succeeded":
                return payload
            if status in {"failed", "canceled"}:
                raise requests.RequestException("operation_failed")
            if attempt < self.max_poll_attempts - 1:
                self._sleep(self._poll_wait_seconds(response))
        if last_payload is not None:
            raise requests.Timeout("analyze polling timed out")
        raise ValueError("empty analyze result")

    def _request_with_retries(self, stage: str, request_func: Callable[[], requests.Response]) -> requests.Response:
        response = request_func()
        retries = 0
        while response.status_code in RETRYABLE_HTTP_STATUS_CODES and retries < self.max_retries:
            self._sleep(self._retry_wait_seconds(response, retries))
            retries += 1
            response = request_func()
        return response

    def _poll_wait_seconds(self, response: requests.Response) -> float:
        retry_after = _retry_after_seconds(response)
        if retry_after is not None:
            return self._clamp_wait_seconds(retry_after)
        return self._clamp_wait_seconds(self.poll_interval_seconds)

    def _retry_wait_seconds(self, response: requests.Response, retry_index: int) -> float:
        retry_after = _retry_after_seconds(response)
        if retry_after is not None:
            return self._clamp_wait_seconds(retry_after)
        return self._clamp_wait_seconds(self.poll_interval_seconds * (2**retry_index))

    def _clamp_wait_seconds(self, seconds: float) -> float:
        return min(max(seconds, MIN_POLL_INTERVAL_SECONDS), self.max_poll_interval_seconds)

    def _sleep(self, seconds: float) -> None:
        if seconds > 0:
            self.sleep_func(seconds)

    def _sanitize_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        fields = self._document_fields(payload)
        mapped_fields = {
            "merchant_name": self._field_value(fields, ["MerchantName"]),
            "transaction_date": self._field_value(fields, ["TransactionDate"]),
            "total_amount": self._field_value(fields, ["Total", "TransactionTotal", "TotalAmount"]),
            "vat_amount": self._field_value(fields, ["TotalTax", "Tax"]),
            "payment_method": self._field_value(fields, ["PaymentMethod"]),
        }
        field_confidences = [
            self._field_confidence(fields.get(name))
            for name in ("MerchantName", "TransactionDate", "Total", "TransactionTotal", "TotalAmount", "TotalTax", "Tax")
        ]
        confidence = _average([value for value in field_confidences if value is not None])
        sanitized_fields = {
            field_name: {
                "value": self._field_value(fields, [field_name]),
                "confidence": self._field_confidence(field),
            }
            for field_name, field in fields.items()
            if field_name in {"MerchantName", "TransactionDate", "Total", "TransactionTotal", "TotalAmount", "TotalTax", "Tax", "PaymentMethod"}
        }
        warnings = []
        if not any(mapped_fields.values()):
            warnings.append("mapped_fields_empty")
        amount_context_lines = _amount_context_lines(payload)
        return {
            **mapped_fields,
            "amount_context_lines": amount_context_lines,
            "fields": sanitized_fields,
            "provider": self.provider_name,
            "confidence": confidence if confidence is not None else 0.0,
            "warnings": warnings,
        }

    def _document_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        analyze_result = payload.get("analyzeResult") if isinstance(payload.get("analyzeResult"), dict) else payload
        documents = analyze_result.get("documents") if isinstance(analyze_result, dict) else None
        if isinstance(documents, list) and documents:
            first_document = documents[0]
            fields = first_document.get("fields") if isinstance(first_document, dict) else None
            if isinstance(fields, dict):
                return fields
        fields = analyze_result.get("fields") if isinstance(analyze_result, dict) else None
        return fields if isinstance(fields, dict) else {}

    def _field_value(self, fields: dict[str, Any], names: list[str]) -> object | None:
        for name in names:
            field = fields.get(name)
            if not isinstance(field, dict):
                continue
            for key in (
                "valueString",
                "valueDate",
                "valueTime",
                "valuePhoneNumber",
                "valueNumber",
                "valueInteger",
            ):
                if field.get(key) not in {None, ""}:
                    return field[key]
            value_currency = field.get("valueCurrency")
            if isinstance(value_currency, dict) and value_currency.get("amount") is not None:
                return value_currency.get("amount")
            if field.get("content") not in {None, ""}:
                return field["content"]
        return None

    def _field_confidence(self, field: object) -> float | None:
        if not isinstance(field, dict):
            return None
        confidence = field.get("confidence")
        if isinstance(confidence, (int, float)):
            return float(confidence)
        return None

    def _safe_summary_text(self, sanitized: dict[str, Any]) -> str:
        labels = [
            ("상호명", sanitized.get("merchant_name")),
            ("거래일자", sanitized.get("transaction_date")),
            ("총금액", sanitized.get("total_amount")),
            ("부가세", sanitized.get("vat_amount")),
            ("결제수단", sanitized.get("payment_method")),
        ]
        return "\n".join(f"{label}: {value}" for label, value in labels if value not in {None, ""})

    def _safe_parser_text(self, sanitized: dict[str, Any]) -> str:
        lines = [self._safe_summary_text(sanitized)]
        context_lines = sanitized.get("amount_context_lines")
        if isinstance(context_lines, list):
            lines.extend(str(line) for line in context_lines if line)
        return "\n".join(line for line in lines if line)

    def _source_info(self, source: OCRInput) -> dict[str, Any]:
        if isinstance(source, StoredFileMetadata):
            stored_relative_path = source.stored_relative_path
            return {
                "source_file_id": self._source_file_id(stored_relative_path),
                "source_file_name": self._display_file_name(source.original_file_name),
                "stored_relative_path": stored_relative_path,
                "file_extension": source.file_extension.lower(),
                "file_path": Path(stored_relative_path),
            }

        path = Path(source)
        stored_relative_path = path.name if path.is_absolute() else path.as_posix()
        return {
            "source_file_id": self._source_file_id(stored_relative_path),
            "source_file_name": path.name,
            "stored_relative_path": stored_relative_path,
            "file_extension": path.suffix.lower(),
            "file_path": path,
        }

    def _failed(
        self,
        source_info: dict[str, Any],
        message: str,
        diagnostic_code: str,
        *,
        diagnostic_detail_code: str | None = None,
    ) -> OCRResult:
        return OCRResult.failed(
            source_file_id=source_info["source_file_id"],
            source_file_name=source_info["source_file_name"],
            stored_relative_path=source_info["stored_relative_path"],
            provider=self.provider_name,
            error_message=message,
            diagnostic_code=diagnostic_code,
            diagnostic_detail_code=diagnostic_detail_code,
        )

    def _analyze_url(self) -> str:
        endpoint = (self.config.azure_document_intelligence_endpoint or "").rstrip("/")
        model_id = self.config.azure_document_intelligence_model_id
        api_version = self.config.azure_document_intelligence_api_version
        return f"{endpoint}/documentintelligence/documentModels/{model_id}:analyze?api-version={api_version}"

    def _validate_config(self) -> None:
        if not self.config.azure_document_intelligence_endpoint:
            raise ConfigurationError("Azure OCR endpoint 설정이 필요합니다.")
        if not self.config.azure_document_intelligence_key:
            raise ConfigurationError("Azure OCR key 설정이 필요합니다.")

    def _source_file_id(self, value: str | None) -> str:
        return sha256((value or "unknown").encode("utf-8")).hexdigest()

    def _display_file_name(self, value: str) -> str:
        return Path(str(value).replace("\\", "/")).name


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _amount_context_lines(payload: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for line in _ocr_text_lines(payload):
        safe_line = sanitize_lines_for_parsing(str(line or ""))
        for item in safe_line.splitlines():
            normalized = re.sub(r"\s+", " ", item).strip()
            if not normalized:
                continue
            if _is_amount_context_line(normalized):
                result.append(normalized)
            if len(result) >= 120:
                return result
    return result


def _ocr_text_lines(payload: Any) -> list[str]:
    lines: list[str] = []
    analyze_result = payload.get("analyzeResult") if isinstance(payload, dict) and isinstance(payload.get("analyzeResult"), dict) else payload
    if isinstance(analyze_result, dict):
        for page in analyze_result.get("pages") or []:
            if not isinstance(page, dict):
                continue
            for line in page.get("lines") or []:
                text = _content_value(line)
                if text:
                    lines.append(text)
        for paragraph in analyze_result.get("paragraphs") or []:
            text = _content_value(paragraph)
            if text:
                lines.append(text)
        for table in analyze_result.get("tables") or []:
            if not isinstance(table, dict):
                continue
            rows: dict[int, list[tuple[int, str]]] = {}
            for cell in table.get("cells") or []:
                if not isinstance(cell, dict):
                    continue
                row_index = _safe_int(cell.get("rowIndex"))
                column_index = _safe_int(cell.get("columnIndex"))
                text = _content_value(cell)
                if row_index is None or column_index is None or not text:
                    continue
                rows.setdefault(row_index, []).append((column_index, text))
            for row_index in sorted(rows):
                row = " ".join(text for _, text in sorted(rows[row_index], key=lambda item: item[0]))
                if row:
                    lines.append(row)
    return lines


def _content_value(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("content", "text", "value", "valueString"):
            if value.get(key) not in {None, ""}:
                return str(value[key])
    if isinstance(value, str):
        return value
    return None


def _safe_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_amount_context_line(line: str) -> bool:
    normalized = line.lower().replace(" ", "")
    if any(keyword.lower().replace(" ", "") in normalized for keyword in _AMOUNT_CONTEXT_KEYWORDS):
        return True
    if re.fullmatch(rf"\s*{_AMOUNT_CONTEXT_PATTERN.pattern}\s*(?:원)?\s*", line, flags=re.IGNORECASE):
        return True
    if _AMOUNT_CONTEXT_PATTERN.search(line) and any(
        keyword in normalized
        for keyword in ("kt", "vvip", "vip", "멤버십", "쿠폰", "포인트", "초이스", "차감", "프로모션")
    ):
        return True
    return False


def _request_diagnostic_code(exc: requests.RequestException) -> str:
    if isinstance(exc, _AzureHttpError):
        return f"{exc.stage}_http_{exc.status_code}"
    message = str(exc)
    if re_match := _HTTP_DIAGNOSTIC_PATTERN.fullmatch(message):
        return f"{re_match.group('stage')}_http_{re_match.group('status')}"
    if message in {"operation_failed"}:
        return message
    return "request_error"


def _request_diagnostic_detail_code(exc: requests.RequestException) -> str | None:
    if isinstance(exc, _AzureHttpError):
        return exc.detail_code
    return None


class _AzureHttpError(requests.RequestException):
    def __init__(self, stage: str, status_code: int, detail_code: str | None = None) -> None:
        super().__init__(f"{stage}_http_{status_code}")
        self.stage = stage
        self.status_code = status_code
        self.detail_code = detail_code


def _http_error(stage: str, response: requests.Response) -> requests.RequestException:
    return _AzureHttpError(stage, response.status_code, _safe_http_error_detail_code(response))


def _safe_http_error_detail_code(response: requests.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return "non_json_error"
    if not isinstance(payload, dict):
        return "unexpected_error_shape"
    error = payload.get("error")
    if not isinstance(error, dict):
        return "unexpected_error_shape"
    raw_code = _safe_code_token(error.get("code"))
    message = str(error.get("message") or "").lower()
    if any(token in message for token in ("quota", "exceed", "limit", "rate")):
        return "quota_or_rate_limit"
    if any(token in message for token in ("key", "credential", "permission", "access", "denied")):
        return "credential_or_permission"
    if any(token in message for token in ("region", "location")):
        return "region_or_endpoint"
    return raw_code or "http_error"


def _safe_code_token(value: object) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    safe = "".join(character for character in text if character.isalnum() or character in {"_", "-"})
    return safe[:80] or None


def _retry_after_seconds(response: requests.Response) -> float | None:
    raw_value = response.headers.get("Retry-After")
    if raw_value is None:
        return None
    try:
        seconds = int(str(raw_value).strip())
    except ValueError:
        return None
    return float(seconds) if seconds > 0 else None


def _positive_float(value: float | None, default: float) -> float:
    if value is None:
        return max(default, MIN_POLL_INTERVAL_SECONDS)
    return max(float(value), MIN_POLL_INTERVAL_SECONDS)

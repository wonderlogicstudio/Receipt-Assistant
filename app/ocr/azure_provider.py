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
from app.storage.file_store import StoredFileMetadata


RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
MIN_POLL_INTERVAL_SECONDS = 1.0
_HTTP_DIAGNOSTIC_PATTERN = re.compile(r"(?P<stage>analyze|poll)_http_(?P<status>\d{3})")


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
            return self._failed(source_info, "OCR 요청에 실패했습니다.", _request_diagnostic_code(exc))
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
            raw_text=self._safe_summary_text(sanitized),
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
            raise _http_error("analyze", response.status_code)

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
                raise _http_error("poll", response.status_code)
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
        return {
            **mapped_fields,
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

    def _failed(self, source_info: dict[str, Any], message: str, diagnostic_code: str) -> OCRResult:
        return OCRResult.failed(
            source_file_id=source_info["source_file_id"],
            source_file_name=source_info["source_file_name"],
            stored_relative_path=source_info["stored_relative_path"],
            provider=self.provider_name,
            error_message=message,
            diagnostic_code=diagnostic_code,
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


def _request_diagnostic_code(exc: requests.RequestException) -> str:
    message = str(exc)
    if re_match := _HTTP_DIAGNOSTIC_PATTERN.fullmatch(message):
        return f"{re_match.group('stage')}_http_{re_match.group('status')}"
    if message in {"operation_failed"}:
        return message
    return "request_error"


def _http_error(stage: str, status_code: int) -> requests.RequestException:
    return requests.RequestException(f"{stage}_http_{status_code}")


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

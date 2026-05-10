from __future__ import annotations

import time
from hashlib import sha256
from pathlib import Path
from typing import Any

import requests

from app.core.config import AppConfig, get_config
from app.core.enums import OCRProviderName, OCRStatus
from app.core.exceptions import ConfigurationError
from app.core.ocr_models import OCRResult
from app.ocr.base import OCRInput, OCRProvider
from app.storage.file_store import StoredFileMetadata


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
        poll_interval_seconds: float = 0.5,
        max_poll_attempts: int = 12,
    ) -> None:
        self.config = config or get_config()
        self._validate_config()
        self.session = session or requests.Session()
        self.poll_interval_seconds = poll_interval_seconds
        self.max_poll_attempts = max_poll_attempts

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
            return self._failed(source_info, "지원하지 않는 OCR 파일 형식입니다.")

        path = source_info["file_path"]
        if not isinstance(path, Path) or not path.exists():
            return self._failed(source_info, "OCR 대상 파일에 접근할 수 없습니다.")

        try:
            result_payload = self._analyze_file(path, suffix)
        except requests.Timeout:
            return self._failed(source_info, "OCR 요청 시간이 초과되었습니다.")
        except requests.RequestException:
            return self._failed(source_info, "OCR 요청에 실패했습니다.")
        except ValueError:
            return self._failed(source_info, "OCR 응답을 해석할 수 없습니다.")
        except KeyError:
            return self._failed(source_info, "OCR 응답 구조를 확인해야 합니다.")

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
        response = self.session.post(
            analyze_url,
            headers=headers,
            data=path.read_bytes(),
            timeout=self.config.ocr_request_timeout_seconds,
        )
        if response.status_code >= 400:
            raise requests.RequestException("analyze request failed")

        operation_location = response.headers.get("Operation-Location")
        if not operation_location:
            return response.json()

        return self._poll_result(operation_location)

    def _poll_result(self, operation_location: str) -> dict[str, Any]:
        headers = {"Ocp-Apim-Subscription-Key": self.config.azure_document_intelligence_key or ""}
        last_payload: dict[str, Any] | None = None
        for attempt in range(self.max_poll_attempts):
            response = self.session.get(
                operation_location,
                headers=headers,
                timeout=self.config.ocr_request_timeout_seconds,
            )
            if response.status_code >= 400:
                raise requests.RequestException("analyze result request failed")
            payload = response.json()
            last_payload = payload
            status = str(payload.get("status", "")).lower()
            if status == "succeeded":
                return payload
            if status == "failed":
                raise requests.RequestException("analyze operation failed")
            if attempt < self.max_poll_attempts - 1 and self.poll_interval_seconds > 0:
                time.sleep(self.poll_interval_seconds)
        if last_payload is not None:
            raise requests.Timeout("analyze polling timed out")
        raise ValueError("empty analyze result")

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

    def _failed(self, source_info: dict[str, Any], message: str) -> OCRResult:
        return OCRResult.failed(
            source_file_id=source_info["source_file_id"],
            source_file_name=source_info["source_file_name"],
            stored_relative_path=source_info["stored_relative_path"],
            provider=self.provider_name,
            error_message=message,
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

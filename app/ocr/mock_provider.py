from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from app.core.enums import OCRProviderName, OCRStatus
from app.core.ocr_models import OCRResult
from app.ocr.base import OCRInput, OCRProvider
from app.storage.file_store import StoredFileMetadata


class MockOCRProvider(OCRProvider):
    provider_name = OCRProviderName.MOCK.value
    ocr_extensions = {".jpg", ".jpeg", ".png", ".pdf"}
    skipped_extensions = {".xlsx", ".csv"}

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
            return OCRResult.failed(
                source_file_id=source_info["source_file_id"],
                source_file_name=source_info["source_file_name"],
                stored_relative_path=source_info["stored_relative_path"],
                provider=self.provider_name,
                error_message=f"지원하지 않는 OCR 파일 형식입니다: {suffix or '확장자 없음'}",
            )

        if not source_info["exists"]:
            return OCRResult.failed(
                source_file_id=source_info["source_file_id"],
                source_file_name=source_info["source_file_name"],
                stored_relative_path=source_info["stored_relative_path"],
                provider=self.provider_name,
                error_message="OCR 대상 파일에 접근할 수 없습니다.",
            )

        sample = self._sample_receipt(source_info["source_file_name"], source_info["stored_relative_path"])
        return OCRResult.completed(
            source_file_id=source_info["source_file_id"],
            source_file_name=source_info["source_file_name"],
            stored_relative_path=source_info["stored_relative_path"],
            provider=self.provider_name,
            raw_text=sample["raw_text"],
            raw_json=sample,
            confidence=sample["confidence"],
        )

    def _source_info(self, source: OCRInput) -> dict[str, object]:
        if isinstance(source, StoredFileMetadata):
            stored_relative_path = source.stored_relative_path
            source_file_name = source.original_file_name
            file_extension = source.file_extension.lower()
            source_file_id = self._source_file_id(stored_relative_path)
            exists = Path(stored_relative_path).exists()
            return {
                "source_file_id": source_file_id,
                "source_file_name": source_file_name,
                "stored_relative_path": stored_relative_path,
                "file_extension": file_extension,
                "exists": exists,
            }

        path = Path(source)
        source_file_name = path.name
        stored_relative_path = path.as_posix() if not path.is_absolute() else source_file_name
        return {
            "source_file_id": self._source_file_id(stored_relative_path),
            "source_file_name": source_file_name,
            "stored_relative_path": stored_relative_path,
            "file_extension": path.suffix.lower(),
            "exists": path.exists(),
        }

    def _source_file_id(self, value: str | None) -> str:
        return sha256((value or "unknown").encode("utf-8")).hexdigest()

    def _sample_receipt(self, source_file_name: str, stored_relative_path: str | None) -> dict[str, object]:
        confidence = 0.94
        raw_text = "\n".join(
            [
                "샘플문구 강남점",
                "사업자번호: 123-45-67890",
                "거래일자: 2026-05-06",
                "공급가액: 30,000",
                "부가세: 3,000",
                "총금액: 33,000",
                "결제수단: 카드",
                "추천비용항목: 소모품비",
            ]
        )
        return {
            "source_file_name": source_file_name,
            "stored_relative_path": stored_relative_path,
            "provider": self.provider_name,
            "status": OCRStatus.COMPLETED.value,
            "confidence": confidence,
            "pages": [
                {
                    "page": 1,
                    "fields": {
                        "merchant_name": "샘플문구 강남점",
                        "transaction_date": "2026-05-06",
                        "business_number": "123-45-67890",
                        "total_amount": 33000,
                        "supply_amount": 30000,
                        "vat_amount": 3000,
                        "payment_method": "카드",
                        "expense_category": "소모품비",
                    },
                    "lines": raw_text.splitlines(),
                }
            ],
            "transaction_date": "2026-05-06",
            "merchant_name": "샘플문구 강남점",
            "business_number": "123-45-67890",
            "total_amount": 33000,
            "supply_amount": 30000,
            "vat_amount": 3000,
            "payment_method": "카드",
            "expense_category": "소모품비",
            "raw_text": raw_text,
        }

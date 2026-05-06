from __future__ import annotations

from pathlib import Path

from app.ocr.base import OCRProvider, OCRResult


class MockOCRProvider(OCRProvider):
    provider_name = "mock"
    supported_extensions = {".jpg", ".jpeg", ".png", ".pdf"}

    def extract(self, file_path: str) -> OCRResult:
        source_file_name = Path(file_path).name
        suffix = Path(source_file_name).suffix.lower()

        if suffix and suffix not in self.supported_extensions:
            return OCRResult.failed(
                source_file_name=source_file_name,
                provider=self.provider_name,
                error_message="지원하지 않는 영수증 파일 형식입니다.",
            )

        sample = self._sample_receipt(source_file_name)
        return OCRResult.success(
            source_file_name=source_file_name,
            provider=self.provider_name,
            raw_text=sample["raw_text"],
            raw_json=sample,
            confidence=sample["confidence"],
        )

    def _sample_receipt(self, source_file_name: str) -> dict[str, object]:
        return {
            "source_file_name": source_file_name,
            "transaction_date": "2026-05-06",
            "merchant_name": "샘플문구 강남점",
            "business_number": "123-45-67890",
            "total_amount": 33000,
            "supply_amount": 30000,
            "vat_amount": 3000,
            "payment_method": "카드",
            "expense_category": "소모품비",
            "confidence": 0.94,
            "raw_text": "\n".join(
                [
                    "샘플문구 강남점",
                    "사업자번호: 123-45-67890",
                    "거래일자: 2026-05-06",
                    "공급가액: 30,000",
                    "부가세: 3,000",
                    "합계: 33,000",
                    "결제수단: 카드",
                    "추천비용항목: 소모품비",
                ]
            ),
        }


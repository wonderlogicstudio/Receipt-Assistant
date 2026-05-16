# StandardOCRResult Schema

## 목적

`StandardOCRResult`는 Azure, PaddleOCR, Tesseract, Android ML Kit, iOS Apple Vision, Mock OCR 등 서로 다른 OCR Provider 결과를 하나의 중간 포맷으로 정리하기 위한 내부 표준입니다.

목표는 OCR Provider가 바뀌어도 `ReceiptParser`, `ReceiptValidator`, `CategoryRules`, `CardMatcher`, `ExcelExporter`, 처리 이력 흐름이 분기되지 않게 하는 것입니다.

## 적용 범위

- 웹 Streamlit MVP
- PC Local OCR Runtime
- Server Runtime
- 모바일 앱 OCR Adapter
- Golden Fixture 기반 Parser/Adapter 테스트

## 필드 정의

| 필드 | 필수 | 설명 |
|---|---|---|
| `id` | 예 | 표준 OCR 결과 식별자 |
| `source_file_id` | 아니오 | 업로드 파일 식별자 |
| `source_file_name` | 예 | 화면/엑셀 표시용 원본 파일명 요약. 전체 경로 금지 |
| `provider` | 예 | `azure`, `paddle`, `tesseract`, `android_mlkit`, `ios_vision`, `mock` 등 |
| `provider_version` | 아니오 | Provider 또는 모델 버전 |
| `engine_runtime` | 예 | `local`, `server`, `mobile`, `mock` 등 |
| `status` | 예 | `completed`, `failed`, `skipped` 등 |
| `pages` | 예 | 페이지 크기와 번호 요약 |
| `safe_text_summary` | 아니오 | Parser와 검수에 필요한 1000자 이하 제한 요약 문자열. 전체 raw text 금지 |
| `text_blocks` | 예 | OCR 텍스트 block/line 목록 |
| `key_value_candidates` | 아니오 | 금액, 날짜, 상호 등 key-value 후보 |
| `table_candidates` | 아니오 | 표 형태 후보 |
| `confidence` | 아니오 | 전체 OCR 신뢰도 요약 |
| `warnings` | 아니오 | 비민감 경고 목록 |
| `diagnostic_code` | 아니오 | 비민감 상태 코드 |
| `created_at` | 예 | ISO 8601 생성 시각 |

## text_blocks 구조

| 필드 | 필수 | 설명 |
|---|---|---|
| `page_index` | 예 | 0부터 시작하는 페이지 번호 |
| `block_id` | 예 | block 식별자 |
| `text` | 예 | OCR 인식 문자열. 민감문구 필터 대상 |
| `normalized_text` | 아니오 | Parser 보조용 정규화 문자열 |
| `confidence` | 아니오 | 0~1 범위 신뢰도. Provider가 제공하지 않으면 `null` 가능 |
| `bbox` | 아니오 | `[x1, y1, x2, y2]` 형식 좌표. Provider가 제공하지 않으면 `null` 가능 |
| `line_order` | 아니오 | 페이지 내 읽기 순서 |
| `block_type` | 아니오 | `line`, `word`, `paragraph`, `field` 등 |
| `sensitive_category` | 아니오 | 민감문구 가능성이 있으면 category만 기록 |

## pages 구조

| 필드 | 필수 | 설명 |
|---|---|---|
| `page_index` | 예 | 0부터 시작하는 페이지 번호 |
| `width` | 아니오 | 이미지 또는 페이지 너비 |
| `height` | 아니오 | 이미지 또는 페이지 높이 |
| `unit` | 아니오 | `pixel`, `inch`, `point` 등 |
| `text_blocks` | 아니오 | 페이지별 block 참조 또는 요약 |
| `key_value_candidates` | 아니오 | 페이지별 key-value 후보 |
| `table_candidates` | 아니오 | 페이지별 table 후보 |

## key_value_candidates 구조

| 필드 | 필수 | 설명 |
|---|---|---|
| `key` | 예 | `total_amount`, `transaction_date`, `merchant_name` 등 표준 key |
| `value` | 예 | 원문에서 추출한 후보값. 민감값은 원문 저장 금지 |
| `normalized_value` | 아니오 | 숫자, 날짜 등 정규화 값 |
| `confidence` | 아니오 | 후보 신뢰도 |
| `source_block_ids` | 아니오 | 근거 block id 목록 |
| `candidate_type` | 아니오 | `amount`, `date`, `merchant`, `tax`, `payment` 등 |

## table_candidates 구조

| 필드 | 필수 | 설명 |
|---|---|---|
| `page_index` | 예 | 페이지 번호 |
| `table_id` | 예 | table 식별자 |
| `rows` | 예 | 더미 또는 정규화된 행 데이터 |
| `confidence` | 아니오 | 후보 신뢰도 |
| `source_block_ids` | 아니오 | 근거 block id 목록 |

## safe_text_summary 사용 원칙

`safe_text_summary`는 전체 OCR raw text가 아닙니다. Parser와 검수에 필요한 제한된 요약 또는 제한된 context line만 1000자 이하 문자열로 포함합니다. OCR raw text 전체는 DB, 화면, 엑셀, 로그에 저장하거나 표시하지 않습니다.

## Azure Adapter 매핑 예시

- Azure line items와 read result line은 `text_blocks`로 변환합니다.
- Azure receipt/document 구조화 필드는 `key_value_candidates`와 `table_candidates`에 요약합니다.
- Azure raw JSON 전체는 DB, 화면, 엑셀, 로그, Parser 입력에 저장하거나 전달하지 않습니다.

## PaddleOCR Adapter 매핑 예시

- PaddleOCR의 detected text와 score는 `text_blocks.text`, `text_blocks.confidence`로 변환합니다.
- 좌표가 있으면 `bbox`에 `[x1, y1, x2, y2]` 형태로 정규화합니다.
- PaddleOCR은 구조화 영수증 필드를 기본 제공하지 않는다고 보고 `key_value_candidates`는 Parser 후보 추론 전까지 비워둘 수 있습니다.

## ML Kit / Apple Vision Adapter 매핑 예시

- Android ML Kit과 iOS Apple Vision의 recognized text block 또는 line을 `text_blocks`로 변환합니다.
- 온디바이스 OCR 결과도 웹/PC와 같은 `schema_version`을 사용합니다.
- 모바일 앱에서 생성한 JSON/ZIP은 웹/PC에서 이어 처리할 수 있어야 합니다.

## 보안 원칙

1. Provider raw JSON 전체를 저장하거나 표시하지 않습니다.
2. OCR raw text 전체를 DB, 화면, 엑셀, 로그에 그대로 노출하지 않습니다.
3. 전체 로컬 절대경로를 저장하거나 표시하지 않습니다.
4. API key, endpoint 전체 URL, secret, token, password를 포함하지 않습니다.
5. 카드번호 전체, 주민번호, 비밀번호, WiFi PW 같은 민감문구 가능성은 실제 값 대신 category와 검토 사유만 남깁니다.

## 버전 관리

- 6주차-B 모델 초안에는 `schema_version`을 필수 필드로 고정하지 않습니다.
- StandardOCRResult 필수 필드가 바뀌면 SPEC.md, CHECKLIST.md, fixture, 관련 테스트를 함께 업데이트합니다.
- Adapter 변경만으로 Parser 입력 계약이 유지되면 문서와 fixture 변경 없이 Provider Adapter 테스트만 보강할 수 있습니다.

## 샘플 JSON

```json
{
  "id": "standard_ocr_001",
  "source_file_id": "file_001",
  "source_file_name": "receipt_001.jpg",
  "provider": "azure",
  "provider_version": "document-intelligence-v4",
  "engine_runtime": "server",
  "status": "completed",
  "pages": [
    {
      "page_index": 0,
      "width": 1080,
      "height": 1920,
      "unit": "pixel"
    }
  ],
  "safe_text_summary": "스타벅스 테스트점. 거래일자 2026-05-14. 합계 12,000.",
  "text_blocks": [
    {
      "page_index": 0,
      "block_id": "b001",
      "text": "스타벅스 테스트점",
      "normalized_text": "스타벅스 테스트점",
      "confidence": 0.96,
      "bbox": [10, 120, 420, 160],
      "line_order": 1,
      "block_type": "line",
      "sensitive_category": null
    },
    {
      "page_index": 0,
      "block_id": "b002",
      "text": "합계 12,000",
      "normalized_text": "합계 12000",
      "confidence": 0.93,
      "bbox": [10, 500, 300, 530],
      "line_order": 5,
      "block_type": "line",
      "sensitive_category": null
    }
  ],
  "key_value_candidates": [
    {
      "key": "merchant_name",
      "value": "스타벅스 테스트점",
      "normalized_value": "스타벅스 테스트점",
      "confidence": 0.96,
      "source_block_ids": ["b001"],
      "candidate_type": "merchant"
    },
    {
      "key": "total_amount",
      "value": "12,000",
      "normalized_value": "12000",
      "confidence": 0.93,
      "source_block_ids": ["b002"],
      "candidate_type": "amount"
    }
  ],
  "table_candidates": [],
  "confidence": 0.94,
  "warnings": [],
  "diagnostic_code": "completed",
  "created_at": "2026-05-14T21:00:00+09:00"
}
```

## 금지사항

- raw JSON 전체 저장 금지
- OCR raw text 전체 노출 금지
- 전체 로컬 절대경로 노출 금지
- Provider별 원본 응답을 Parser에 직접 전달 금지
- Provider Adapter 없이 Parser에 신규 OCR Provider 분기 추가 금지

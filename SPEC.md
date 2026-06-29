# 기능 명세

## 1. 핵심 흐름

```text
영수증 이미지/PDF 업로드 + 카드 사용내역 CSV/XLSX 업로드
→ OCR Provider 실행
→ OCRResult 생성
→ ReceiptParser로 ReceiptRecord 생성
→ Validator, 비용항목 추천, 중복 의심 탐지, 카드 매칭
→ 사용자 검수
→ ExcelExporter로 표준 엑셀 정리 파일 생성
→ 처리 이력 DB 저장
→ 다운로드 및 처리 이력 재다운로드
```

OCR 결과와 분류 후보는 사용자가 확인해야 합니다.

## 1-1. StandardOCRResult

`StandardOCRResult`는 Azure, PaddleOCR, Tesseract, Android ML Kit, iOS Apple Vision, Mock OCR 등 Provider가 달라도 Parser 이후 흐름을 하나로 유지하기 위한 공통 OCR 중간 포맷입니다. 기존 `OCRResult`는 처리 결과/상태 모델로 유지할 수 있고, `StandardOCRResult`는 Provider 독립적인 Parser 입력 계약으로 사용합니다.

목적:

- OCR Provider별 원본 응답 구조를 Parser/Validator/ExcelExporter로 직접 전파하지 않습니다.
- 웹, PC Local Runtime, Server Runtime, 모바일 앱이 같은 OCR 결과 계약을 사용합니다.
- Provider가 달라도 `ReceiptParser`, `ReceiptValidator`, `CategoryRules`, `CardMatcher`, `ExcelExporter`, 처리 이력 흐름은 하나로 유지합니다.

향후 구조:

```text
Provider raw response
→ Provider Adapter
→ StandardOCRResult
→ ReceiptParser
→ ReceiptRecord
→ ReceiptValidator / CategoryRules / CardMatcher
→ ExcelExporter / Processing History
```

`StandardOCRResult` 초안 필드:

```text
id
source_file_id
source_file_name
provider
provider_version
engine_runtime
status
pages
safe_text_summary
text_blocks
key_value_candidates
table_candidates
confidence
warnings
diagnostic_code
created_at
```

`StandardOCRPage` 초안 필드:

```text
page_index
width
height
unit
text_blocks
key_value_candidates
table_candidates
```

`StandardOCRTextBlock` 초안 필드:

```text
page_index
block_id
text
normalized_text
confidence
bbox
line_order
block_type
sensitive_category
```

`StandardOCRKeyValueCandidate` 초안 필드:

```text
key
value
normalized_value
confidence
source_block_ids
candidate_type
```

`StandardOCRTableCandidate` 초안 필드:

```text
page_index
table_id
rows
confidence
source_block_ids
```

`bbox`는 OCR Provider별 좌표계를 그대로 노출하지 않고 표준화된 좌표 정보로 관리합니다. 초기에는 선택 필드로 둘 수 있으며, Parser는 `bbox` 없이도 동작할 수 있어야 합니다.

`safe_text_summary`는 전체 OCR raw text가 아닙니다. Parser와 검수에 필요한 제한된 요약 또는 제한된 context line만 포함합니다. OCR raw text 전체는 DB, 화면, 엑셀, 로그에 저장하거나 표시하지 않습니다.

예시 JSON:

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
      "key": "total_amount",
      "value": "12,000",
      "normalized_value": "12000",
      "confidence": 0.93,
      "source_block_ids": ["b001"],
      "candidate_type": "amount"
    }
  ],
  "table_candidates": [],
  "confidence": 0.93,
  "warnings": [],
  "diagnostic_code": "completed",
  "created_at": "2026-05-14T21:00:00+09:00"
}
```

원칙:

1. Parser는 Provider raw response를 직접 보지 않습니다.
2. Parser는 `StandardOCRResult`만 입력으로 받는 방향으로 정리합니다.
3. Azure raw JSON 전체와 OCR raw text 전체는 DB, 화면, 엑셀, 로그에 저장하거나 표시하지 않습니다.
4. PaddleOCR, Tesseract, ML Kit, Apple Vision은 `text_blocks`와 `key_value_candidates` 중심으로 `StandardOCRResult`를 생성합니다.
5. Azure는 구조화 결과를 `key_value_candidates`와 `table_candidates`로 요약할 수 있습니다.
6. Provider Adapter는 원본 응답에서 필요한 요약 정보만 표준 포맷으로 변환하고, 원본 전체를 Parser로 넘기지 않습니다.

Parser 금지 사항:

- Parser는 Azure raw JSON 구조를 직접 참조하지 않습니다.
- Parser는 PaddleOCR raw output 구조를 직접 참조하지 않습니다.
- Parser는 Tesseract 원문 구조를 직접 참조하지 않습니다.
- Parser는 Android ML Kit block 구조를 직접 참조하지 않습니다.
- Parser는 iOS Apple Vision observation 구조를 직접 참조하지 않습니다.
- Parser는 provider별 SDK response object를 import하지 않습니다.

보안 기준:

아래 정보는 `StandardOCRResult`, DB, 화면, 엑셀, 로그에 전체 원문 형태로 남기지 않습니다.

- OCR raw JSON 전체
- OCR raw text 전체
- 전체 로컬 절대경로
- API key
- Azure endpoint 전체 URL
- 실제 고객 파일
- 카드번호 전체
- 주민번호
- 전화번호 등 민감정보
- WiFi PW, 비밀번호, token, secret 등 민감문구 실제 값

민감문구 가능성이 있는 값은 실제 값을 저장하지 않고, 필요한 경우 `sensitive_category`만 저장합니다. 사업자등록번호와 승인번호는 업무상 필요한 필드일 수 있으므로 무조건 제거하지 않되, 금액 후보로 잘못 쓰이지 않도록 Parser/Validator에서 보수적으로 처리합니다.

Golden Test Fixture 전략:

- 동일한 영수증 의미를 가진 Provider별 OCR 결과를 `StandardOCRResult` fixture로 정규화합니다.
- Azure fixture, Mock fixture, 향후 PaddleOCR fixture가 같은 `ReceiptRecord` 결과를 만들 수 있는지 비교합니다.
- fixture에는 실제 고객 파일, 실제 카드번호, 실제 전화번호, 실제 민감정보를 넣지 않습니다.
- OCR raw JSON 전체를 fixture로 저장하지 않습니다.
- 필요한 최소 `text_blocks`, `key_value_candidates`, `warnings`만 더미 데이터로 구성합니다.

6주차-B 구현 메모:

- `app/core/standard_ocr.py`에 `StandardOCRResult`, `StandardOCRPage`, `StandardOCRTextBlock`, `StandardOCRKeyValueCandidate`, `StandardOCRTableCandidate` Pydantic 모델 초안을 추가합니다.
- 6주차-B 모델의 `safe_text_summary`는 전체 OCR raw text가 아니라 1000자 이하의 제한된 문자열 요약으로 둡니다.
- 6주차-B에서는 `schema_version`을 모델 필드로 고정하지 않고, 실제 Parser 전환과 Adapter 버전 정책은 6주차-C 또는 8주차에서 다시 검토합니다.
- 기존 `OCRResult`, `ReceiptRecord`, `ReceiptParser`, `ExcelExporter`, Processing History DB schema는 변경하지 않습니다.

## 1-2. StandardOCRParserContext

`StandardOCRParserContext`는 `StandardOCRResult`에서 `ReceiptParser`가 사용할 수 있는 제한된 line, candidate, review hint만 추출한 중간 입력입니다. Parser 전환 중간 단계에서 사용하며, 이번 단계에서는 운영 흐름에 연결하지 않습니다.

원칙:

- `raw_json`, `raw_text`, `provider_raw_response`, `full_ocr_text`를 포함하지 않습니다.
- Provider raw response 구조를 숨깁니다.
- `amount_candidate_map`과 `non_amount_candidate_map`을 분리합니다.
- `quantity`, `approval_number`, `footer_number`, `business_number`는 금액 후보로 분류하지 않습니다.
- `vat_missing`, `vat_review_hint`는 명시 부가세 후보가 아니라 검토 힌트 또는 non-amount candidate로 분류합니다.
- 향후 `ReceiptParser`는 `StandardOCRParserContext` 또는 `StandardOCRResult` 기반 입력을 사용해야 합니다.
- 기존 raw_text 기반 경로는 즉시 삭제하지 않고 compatibility wrapper로 단계적 전환합니다.

## 1-2-1. Parser Standard Input Contract

8주차 Parser 전환의 목표 구조는 다음과 같습니다.

```text
Provider raw response
→ Provider Adapter
→ StandardOCRResult
→ StandardOCRParserContext
→ ReceiptParser
→ ReceiptRecord
→ ReceiptValidator / CategoryRules / CardMatcher
→ ExcelExporter / Processing History
```

Parser 입력 원칙:

- `ReceiptParser`는 Provider raw response를 직접 받지 않습니다.
- `ReceiptParser`는 Azure SDK response object를 import하지 않습니다.
- `ReceiptParser`는 PaddleOCR raw output 구조를 직접 알지 않습니다.
- `ReceiptParser`는 Tesseract 원본 텍스트/라인 구조에 직접 의존하지 않습니다.
- `ReceiptParser`는 Android ML Kit block 구조를 직접 알지 않습니다.
- `ReceiptParser`는 iOS Apple Vision observation 구조를 직접 알지 않습니다.
- `ReceiptParser`는 `StandardOCRParserContext` 또는 `StandardOCRResult` 기반 입력만 사용하도록 단계적으로 정리합니다.
- 기존 raw_text 기반 경로는 즉시 삭제하지 않고 compatibility wrapper로 유지합니다.

8주차-B Parser entry 후보:

```python
parse_standard_context(context: StandardOCRParserContext) -> ReceiptRecord
parse_from_standard_ocr(result: StandardOCRResult) -> ReceiptRecord
```

실제 함수명은 기존 `ReceiptParser` 스타일에 맞춥니다. 기존 `parse(...)` 같은 public interface는 즉시 삭제하지 않고, 새 entry는 기존 `ReceiptRecord`를 반환해야 합니다. 새 entry는 기존 Parser 내부 정규화 함수와 재사용 가능한 로직을 최대한 공유하되, Provider raw response를 인자로 받지 않습니다.

`StandardOCRParserContext` 사용 기준:

- `safe_text_lines`
- `candidate_map`
- `amount_candidate_map`
- `non_amount_candidate_map`
- `review_hints`
- `sensitive_categories`
- `diagnostic_code`

Parser 입력 경로 금지 항목:

- `raw_json`
- OCR raw text 전체
- `provider_raw_response`
- `full_ocr_text`
- endpoint 전체 URL
- `operation_location` 전체 URL
- API key
- 전체 로컬 절대경로
- 실제 고객 파일명
- 실제 민감정보 원문
- Azure SDK object
- PaddleOCR raw object
- ML Kit raw block
- Apple Vision raw observation

금액 후보 처리 기준:

- `total_amount`, `gross_amount`, `discount_amount`, `final_amount`, `paid_amount`는 금액 후보로 볼 수 있습니다.
- `supply_amount`, `vat_amount`는 명시 공급가액/부가세 후보로만 봅니다.
- `vat_missing`, `vat_review_hint`는 명시 부가세가 아닙니다.
- `quantity`, `approval_number`, `footer_number`, `business_number`는 금액 후보가 아닙니다.
- 할인 후 0원 결제는 자동 제외하지 않습니다.
- 추정 부가세는 명시 부가세로 넣지 않습니다.

fixture 기반 Parser 비교 핵심 필드:

```text
transaction_date
merchant_name
business_number
total_amount
gross_amount
discount_amount
final_amount
paid_amount
amount_source
amount_warnings
supply_amount
vat_amount
estimated_supply_amount
estimated_vat_amount
vat_source
vat_note
vat_warnings
vat_review_required
sensitive_text_detected
sensitive_text_categories
payment_method
approval_number
review_status
parser_warnings
confidence
ocr_provider
```

모든 필드를 한 번에 완벽히 채우는 것이 아니라 핵심 필드부터 fixture 기반으로 비교합니다. Parser 표준 입력화는 `ReceiptRecord` 구조 개편 작업이 아니며, 기존 ExcelExporter가 사용하는 `ReceiptRecord` 구조와 호환되어야 합니다.

## 1-3. Azure Adapter Contract

Azure Adapter의 목적은 Azure Document Intelligence 또는 Azure OCR Provider에서 얻은 provider raw response를 Parser에 직접 넘기지 않고 `StandardOCRResult`로 정규화하는 것입니다.

목표 구조:

```text
Azure raw response
→ AzureStandardOCRAdapter
→ StandardOCRResult
→ StandardOCRParserContext
→ ReceiptParser
→ ReceiptRecord
```

Azure Adapter 입력:

- Azure OCR 결과 객체 또는 provider 내부에서 얻은 제한된 요약 데이터
- `source_file_id`
- `source_file_name`
- provider metadata
- `diagnostic_code`
- `warnings`

Azure Adapter 출력:

- `StandardOCRResult`

Azure Adapter 금지:

- Azure raw JSON 전체를 `StandardOCRResult`에 넣지 않습니다.
- Azure raw text 전체를 `StandardOCRResult`에 넣지 않습니다.
- Azure SDK response object를 Parser로 넘기지 않습니다.
- Azure endpoint 전체 URL을 넣지 않습니다.
- `operation_location` 전체 URL을 넣지 않습니다.
- API key, secret, token을 넣지 않습니다.
- 전체 로컬 절대경로를 넣지 않습니다.
- 실제 고객 파일이나 실제 민감정보를 fixture에 넣지 않습니다.
- `provider_fields`를 raw JSON 저장소로 사용하지 않습니다.

`provider_fields` 매핑 기준:

- 7주차-B에서 `StandardOCRResult`에 `provider_fields`를 선택 필드(`dict[str, Any]`, 기본값 빈 dict)로 추가했습니다.
- 7주차-B 구현 파일은 `app/ocr/adapters/azure_standard_adapter.py`이며, 기존 Azure Provider 운영 흐름에는 연결하지 않습니다.
- `provider_fields`는 Azure 전용 구조화 정보를 제한적으로 담는 dict입니다.
- `provider_fields`는 raw JSON 전체 저장소가 아닙니다.
- `provider_fields`는 Parser가 Azure raw 구조를 알게 만드는 통로가 아닙니다.
- `provider_fields`는 비민감 metadata와 adapter 진단 요약만 담습니다.

`provider_fields` 허용 예시:

```text
provider_family: azure
api_model: prebuilt-receipt 또는 document-intelligence
api_version: test 또는 비민감 버전 문자열
document_type: receipt
page_count: 1
has_key_value_pairs: true
has_tables: false
has_styles: false
locale_hint: ko-KR
adapter_version: azure-standard-adapter-v1
normalized_block_count: 12
normalized_candidate_count: 8
```

`provider_fields` 금지 예시:

```text
raw_response
raw_json
provider_raw_response
full_ocr_text
analyze_result 전체
read_result 전체
pages 전체 raw payload
lines 전체 raw payload
words 전체 raw payload
key_value_pairs 전체 raw payload
tables 전체 raw payload
endpoint 전체 URL
headers 전체
API key
operation_location 전체 URL
실제 파일 전체 경로
실제 고객 파일명
실제 민감정보 원문
```

Azure field mapping 기준:

- Azure page/line/word/block 구조는 `StandardOCRTextBlock`으로 정규화합니다.
- Azure document fields 또는 key-value 후보는 `StandardOCRKeyValueCandidate`로 정규화합니다.
- Azure table 구조는 필요 시 `StandardOCRTableCandidate`로 정규화합니다.
- Azure confidence는 0~1 범위 confidence로 정규화합니다.
- Azure bounding polygon은 `bbox`로 정규화하되 필수값으로 만들지 않습니다.
- Azure operation status 또는 polling 실패 정보는 `diagnostic_code`/`warnings`로 제한적으로 전달합니다.
- Azure raw text 전체가 아니라 Parser에 필요한 제한된 context line만 `text_blocks` 또는 `safe_text_summary`에 반영합니다.
- Azure SDK object의 원본 구조명은 Parser까지 전달하지 않습니다.

Azure `candidate_type` 매핑 예시:

```text
merchant_name
transaction_date
business_number
total_amount
gross_amount
discount_amount
final_amount
paid_amount
supply_amount
vat_amount
vat_missing
vat_review_hint
payment_method
approval_number
quantity
footer_number
sensitive_hint
```

금액 후보 분리:

- `total_amount`, `gross_amount`, `discount_amount`, `final_amount`, `paid_amount`, `supply_amount`, `vat_amount`는 amount candidate로 볼 수 있습니다.
- `quantity`, `approval_number`, `footer_number`, `business_number`는 amount candidate가 아닙니다.
- `vat_missing`, `vat_review_hint`는 명시 부가세가 아닙니다.
- 승인번호나 수량, 푸터 숫자가 금액으로 들어가지 않도록 Adapter 단계에서 `candidate_type`을 분리합니다.

Azure `diagnostic_code`/`warnings` 기준:

- polling timeout, 429, 5xx, invalid response, missing result 등은 `diagnostic_code` 또는 `warnings`에 비민감 코드로만 남깁니다.
- raw error body 전체를 남기지 않습니다.
- response headers 전체를 남기지 않습니다.
- `operation_location` 전체 URL을 남기지 않습니다.
- endpoint 전체 URL을 남기지 않습니다.

기존 Azure Provider와의 관계:

- 기존 Azure Provider는 7주차-A에서 변경하지 않습니다.
- 기존 Azure Provider가 `OCRResult`를 반환하는 흐름은 유지합니다.
- 7주차-B에서는 `AzureStandardOCRAdapter`를 별도 계층으로 만듭니다.
- 7주차-C에서 기존 Azure Provider와 Adapter의 연결 여부를 검토합니다.
- Parser 전환은 8주차에서 별도 작업으로 진행합니다.
- 기존 `OCRResult`/raw_text 경로는 즉시 제거하지 않습니다.

## 2. Core 모델

### ReceiptRecord

주요 필드:

```text
id
session_id
source_file_id
ocr_result_id
source_file_name
stored_relative_path
evidence_type
transaction_date
merchant_name
business_number
total_amount
gross_amount
discount_amount
final_amount
paid_amount
amount_source
amount_warnings
supply_amount
vat_amount
estimated_supply_amount
estimated_vat_amount
vat_source
vat_note
vat_warnings
vat_review_required
sensitive_text_detected
sensitive_text_categories
sensitive_warnings
payment_method
recommended_expense_category
recommended_expense_category_reason
expense_category
review_status
review_reason
review_reasons
card_match_status
confidence
parser_warnings
validation_warnings
validator_version
matched_card_transaction_id
card_match_score
card_match_reason
card_match_candidate_count
duplicate_group_id
duplicate_candidate_ids
duplicate_reason
approval_number
export_included
user_note
created_at
ocr_provider
```

`recommended_expense_category`는 시스템 추천값입니다. `expense_category`는 사용자가 검수 화면에서 확인하거나 수정한 최종 입력값입니다. 엑셀의 비용항목별 요약은 `expense_category` 기준입니다.

`total_amount`는 비용 기준 최종 결제금액입니다. 할인금액이 있는 영수증에서는 할인 전 금액(`gross_amount`), 할인/쿠폰/포인트 등 차감 금액(`discount_amount`), 할인 적용 후 결제대상금액(`final_amount`), 실제 받은금액/카드결제/현금결제 기준 금액(`paid_amount`)을 별도 필드로 보존합니다. `amount_source`는 `total_amount` 판단 기준이며, `amount_warnings`는 할인 감지, 할인 후 0원 결제, 금액 불일치 같은 검토 사유입니다. 할인 후 결제금액이 0원인 경우 `total_amount=0`이 가능하며 자동 제외하지 않습니다.

`final_amount`와 `paid_amount`가 함께 있는 경우 일반적으로 `paid_amount`를 우선하되, `결제금액 기준` 같은 설명 문구나 영수증 하단의 푸터 숫자처럼 실제 결제금액으로 보기 어려운 후보는 사용하지 않습니다. `paid_amount`가 `final_amount` 또는 `payment_target_amount`와 크게 어긋나면 `amount_warnings`에 검토 사유를 남기고 비용 기준 금액은 더 신뢰할 수 있는 최종/결제대상금액을 사용합니다.

`supply_amount`와 `vat_amount`는 영수증에 명시된 공급가액과 부가세만 저장합니다. 부가세가 명시되지 않은 경우 추정값을 `supply_amount` 또는 `vat_amount`에 넣지 않고, 참고용 추정 공급가액(`estimated_supply_amount`)과 참고용 추정 부가세(`estimated_vat_amount`)에 별도로 저장합니다. `vat_source`는 부가세 정보 출처, `vat_note`는 부가세 관련 설명, `vat_warnings`는 부가세 검토 사유, `vat_review_required`는 사용자 확인 필요 여부입니다. 추정값은 확정 세무 처리값이 아니라 사용자 확인이 필요한 참고값입니다.

`sensitive_text_detected`는 OCR 결과에서 민감문구 가능성이 감지되었는지 나타냅니다. `sensitive_text_categories`는 감지 유형 목록이며, `sensitive_warnings`는 민감문구 관련 검토 사유입니다. 실제 민감값은 DB, 엑셀, 화면에 저장하거나 표시하지 않고 category만 저장합니다. 사업자등록번호와 승인번호는 현재 업무상 필요한 필드일 수 있으므로 이번 단계에서 무조건 제거하지 않습니다.

### OCRResult

주요 필드:

```text
id
source_file_id
source_file_name
stored_relative_path
provider
raw_text
raw_json
confidence
status
diagnostic_code
error_message
created_at
```

`raw_text`와 `raw_json`은 파싱 내부 입력으로만 다루며, 전체 내용을 DB/엑셀/화면에 저장하거나 표시하지 않는 것을 원칙으로 합니다.

### CardTransaction

주요 필드:

```text
id
session_id
source_file_id
source_file_name
stored_relative_path
row_number
transaction_date
merchant_name
total_amount
card_name
approval_number
currency
parse_status
warning_messages
created_at
```

카드번호 전체나 카드 사용내역 원문 전체는 저장/표시하지 않습니다.

### CardParseResult

주요 필드:

```text
id
session_id
source_file_id
source_file_name
total_rows
parsed_rows
failed_rows
transactions
missing_required_columns
warning_messages
status
created_at
```

## 3. Enum

```text
OCRStatus: completed, failed, skipped
OCRProviderName: mock, azure
EvidenceType: receipt_image, receipt_pdf, ocr_text, manual
ReviewStatus: pending, needs_review, approved, rejected, excluded
CardMatchStatus: unmatched, matched, candidate, mismatch, needs_review
CardParseStatus: parsed, needs_review, failed
CardParseResultStatus: completed, completed_with_warnings, failed
```

## 4. 처리 이력 DB

SQLite를 사용하며 기본 경로는 `data/app.db`입니다. DB 파일은 Git에 올리지 않습니다.

### processing_jobs

```text
id
session_id
status
created_at
updated_at
receipt_count
card_transaction_count
needs_review_count
excluded_count
total_amount
export_file_name
export_relative_path
note
```

### uploaded_files

```text
id
job_id
session_id
original_file_name
stored_file_name
stored_relative_path
file_extension
file_size_bytes
file_role
created_at
```

### receipt_records

```text
id
job_id
session_id
source_file_id
ocr_result_id
source_file_name
transaction_date
merchant_name
business_number
total_amount
gross_amount
discount_amount
final_amount
paid_amount
amount_source
amount_warnings_json
supply_amount
vat_amount
estimated_supply_amount
estimated_vat_amount
vat_source
vat_note
vat_warnings_json
vat_review_required
sensitive_text_detected
sensitive_text_categories_json
sensitive_warnings_json
payment_method
recommended_expense_category
expense_category
review_status
review_reasons_json
validation_warnings_json
parser_warnings_json
card_match_status
card_match_reason
card_match_score
duplicate_suspected
memo
created_at
updated_at
```

### card_transactions

```text
id
job_id
session_id
source_file_id
source_file_name
transaction_date
merchant_name
total_amount
card_name
approval_number
currency
parse_status
warning_messages_json
created_at
```

### export_files

```text
id
job_id
session_id
export_file_name
export_relative_path
file_size_bytes
created_at
```

DB에는 OCR 원문 전체, raw JSON 전체, 카드 사용내역 원문 전체, 전체 로컬 절대경로를 저장하지 않습니다. Excel 파일 bytes는 DB에 저장하지 않고 `OUTPUT_DIR` 하위 파일로 저장한 뒤 상대경로만 저장합니다.

## 5. Excel 산출물

파일명:

```text
receipt_summary_YYYYMMDD_HHMMSS.xlsx
```

시트 구성:

| 순서 | 의미 |
|---|---|
| 01 | 정리내역 |
| 02 | 월별요약 |
| 03 | 비용항목별요약 |
| 04 | 검토필요 |
| 05 | 카드대조 |
| 06 | 원본파일목록 |
| 07 | 처리로그 |
| 08 | 제외내역 |

`07` 시트는 OCR 원문 전체나 provider raw JSON 전체를 넣지 않고, 처리 단계와 상태, 짧은 메시지만 기록합니다.

`01 정리내역`은 기존 총금액 컬럼을 유지하면서 할인전금액, 할인금액, 최종결제금액, 실제결제금액, 금액판단기준, 금액검토사유를 함께 표시합니다. 공급가액과 부가세는 영수증 명시값 기준이며, 참고 추정값은 추정공급가액과 추정부가세 컬럼으로 분리합니다. 민감문구가 감지된 경우에는 감지 여부와 category만 표시하고 실제 값은 표시하지 않습니다.

`02 월별요약`과 `03 비용항목별요약`은 `total_amount` 기준으로 합계를 계산합니다. 추정부가세는 명시 부가세 합계에 자동으로 합산하지 않습니다.

## 6. 검수 상태와 제외 처리

- `needs_review`, `pending`은 검수 필요로 표시합니다.
- `approved`는 확인완료로 표시할 수 있습니다.
- `excluded` 또는 `export_included=False`는 정리내역에서 제외하고 제외내역 시트에 따로 기록합니다.
- 제외 데이터는 삭제하지 않습니다.

## 7. 처리 이력 화면

- 목록 화면은 최근 작업 50건을 최신순으로 표시합니다.
- 상세 화면은 job 요약, ReceiptRecord 요약, CardTransaction 요약, ExportFile 목록을 읽기 전용으로 표시합니다.
- 과거 엑셀 재다운로드는 기존 `OUTPUT_DIR` 하위 파일만 허용합니다.
- 과거 작업 재검수와 엑셀 재생성은 구현하지 않습니다.

## 8. 설정 화면

설정 화면은 읽기 전용입니다.

표시 항목:

- OCR provider와 Azure 설정 여부
- 보관기간과 cleanup dry-run 기본값
- 업로드/출력 저장소 파일 수와 용량
- DB 접근 가능 여부, 처리 이력 건수, 최근 처리일시
- 처리 이력 연결 상태
- cleanup dry-run 요약

표시하지 않는 항목:

- API key
- endpoint 전체 URL
- `.env` 내용
- 전체 로컬 절대경로
- 파일명 목록
- OCR 원문 전체
- raw JSON 전체
- 카드 사용내역 원문 전체

## 9. 보안/개인정보 기준

1. 원본 파일 전체 경로를 화면, DB, 엑셀에 노출하지 않습니다.
2. OCR 원문 전체를 로그, DB, 엑셀, 화면에 남기지 않습니다.
3. Provider raw JSON 전체를 로그, DB, 엑셀, 화면에 남기지 않습니다.
4. API key와 secret은 코드에 하드코딩하지 않습니다.
5. `.env`, `data/uploads`, `data/outputs`, `output`, `data/app.db`, `*.db`는 Git에 올리지 않습니다.
6. 테스트 데이터에는 실제 고객 파일이나 실제 민감정보를 넣지 않습니다.
7. WiFi PW, 비밀번호, 카드번호 전체 등 민감문구 가능성이 감지되면 실제 값이 아니라 category와 검토 사유만 저장합니다.

## 10. Azure OCR Parser 입력 기준

Azure OCR provider는 provider raw JSON 전체나 OCR 원문 전체를 화면, DB, 엑셀에 저장하지 않습니다. Parser 입력에는 문서 필드 요약과 제한된 context line만 전달합니다.

Parser 입력용 context line에는 금액 판단과 기본 식별에 필요한 라인만 포함합니다. 예를 들어 사업자번호, 전화/TEL, 상호/가맹점명, 총매출액, 상품금액, 할인금액, 합계금액, 받은금액, 결제대상금액, 카드결제, 현금결제, 쿠폰/포인트/멤버십 관련 라인이 해당됩니다.

WiFi PW, 비밀번호, token, secret, 카드번호 전체, 주민번호 형식 등 민감문구 가능성이 있는 라인은 실제 값을 저장하거나 표시하지 않습니다. 사업자등록번호와 승인번호는 업무상 필요한 필드일 수 있으므로 무조건 제거하지 않되, 승인번호나 수량 숫자가 금액 후보로 잘못 사용되지 않도록 Parser에서 필터링합니다.

## Week 8-B Parser Entry Implementation Note

- `ReceiptParser.parse_standard_context(context: StandardOCRParserContext, ...) -> ReceiptRecord` is the standard context entry added for 8-B.
- `ReceiptParser.parse_from_standard_ocr(result: StandardOCRResult, ...) -> ReceiptRecord` is a wrapper that first builds `StandardOCRParserContext`.
- Both entries return the existing `ReceiptRecord` shape and do not change `OCRResult`, the legacy `parse(...)` entry, Excel output, UI, or Processing History.
- The new entries are not wired into Streamlit, AzureProvider, MockProvider, or provider selection.
- Parser input remains limited to `safe_text_lines`, candidate maps, review hints, sensitive categories, status, provider, and diagnostic code. Provider raw response, raw JSON, full OCR text, endpoint, operation location, API key, and absolute local paths are not parser inputs.
- Amount candidates are read only from `amount_candidate_map`; `quantity`, `approval_number`, `footer_number`, and `business_number` remain non-amount candidates.
- `vat_missing` and `vat_review_hint` mark review hints and are not explicit `vat_amount` values.

## PaddleOCR Local Provider Contract

Purpose:
PaddleOCR is the first PC Local OCR Runtime candidate for reducing long-term Azure cost dependency. Week 9 is a local OCR PoC contract phase and does not make PaddleOCR a default or required runtime.

Target flow:

```text
image file
-> PaddleOCRProvider
-> PaddleOCR raw output
-> PaddleStandardOCRAdapter
-> StandardOCRResult
-> StandardOCRParserContext
-> ReceiptParser
-> ReceiptRecord
-> ReceiptValidator / CategoryRules / CardMatcher
-> ExcelExporter / Processing History
```

Core rules:

- `PaddleOCRProvider` must ultimately return `StandardOCRResult`.
- `ReceiptParser` must not receive PaddleOCR raw output.
- `ReceiptValidator`, `CategoryRules`, `CardMatcher`, and `ExcelExporter` must not receive PaddleOCR raw output.
- PaddleOCR raw output, full OCR raw text, full local absolute paths, actual customer files, and actual sensitive values must not be stored in DB, Excel, UI, logs, fixtures, or test output.
- `provider_fields` is a non-sensitive metadata area, not a raw output store.
- The default provider is not changed by this contract.

PaddleOCRProvider input:

- image file path or safe file reference
- `source_file_id`
- `source_file_name`
- provider metadata
- optional runtime config

Input limits:

- `source_file_name` is file-name only.
- Full local absolute paths are not placed into `StandardOCRResult`.
- PDF input is out of scope for the Week 9 image-first PoC.
- PDF page image conversion, multi-page handling, and local runtime packaging are follow-up work.

PaddleOCRProvider output:

- `StandardOCRResult`

PaddleOCRProvider responsibilities:

- Lazy import `paddleocr` only when the provider is instantiated or executed.
- If PaddleOCR is not installed, return a clear failed/skipped result or configuration error without breaking default pytest.
- Run OCR only for image-file PoC scope.
- Convert PaddleOCR raw output through `PaddleStandardOCRAdapter`.
- Do not return or persist the full raw output.
- Keep actual OCR execution tests opt-in.

PaddleStandardOCRAdapter responsibilities:

- Convert PaddleOCR-like output to `StandardOCRTextBlock`.
- Normalize PaddleOCR confidence into the 0 to 1 range.
- Normalize PaddleOCR bbox/polygon into `StandardOCRTextBlock.bbox` when available.
- Create `key_value_candidates` only from safe, limited candidate hints.
- Provide only limited parser-safe text lines.
- Store only non-sensitive count/flag metadata in `provider_fields`.

Allowed `provider_fields` examples:

```text
provider_family: paddleocr
engine: paddleocr
engine_runtime: pc_local
adapter_version: paddle-standard-adapter-v1
language_hint: ko
page_count: 1
normalized_block_count: 12
normalized_candidate_count: 5
has_angle_classifier: true/false
has_gpu: true/false
image_count: 1
```

Forbidden `provider_fields` examples:

```text
raw_response
raw_json
provider_raw_response
full_ocr_text
paddle_raw_output
image_path
absolute_path
full model path
headers
endpoint
api_key
actual full file path
actual customer file name
actual sensitive value
```

Supported Week 9 PoC scope:

- JPG/JPEG/PNG image-first PoC.
- PDF handling is deferred.
- Mobile OCR and Tauri/Electron/Desktop packaging are deferred.
- The default `python -m pytest` suite must pass without PaddleOCR installed.

Missing PaddleOCR handling:

- Import failure must not happen at module import time.
- Missing installation should produce a non-sensitive diagnostic such as `paddle_not_installed`, `paddle_import_failed`, `paddle_runtime_error`, or `paddle_no_text_detected`.
- Failure messages must not include raw traceback, full local paths, environment details, endpoint, key, token, or secret values.

Week 9-B adapter implementation note:

- `app/ocr/adapters/paddle_standard_adapter.py` defines `PaddleStandardOCRAdapter` for sanitized PaddleOCR-like mapping input only.
- The adapter returns `StandardOCRResult` with `provider="paddleocr"`, `engine_runtime="pc_local"`, and `provider_fields.provider_family="paddleocr"`.
- `provider_fields` is limited to non-sensitive metadata such as engine, runtime, adapter version, language hint, image/page counts, normalized block/candidate/table counts, and runtime flags.
- Sanitized fixture tests cover regular, edge, and empty/failed image-style results without actual PaddleOCR import, actual OCR execution, PDF handling, image files, full raw output, full OCR text, or full local paths.
- `OCR_PROVIDER=paddle` remains a 9주차-C provider factory candidate; 9주차-B does not add `PaddleOCRProvider` or change the default provider.
## Week 9-C PaddleOCRProvider Candidate Implementation Note

- `PaddleOCRProvider` lives in `app/ocr/paddle_provider.py`.
- The provider name used in `StandardOCRResult.provider` is `paddleocr`; the environment/provider factory candidate is `OCR_PROVIDER=paddle`, with `paddleocr` as an alias.
- `PaddleOCRProvider.extract(...)` returns `StandardOCRResult` and uses `PaddleStandardOCRAdapter`; it does not return `OCRResult` and does not pass PaddleOCR raw output to Parser or downstream layers.
- `paddleocr` is not imported at module top level. The package is loaded only from a private lazy import path at execution time.
- If `paddleocr` is not installed, `extract(...)` returns a failed `StandardOCRResult` with `diagnostic_code="paddle_not_installed"` or a related non-sensitive code.
- PDF input is explicitly unsupported/deferred in this step and returns a failed result with `diagnostic_code="paddle_pdf_not_supported"`; no PDF image conversion dependency is introduced.
- Provider output must not contain raw output, full OCR text, model path, image path, absolute local path, endpoint, API key, secret, token, or raw traceback.
- 9-D opt-in smoke tests should validate real image OCR through `StandardOCRResult`, not PaddleOCR raw output.

## Week 9-D PaddleOCR Smoke Test Contract

- The smoke test is an execution-path check, not an OCR quality evaluation.
- The smoke test is opt-in and must be skipped by default pytest unless `RUN_PADDLEOCR_TESTS` is explicitly enabled.
- The smoke test receives a local image via `PADDLEOCR_TEST_IMAGE_PATH`; the repository must not include real customer images.
- The test validates that `PaddleOCRProvider` returns `StandardOCRResult` with `engine_runtime="pc_local"` and non-sensitive `provider_fields`.
- The result must be convertible to `StandardOCRParserContext`.
- `ReceiptParser.parse_standard_context` may be called to confirm the standard parser entry accepts the context, but parsed field accuracy is left to 10-week quality comparison.
- PDF input remains `paddle_pdf_not_supported` or equivalent unsupported/deferred status.
- Smoke test failure categories are environment failure, provider failure, security failure, and quality failure.
- Local runtime packaging and PDF image conversion remain follow-up work.

## Week 10-A Azure vs PaddleOCR Quality Comparison Contract

10주차 품질 비교는 Provider별 raw output이 아니라 표준 계층의 결과를 비교합니다.

Comparison flow:

```text
Azure/PaddleOCR Provider execution
-> StandardOCRResult
-> StandardOCRParserContext
-> ReceiptParser.parse_standard_context()
-> ReceiptRecord
-> quality comparison summary
```

Comparison inputs:

- `StandardOCRResult.status`, `diagnostic_code`, `warnings`, `confidence`
- `StandardOCRResult.text_blocks` count and `key_value_candidates` count
- `StandardOCRParserContext.amount_candidate_map` and `non_amount_candidate_map`
- `StandardOCRParserContext.review_hints` and `sensitive_categories`
- existing `ReceiptRecord` core fields

Expected fixture strategy:

- Expected fixtures are comparison baselines, not full truth objects.
- Expected fixtures focus on core `ReceiptRecord` fields rather than provider raw output.
- Same safe `sample_id` can connect Azure result, PaddleOCR result, and expected core fields.
- Fixtures must use synthetic or non-sensitive sample data only.
- Fixtures must not contain full OCR raw text, raw JSON, full local absolute paths, actual customer files, secrets, or raw tracebacks.
- PDF PaddleOCR expected fixtures are deferred.

Core `ReceiptRecord` comparison fields:

```text
merchant_name
transaction_date
business_number
total_amount
gross_amount
discount_amount
final_amount
paid_amount
supply_amount
vat_amount
estimated_supply_amount
estimated_vat_amount
vat_review_required
payment_method
approval_number
review_status
review_reasons
parser_warnings
validation_warnings
confidence
ocr_provider
```

Security rules:

- Provider raw JSON 전체를 비교 리포트, fixture, DB, 화면, 로그에 저장하지 않습니다.
- OCR raw text 전체를 비교 리포트, fixture, DB, 화면, 로그에 저장하지 않습니다.
- 전체 로컬 절대경로, Azure endpoint 전체 URL, `operation_location` 전체 URL, API key, secret, token을 저장하지 않습니다.
- `provider_fields`는 count/flag metadata와 adapter diagnostic summary로만 사용하고 Parser context나 report detail로 그대로 복사하지 않습니다.
- 샘플은 합성 또는 비민감 테스트 이미지 중심이며, 실제 고객 파일은 사용하지 않습니다.

Initial report row fields:

```text
sample_id
source_file_name
provider
provider_status
diagnostic_code
ocr_elapsed_ms
standard_text_block_count
standard_candidate_count
parser_review_hint_count
sensitive_category_count
low_confidence_line_count
merchant_name
transaction_date
business_number_present
total_amount
vat_amount_present
payment_method
approval_number_present
review_status
review_reason_count
field_match_score
fallback_candidate_reason
```

Initial Azure fallback candidate signals:

- PaddleOCR execution fails, is skipped, or returns partial output.
- PaddleOCR diagnostic code indicates missing runtime, runtime error, no text detected, or unsupported input.
- `transaction_date`, `merchant_name`, `total_amount` 중 2개 이상이 비어 있습니다.
- amount candidate separation fails or amount candidates are missing.
- VAT review hints or sensitive category hints make manual review likely.
- Low-confidence line ratio is high enough to make manual review likely.
- Average local runtime duration or environment failure rate exceeds the pilot threshold.

Fallback signals are review/reprocessing candidates only. They are not tax conclusions and do not change the rule that OCR result, expense category recommendation, and evidence type estimation require user review.
## Week 10-B Safe OCR Preview Contract

The safe OCR preview is a UI/helper feature built from `StandardOCRResult.text_blocks` only. It is intended to let a reviewer inspect a limited, sanitized sample of OCR lines after a PaddleOCR smoke run and to prepare a provider-neutral shape that Azure adapter output can reuse later.

Preview row fields:

```text
line_order
page_index
block_id
text
confidence
confidence_label
is_low_confidence
sensitive_category
is_redacted
```

Preview summary fields:

```text
provider
status
diagnostic_code
source_file_name
text_block_count
preview_line_count
low_confidence_line_count
redacted_line_count
max_lines
low_confidence_threshold
```

Rules:

- Display only the top N safe preview rows.
- Display confidence labels and low-confidence flags without exposing provider raw output.
- Keep sensitive lines as `[REDACTED]`; category labels may be shown only as safe category names.
- Store and display file names only, never full local absolute paths.
- Do not provide raw text download, raw JSON display, raw provider output display, or full OCR text display.
- Do not change `ReceiptRecord`, ExcelExporter sheets/columns, Processing History DB schema, provider defaults, or Parser raw-input boundaries.
- Do not implement side-by-side comparison, statistics aggregation, `field_match_score`, Azure fallback automation, or PDF PaddleOCR handling in 10-B.
## Week 10-C Side-by-side Comparison Report Contract

The Azure vs PaddleOCR comparison report is a diagnostic-only settings flow for one explicitly uploaded, non-sensitive image sample. It does not alter default OCR provider selection, Excel export output, or Processing History storage.

Comparison input must be provider-normalized before parsing:

`Provider execution -> StandardOCRResult -> StandardOCRParserContext -> ReceiptParser.parse_standard_context() -> ReceiptRecord -> side-by-side comparison report`

The report may show these per-provider, per-sample metrics for future Week 10-D reuse: provider status, diagnostic code, elapsed milliseconds, text block count, key-value candidate count, table candidate count, parser safe line count, parser review hint count, sensitive category count, warning count, full text-block low-confidence count, full text-block redacted count, review status, review reason count, parser warning count, and validation warning count.

Provider failure diagnostics may include a safe `diagnostic_detail_code` such as `quota_or_rate_limit`, `credential_or_permission`, `region_or_endpoint`, or `non_json_error`. This detail code must be derived from status/error shape only and must not include raw Azure error messages, endpoint URLs, operation URLs, keys, request IDs, raw tracebacks, or raw provider payloads.

The report may show field equality flags for the core `ReceiptRecord` fields defined in the Week 10-A contract. Week 10-C does not define or compute a formal `field_match_score`; it only leaves `azure_present`, `paddle_present`, and `is_same` per field for Week 10-D aggregation.

The report must not display or persist provider raw output, full OCR text, raw JSON, full local paths, Azure endpoint URLs, operation URLs, secrets, raw tracebacks, customer files, or raw fixtures. Parser input remains `StandardOCRParserContext`; provider raw response objects are never passed to `ReceiptParser`.

## Week 10-D-prep Synthetic PaddleOCR Quality Fixture Contract

Synthetic PaddleOCR quality fixtures are safe standard-layer test inputs used when
live Azure comparison is unavailable or unstable. They are not PaddleOCR provider
raw output and are not full OCR text dumps.

Fixture input contract:

- Each case has `sample_id`, `description`, `source_file_name`, `paddle_lines`,
  `expected`, and optional `risk_tags`.
- `source_file_name` must use a `synthetic_` prefix and must be a file name only.
- `paddle_lines` are sanitized line rows with `text`, `confidence`, and optional
  `sensitive_category`.
- Sensitive cases use `[REDACTED]` plus safe category names only.
- Forbidden keys include `raw_text`, `raw_json`, `raw_response`,
  `provider_raw_response`, `full_ocr_text`, and `paddle_raw_output`.

Expected output contract:

- Expected values are selected core `ReceiptRecord` fields, not accounting or tax
  conclusions.
- Only fields explicitly present in `expected` are compared.
- `vat_amount: null` means no explicit VAT value may be written into
  `ReceiptRecord.vat_amount`; estimated VAT remains a review-only reference.
- Approval numbers, quantities, footer numbers, identifiers, and redacted lines
  must not become amount fields.
- The parser remains conservative: no unlabeled first-line merchant guessing and
  no unlabeled maximum-amount total guessing.

## New Job Runtime OCR Provider Selection Contract

The New Job screen supports a per-run OCR provider selector. The selector may
offer `PaddleOCR Local` as an explicit runtime override, but the configured
default provider remains unchanged unless environment configuration changes it.

Runtime provider parsing contract:

```text
Mock/Azure OCRResult -> ReceiptParser.parse(...) -> ReceiptRecord
PaddleOCR StandardOCRResult -> StandardOCRParserContext -> ReceiptParser.parse_standard_context(...) -> ReceiptRecord
```

The PaddleOCR runtime path must not pass PaddleOCR raw output, provider raw
response objects, raw JSON, full OCR text, full local paths, secrets, endpoint
URLs, operation URLs, or raw tracebacks to `ReceiptParser`, `ReceiptValidator`,
`CategoryRules`, `CardMatcher`, `ExcelExporter`, Processing History, logs, tests,
or UI. Source file names must be reduced to file names before being copied into
OCR or receipt records.

PaddleOCR PDF handling remains unsupported/deferred in this runtime selection
flow. This contract does not change Excel export sheets/columns, Processing
History schema, default provider behavior, automatic fallback behavior, or
formal quality scoring.

## Review UI Receipt Source Preview Contract

The review screen may show a selected receipt source preview to help manual
verification. The preview is driven by the selected review row, not by provider
raw output.

Review table display fields:

```text
검토우선순위
누락필드
검토사유요약
원본파일명
원본보기
```

Priority values:

- `HIGH`: missing `transaction_date`, `merchant_name`, or `total_amount`; amount
  or VAT review reason exists; sensitive text is detected; or card match status
  is `needs_review`, `candidate`, or `mismatch`.
- `MEDIUM`: recommended category is uncategorized or review status is `pending`.
- `LOW`: review status is `approved` and no major review reason exists.

Source preview rules:

- Resolve files only from `stored_relative_path` under the configured upload
  root and upload relative root.
- Block absolute paths, traversal paths, and paths outside `data/uploads`.
- Show JPG/JPEG/PNG with `st.image`.
- Show a PDF notice for PDF files instead of forcing rendering.
- Display file names only, never full local paths.
- Do not display OCR raw text, provider raw JSON, provider raw output, sensitive
  raw values, secrets, endpoint URLs, or raw tracebacks.

The preview contract does not change review editing, exclusion handling,
ExcelExporter output, Processing History schema, default provider behavior,
automatic fallback, formal scoring, mobile/PWA behavior, OCR provider behavior,
or PaddleOCR accuracy rules.

## 12. Merchant candidate dictionary

Merchant dictionary data is a review-candidate aid. It must not be treated as a
confirmed national merchant or business-number database.

SQLite tables:

```text
merchant_master
- id TEXT PRIMARY KEY
- merchant_name TEXT NOT NULL
- normalized_merchant_name TEXT NOT NULL
- business_number TEXT NULL
- branch_name TEXT NULL
- area_hint TEXT NULL
- category_large TEXT NULL
- category_medium TEXT NULL
- category_small TEXT NULL
- road_name TEXT NULL
- building_main_number TEXT NULL
- building_sub_number TEXT NULL
- building_name TEXT NULL
- road_address TEXT NULL
- normalized_road_address TEXT NULL
- source TEXT NOT NULL
- source_row_hash TEXT NOT NULL
- source_batch_id TEXT NOT NULL
- review_required INTEGER NOT NULL DEFAULT 1
- created_at TEXT NOT NULL
- updated_at TEXT NOT NULL

merchant_alias
- id TEXT PRIMARY KEY
- merchant_master_id TEXT NULL
- alias_name TEXT NOT NULL
- normalized_alias_name TEXT NOT NULL
- business_number TEXT NULL
- source TEXT NOT NULL
- created_at TEXT NOT NULL

merchant_source_log
- id TEXT PRIMARY KEY
- source_name TEXT NOT NULL
- source_file_name TEXT NULL
- source_file_hash TEXT NULL
- source_batch_id TEXT NOT NULL
- imported_row_count INTEGER NOT NULL DEFAULT 0
- skipped_row_count INTEGER NOT NULL DEFAULT 0
- duplicate_file INTEGER NOT NULL DEFAULT 0
- note TEXT NULL
- created_at TEXT NOT NULL
```

CSV import stores only merchant name, branch name, category names, road name,
building main/sub number, building name, road address, source row hash, allowed
column file hash, and import batch id. It must not store representative names,
phone raw values, full OCR text, provider raw JSON, raw source rows, or full
local paths.

Import result summary:

```text
source_file_name
source_batch_id
scanned_row_count
imported_row_count
skipped_row_count
skipped_duplicate_row_count
skipped_invalid_row_count
duplicate_file
elapsed_seconds
rows_per_second
```

This summary is for CLI/UI diagnostics only. It must show file names only, not
full local paths, raw CSV rows, representative names, phone raw values, or
blocked columns.

Candidate DTO:

```text
candidate_merchant_name
candidate_business_number
score
match_type
source
review_required=True
address_summary
```

Matching priority:

1. Business-number exact match, score 100.
2. Alias exact/fuzzy matches before master name matches.
3. Master exact match score 90.
4. Fuzzy name candidates above the configured threshold, default 72.
5. If an OCR address hint is available, road-name/building-number or normalized
   road-address matches may boost the candidate score. Address hints never
   confirm a candidate by themselves.
6. If merchant name and business number are missing but a structured road-name
   and building-number hint exactly matches `merchant_master`, the matcher may
   return low-score address-only review candidates. These candidates are hints
   only and remain below the fuzzy-name confirmation threshold.

Candidates do not automatically overwrite `ReceiptRecord.merchant_name`,
`business_number`, or `review_status`. ExcelExporter sheets and columns remain
unchanged, and candidate details are not exported.

OCR address hints are extracted only from safe parser lines and may contain
`road_address_hint`, `road_name`, `building_main_number`, and
`building_sub_number`. They are transient review-candidate scoring inputs, not
`ReceiptRecord` fields. Full OCR raw text, provider raw JSON, phone lines,
representative lines, business-number lines, approval/card identifiers, dates,
and amount lines must not become address hints.

NTS business status lookup reads `NTS_BUSINESS_API_KEY` from `.env`. It is
limited to OCR-detected business numbers and stores/displays only safe summary
fields: normalized business number, status category, tax type category, closed
date if present, and diagnostic code. It is not a mass collection or tax
judgment feature.

Review alias learning:

- Reviewed merchant names may be added to `merchant_alias` with `source=review`
  when the user creates the reviewed Excel output.
- If the original parsed merchant name differs from the reviewed merchant name,
  the original parsed merchant name may also be added as an alias.
- Alias rows store only `alias_name`, `normalized_alias_name`,
  nullable `merchant_master_id`, nullable normalized `business_number`,
  `source`, and timestamps.
- Empty names, too-short names, mostly numeric/symbolic values, business-number
  patterns, phone-number patterns, representative/owner labels, amount lines,
  date lines, card identifiers, and approval identifiers are not stored.
- Duplicate `normalized_alias_name + business_number + source` combinations are
  skipped.
- Alias rows improve future candidate ranking only. They do not automatically
  confirm or overwrite `ReceiptRecord` fields, ExcelExporter output, or
  Processing History receipt rows.

Merchant diagnostics:

- Merchant dictionary diagnostics are read-only operator helpers.
- Dictionary summary may show merchant master count, alias count, import batch
  count, duplicate file count, latest import date, latest source file name, top
  category counts, and recent import batch summaries.
- Candidate diagnostic output may show candidate merchant name, masked business
  number, business-number presence flag, score, match type, source,
  `review_required`, and safe address summary.
- Business numbers are masked as `123-**-*****`.
- Saved ReceiptRecord diagnostics may use only `merchant_name`,
  `business_number`, `source_file_name`, and `review_status`.
- Saved-record diagnostic output is aggregate-first: candidate present/missing
  counts, exact/fuzzy/alias match counts, score buckets, and review-required
  count.
- Diagnostics must not include raw OCR text, provider raw JSON, full local
  paths, representative names, phone raw values, API keys, or raw CSV rows.
- Diagnostics never update `ReceiptRecord`, ExcelExporter sheets/columns,
  Processing History schema, or review status.
## Merchant Dictionary Search and Short Candidate Scoring

Merchant dictionary search is an operator-only Settings helper. It may query
`merchant_master` by merchant-name prefix or by road-name plus building number.
It returns safe summaries only and must not change `ReceiptRecord`, ExcelExporter
sheets/columns, Processing History schema, or review status.

Search output contract:

```text
merchant_name
branch_name
category
road_name
building_number
road_hint
business_number_present
source
source_batch_id
query_elapsed_ms
result_count
limit
```

Search output must not include full local paths, raw CSV rows, full road-address
payload dumps, raw OCR text, provider raw JSON, representative names, phone raw
values, API keys, raw tracebacks, or full business numbers.

Fuzzy candidate scoring keeps business-number exact and alias priority rules.
Very short substring matches, such as a two- or three-character public merchant
name inside a longer OCR merchant name, stay below the default fuzzy threshold
unless an address hint safely boosts the candidate. Address support remains a
review hint only and never auto-confirms a merchant.

Quality stabilization diagnostics:

- Real PaddleOCR sample checks are manual/opt-in and must not run in default
  pytest.
- Sample reports compare visual receipt fields against current parser output
  using safe summaries only.
- Processing History safety diagnostics are read-only and count forbidden
  columns/path-like values without showing the values themselves.
- Review performance summaries may show dataframe generation time, merchant
  candidate lookup time, cache hit/miss counts, preview preparation time, and
  merchant DB search query time.
- These diagnostics never change `ReceiptRecord`, ExcelExporter sheets/columns,
  Processing History schema, merchant candidates, NTS behavior, or OpenAI
  behavior.

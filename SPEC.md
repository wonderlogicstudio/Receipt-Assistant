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
supply_amount
vat_amount
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
supply_amount
vat_amount
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

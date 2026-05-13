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

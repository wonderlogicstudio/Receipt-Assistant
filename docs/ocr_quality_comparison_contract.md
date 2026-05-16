# Azure vs PaddleOCR Quality Comparison Contract

## Purpose

10주차 품질 비교는 Azure와 PaddleOCR 중 어느 Provider를 기본 처리, 재처리, fallback 후보로 둘지 판단하기 위한 기준선입니다.

이 문서는 10주차-A 계약 단계의 산출물입니다. 이후 10주차-B 안전한 OCR 미리보기와 10주차-C per-sample side-by-side 비교 리포트가 이 계약을 기준으로 구현되었습니다. 통계 요약, formal `field_match_score`, 자동 fallback 동작은 아직 10주차-D 범위로 남겨둡니다.

## Scope

10주차 비교는 같은 비민감 영수증 샘플을 두 Provider로 처리한 뒤 다음 표준 계층에서만 비교합니다.

```text
Provider execution
-> StandardOCRResult
-> StandardOCRParserContext
-> ReceiptParser.parse_standard_context()
-> ReceiptRecord
-> quality comparison summary
```

Provider raw output, full OCR raw text, full local absolute paths, actual customer files, API keys, endpoints, tokens, and raw tracebacks are not comparison inputs.

## Sample Set Rules

- 샘플은 합성 데이터 또는 비민감 테스트 영수증만 사용합니다.
- 실제 고객 파일, 실제 카드번호 전체, 주민번호, 전화번호, 비밀번호, WiFi PW가 포함된 이미지는 사용하지 않습니다.
- 리포트에는 파일명만 남기고 전체 로컬 절대경로는 남기지 않습니다.
- PDF PaddleOCR 처리는 아직 deferred 상태이므로 10주차-A 기준 비교 샘플은 JPG/JPEG/PNG 이미지 중심입니다.
- 동일 샘플은 Azure와 PaddleOCR 모두 같은 `source_file_id` 또는 안전한 sample id로 묶습니다.

## Expected Fixture Strategy

10주차 expected fixture는 Provider raw output fixture가 아니라 비교 기준선입니다.

- 실제 고객 파일, 실제 OCR raw output, 실제 Azure raw JSON, 실제 PaddleOCR raw output을 fixture로 커밋하지 않습니다.
- fixture sample은 합성 또는 비민감 샘플만 사용합니다.
- 같은 `sample_id` 아래에 Azure 결과, PaddleOCR 결과, expected 핵심 필드를 연결할 수 있게 설계합니다.
- expected 값은 `ReceiptRecord` 핵심 필드 중심으로 둡니다.
- expected fixture는 “완벽한 정답”이 아니라 Provider별 품질과 Parser 결과를 비교하기 위한 기준선입니다.
- expected fixture에는 파일명만 저장하고 전체 로컬 절대경로를 저장하지 않습니다.
- expected fixture에는 OCR raw text 전체가 아니라 필요한 경우 제한된 `StandardOCRResult`/`StandardOCRParserContext` 요약만 둡니다.
- PDF PaddleOCR expected fixture는 이번 단계에서 만들지 않고 deferred로 둡니다.
- expected fixture 추가는 10주차-C/D 구현 또는 테스트 단계에서 별도 작업으로 진행합니다.

## Comparison Input Contract

각 Provider 실행 결과는 다음 조건을 만족해야 비교 대상이 됩니다.

- `StandardOCRResult.provider`는 `azure` 또는 `paddleocr`입니다.
- `StandardOCRResult.status`, `diagnostic_code`, `warnings`, `confidence`, `provider_fields`는 비민감 값만 포함합니다.
- `StandardOCRResult.text_blocks`, `key_value_candidates`, `table_candidates`는 count와 제한된 표준 필드만 비교합니다.
- `StandardOCRParserContext`는 `safe_text_lines`, `candidate_map`, `amount_candidate_map`, `non_amount_candidate_map`, `review_hints`, `sensitive_categories`만 비교에 사용합니다.
- `ReceiptRecord` 비교는 `ReceiptParser.parse_standard_context()` 결과를 사용하며 기존 모델 필드를 유지합니다.
- ExcelExporter나 Processing History schema를 바꾸지 않습니다.
- `provider_fields`는 count/flag metadata로만 취급하며 Parser context나 리포트 상세값으로 그대로 복사하지 않습니다.

## Core Field Metrics

Provider별 품질 비교의 핵심 필드는 다음입니다.

| 영역 | 비교 필드 |
|---|---|
| 기본 인식 | `merchant_name`, `transaction_date`, `business_number` |
| 금액 | `total_amount`, `gross_amount`, `discount_amount`, `final_amount`, `paid_amount` |
| 부가세 | `supply_amount`, `vat_amount`, `estimated_supply_amount`, `estimated_vat_amount`, `vat_review_required` |
| 결제 | `payment_method`, `approval_number` |
| 검수 | `review_status`, `review_reasons`, `parser_warnings`, `validation_warnings` |
| OCR 상태 | `status`, `diagnostic_code`, `warnings`, `confidence` |
| Parser context | amount/non-amount candidate separation, review hint count, sensitive category count |

품질 비교는 “정답 확정”이 아니라 검수 필요도를 낮추는지 확인하는 보조 기준입니다. 비용항목은 계속 추천이고, 증빙유형은 계속 추정입니다.

## Report Row Contract

10주차-C side-by-side 리포트의 최소 행 단위 계약은 다음입니다.

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

`source_file_name`은 파일명만 허용합니다. `ocr_elapsed_ms`는 Provider 실행 시간만 기록하고, Azure 비용과 PaddleOCR 설치 난이도 또는 모델 다운로드 여부는 별도 요약 메모로 분리합니다.

## Fallback Candidate Rules

10주차-D에서 Azure fallback 기준을 정리할 때의 초기 후보 조건은 다음입니다.

- PaddleOCR `status`가 `failed`, `skipped`, `partial`인 경우
- PaddleOCR `diagnostic_code`가 `paddle_not_installed`, `paddle_runtime_missing`, `paddle_runtime_error`, `paddle_no_text_detected`, `unsupported_input_type` 계열인 경우
- 핵심 필드 중 `transaction_date`, `merchant_name`, `total_amount` 중 2개 이상이 비어 있는 경우
- `amount_candidate_map`이 비어 있거나 금액 후보가 non-amount 후보와 충돌하는 경우
- `vat_review_required` 또는 부가세 관련 review hint가 반복적으로 발생하는 경우
- low confidence 라인 비율이 높은 경우
- 민감문구 감지가 발생하여 안전한 미리보기만으로 검수가 어려운 경우
- 평균 처리시간이나 환경 실패율이 파일럿 허용 기준을 넘는 경우

Fallback은 자동 세무 판단이 아니며, 사용자가 검수하거나 유료 재처리를 선택할 수 있는 후보 표시 기준입니다.

## Out Of Scope For 10-A

- 안전한 OCR 미리보기 UI 구현
- Azure vs PaddleOCR side-by-side 리포트 생성 코드
- 통계 요약 계산 코드
- 자동 fallback 실행
- PDF PaddleOCR 처리
- Provider 변경 UI
- ExcelExporter sheet/column 변경
- Processing History DB schema 변경
- 실제 Azure API 또는 실제 PaddleOCR smoke test를 기본 pytest에 추가

## Verification For Contract Work

문서 계약 변경 후 기본 확인은 다음입니다.

```bash
python -m compileall app tests
python -m pytest
```

실제 PaddleOCR 품질 비교는 기본 pytest가 아니라 별도 opt-in 실행과 샘플 관리 절차로 분리합니다.
## 10-B Safe OCR Preview Addendum

10-B implements a safe preview layer only. It does not change the 10-A comparison contract and does not implement the 10-C side-by-side report or 10-D statistics/fallback policy.

Allowed preview inputs:

- `StandardOCRResult.provider`
- `StandardOCRResult.status`
- `StandardOCRResult.diagnostic_code`
- `StandardOCRResult.source_file_name`, file name only
- `StandardOCRResult.text_blocks`

Allowed preview row fields:

- `line_order`
- `page_index`
- `block_id`
- safe preview `text`
- `confidence`
- `confidence_label`
- `is_low_confidence`
- safe `sensitive_category`
- `is_redacted`

Allowed preview summary fields:

- `provider`
- `status`
- `diagnostic_code`
- `source_file_name`
- `text_block_count`
- `preview_line_count`
- `low_confidence_line_count`
- `redacted_line_count`
- `max_lines`
- `low_confidence_threshold`

The preview must show only the top N safe rows and must keep sensitive lines as `[REDACTED]`. It must not show or save provider raw output, full OCR raw text, raw JSON, full local absolute paths, Azure endpoint URLs, operation-location URLs, secrets, tokens, raw tracebacks, actual customer files, or full sensitive values.

The preview summary can feed 10-C/D counts later, but 10-B does not calculate `field_match_score`, aggregate statistics, or execute/recommend Azure fallback.
## 10-C Side-by-side Report Addendum

Week 10-C implements a per-sample side-by-side report for Azure and PaddleOCR. The report follows the existing comparison flow and compares only safe standard-layer and parser-layer values:

`Provider execution -> StandardOCRResult -> StandardOCRParserContext -> ReceiptParser.parse_standard_context() -> ReceiptRecord -> side-by-side comparison report`

Week 10-B safe preview is implemented and remains limited to top-N preview rows. Its low-confidence count is preview-row scoped. Week 10-C separately records full `text_blocks` low-confidence and redacted counts for each provider so Week 10-D can aggregate them later without exposing raw OCR text.

Week 10-C report rows may contain provider status, diagnostic code, elapsed milliseconds, standard text block count, candidate counts, parser review hint counts, sensitive category counts, warning counts, full-result low-confidence/redacted counts, parsed core field values, and per-field present/same flags.

Week 10-C may also expose per-field `match_status` values (`matched`, `mismatched`, `azure_only`, `paddle_only`, `both_missing`) and a per-sample match summary count. These values are diagnostic comparison aids only and are not a formal `field_match_score`.

Provider failures may include a sanitized `diagnostic_detail_code`. Allowed examples include `quota_or_rate_limit`, `credential_or_permission`, `region_or_endpoint`, `non_json_error`, and provider-runtime exception class categories such as `runtime_error` or `value_error`. The detail code must never contain raw Azure error messages, endpoint URLs, operation URLs, keys, request IDs, raw tracebacks, full local paths, or provider raw payloads.

PaddleOCR candidate hints are intentionally conservative. They can be generated from safe line text for obvious dates, business numbers, payment methods, and labeled amounts, but they must not guess merchant names from arbitrary top lines or infer totals from unlabeled maximum amounts.

Week 10-C does not compute `field_match_score`, average processing time, failure rate, field-level match-rate summaries, fallback recommendations, or automatic Azure retries. Those remain Week 10-D scope. Provider raw output, full OCR text, raw JSON, full local paths, Azure endpoint URLs, operation URLs, secrets, raw tracebacks, real customer files, and raw OCR fixtures remain prohibited in reports, fixtures, logs, DB, Excel, and UI.

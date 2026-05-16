# StandardOCRResult Transition Plan

## 1. 현재 구조

현재 MVP 흐름은 다음 구조를 유지합니다.

```text
OCR Provider
→ OCRResult
→ ReceiptParser
→ ReceiptRecord
→ ReceiptValidator / CategoryRules / CardMatcher
→ ExcelExporter
→ Processing History
```

이번 단계에서는 이 흐름을 바꾸지 않습니다.

## 2. 목표 구조

후속 전환의 목표 구조는 다음과 같습니다.

```text
Provider raw response
→ Provider Adapter
→ StandardOCRResult
→ StandardOCRParserContext
→ ReceiptParser
→ ReceiptRecord
→ Validator / CategoryRules / CardMatcher
→ ExcelExporter / Processing History
```

`StandardOCRParserContext`는 기존 Parser를 한 번에 바꾸지 않기 위한 중간 입력 형태입니다.

## 3. 책임 경계

Provider 책임:

- OCR 실행
- Provider raw response 수신
- raw response를 `StandardOCRResult`로 변환
- raw response 전체를 DB, 화면, 엑셀, 로그에 남기지 않음

Provider Adapter 책임:

- provider별 raw response를 `StandardOCRResult`로 변환
- provider별 좌표계, block 구조, key-value 구조를 표준 필드로 정규화
- Parser가 필요한 제한된 text block과 `key_value_candidates`만 생성
- OCR raw JSON 전체와 OCR raw text 전체를 반환하지 않음
- 민감문구는 실제 값이 아니라 `sensitive_category` 또는 `[REDACTED]`로 처리

StandardOCRResult 책임:

- Provider 독립적인 OCR 결과 표현
- Parser가 필요한 제한된 text block, key-value candidate, warning 제공
- 민감값 대신 `sensitive_category` 제공
- DB 저장 모델이 아니라 Parser 입력 계약에 가까운 표준 모델 역할

StandardOCRParserContext 책임:

- Parser가 사용할 수 있는 제한된 line/candidate/review hint만 제공
- Provider별 raw 구조를 숨김
- 기존 Parser 전환을 위한 중간 adapter 역할
- amount candidate와 non-amount candidate를 분리

ReceiptParser 책임:

- Provider raw response를 직접 알지 않음
- `StandardOCRParserContext` 또는 `StandardOCRResult` 기반 입력만 사용
- `ReceiptRecord` 생성
- 기존 raw_text 기반 경로는 즉시 삭제하지 않고 compatibility wrapper로 단계적 전환

ReceiptRecord 책임:

- 기존 엑셀, 검수, 처리 이력 흐름과 호환되는 업무 데이터 유지

ExcelExporter 책임:

- 기존 산출물 구조 유지
- OCR raw text 전체, raw JSON 전체, 전체 로컬 경로 미노출 유지

## 4. Provider Adapter Contract

모든 Provider Adapter는 향후 아래 계약을 따릅니다.

입력:

- provider별 raw response
- `source_file_id`
- `source_file_name`
- provider metadata
- diagnostic info

출력:

- `StandardOCRResult`

금지:

- provider raw response를 Parser에 직접 전달
- provider raw JSON 전체를 `StandardOCRResult`에 저장
- OCR raw text 전체를 `StandardOCRResult`에 저장
- 전체 로컬 절대경로 저장
- API key, endpoint 전체 URL 저장
- 실제 민감정보 저장

Adapter별 방향:

- Azure Adapter: Azure Document Intelligence 결과를 `StandardOCRResult`로 변환
- Mock Adapter: 테스트 fixture 기반 `StandardOCRResult` 생성
- PaddleOCR Adapter: 향후 PC Local Runtime에서 PaddleOCR 결과를 `StandardOCRResult`로 변환
- Tesseract Adapter: 향후 Tesseract line/text 결과를 `StandardOCRResult`로 변환
- Android ML Kit Adapter: 모바일 OCR block을 `StandardOCRResult`로 변환
- iOS Apple Vision Adapter: Vision observation을 `StandardOCRResult`로 변환

## 5. 7주차 Azure Adapter 작업 기준

- Azure raw response를 `StandardOCRResult`로 변환합니다.
- Azure SDK response object를 Parser로 넘기지 않습니다.
- Azure raw JSON 전체를 fixture나 DB에 저장하지 않습니다.
- 기존 Azure provider 동작을 한 번에 갈아엎지 않습니다.
- 먼저 adapter 단위 테스트를 만듭니다.
- Azure-like fixture와 실제 Azure adapter output의 shape를 비교합니다.
- 실패, timeout, polling `diagnostic_code`는 `StandardOCRResult.diagnostic_code` 또는 `warnings`로 제한적으로 전달합니다.
- Azure endpoint 전체 URL, key, raw response는 노출하지 않습니다.

Azure Adapter Contract:

- 입력은 Azure provider 내부의 raw response 또는 제한된 요약 데이터, `source_file_id`, `source_file_name`, provider metadata, diagnostic info입니다.
- 출력은 `StandardOCRResult`입니다.
- `AzureStandardOCRAdapter`는 7주차-B에서 `app/ocr/adapters/azure_standard_adapter.py` 별도 모듈로 추가합니다.
- 7주차-B에서는 Azure-like dummy response 또는 제한된 sanitized sample을 이용해 `tests/test_azure_standard_adapter.py`에서 `StandardOCRResult` 생성 테스트를 작성합니다.
- 기존 `AzureProvider.extract()`의 반환 구조는 7주차-A/B에서 변경하지 않습니다.
- 7주차-C에서 기존 Azure Provider와 Adapter 연결 여부를 검토합니다.
- 8주차 전까지 `ReceiptParser`는 Azure raw response 또는 Azure SDK object를 직접 알면 안 됩니다.

`provider_fields` 기준:

- 7주차-B에서 `StandardOCRResult`의 선택 필드로 `provider_fields`를 추가했습니다.
- 기본값은 빈 dict이며, Adapter가 넣는 값은 비민감 metadata와 count/flag 중심 진단 요약으로 제한합니다.
- `provider_fields`는 raw JSON 저장소가 아니라 비민감 provider metadata와 adapter 진단 요약 영역입니다.
- 허용 예시는 `provider_family`, `api_model`, `api_version`, `document_type`, `page_count`, `has_key_value_pairs`, `has_tables`, `has_styles`, `locale_hint`, `adapter_version`, `normalized_block_count`, `normalized_candidate_count`입니다.
- 금지 예시는 `raw_response`, `raw_json`, `provider_raw_response`, `full_ocr_text`, analyze/read result 전체, pages/lines/words/key-value/table raw payload 전체, headers 전체, endpoint 전체 URL, API key, `operation_location` 전체 URL, 실제 파일 전체 경로, 실제 민감정보 원문입니다.

Azure field mapping 기준:

- Azure page/line/word/block 구조는 `StandardOCRTextBlock`으로 정규화합니다.
- Azure document fields 또는 key-value 후보는 `StandardOCRKeyValueCandidate`로 정규화합니다.
- Azure table 구조는 필요 시 `StandardOCRTableCandidate`로 정규화합니다.
- Azure confidence는 0~1 범위 confidence로 정규화합니다.
- Azure bounding polygon은 `bbox`로 정규화하되 필수값으로 만들지 않습니다.
- Azure operation status 또는 polling 실패 정보는 `diagnostic_code`/`warnings`로 제한적으로 전달합니다.
- Azure raw text 전체가 아니라 Parser에 필요한 제한된 context line만 `text_blocks` 또는 `safe_text_summary`에 반영합니다.
- Azure SDK object의 원본 구조명은 Parser까지 전달하지 않습니다.

Azure diagnostic 기준:

- polling timeout, 429, 5xx, invalid response, missing result 등은 비민감 `diagnostic_code` 또는 짧은 `warnings`로만 남깁니다.
- raw error body 전체, response headers 전체, endpoint 전체 URL, `operation_location` 전체 URL은 남기지 않습니다.

7주차-B 구현 범위:

- `AzureStandardOCRAdapter` 구현
- sanitized dummy response 또는 azure_like fixture 기반 단위 테스트
- `StandardOCRResult` 생성 검증
- `provider_fields` 비민감 metadata 검증
- raw JSON/raw text/`operation_location` 전체 URL 미노출 테스트

7주차-C 연결 검토 기준:

- 기존 Azure Provider와 Adapter 연결 준비
- 기존 `AzureProvider.extract()`의 `OCRResult` 반환 흐름 유지 여부 점검
- Adapter를 운영 흐름에 바로 연결할지 여부는 별도 판단
- 회귀 테스트
- 8주차 Parser 전환 준비

7주차-C 연결 준비 보완:

- `AzureStandardOCRAdapter`는 구현되어 있지만 기존 `AzureProvider.extract()` 반환값은 `OCRResult`로 유지합니다.
- Azure Provider와 Adapter 연결은 즉시 운영 흐름에 강제하지 않습니다.
- 연결 방식 후보는 Azure Provider 내부에서 선택적으로 `StandardOCRResult`를 생성하는 방식, Azure Provider 밖에서 sanitized summary를 bridge로 넘기는 방식, 8주차 Parser 전환 이후 StandardOCRResult 기반 경로를 정식 연결하는 방식입니다.
- 7주차-C에서는 `app/ocr/adapters/azure_adapter_bridge.py` helper와 회귀 테스트까지만 둡니다.
- 8주차 전에는 기존 Parser 입력을 바꾸지 않습니다.

8주차 Parser 전환 진입 조건:

- `StandardOCRResult` 모델 테스트 통과
- `AzureStandardOCRAdapter` 테스트 통과
- `StandardOCRResult`에서 `StandardOCRParserContext` 생성 테스트 통과
- 기존 raw_text Parser 테스트 통과
- 기존 end-to-end export flow 테스트 통과
- Adapter output과 parser context에 `raw_json`, `raw_text`, `provider_raw_response`, `full_ocr_text` 미노출 확인
- 동일 fixture 기반 핵심 `ReceiptRecord` 필드 비교 가능
- ExcelExporter end-to-end 테스트 통과

## 6. 8주차 Parser 정리 작업 기준

- `ReceiptParser`가 `StandardOCRParserContext`를 받을 수 있도록 단계적으로 정리합니다.
- 기존 raw_text 기반 Parser가 있다면 backward-compatible wrapper를 둡니다.
- 기존 Parser public interface를 한 번에 깨지 않습니다.
- 기존 end-to-end 테스트를 깨지 않습니다.
- `ReceiptRecord` 필드는 대규모로 바꾸지 않습니다.
- `ExcelExporter`는 변경하지 않습니다.
- Processing History DB schema는 변경하지 않습니다.
- `StandardOCRParserContext` 기반 Parser 테스트를 먼저 추가합니다.
- 이후 기존 raw_text 테스트와 `StandardOCRParserContext` 테스트가 같은 `ReceiptRecord` 핵심 필드를 만드는지 비교합니다.

8주차 단계:

- 8주차-A: Parser 표준 입력 전환 계약/문서 보완
- 8주차-B: `StandardOCRParserContext` 기반 Parser entry 추가
- 8주차-C: fixture 기반 Parser 결과 비교 테스트
- 8주차-D: Validator/CategoryRules/CardMatcher/ExcelExporter/Processing History 회귀 점검

8주차-B 기준:

- 기존 `ReceiptParser` public interface를 유지합니다.
- 새 entry를 추가하되 기존 raw_text 경로 compatibility를 유지합니다.
- Provider raw response 직접 참조를 금지합니다.
- 새 entry는 기존 `ReceiptRecord`를 반환합니다.
- ExcelExporter, DB, UI는 변경하지 않습니다.
- 성공 기준은 새 entry 추가와 기존 테스트 유지입니다.

8주차-C 기준:

- mock fixture 기반 테스트를 추가합니다.
- azure-like fixture 기반 테스트를 추가합니다.
- Azure Adapter output 기반 테스트를 추가합니다.
- edge-case fixture 기반 테스트를 추가합니다.
- legacy raw_text 결과와 `StandardOCRParserContext` 결과의 핵심 필드를 비교합니다.
- 비교 대상은 `ReceiptRecord` 핵심 필드 중심으로 합니다.
- Parser 결과가 다르면 `parser_warnings` 또는 `review_status`로 안전하게 검토필요 처리합니다.

8주차-D 기준:

- ReceiptValidator 회귀 테스트를 실행합니다.
- CategoryRules 회귀 테스트를 실행합니다.
- CardMatcher 회귀 테스트를 실행합니다.
- ExcelExporter 회귀 테스트를 실행합니다.
- Processing History 저장/조회 회귀 테스트를 실행합니다.
- end-to-end export flow 테스트를 실행합니다.
- downstream 구조 변경은 최소화하고, 구조 변경이 필요하면 별도 8주차-E 또는 후속 작업으로 분리합니다.

8주차 진입 조건:

- `StandardOCRResult` 모델 테스트 통과
- `StandardOCRParserContext` 테스트 통과
- `AzureStandardOCRAdapter` 테스트 통과
- Azure Provider 회귀 테스트 통과
- 기존 end-to-end export flow 테스트 통과

8주차 완료 조건:

- 새 Parser entry가 추가되었거나 추가 기준이 확정됨
- fixture 기반 Parser 비교 테스트가 있음
- 기존 raw_text Parser 경로가 유지됨
- 기존 `ReceiptRecord` 구조가 유지됨
- 기존 ExcelExporter 산출물 구조가 유지됨
- downstream 회귀 테스트가 통과함

## 7. Golden Fixture Comparison Strategy

- 같은 의미의 영수증을 mock, azure_like, edge_case fixture로 표현합니다.
- provider가 달라도 `candidate_type` 구조가 비교 가능해야 합니다.
- 핵심 비교 대상은 다음입니다.

```text
merchant_name
transaction_date
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

- parser context 비교는 완전 동일값 비교가 아니라 구조 비교를 우선합니다.
- 8주차 이후에는 같은 의미의 fixture가 같은 `ReceiptRecord` 핵심 필드를 만드는지 비교합니다.
- 실제 고객 파일이나 실제 OCR raw JSON은 Golden Fixture에 넣지 않습니다.

## 8. 금액 후보 처리 기준

- `total_amount`, `gross_amount`, `discount_amount`, `final_amount`, `paid_amount`를 구분합니다.
- `supply_amount`, `vat_amount`는 명시값 후보로만 다룹니다.
- `vat_missing`, `vat_review_hint`는 부가세 검토 힌트이지 명시 부가세가 아닙니다.
- `quantity`는 금액 후보가 아닙니다.
- `approval_number`는 금액 후보가 아닙니다.
- `footer_number`는 금액 후보가 아닙니다.
- `business_number`는 금액 후보가 아닙니다.
- 부가세 미표기는 `vat_missing` 또는 `vat_review_hint`로 남깁니다.
- 추정부가세는 명시 부가세로 취급하지 않습니다.
- 할인 후 0원 결제는 자동 제외하지 않습니다.
- 수량, 승인번호, 푸터 숫자가 금액으로 반복 오인식되지 않도록 parser context에서 `candidate_type`을 분리합니다.

## 9. 보안 기준

아래 정보는 `StandardOCRResult`, `StandardOCRParserContext`, Parser, DB, 화면, 엑셀, 로그에 전체 형태로 들어가면 안 됩니다.

- OCR raw JSON 전체
- OCR raw text 전체
- provider raw response 전체
- 전체 로컬 절대경로
- API key
- Azure endpoint 전체 URL
- 실제 고객 파일명
- 실제 카드번호 전체
- 주민번호
- 전화번호
- WiFi PW 실제 값
- token, secret, password 실제 값

## 10. 전환 순서

1. `StandardOCRResult` 모델과 fixture 확정
2. `StandardOCRParserContext` 준비
3. Azure Adapter가 `StandardOCRResult`를 생성하도록 테스트
4. Mock Provider fixture와 Azure-like fixture가 같은 Parser context 구조를 만들 수 있는지 비교
5. `ReceiptParser`가 `StandardOCRParserContext`를 선택적으로 받을 수 있게 준비
6. 기존 `OCRResult`/raw_text 경로는 deprecated 처리하되 즉시 제거하지 않음
7. end-to-end 흐름 검증 후 기존 경로 정리 검토

## 11. 이번 단계에서 하지 않는 것

- Azure Provider 실제 전환
- Mock Provider 실제 전환
- `ReceiptParser` 실제 전환
- `ExcelExporter` 변경
- Processing History DB 변경
- Streamlit UI 변경
- `PaddleOCRProvider` 구현
- `TesseractProvider` 구현
- ML Kit 앱 구현
- Apple Vision 앱 구현
- FastAPI 서버 구현
- Tauri/Electron 앱 구현
## Week 8-B Parser Entry Implementation Note

- `ReceiptParser.parse_standard_context(context: StandardOCRParserContext, ...) -> ReceiptRecord` has been added as the isolated standard parser entry.
- `ReceiptParser.parse_from_standard_ocr(result: StandardOCRResult, ...) -> ReceiptRecord` has been added as a convenience wrapper through `build_parser_context_from_standard_ocr`.
- The legacy raw_text parser path and public `parse(ocr_result: OCRResult)` entry remain in place.
- The new entry is not connected to Streamlit, AzureProvider, MockProvider, AzureStandardOCRAdapter runtime behavior, or provider selection.
- 8-C should expand comparison tests across mock, azure-like, edge-case, and Azure adapter output fixtures against legacy parser core fields.
- 8-D should verify ReceiptValidator, CategoryRules, CardMatcher, ExcelExporter, Processing History, and end-to-end export flow without changing their structures.

## Week 8-C Parser Fixture Comparison Note

- `tests/test_receipt_parser_standard_comparison.py` verifies `ReceiptParser` standard-context output for mock, azure-like, edge-case, and Azure adapter sanitized fixtures.
- Limited legacy raw_text fixtures under `tests/fixtures/parser_legacy/` are comparison fixtures, not full OCR raw text captures.
- Comparison focuses on core `ReceiptRecord` business fields instead of full-object equality.
- Non-amount candidates remain separated from amount fields: quantity, approval number, footer number, and business number are not used as totals.
- `vat_missing` and `vat_review_hint` remain review signals and do not populate explicit `vat_amount`.
- Failed Azure adapter output is converted to a review-required `ReceiptRecord` with non-sensitive diagnostic warnings.
- `provider_fields` raw metadata is not copied into `ReceiptRecord`.
- Parser output is checked for raw payload, secret, endpoint, operation location, and absolute path exposure.
- 8-D downstream regression remains separate and should cover ReceiptValidator, CategoryRules, CardMatcher, ExcelExporter, Processing History, and end-to-end export flow.

8-D entry conditions after 8-C:

- Standard parser fixture comparison tests pass.
- Legacy raw_text parser tests pass.
- Non-amount candidate defense tests pass.
- Parser output security non-exposure tests pass.
- Existing end-to-end export flow remains passing.
- Existing Provider, Adapter, Exporter, DB, and UI flows remain unchanged.

## Week 8-D Downstream Regression Note

- Standard Parser `ReceiptRecord` outputs are now covered against ReceiptValidator, CategoryRules, CardMatcher, ExcelExporter, Processing History, provider independence, and existing end-to-end export flow.
- The downstream tests verify that downstream layers continue to consume `ReceiptRecord` and `CardTransaction`, not `StandardOCRResult`, `StandardOCRParserContext`, provider raw response, Azure SDK objects, or `provider_fields` raw metadata.
- Excel regression checks keep the existing sheet set and headers, and verify raw OCR text, raw provider JSON, endpoint, operation location, API key, secret, token, absolute local paths, and `provider_fields` metadata are not exported.
- Processing History regression checks save and read Standard Parser records with the existing DB schema and verify raw payload/path metadata is not stored.
- Provider independence checks use a `provider="paddleocr"` candidate `ReceiptRecord` only; no PaddleOCRProvider implementation or `paddleocr` dependency is introduced in 8-D.
- Existing raw_text parser path, Parser public interface, Provider code, AzureStandardOCRAdapter, ExcelExporter structure, Processing History DB schema, and Streamlit UI remain unchanged.

9주차 PaddleOCR Local Provider PoC entry conditions:

- `StandardOCRResult` model tests pass.
- `StandardOCRParserContext` tests pass.
- `AzureStandardOCRAdapter` tests pass.
- Standard Parser fixture comparison tests pass.
- ReceiptValidator, CategoryRules, CardMatcher, ExcelExporter, and Processing History regression tests pass.
- Existing end-to-end export flow passes.
- Parser and downstream layers do not consume provider raw response directly.
- Excel, DB, logs, and test outputs do not expose raw JSON, raw OCR text, full local paths, endpoint, operation location, API key, token, or secret values.
- A `provider="paddleocr"` candidate record can pass downstream without special casing.
- 9주차의 목표는 PaddleOCR Adapter가 `StandardOCRResult`를 반환하게 하는 PoC이며, Parser/Validator/Exporter 구조 변경 없이 붙이는 것입니다.

## Week 9 PaddleOCR Local Provider PoC Plan

Week 9 is split into contract, adapter fixture, optional provider, and opt-in smoke-test phases. It does not change the default provider and does not make PaddleOCR a required dependency.

### 9주차-A: PaddleOCR Local Provider 계약/문서 보완

- Define `OCR_PROVIDER=paddle` as a future candidate only.
- Define `PaddleOCRProvider` and `PaddleStandardOCRAdapter` contracts.
- State that `PaddleOCRProvider` must return `StandardOCRResult`.
- State that Parser, Validator, CategoryRules, CardMatcher, ExcelExporter, and Processing History must not consume PaddleOCR raw output.
- Document lazy import, optional dependency, image-first PoC, PDF deferral, opt-in OCR smoke tests, and raw output non-exposure rules.

### 9주차-B: PaddleOCR-like Adapter 및 sanitized fixture 테스트

- Use PaddleOCR-like sanitized/dummy fixture data.
- Implement `PaddleStandardOCRAdapter`.
- Convert PaddleOCR-like result shape into `StandardOCRResult`.
- Verify `provider_fields` contains only non-sensitive count/flag metadata.
- Verify full raw output, full OCR raw text, full local paths, and actual customer files are not stored.
- Do not import or call actual `paddleocr`.
- Do not connect provider factory.
- Do not modify Parser, Validator, ExcelExporter, Processing History, or Streamlit UI.

Implementation note:

- `PaddleStandardOCRAdapter` lives in `app/ocr/adapters/paddle_standard_adapter.py`.
- Sanitized fixture coverage lives under `tests/fixtures/paddle/` and includes regular, edge, and empty/failed image-style results.
- The adapter output uses `provider="paddleocr"` and `provider_fields.provider_family="paddleocr"`; `OCR_PROVIDER=paddle` remains the 9주차-C provider factory candidate.
- The output is comparable with Azure adapter output at the `StandardOCRResult`, `StandardOCRParserContext`, and `ReceiptRecord` levels without comparing provider raw output.
- 9주차-C should wrap this adapter from an optional provider with lazy import and should keep actual OCR execution outside default pytest.

### 9주차-C: Optional PaddleOCRProvider 구현과 provider factory 후보 추가

- Add optional `PaddleOCRProvider` only after adapter tests exist.
- Use lazy import so module import and default pytest pass without PaddleOCR installed.
- Add `OCR_PROVIDER=paddle` as a candidate path, not the default.
- If PaddleOCR is missing, return a clear failed/skipped result or configuration error with a non-sensitive diagnostic code.
- Keep actual OCR execution out of default pytest.
- Do not change Parser, Validator, CategoryRules, CardMatcher, ExcelExporter, Processing History DB schema, or Streamlit UI.

### 9주차-D: 이미지 기준 opt-in Local OCR smoke test와 회귀 점검

- Add actual image OCR smoke tests only behind an explicit opt-in flag such as `RUN_PADDLEOCR_TESTS=1`.
- Default pytest must skip actual PaddleOCR execution.
- PDF handling remains follow-up work.
- Validate output through `StandardOCRResult` and `StandardOCRParserContext`, not provider raw output.
- Re-run mock/Azure/standard parser/downstream/end-to-end regression tests.

### 10주차 Azure vs PaddleOCR 품질 비교 연결 기준

- Compare via `StandardOCRResult`, `StandardOCRParserContext`, and core `ReceiptRecord` fields.
- Do not compare or store provider raw output.
- Compare at least `merchant_name`, `transaction_date`, `total_amount`, `supply_amount`, `vat_amount`, `payment_method`, warnings, `review_status`, and failure/diagnostic rates.
- Record Azure call cost separately from PaddleOCR local execution time, install complexity, and runtime stability.
- Cases where PaddleOCR quality is insufficient can become Azure fallback candidates.

10주차-A contract note:

- `docs/ocr_quality_comparison_contract.md` is the source contract for the comparison input, metrics, report row shape, and fallback candidate signals.
- Expected fixtures for Week 10 compare core `ReceiptRecord` fields by safe `sample_id`; they must not store provider raw output, full OCR raw text, or actual customer files.
- 10-A does not implement safe OCR preview, side-by-side report code, statistics aggregation, automatic Azure fallback execution, or PDF PaddleOCR handling.
- 10-B may add a safe preview only from `StandardOCRResult` and `StandardOCRParserContext`, with full OCR raw text and sensitive values excluded.
- 10-C may add side-by-side report output using file-name-only sample identifiers and non-sensitive summary fields.
- 10-D may summarize field match rates, review-needed rates, failure rates, average processing time, and Azure fallback candidate reasons.
## Week 9-C Optional PaddleOCRProvider Implementation Note

- `PaddleOCRProvider` is available as an optional provider candidate in `app/ocr/paddle_provider.py`.
- Provider factory accepts `OCR_PROVIDER=paddle` and `OCR_PROVIDER=paddleocr`, while the default provider remains unchanged.
- The provider returns `StandardOCRResult` through `PaddleStandardOCRAdapter`; Parser and downstream layers still do not receive PaddleOCR raw output.
- `paddleocr` is lazy-imported only during provider execution, so default pytest does not require the package.
- Missing `paddleocr` returns a failed diagnostic result rather than failing provider import.
- PDF input is deferred and returns `paddle_pdf_not_supported`; PDF conversion remains out of scope.
- 9-D can add an opt-in smoke test such as `RUN_PADDLEOCR_TESTS=1 python -m pytest tests/integration/test_paddle_ocr_provider_smoke.py`.
- 10-week Azure vs PaddleOCR comparison should compare `StandardOCRResult`, `StandardOCRParserContext`, and core `ReceiptRecord` fields, not provider raw output.

## Week 9-D Opt-In PaddleOCR Smoke Test Note

- `tests/integration/test_paddle_ocr_provider_smoke.py` verifies the real image OCR execution path only when `RUN_PADDLEOCR_TESTS` is enabled.
- `PADDLEOCR_TEST_IMAGE_PATH` must point to an existing local JPG/JPEG/PNG image; the test reports only the file name in skip messages.
- Default pytest skips the real OCR smoke test and must continue to pass without `paddleocr` installed.
- The smoke test validates `StandardOCRResult`, `StandardOCRParserContext`, and `ReceiptParser.parse_standard_context` wiring, but it does not score OCR quality.
- Smoke test failures should be classified as environment, provider, security, or quality failures.
- PDF remains unsupported/deferred; no PDF conversion dependency is introduced.
- 10-week quality comparison can start after adapter/provider/factory tests, default pytest, and the opt-in smoke scaffold are stable.
## Week 10-B Safe Preview Connection

The safe OCR preview added in 10-B uses only `StandardOCRResult.text_blocks` and produces limited preview rows plus summary counts for UI display. PaddleOCR smoke-test output can now be inspected in Settings without exposing provider raw output or full OCR raw text.

The same utility can be reused by Azure adapter results because it depends on the standard result contract, not provider SDK objects. This does not implement side-by-side comparison, field match scoring, statistics aggregation, fallback automation, default provider changes, ExcelExporter changes, Processing History schema changes, or PDF PaddleOCR handling.
## Week 10-C Side-by-side Report Connection

The Week 10-C report is the first UI path that compares Azure and PaddleOCR through the standard OCR transition layers. Both providers are normalized to `StandardOCRResult`, converted to `StandardOCRParserContext`, and parsed with `ReceiptParser.parse_standard_context()` before any field comparison is shown.

This connection is diagnostic-only. It does not remove the legacy parser path, change the default provider, change Excel export output, or store comparison data in Processing History. Per-sample metrics, field equality flags, and `match_status` values are intentionally shaped so Week 10-D can aggregate them later without introducing raw provider payloads.

Provider diagnostics now support safe detail categories. For example, Azure HTTP 403 can be represented as `diagnostic_code="analyze_http_403"` with `diagnostic_detail_code="quota_or_rate_limit"`. This is safe metadata only and must not include raw Azure error messages, endpoint URLs, operation URLs, request IDs, keys, or raw tracebacks.

PaddleOCRProvider may generate conservative parser candidates from safe OCR lines for obvious dates, business numbers, payment methods, and labeled amount lines. It must not pass PaddleOCR raw output to the parser, and it must not guess merchant names or unlabeled total amounts as if they were reliable extracted fields.

# 파일럿 전 체크리스트

## 1. 공통 원칙

| 체크 | 항목 |
|---|---|
| [ ] | OCR 결과는 항상 검수 대상으로 안내된다 |
| [ ] | 비용항목은 추천값과 최종 입력값이 구분된다 |
| [ ] | 원본 파일 장기 보관을 전제로 하지 않는다 |
| [ ] | API key, secret, token이 코드와 문서에 없다 |
| [ ] | 전체 로컬 경로가 화면/DB/엑셀에 노출되지 않는다 |
| [ ] | OCR 원문 전체와 raw JSON 전체가 화면/DB/엑셀에 노출되지 않는다 |
| [ ] | 민감문구 감지 건은 실제 값이 아니라 category만 화면/DB/엑셀에 표시된다 |
| [ ] | README/PLAN/SPEC/CHECKLIST가 현재 코드와 충돌하지 않는다 |

## 2. 새 작업 흐름

| 체크 | 항목 |
|---|---|
| [ ] | `streamlit run app/main.py`로 앱이 실행된다 |
| [ ] | `새 작업` 메뉴가 표시된다 |
| [ ] | 영수증 이미지/PDF 업로드가 가능하다 |
| [ ] | 카드 사용내역 CSV/XLSX 업로드가 가능하다 |
| [ ] | Mock OCR 처리가 가능하다 |
| [ ] | Azure OCR 선택 시 네트워크와 API key 설정이 필요하다는 점을 알고 있다 |
| [ ] | `파일 저장 및 처리` 중 버튼이 비활성화되고 진행 상태가 표시된다 |
| [ ] | 검수 UI가 표시된다 |
| [ ] | 할인전금액, 할인금액, 최종결제금액, 실제결제금액, 금액판단기준, 금액검토사유를 확인할 수 있다 |
| [ ] | 부가세 명시값과 참고 추정값이 구분되어 표시된다 |
| [ ] | 민감문구감지와 민감문구유형은 실제 값 없이 category만 표시된다 |
| [ ] | 검수 테이블 수정값이 엑셀에 반영된다 |
| [ ] | 제외 상태가 제외내역 시트에 반영된다 |
| [ ] | 표준 엑셀 생성이 가능하다 |
| [ ] | 엑셀 다운로드가 가능하다 |
| [ ] | 엑셀 파일이 열린다 |

## 3. 엑셀 산출물

| 체크 | 항목 |
|---|---|
| [ ] | 정리내역 시트가 있다 |
| [ ] | 월별요약 시트가 있다 |
| [ ] | 비용항목별요약 시트가 있다 |
| [ ] | 검토필요 시트가 있다 |
| [ ] | 카드대조 시트가 있다 |
| [ ] | 원본파일목록 시트가 있다 |
| [ ] | 처리로그 시트가 있다 |
| [ ] | 제외내역 시트가 있다 |
| [ ] | OCR 원문 전체가 엑셀에 없다 |
| [ ] | raw JSON 전체가 엑셀에 없다 |
| [ ] | 전체 로컬 경로가 엑셀에 없다 |
| [ ] | 할인 후 0원 결제 건은 총금액 0으로 남고 자동 제외되지 않는다 |
| [ ] | 추정부가세는 명시 부가세 합계에 자동 합산되지 않는다 |
| [ ] | 민감문구 감지 건은 실제 값 없이 category만 표시된다 |

## 3-1. 실제 OCR 금액/민감문구 확인

| 체크 | 항목 |
|---|---|
| [ ] | 할인금액이 있는 영수증에서 할인전금액, 할인금액, 최종결제금액이 분리된다 |
| [ ] | 받은금액 또는 합계금액이 0인 할인 영수증은 총금액 0으로 표시된다 |
| [ ] | 상품권/포인트/카드결제 혼재 영수증에서 최종결제금액과 실제결제금액을 구분해 검토할 수 있다 |
| [ ] | 수량 1, 3, 10 같은 숫자가 할인금액이나 실제결제금액으로 들어가지 않는다 |
| [ ] | 카드/승인번호 같은 긴 숫자가 할인금액으로 들어가지 않는다 |
| [ ] | 결제금액 기준 같은 설명 문구 뒤의 푸터 숫자가 실제결제금액으로 들어가지 않는다 |
| [ ] | 부가세 미표기 영수증은 명시 부가세가 비어 있고 참고 추정값이 별도 컬럼에 표시된다 |
| [ ] | WiFi PW, 비밀번호, 카드번호 전체 등 민감문구 가능성이 있는 값은 원문이 표시되지 않는다 |
| [ ] | Azure OCR 사용 시 사업자번호, 전화/TEL, 카드결제/현금결제 관련 context line이 Parser에 필요한 범위로 반영된다 |

## 4. 처리 이력

| 체크 | 항목 |
|---|---|
| [ ] | 엑셀 생성 성공 직후 ProcessingJob이 DB에 저장된다 |
| [ ] | 같은 작업에서 엑셀 생성 버튼을 반복 눌러도 불필요한 job이 계속 쌓이지 않는다 |
| [ ] | `처리 이력` 메뉴가 표시된다 |
| [ ] | 처리 이력 목록이 최신순으로 표시된다 |
| [ ] | 방금 저장된 작업이 목록에서 조회된다 |
| [ ] | 상세 화면에서 작업 요약이 표시된다 |
| [ ] | 상세 화면에서 ReceiptRecord 요약이 표시된다 |
| [ ] | 상세 화면에서 CardTransaction 요약이 표시된다 |
| [ ] | 상세 화면에서 ExportFile 목록이 표시된다 |
| [ ] | 기존 엑셀 파일 재다운로드가 가능하다 |
| [ ] | export 파일이 없을 때 안전한 안내 메시지가 표시된다 |
| [ ] | 과거 작업 재검수 기능은 표시되지 않는다 |
| [ ] | 과거 엑셀 재생성 기능은 표시되지 않는다 |

## 5. 설정 화면

| 체크 | 항목 |
|---|---|
| [ ] | `설정` 메뉴가 표시된다 |
| [ ] | 현재 OCR provider를 확인할 수 있다 |
| [ ] | API key 값은 표시되지 않는다 |
| [ ] | Azure endpoint 전체 URL은 표시되지 않는다 |
| [ ] | 업로드/출력 보관기간을 확인할 수 있다 |
| [ ] | 저장소 파일 수와 총 용량을 확인할 수 있다 |
| [ ] | DB 접근 가능 여부와 처리 이력 건수를 확인할 수 있다 |
| [ ] | 처리 이력 연결 상태를 확인할 수 있다 |
| [ ] | cleanup dry-run 요약을 확인할 수 있다 |
| [ ] | 실제 cleanup 삭제 버튼은 없다 |
| [ ] | provider 변경 UI는 없다 |
| [ ] | API key 입력 UI는 없다 |

## 6. 깨끗한 상태/기존 상태 점검

| 체크 | 항목 |
|---|---|
| [ ] | `data/app.db`가 없는 상태에서도 앱이 실행된다 |
| [ ] | DB가 없는 상태에서 처리 이력 화면이 빈 상태를 안전하게 표시한다 |
| [ ] | DB가 없는 상태에서 설정 화면이 오류 없이 표시된다 |
| [ ] | 기존 DB가 있는 상태에서 목록/상세/재다운로드가 동작한다 |
| [ ] | 새 작업 → 처리 이력 → 상세 → 설정 → 새 작업 이동 중 session_state 오류가 없다 |
| [ ] | cleanup dry-run이 실제 파일을 삭제하지 않는다 |

## 7. Git/민감 파일 점검

| 체크 | 항목 |
|---|---|
| [ ] | `.env`가 Git 변경사항에 없다 |
| [ ] | `data/uploads` 실제 파일이 Git 변경사항에 없다 |
| [ ] | `data/outputs` 실제 파일이 Git 변경사항에 없다 |
| [ ] | `output` 실제 파일이 Git 변경사항에 없다 |
| [ ] | `data/app.db` 또는 `*.db`가 Git 변경사항에 없다 |
| [ ] | 실제 고객 파일이나 실제 영수증 파일이 Git 변경사항에 없다 |
| [ ] | `git diff --check`가 통과한다 |

## 8. 테스트

```bash
python -m compileall app tests
python -m pytest
python -m pytest tests/test_end_to_end_export_flow.py
python -m pytest tests/test_history_utils.py
python -m pytest tests/test_history_detail_view.py
python -m pytest tests/test_settings_utils.py
```

| 체크 | 항목 |
|---|---|
| [ ] | compileall 통과 |
| [ ] | 전체 pytest 통과 |
| [ ] | end-to-end export flow 테스트 통과 |
| [ ] | history utils 테스트 통과 |
| [ ] | history detail 테스트 통과 |
| [ ] | settings utils 테스트 통과 |

## 9. 테스트 실패 기록

| 항목 | 기록 |
|---|---|
| 실패 명령 |  |
| 실패 테스트 |  |
| 실패 위치 |  |
| 원인 추정 |  |
| 즉시 수정 여부 |  |
| 파일럿 진행 가능 여부 |  |
| 다음 액션 |  |

## 10. Standard Core / Provider 독립화 체크리스트

| 체크 | 항목 |
|---|---|
| [ ] | Parser가 provider raw response를 직접 import하지 않는가 |
| [ ] | Parser 입력은 `StandardOCRResult` 기준인가 |
| [ ] | Azure Adapter는 Azure raw response를 `StandardOCRResult`로 변환하는가 |
| [ ] | Mock Provider도 `StandardOCRResult` fixture를 만들 수 있는가 |
| [ ] | PaddleOCR, Tesseract, ML Kit, Apple Vision은 향후 Adapter만 추가하면 Parser 흐름을 재사용할 수 있는가 |
| [ ] | OCR raw JSON 전체가 DB/화면/엑셀/로그에 노출되지 않는가 |
| [ ] | OCR raw text 전체가 DB/화면/엑셀/로그에 노출되지 않는가 |
| [ ] | 전체 로컬 절대경로가 DB/화면/엑셀/로그에 노출되지 않는가 |
| [ ] | `StandardOCRResult` fixture 테스트 계획이 있는가 |
| [ ] | Golden Test Fixture로 provider와 무관하게 Parser 결과를 비교할 수 있는가 |
| [ ] | `ReceiptRecord`와 `ExcelExporter` 구조를 불필요하게 대규모 변경하지 않았는가 |
| [ ] | `StandardOCRResult` Pydantic 모델 생성 테스트가 있는가 |
| [ ] | Mock/Azure-like/edge-case fixture를 모델로 로딩하는 테스트가 있는가 |
| [ ] | fixture의 `source_block_ids`가 실제 `text_blocks.block_id`와 연결되는가 |
| [ ] | `quantity`, `approval_number`, `footer_number` 후보가 `total_amount` 후보와 분리되어 있는가 |
| [ ] | `StandardOCRParserContext`에 `raw_json`/`raw_text`/`provider_raw_response`가 없는가 |
| [ ] | `StandardOCRParserContext`가 fixture에서 안전하게 생성되는가 |
| [ ] | `business_number`가 금액 후보와 분리되는가 |
| [ ] | `vat_missing`, `vat_review_hint`가 명시 부가세와 분리되는가 |
| [ ] | `StandardOCRParserContext` 테스트가 있는가 |
| [ ] | Golden Fixture context shape 비교가 가능한가 |
| [ ] | 기존 end-to-end 테스트가 깨지지 않는가 |
| [ ] | 기존 `ExcelExporter` 산출물 구조가 변경되지 않았는가 |
| [ ] | 기존 Processing History DB schema가 변경되지 않았는가 |

## 11. Local OCR Runtime 점검

| 체크 | 항목 |
|---|---|
| [ ] | `OCR_PROVIDER=paddle` 설정 후보가 문서화되어 있는가 |
| [ ] | PaddleOCR 미설치 시 앱이 안전하게 실패하거나 명확한 안내를 하는가 |
| [ ] | Local OCR Runtime은 전체 로컬 절대경로를 화면/DB/엑셀에 노출하지 않는가 |
| [ ] | 대량 처리 시 평균 처리시간을 측정할 수 있는가 |
| [ ] | Azure fallback 조건이 정의되어 있는가 |

## 11-1. Azure Adapter 표준화 체크리스트

| 체크 | 항목 |
|---|---|
| [ ] | Azure raw response가 Parser로 직접 전달되지 않는다 |
| [ ] | Azure SDK response object를 Parser가 import하지 않는다 |
| [ ] | Azure raw JSON 전체가 `StandardOCRResult`에 저장되지 않는다 |
| [ ] | Azure raw text 전체가 `StandardOCRResult`에 저장되지 않는다 |
| [ ] | `provider_fields`가 raw JSON 저장소로 사용되지 않는다 |
| [ ] | `provider_fields`에는 비민감 metadata와 adapter 진단 요약만 들어간다 |
| [ ] | `tests/test_azure_standard_adapter.py`에서 `provider_fields` 금지 키와 count/flag metadata를 검증한다 |
| [ ] | sanitized Azure fixture 3종으로 성공/edge/failed 변환을 검증한다 |
| [ ] | Azure endpoint 전체 URL이 화면/DB/엑셀/로그/fixture에 없다 |
| [ ] | `operation_location` 전체 URL이 화면/DB/엑셀/로그/fixture에 없다 |
| [ ] | API key, secret, token이 코드/문서/fixture에 없다 |
| [ ] | Azure field는 `StandardOCRTextBlock`, `StandardOCRKeyValueCandidate`, `StandardOCRTableCandidate`로 정규화된다 |
| [ ] | `quantity`, `approval_number`, `footer_number`, `business_number`가 amount candidate와 분리된다 |
| [ ] | `vat_missing`, `vat_review_hint`가 명시 부가세와 분리된다 |
| [ ] | Azure `diagnostic_code`/`warnings`는 비민감 코드와 짧은 메시지만 포함한다 |
| [ ] | 기존 Azure Provider 동작은 유지된다 |
| [ ] | 기존 `AzureProvider.extract()` 반환값이 변경되지 않았다 |
| [ ] | 기존 Azure Provider public interface가 유지된다 |
| [ ] | Azure Provider 테스트가 실제 Azure API key 없이 통과한다 |
| [ ] | Azure Adapter integration contract test가 있다 |
| [ ] | Adapter output이 `StandardOCRParserContext`로 변환된다 |
| [ ] | Adapter output이 기존 `ReceiptParser`에 직접 연결되지 않았다 |
| [ ] | `provider_fields`가 parser context로 그대로 전달되지 않는다 |
| [ ] | Azure Provider 연결과 Parser 전환이 분리되어 있다 |
| [ ] | 8주차 Parser 전환 진입 조건이 문서화되어 있다 |
| [ ] | 기존 `ReceiptParser` 동작은 유지된다 |
| [ ] | 기존 `ExcelExporter` 산출물 구조는 유지된다 |
| [ ] | 기존 Processing History DB schema는 유지된다 |
| [ ] | 기존 end-to-end export flow 테스트가 깨지지 않는다 |

## 11-2. Parser 표준 입력 전환 체크리스트

| 체크 | 항목 |
|---|---|
| [ ] | `ReceiptParser`가 Provider raw response를 직접 받지 않는다 |
| [ ] | `ReceiptParser`가 Azure SDK response object를 import하지 않는다 |
| [ ] | `ReceiptParser`가 PaddleOCR/Tesseract/ML Kit/Apple Vision 원본 구조를 직접 참조하지 않는다 |
| [ ] | `StandardOCRParserContext` 기반 Parser entry 추가 계획이 있다 |
| [ ] | 기존 raw_text 기반 Parser 경로를 즉시 삭제하지 않는다 |
| [ ] | compatibility wrapper 전략이 문서화되어 있다 |
| [ ] | Parser 입력에 `raw_json`/`raw_text`/`provider_raw_response`/`full_ocr_text`가 없다 |
| [ ] | Parser 입력에 endpoint/`operation_location`/API key/전체 로컬 절대경로가 없다 |
| [ ] | `quantity`, `approval_number`, `footer_number`, `business_number`가 amount candidate와 분리된다 |
| [ ] | `vat_missing`, `vat_review_hint`가 명시 부가세와 분리된다 |
| [ ] | mock fixture 기반 Parser 테스트 계획이 있다 |
| [ ] | azure-like fixture 기반 Parser 테스트 계획이 있다 |
| [ ] | Azure Adapter output 기반 Parser 테스트 계획이 있다 |
| [ ] | edge-case fixture 기반 Parser 테스트 계획이 있다 |
| [ ] | legacy raw_text Parser 결과와 standard context Parser 결과의 핵심 필드 비교 계획이 있다 |
| [ ] | 기존 `ReceiptRecord` 구조가 대규모로 변경되지 않는다 |
| [ ] | 기존 `ExcelExporter` 산출물 구조가 변경되지 않는다 |
| [ ] | 기존 Processing History DB schema가 변경되지 않는다 |
| [ ] | 기존 end-to-end export flow 테스트가 유지된다 |
| [ ] | 8주차-D에서 Validator/CategoryRules/CardMatcher/ExcelExporter/Processing History 회귀 테스트가 실행된다 |

## 12. Mobile OCR Standard 점검

| 체크 | 항목 |
|---|---|
| [ ] | 모바일 앱도 `StandardOCRResult`를 생성하는 방향인가 |
| [ ] | Android ML Kit과 iOS Apple Vision 결과를 Adapter로 변환하는 전략이 있는가 |
| [ ] | 앱은 상세 검수/처리 이력/카드내역 대조 전체를 처음부터 구현하지 않는가 |
| [ ] | 앱에서 생성한 JSON/ZIP을 웹/PC에서 이어 처리하는 후보가 문서화되어 있는가 |

## Week 8-B Parser Entry Checkpoints

| Check | Item |
|---|---|
| [ ] | `ReceiptParser.parse_standard_context(...)` exists and returns `ReceiptRecord`. |
| [ ] | `ReceiptParser.parse_from_standard_ocr(...)` routes through `StandardOCRParserContext`. |
| [ ] | Existing `ReceiptParser.parse(...)` signature and raw_text path remain unchanged. |
| [ ] | New parser entry is not wired to Streamlit, AzureProvider, MockProvider, or provider factory. |
| [ ] | Mock standard fixture can produce a `ReceiptRecord` through the new entry. |
| [ ] | Azure-like standard fixture can produce separated gross/discount/final/paid amount fields. |
| [ ] | Edge-case fixture keeps quantity, approval number, footer number, and business number out of amount candidates. |
| [ ] | Azure adapter output can become `StandardOCRParserContext` and then `ReceiptRecord`. |
| [ ] | Failed or partial context becomes a review-required record with non-sensitive warnings. |
| [ ] | Parser output does not expose raw JSON, raw text, provider raw response, endpoint, operation location, API key, token, secret, or absolute local paths. |
| [ ] | 8-C still needs deeper legacy-vs-standard fixture comparison tests. |
| [ ] | 8-D still needs downstream Validator/Exporter/History regression checks. |

## Week 8-C Parser Fixture Comparison Checkpoints

| Check | Item |
|---|---|
| [ ] | `tests/test_receipt_parser_standard_comparison.py` compares standard parser output across mock, azure-like, edge-case, and Azure adapter fixtures. |
| [ ] | Limited legacy raw_text fixtures exist under `tests/fixtures/parser_legacy/` for core-field comparison only. |
| [ ] | Legacy raw_text parser path and `ReceiptParser.parse(...)` public interface remain unchanged. |
| [ ] | Standard parser output keeps quantity, approval number, footer number, and business number out of amount fields. |
| [ ] | `vat_missing` and `vat_review_hint` do not populate explicit `vat_amount`. |
| [ ] | Failed Azure adapter output becomes a review-required record with non-sensitive warnings. |
| [ ] | Sensitive categories are category-only and do not expose raw sensitive values. |
| [ ] | `provider_fields` raw metadata is not copied to `ReceiptRecord`. |
| [ ] | Parser output does not expose raw JSON, raw text, provider raw response, endpoint, operation location, API key, token, secret, or absolute local paths. |
| [ ] | Downstream-ready `ReceiptRecord` shape is present, but Validator/CategoryRules/CardMatcher/ExcelExporter/Processing History regression remains 8-D scope. |

## Week 8-D Downstream Regression Checkpoints

| Check | Item |
|---|---|
| [ ] | Standard Parser records pass through `ReceiptValidator` without provider raw response or raw payload exposure. |
| [ ] | `CategoryRules` still works from `ReceiptRecord.merchant_name` and does not consume `StandardOCRResult` or provider raw response. |
| [ ] | `CardMatcher` still works from `ReceiptRecord` and `CardTransaction`, including amount/non-amount separation. |
| [ ] | `ExcelExporter` creates the existing sheet set and keeps existing summary/review headers. |
| [ ] | Excel output does not expose OCR raw text, provider raw JSON, `provider_fields`, endpoint, operation location, API key, token, secret, or absolute local paths. |
| [ ] | Processing History save/read works with Standard Parser records without DB schema changes. |
| [ ] | Processing History rows do not store provider raw JSON, raw OCR text, `provider_fields`, or absolute local paths. |
| [ ] | Provider independence test confirms `provider="paddleocr"` candidate records pass downstream without special casing. |
| [ ] | `requirements.txt` does not add PaddleOCR or Tesseract dependencies during 8-D. |
| [ ] | Existing raw_text parser path, Provider code, AzureStandardOCRAdapter, ExcelExporter structure, Processing History DB schema, and Streamlit UI remain unchanged. |
| [ ] | Existing end-to-end export flow remains passing. |
| [ ] | 9주차 PaddleOCR Local Provider PoC entry conditions are documented. |

## Week 9-A PaddleOCR Local Provider PoC Checklist

| Check | Item |
|---|---|
| [ ] | `OCR_PROVIDER=paddle` candidate is documented, but the default provider is not changed. |
| [ ] | `PaddleOCRProvider` must return `StandardOCRResult`. |
| [ ] | `PaddleStandardOCRAdapter` is responsible for converting PaddleOCR-like output into `StandardOCRResult`. |
| [ ] | `ReceiptParser` does not receive PaddleOCR raw output. |
| [ ] | `ReceiptValidator`, `CategoryRules`, `CardMatcher`, and `ExcelExporter` do not receive PaddleOCR raw output. |
| [ ] | `paddleocr` import must be lazy and optional. |
| [ ] | Default pytest must pass when `paddleocr` is not installed. |
| [ ] | Default pytest must not download models, call network resources, or run actual PaddleOCR. |
| [ ] | Actual PaddleOCR OCR tests are opt-in only. |
| [ ] | Week 9 PoC is image-first, limited to JPG/JPEG/PNG-style inputs. |
| [ ] | PDF processing is deferred to follow-up work. |
| [ ] | PaddleOCR raw output is not stored in DB, Excel, UI, logs, fixtures, or test output. |
| [ ] | Full OCR raw text is not stored in DB, Excel, UI, logs, fixtures, or test output. |
| [ ] | Full local absolute paths are not stored in `StandardOCRResult`, DB, Excel, UI, logs, fixtures, or test output. |
| [ ] | `provider_fields` is not used as a raw output store. |
| [ ] | Week 9-B adapter fixtures are sanitized/dummy data, not actual customer files or full raw PaddleOCR output. |
| [ ] | Week 9-C provider implementation remains optional dependency based. |
| [ ] | Week 9-D actual OCR smoke test is gated by an explicit opt-in environment variable. |
| [ ] | 10주차 Azure vs PaddleOCR comparison uses `StandardOCRResult`, `StandardOCRParserContext`, and `ReceiptRecord` fields, not provider raw output. |

## Week 9-B PaddleOCR-like Adapter Fixture Checklist

| Check | Item |
|---|---|
| [x] | `PaddleStandardOCRAdapter` converts sanitized PaddleOCR-like mapping input to `StandardOCRResult`. |
| [x] | Regular, edge, and empty/failed sanitized Paddle fixture files exist under `tests/fixtures/paddle/`. |
| [x] | Adapter output uses `provider="paddleocr"` and `engine_runtime="pc_local"`. |
| [x] | `provider_fields` contains only non-sensitive metadata and count/flag values. |
| [x] | Fixture and output tests reject raw output, raw OCR text, image/model/absolute paths, endpoint, key, token, secret, and password exposure. |
| [x] | `quantity`, `approval_number`, `footer_number`, and `business_number` remain non-amount candidates. |
| [x] | `vat_missing` and `vat_review_hint` remain review hints, not explicit `vat_amount`. |
| [x] | Paddle-like bbox and confidence values are normalized into `StandardOCRTextBlock`. |
| [x] | Empty/failed Paddle-like results carry non-sensitive `diagnostic_code` and warning context. |
| [x] | Adapter output can build `StandardOCRParserContext` and can be parsed by the standard parser entry in tests. |
| [x] | 9주차-B does not add `PaddleOCRProvider`, actual `paddleocr` import, actual OCR execution, PDF handling, provider factory changes, default provider changes, or `requirements.txt` changes. |
## Week 9-C Optional PaddleOCRProvider Checklist

- [x] `PaddleOCRProvider` is added as an optional provider candidate.
- [x] `PaddleOCRProvider` returns `StandardOCRResult`.
- [x] `PaddleOCRProvider` reuses `PaddleStandardOCRAdapter`.
- [x] `paddleocr` is not imported at module top level.
- [x] Provider import and provider construction do not require `paddleocr` to be installed.
- [x] Missing `paddleocr` is reported as a failed `StandardOCRResult` with a non-sensitive diagnostic code.
- [x] Warnings do not include raw traceback, full local path, model path, or environment details.
- [x] PDF input is marked unsupported/deferred without adding PDF conversion code.
- [x] Provider factory supports `OCR_PROVIDER=paddle` and optional `paddleocr` alias.
- [x] Default provider remains unchanged.
- [x] Provider factory tests do not execute real OCR.
- [x] `requirements.txt` is not changed and no `paddleocr` dependency is added.
- [x] Parser, Validator, CategoryRules, CardMatcher, ExcelExporter, Processing History DB, and Streamlit UI remain unchanged.
- [x] 9-D opt-in smoke test entry conditions are documented.

## Week 9-D Opt-In Local OCR Smoke Test Checklist

- [x] Real PaddleOCR image smoke test is opt-in only.
- [x] Smoke test skips unless `RUN_PADDLEOCR_TESTS` is explicitly enabled.
- [x] Smoke test skips unless `PADDLEOCR_TEST_IMAGE_PATH` is configured.
- [x] Smoke test skips when the configured file is missing or not a supported image extension.
- [x] Smoke test skips when `paddleocr` is not installed.
- [x] Default pytest does not run real OCR.
- [x] Smoke test validates `StandardOCRResult` output, not provider raw output.
- [x] Smoke test validates parser context conversion.
- [x] Smoke test validates the standard parser entry can be called without provider raw output.
- [x] PDF input remains unsupported/deferred without PDF conversion.
- [x] No real customer image or real OCR image fixture is committed.
- [x] Smoke test failure classification is documented as environment/provider/security/quality.
- [x] 10-week Azure vs PaddleOCR comparison remains a separate follow-up.

## Week 10-A Azure vs PaddleOCR Quality Comparison Contract Checklist

- [x] Quality comparison uses `StandardOCRResult`, `StandardOCRParserContext`, and `ReceiptRecord`, not provider raw output.
- [x] `docs/ocr_quality_comparison_contract.md` defines the comparison purpose, scope, input contract, metrics, and fallback candidate signals.
- [x] Core comparison fields include date, merchant, business number, total amount, VAT fields, payment fields, review status, warnings, confidence, and provider status.
- [x] Report row contract excludes provider raw JSON, full OCR raw text, full local absolute paths, endpoint, operation location, API key, token, secret, and raw traceback.
- [x] Sample set rules require synthetic or non-sensitive test data and file-name-only reporting.
- [x] Expected fixture strategy is defined around safe `sample_id` and core `ReceiptRecord` fields, not provider raw output.
- [x] Report row contract includes low-confidence line counting as a future comparison signal.
- [x] PDF PaddleOCR handling remains deferred.
- [x] 10-A does not implement safe OCR preview UI.
- [x] 10-A does not implement side-by-side report code.
- [x] 10-A does not implement statistics aggregation or automatic Azure fallback execution.
- [x] Existing ExcelExporter sheet/column structure remains unchanged.
- [x] Existing Processing History DB schema remains unchanged.
## Week 10-B Safe OCR Preview Checklist

- [x] Safe preview rows are built from `StandardOCRResult.text_blocks`, not provider raw output.
- [x] PaddleOCR smoke-test results can display a limited preview in Settings.
- [x] Azure adapter output can reuse the same preview utility through `StandardOCRResult`.
- [x] Preview rows include line order, page index, block id, text, confidence label, low-confidence flag, sensitive category, and redaction flag.
- [x] Preview summary includes provider, status, diagnostic code, source file name, text block count, preview line count, low-confidence line count, redacted line count, max lines, and low-confidence threshold.
- [x] Sensitive lines remain `[REDACTED]`.
- [x] Full OCR raw text, provider raw output, raw JSON, full local absolute paths, endpoints, keys, secrets, tokens, and raw tracebacks are not displayed or stored.
- [x] No raw text download or full OCR preview download is added.
- [x] Side-by-side reports, statistics aggregation, `field_match_score`, fallback automation, provider default changes, ExcelExporter changes, Processing History schema changes, and PDF PaddleOCR handling remain out of scope.
- [x] Default pytest does not call real Azure or real PaddleOCR execution.
## Week 10-C Azure vs PaddleOCR Side-by-side Report

- [x] Side-by-side report utility compares only `StandardOCRResult`, `StandardOCRParserContext`, and parsed `ReceiptRecord` output.
- [x] Provider failure details use sanitized `diagnostic_detail_code` categories only, not raw provider messages or payloads.
- [x] Settings UI requires an explicit single-image upload and button press before Azure/PaddleOCR execution.
- [x] Provider summary includes per-sample elapsed time, status, diagnostic code, text block count, candidate count, review hint count, sensitive category count, warning count, full-result low-confidence count, and redacted count.
- [x] Core `ReceiptRecord` field rows include Azure/Paddle values plus `azure_present`, `paddle_present`, and `is_same` flags for Week 10-D reuse.
- [x] Default provider flow, ExcelExporter sheets/columns, and Processing History DB schema are unchanged.
- [x] No raw provider output, full OCR text, raw JSON, full local paths, Azure endpoint URLs, operation URLs, secrets, raw tracebacks, customer files, or raw OCR fixtures are added.
- [x] No default pytest path calls real Azure or real PaddleOCR.
- [ ] Week 10-D statistics, formal score, aggregate fallback criteria, and fallback recommendation rules remain unimplemented by design.

## Review UX Quality Triage

- [x] Review table shows manual triage columns for priority, missing fields, and quality-check flags.
- [x] Review screen supports status and issue filters without dropping hidden rows when edits are saved.
- [x] Selected-receipt detail panel shows only safe parsed fields and source file names.
- [x] Detail and table views do not expose provider raw output, full OCR text, raw JSON, full local paths, secrets, or endpoint URLs.
- [x] ExcelExporter sheets/columns, Processing History schema, default provider, automatic fallback, formal score, and statistics UI remain unchanged.

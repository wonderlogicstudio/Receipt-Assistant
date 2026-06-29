# 변경 관리 규칙

## Week 9-A PaddleOCR Provider PoC Change Control

- Adding `PaddleOCRProvider` is a Provider expansion change.
- PaddleOCRProvider implementation and Parser changes must be separate work items.
- PaddleOCRProvider implementation and ExcelExporter or Processing History changes must be separate work items.
- Do not add `paddleocr` directly to `requirements.txt` without an explicit dependency decision; prefer optional dependency or separate install documentation.
- Default pytest must pass without PaddleOCR installed.
- PaddleOCR raw output must not be passed directly to Parser, Validator, CategoryRules, CardMatcher, or ExcelExporter.
- Full PaddleOCR raw output, full OCR raw text, full local absolute paths, actual customer files, and actual sensitive values must not be stored or displayed in DB, Excel, UI, logs, fixtures, or test output.
- Week 9-B is adapter/fixture only and must not connect provider factory.
- Week 9-C may add an optional provider and provider factory candidate, but actual OCR execution must stay out of default pytest.
- Week 9-D may add opt-in smoke tests only; PDF handling remains out of Week 9 scope.

Rollback criteria:

- Default pytest fails when PaddleOCR is not installed.
- Default app startup fails.
- `OCR_PROVIDER=mock` flow fails.
- Existing Azure Provider flow fails.
- Parser, Validator, CategoryRules, CardMatcher, or ExcelExporter imports or consumes PaddleOCR raw output directly.
- Full raw output, full OCR text, endpoint, key, token, secret, or full local absolute path exposure occurs.
- Heavy OCR dependency is added to `requirements.txt` and breaks the default environment.
- Actual PaddleOCR OCR test runs in default pytest.
- PDF handling is pulled into Week 9 scope.

## 1. 목적

이 문서는 영수증 OCR 엑셀 비서 MVP의 범위, 문서, 코드 변경을 안전하게 관리하기 위한 기준입니다.

## 2. 고정 방향

MVP의 고정 방향은 다음과 같습니다.

```text
영수증 이미지/PDF + 카드 사용내역 CSV/XLSX 업로드
→ OCR/Parser 처리
→ 사용자 검수
→ 세무사 전달용 표준 엑셀 정리 파일 다운로드
→ 처리 이력 조회와 기존 export 파일 재다운로드
```

MVP는 증빙 정리 보조 도구입니다. 사용자 확인 없이 결과를 확정하지 않습니다.

## 3. 문서 변경이 필요한 경우

| 변경 내용 | 함께 확인할 문서 |
|---|---|
| 실행 방법 변경 | README.md, AGENTS.md |
| MVP 범위 변경 | README.md, PLAN.md, DECISIONS.md |
| 데이터 모델 변경 | SPEC.md, tests |
| 엑셀 시트/컬럼 변경 | SPEC.md, CHECKLIST.md, docs/sample_output_schema.md |
| 처리 이력 DB 구조 변경 | SPEC.md, PLAN.md |
| 화면 메뉴 변경 | README.md, PLAN.md, CHECKLIST.md |
| 파일럿 절차 변경 | docs/pilot_guide.md, docs/sample_user_flow.md |
| 테스트 명령 변경 | README.md, AGENTS.md |
| OCR Provider 추가/변경 | SPEC.md, CHECKLIST.md, docs/standard_ocr_result_schema.md |
| StandardOCRResult schema_version 변경 | SPEC.md, CHECKLIST.md, tests/fixtures |

## 4. 변경 절차

1. 관련 문서와 코드를 먼저 확인한다.
2. 기능 변경이 필요한지, 문서 동기화만 필요한지 구분한다.
3. MVP 범위를 넓히는 변경은 바로 구현하지 않고 결정 기록을 남긴다.
4. 코드 변경이 있으면 테스트를 함께 작성하거나 기존 테스트를 확인한다.
5. 주요 결정은 DECISIONS.md에 기록한다.
6. `python -m compileall app tests`와 `python -m pytest`를 실행한다.
7. Git 변경사항에 민감 파일이 포함되지 않았는지 확인한다.
8. OCR Provider 원본 응답 구조가 바뀌어도 Parser 입력 계약은 `StandardOCRResult`로 유지한다.
9. `StandardOCRResult` `schema_version` 변경 시 fixture와 문서도 함께 업데이트한다.
10. Parser/Validator 버전 변경 시 `parser_version`/`validator_version` 기록 필요 여부를 확인한다.

## 5. 금지되는 변경

명시적 요청 없이 아래 작업을 진행하지 않습니다.

- 로그인/권한관리
- 결제 기능
- 클라우드 배포
- 모바일 앱
- 홈택스/카드사 연동
- 회계 프로그램 API 연동
- 과거 작업 재검수
- 과거 엑셀 재생성
- 실제 cleanup 삭제 버튼
- API key 입력 UI
- OCR Provider 변경 UI
- OpenAI API 기반 전체 자동 보정
- 장기 파일 보관 전제 기능

OCR Provider 독립화 기준:

- OCR Provider 추가는 범위 확장 변경으로 봅니다.
- Provider 추가 시 SPEC.md, PLAN.md, CHECKLIST.md, DECISIONS.md를 함께 확인합니다.
- Parser가 provider raw response에 직접 의존하는 변경은 금지합니다.
- `StandardOCRResult` 스키마 변경 시 Golden Test Fixture 영향도를 확인합니다.
- OCR raw JSON 전체, OCR raw text 전체, 전체 로컬 절대경로, API key, 실제 고객 파일이 노출되는 변경은 금지합니다.
- `ReceiptParser` 입력을 `StandardOCRResult` 또는 `StandardOCRParserContext`로 바꾸는 작업은 영향도 있는 구조 변경으로 봅니다.
- Parser 전환 시 SPEC.md, CHECKLIST.md, DECISIONS.md, tests를 함께 확인합니다.
- Provider Adapter 변경과 Parser 변경은 가능하면 별도 커밋으로 분리합니다.
- `ExcelExporter`, Processing History DB, Streamlit UI 변경은 별도 변경으로 분리합니다.
- Azure Adapter 구현은 Provider 독립화 구조 변경으로 봅니다.
- Azure Adapter 변경 시 SPEC.md, CHECKLIST.md, DECISIONS.md, tests를 함께 확인합니다.
- Azure Adapter 구현, Azure Provider 연결, Parser 전환은 가능하면 별도 커밋으로 분리합니다.
- Azure Provider 변경과 Parser 변경은 한 작업에서 동시에 하지 않습니다.
- Azure raw response를 Parser에 직접 전달하는 변경은 금지합니다.
- `provider_fields`에 raw JSON 전체를 넣는 변경은 금지합니다.
- Azure endpoint 전체 URL, API key, `operation_location` 전체 URL이 화면/DB/엑셀/로그/fixture에 노출되는 변경은 금지합니다.
- 기존 Azure Provider 동작을 바꾸는 경우에는 회귀 테스트와 변경 사유를 남깁니다.
- Azure Provider에 Adapter를 연결하는 작업은 기존 OCR 흐름에 영향을 줄 수 있으므로 회귀 테스트가 필요합니다.
- `AzureProvider.extract()` 반환 타입 변경은 별도 주요 변경으로 보며, 7주차-C에서는 금지합니다.
- Azure Adapter bridge/helper 추가는 운영 흐름에 연결하지 않는 경우 낮은 위험 변경으로 봅니다.
- Parser 전환은 8주차 작업으로 분리합니다.
- 8주차 Parser 전환 전에는 Azure Provider 회귀 테스트와 end-to-end export flow 테스트가 통과해야 합니다.
- rollback 기준은 기존 Azure Provider 테스트 실패, end-to-end export flow 실패, Parser/Exporter/DB/UI 변경 발생, raw JSON/raw text/endpoint/`operation_location` 노출 발생입니다.

Parser 표준 입력 전환 기준:

- `ReceiptParser` 입력 변경은 핵심 구조 변경으로 봅니다.
- Parser 전환 시 SPEC.md, CHECKLIST.md, DECISIONS.md, tests를 함께 확인합니다.
- Parser 전환과 ExcelExporter 변경은 별도 커밋으로 분리합니다.
- Parser 전환과 Processing History DB 변경은 별도 커밋으로 분리합니다.
- Parser 전환과 Streamlit UI 변경은 별도 커밋으로 분리합니다.
- 기존 raw_text Parser 경로 제거는 별도 결정과 회귀 테스트 통과 후 진행합니다.
- Parser가 provider raw response를 직접 import하거나 참조하는 변경은 금지합니다.
- Parser 입력에 raw JSON 전체, raw text 전체, endpoint, key, 전체 경로가 들어가는 변경은 금지합니다.
- 8주차-B에서는 새 Parser entry 추가만 허용하고 downstream 구조 변경은 하지 않습니다.
- 8주차-C에서는 fixture 비교 테스트를 중심으로 하고 ExcelExporter 변경은 하지 않습니다.
- 8주차-D에서 downstream 회귀를 점검하되, 구조 변경이 필요하면 별도 작업으로 분리합니다.

Parser 전환 rollback 기준:

- 기존 end-to-end export flow 실패
- 기존 Parser 테스트 실패
- ExcelExporter 테스트 실패
- Processing History 테스트 실패
- `ReceiptRecord` 핵심 필드 누락 증가
- raw JSON/raw text 전체 노출 발생
- provider raw response가 Parser로 전달됨
- `AzureProvider.extract()` 반환값 변경 발생
- Processing History DB schema 변경 발생
- 기존 raw_text Parser 경로 삭제 발생

이번 단계에서 금지되는 변경:

- `PaddleOCRProvider` 실제 구현
- `TesseractProvider` 실제 구현
- ML Kit 앱 구현
- Apple Vision 앱 구현
- FastAPI 서버 구현
- Tauri/Electron 앱 구현
- Provider 변경 UI 구현
- API key 입력 UI 구현
- 기존 Processing History DB 대규모 변경
- 기존 `ExcelExporter` 대규모 변경

## 6. 보안 기준

문서, 코드, 테스트, 화면, DB, 엑셀에는 아래 정보가 노출되면 안 됩니다.

- `.env` 내용
- API key, secret, token, password
- Azure endpoint 전체 URL
- 전체 로컬 절대경로
- OCR raw text 전체
- provider raw JSON 전체
- 카드 사용내역 원문 전체
- 실제 카드번호 전체
- 주민번호, 전화번호 등 민감정보
- 실제 고객 파일

## 7. 문서 동기화 전용 작업

코드 기능 변경 없이 문서만 현재 구현과 맞추는 경우:

1. README.md, PLAN.md, SPEC.md, CHECKLIST.md, DECISIONS.md, CHANGE_CONTROL.md를 확인한다.
2. app/, tests/, requirements.txt, .env.example, .gitignore, docs/를 읽기 전용으로 확인한다.
3. 실제 구현과 다른 문서만 수정한다.
4. 구현되지 않은 기능을 구현된 것처럼 쓰지 않는다.
5. 문서에 실제 key, 개인정보, 전체 로컬 경로, 실제 파일명을 넣지 않는다.
6. 수정 후 compileall과 pytest를 실행한다.

## 8. 커밋 전 확인

```bash
python -m compileall app tests
python -m pytest
git status
git diff --check
```

확인 항목:

- `.env`가 포함되지 않는다.
- `data/uploads`, `data/outputs`, `output` 실제 파일이 포함되지 않는다.
- `data/app.db`, `*.db`가 포함되지 않는다.
- 실제 고객 파일이나 실제 영수증 파일이 포함되지 않는다.
- 테스트가 통과한다.
## Week 9-C PaddleOCRProvider Candidate Change Control

- Adding `PaddleOCRProvider` and provider factory support for `OCR_PROVIDER=paddle` is allowed only as an optional provider candidate.
- The default OCR provider must remain unchanged.
- `paddleocr` must remain an optional dependency and must not be added to `requirements.txt` in this step.
- Provider import, provider factory import, and default pytest must pass without `paddleocr` installed.
- Real OCR execution must stay out of default pytest and move to a 9-D opt-in smoke test.
- PDF conversion and multi-page handling remain deferred.
- Roll back or disable the candidate path if provider factory import fails, mock/Azure provider creation breaks, default pytest requires `paddleocr`, or raw PaddleOCR output/full local paths are exposed.

## Week 9-D PaddleOCR Smoke Test Change Control

- Actual PaddleOCR OCR execution may only be added behind an explicit opt-in flag.
- Default pytest must skip real OCR and must pass without `paddleocr` installed.
- Smoke tests must not commit or require real customer images.
- Smoke test reports must not include full local paths, raw traceback, raw output, or environment dumps.
- PDF handling remains deferred; adding PDF conversion is out of scope.
- Roll back or disable the smoke test if it runs without opt-in, exposes raw output/path data, or breaks existing mock/Azure/parser/downstream regressions.

## Week 10-A Azure vs PaddleOCR Quality Comparison Contract Change Control

- 10-A is a contract and documentation step only.
- Quality comparison must use `StandardOCRResult`, `StandardOCRParserContext`, and existing `ReceiptRecord` fields.
- Provider raw output, full OCR raw text, full local absolute paths, endpoints, operation locations, API keys, secrets, tokens, and raw tracebacks must not become report inputs or outputs.
- `provider_fields` may be used only for non-sensitive count/flag metadata and adapter diagnostic summaries.
- Expected fixtures must use synthetic or non-sensitive samples and expected core `ReceiptRecord` fields instead of provider raw output.
- Safe OCR preview, side-by-side report generation, statistics aggregation, and fallback automation must remain separate 10-B/C/D work items.
- PDF PaddleOCR handling remains deferred.
- Existing Parser raw-text compatibility path, ExcelExporter structure, Processing History DB schema, default provider, and provider factory behavior must not change in 10-A.
- Default pytest must not run real Azure or real PaddleOCR execution for this contract step.

Rollback criteria:

- Any document describes safe preview, side-by-side report generation, statistics summary, or Azure fallback automation as already implemented.
- Any comparison contract requires provider raw output, full OCR raw text, full local absolute paths, actual customer files, or secrets.
- Any expected fixture strategy requires actual customer files or full provider raw payloads.
- Any code change in 10-A alters default provider behavior, Excel columns/sheets, Processing History schema, or Parser raw-input boundaries.
## Week 10-B Safe OCR Preview Change Control

- 10-B may add a provider-neutral safe preview utility for `StandardOCRResult.text_blocks`.
- 10-B may display the safe preview in the Settings PaddleOCR smoke-test box after an opt-in smoke run.
- The preview must expose only limited safe rows, confidence labels, low-confidence flags, redaction flags, safe category labels, and summary counts.
- The preview must not display, persist, export, or log provider raw output, full OCR raw text, raw JSON, full local absolute paths, endpoint URLs, operation-location URLs, secrets, tokens, raw tracebacks, or actual customer files.
- The preview utility may support Azure adapter results through `StandardOCRResult`; it must not add real Azure API execution to default tests or UI flows.
- 10-B must not implement side-by-side comparison, statistics aggregation, `field_match_score`, automatic Azure fallback execution, provider default changes, ExcelExporter sheet/column changes, Processing History schema changes, Parser raw-input changes, or PDF PaddleOCR handling.

Rollback criteria:

- Revert the 10-B preview changes if any UI/log/test fixture exposes full OCR raw text, provider raw JSON, full local paths, secrets, endpoint URLs, or raw tracebacks.
- Revert if the preview path starts calling real Azure/PaddleOCR during default pytest.
- Revert if the change modifies default provider selection, ExcelExporter output structure, Processing History DB schema, or Parser raw-input boundaries.
- Revert if 10-B documentation claims side-by-side reports, statistics, `field_match_score`, or Azure fallback automation are implemented.
## Week 10-C Side-by-side Report Change Control

Week 10-C is limited to a diagnostic side-by-side report for one explicit sample image. It may add UI helpers, sanitized comparison utilities, and fixture-based tests. It must not change the production OCR default, Excel export format, Processing History schema, parser raw-input boundary, or provider adapter contracts.

Rollback or correction is required if the change introduces any of the following:

- Provider raw output, full OCR text, raw JSON, full local paths, Azure endpoint URLs, operation URLs, secrets, or raw tracebacks in UI, DB, Excel, logs, fixtures, or test output.
- Default pytest execution that calls real Azure APIs, downloads PaddleOCR models, or runs real PaddleOCR OCR.
- A Parser path that accepts provider raw response objects instead of `StandardOCRParserContext`.
- A formal field match score, aggregate statistics, fallback recommendation, or automatic Azure retry policy before Week 10-D.
- Any ExcelExporter column/sheet change, Processing History DB schema change, or production provider default change.

Safe diagnostic detail codes are allowed for provider failures when they are sanitized categories only, for example `quota_or_rate_limit` for Azure HTTP 403 quota/rate-limit responses. Roll back or correct the change if raw Azure error messages, endpoint URLs, operation URLs, request headers, keys, raw tracebacks, or provider payloads are exposed as diagnostic details.

## Week 10-D-prep Synthetic PaddleOCR Fixture Change Control

Week 10-D-prep may add synthetic sanitized PaddleOCR line fixtures, expected
`ReceiptRecord` baselines, and fixture-driven parser tests. It may improve parser
or Paddle candidate rules only when the rule is conservative and label-based.

Allowed improvements:

- Merchant candidates from explicit labels such as `상호`, `상호명`, `매장명`,
  `가맹점명`, and `점포명`.
- Date, business-number, payment-method, labeled amount, explicit supply/VAT, and
  amount OCR-character normalization rules.
- Security tests that reject raw payload keys, full paths, endpoints, secrets,
  tokens, and sensitive full values.

Rollback or correction is required if any of the following occur:

- Default pytest calls live Azure, imports/executes real PaddleOCR, or downloads
  OCR models.
- Fixture files include customer receipts, provider raw output, full OCR text,
  raw JSON, full local paths, endpoints, secrets, tokens, full card numbers, full
  phone numbers, resident registration numbers, passwords, or WiFi passwords.
- Parser changes guess merchant names from unlabeled first lines, infer totals
  from unlabeled maximum amounts, force broken business numbers into valid
  shapes, or use redacted sensitive lines as candidates.
- Existing parser, adapter, ExcelExporter, Processing History, provider default,
  or side-by-side comparison regressions fail.
- The change implements automatic Azure fallback, formal `field_match_score`,
  aggregate statistics UI, ExcelExporter sheet/column changes, or Processing
  History schema changes.

## Review UX Quality Triage Change Control

Review UX triage may add safe, derived review indicators and filters from
`ReceiptRecord` only. It may not call OCR providers, reprocess files, or change
the persisted history/export contracts.

Allowed changes:

- Derived review priority, missing-field, and quality-check labels.
- Status and issue filters for the existing review table.
- Safe selected-receipt detail panels that show parsed fields and source file
  names only.

Rollback or correction is required if any of the following occur:

- The review UI displays provider raw output, full OCR text, raw JSON, full local
  paths, endpoint URLs, operation URLs, secrets, tokens, or raw tracebacks.
- Filtering causes hidden review rows to be dropped or overwritten.
- The change modifies ExcelExporter sheets/columns, Processing History schema,
  default OCR provider selection, automatic fallback behavior, or formal quality
  scoring.

## New Job PaddleOCR Runtime Selection Change Control

The New Job screen may expose `PaddleOCR Local` as an explicit per-run OCR
provider option. This is a runtime override only and must not change the
configured default provider.

Allowed changes:

- Add `paddle`/`paddleocr` to the New Job runtime provider selection allowlist.
- Route `StandardOCRResult` outputs through `StandardOCRParserContext` before
  parsing.
- Show a short PaddleOCR PDF unsupported/deferred note when selected.
- Store and display source file names only.

Rollback or correction is required if any of the following occur:

- The configured default OCR provider changes.
- Default pytest runs real PaddleOCR, downloads OCR models, or requires
  `paddleocr` to be installed.
- Provider raw output, full OCR text, raw JSON, full local paths, secrets,
  endpoint URLs, operation URLs, or raw tracebacks are displayed, persisted,
  logged, or added to fixtures.
- Parser receives PaddleOCR raw output or any provider raw response object.
- ExcelExporter sheets/columns or Processing History schema change.
- Automatic Azure fallback, formal `field_match_score`, or PDF PaddleOCR support
  is implemented as part of this change.

## PaddleOCR Speed Pass Change Control

Performance work may reduce repeated local computation only when parsed output
quality and review behavior are preserved.

Allowed changes:

- Reuse a `PaddleOCRProvider` OCR engine instance for multiple images in the same
  provider instance.
- Cache pure text normalization helpers with bounded caches.
- Avoid repeated extraction of the same standard OCR candidate map during parser
  context construction.

Rollback or correction is required if any of the following occur:

- OCR quality, parser field extraction, candidate generation, validation,
  review-required behavior, or safe diagnostics regress.
- A performance shortcut disables image normalization fallback, candidate hints,
  parser checks, or validator checks.
- Default pytest runs real PaddleOCR, downloads OCR models, or requires
  `paddleocr`.
- Provider raw output, full OCR text, raw JSON, full local paths, secrets,
  endpoint URLs, operation URLs, or raw tracebacks are exposed.
- Default provider behavior, ExcelExporter sheets/columns, Processing History
  schema, automatic Azure fallback, formal scoring, or PDF PaddleOCR handling
  changes.

## Review UI Receipt Source Preview Change Control

Review source preview may help reviewers compare parsed fields with the original
receipt file, but it must stay inside the safe upload boundary and must not alter
export or history contracts.

Allowed changes:

- Add review priority, missing-field, review-reason summary, source file name,
  and source-preview status columns.
- Store selected receipt id and selected row number in session state.
- Highlight the selected row in a read-only selection table.
- Preview JPG/JPEG/PNG files only after resolving them under the configured
  upload root.
- Show a PDF notice instead of forcing PDF rendering.

Rollback or correction is required if any of the following occur:

- The UI displays full local paths, OCR raw text, provider raw JSON, raw provider
  output, endpoint URLs, secrets, raw tracebacks, or sensitive raw values.
- Source preview can open files outside `data/uploads` or accepts traversal
  paths.
- Review edits, exclusion handling, ExcelExporter sheets/columns, Processing
  History schema, default provider behavior, automatic fallback, or formal score
  behavior changes.
- The change adds mobile/PWA features, OCR provider changes, PaddleOCR accuracy
  changes, OpenAI correction, or customer test files.

## PaddleOCR Split Label Quality Hardening Change Control

PaddleOCR parser-quality hardening may add conservative label-based candidate
rules when a synthetic fixture demonstrates a missing field that is visibly
present on a receipt.

Allowed changes:

- Recognize split `매출일`/`매출일자` label-value date lines when the nearby value is
  a valid `YYYYMMDD` or short labeled date.
- Recognize split `매장명` label-value merchant lines only after an explicit
  merchant label and only when the nearby value is not a date, amount, business
  number, phone number, card number, or known non-merchant label.
- Recognize unlabeled merchant segments immediately before a valid business
  number only when the segment passes merchant-like checks and is not an
  identifier, address, amount, date, phone, card, approval, tax, or total label.
- Recognize compact `YYYYMMDD HH:MM[:SS]` approval date-time patterns only with
  nearby date/time labels such as `승인시간`, `승인일시`, `거래일시`, or `매출일`.
- Add synthetic sanitized PaddleOCR fixture cases and unit tests only.

Rollback or correction is required if any of the following occur:

- Merchant names are guessed from arbitrary unlabeled lines.
- Dates are inferred from unrelated identifiers, approval numbers, or invalid
  calendar values.
- Actual customer images, full OCR text, provider raw output, raw JSON, full
  local paths, secrets, or endpoint URLs are added to fixtures, logs, UI, DB, or
  Excel output.
- Default pytest runs real Azure or real PaddleOCR, downloads OCR models, or
  requires `paddleocr`.

## Merchant Candidate Dictionary Change Control

- Adding merchant candidate tables is allowed only as separate dictionary data.
  Existing `receipt_records`, `processing_jobs`, and ExcelExporter contracts must
  remain compatible.
- Public store CSV import may store merchant name, branch name, coarse area hint,
  category names, source row hash, and batch id only.
- `merchant_master.business_number` must remain nullable because public store
  data is not a full business-number source.
- Candidate matching may rank business-number exact, alias, and fuzzy name
  candidates, but must return review-required hints only.
- NTS business status API may be used only for OCR-detected business numbers and
  must read `NTS_BUSINESS_API_KEY` from `.env`.

Rollback or correction is required if any of the following occur:

- Representative names, phone raw values, full addresses, full OCR text,
  provider raw JSON, raw API responses, full local paths, secrets, or tracebacks
  are stored or displayed.
- Merchant candidates automatically overwrite receipt merchant name, business
  number, or review status.
- Private site crawling, mass business-number collection, true-name verification,
  tax judgment, ExcelExporter sheet/column changes, or Processing History receipt
  schema changes are introduced in this step.

## Merchant Road Address Hint Change Control

- Public merchant CSV import may read only `상호명`, `지점명`, category columns,
  `도로명`, `건물본번지`, `건물부번지`, `건물명`, and `도로명주소`.
- Road-address fields may be stored in `merchant_master` for matching hints and
  duplicate detection.
- OCR-derived road-address hints may be extracted only from safe parser lines and
  used as transient candidate scoring inputs.
- Same-file detection must use allowed-column content only so unrelated CSV
  columns do not affect duplicate decisions.
- The Settings UI may import multiple CSV files sequentially but must retain no
  original CSV file after import.
- The Settings UI may raise the Streamlit browser-upload limit to 400MB per CSV
  file, but larger files must be rejected safely and the CLI path should remain
  the preferred path for near-limit imports.

Rollback or correction is required if any of the following occur:

- Representative names, phone raw values, raw CSV rows, full local paths, OCR raw
  text, provider raw JSON, or API keys are stored or displayed.
- Full address candidates are added to Excel output or used as automatic
  confirmation.
- Address-only matches overwrite `ReceiptRecord.merchant_name`,
  `business_number`, or `review_status`.
- OCR-derived address hints are stored in `ReceiptRecord`, Excel output,
  Processing History receipt rows, logs, or raw parser warnings.
- Phone, representative, business-number, approval/card, amount, or date lines
  are treated as address hints.
- Public CSV originals under `data/gov` or `govdata` are committed.
- Files larger than the configured 400MB UI limit are imported, retained, or
  reported with full local paths instead of a safe skip/error.

## Merchant Review Alias Learning Change Control

- Review alias learning may add safe reviewed merchant names to
  `merchant_alias` with `source=review`.
- It may link aliases to `merchant_master` only when business-number exact,
  normalized merchant-name exact, or a high-confidence master name match is
  available.
- It must skip uncertain master links by keeping `merchant_master_id` nullable.
- It must skip empty names, too-short names, mostly numeric/symbolic values,
  business-number patterns, phone-number patterns, representative labels,
  amount lines, dates, card identifiers, and approval identifiers.
- Repeated review saves must not keep appending the same
  `normalized_alias_name + business_number + source` row.

Rollback or correction is required if any of the following occur:

- Learned aliases automatically overwrite future `ReceiptRecord.merchant_name`,
  `business_number`, or `review_status`.
- Alias learning changes ExcelExporter sheets/columns or existing Processing
  History receipt schema.
- Raw OCR text, provider raw JSON, full local paths, representative names, phone
  raw values, full addresses, API keys, or raw tracebacks are stored or shown.
- Alias learning failure blocks review save, Excel generation, or download.
- Private crawling, mass business-number collection, NTS automatic calls, or
  OpenAI automatic correction are introduced in this step.

## Public Merchant CSV Import Performance Change Control

- Public merchant CSV import may use chunked `executemany` and one transaction
  per import batch.
- Import-time SQLite PRAGMA settings are allowed only for safe local bulk import
  performance, such as WAL, `synchronous=NORMAL`, and `temp_store=MEMORY`.
- Import result summaries may include file name, batch id, scanned/imported/
  skipped counts, duplicate-file status, elapsed seconds, and rows per second.
- Duplicate-file detection must continue to use allowed-column content hash.
- Duplicate-row detection must continue to use allowed-column row hash.

Rollback or correction is required if any of the following occur:

- A failed import leaves partial `merchant_master` rows or duplicate source logs.
- CLI/UI summaries expose full local paths, raw CSV rows, representative names,
  phone raw values, blocked columns, OCR raw text, provider raw JSON, API keys,
  or raw tracebacks.
- Bulk import changes existing `ReceiptRecord`, ExcelExporter, or Processing
  History receipt schemas.
- Address or merchant candidates become automatically confirmed.
- Public CSV originals under `data/gov` or `govdata` are committed.

## Merchant Dictionary Diagnostics Change Control

- Merchant diagnostics may read `merchant_master`, `merchant_alias`,
  `merchant_source_log`, and safe Processing History receipt fields.
- Dictionary summaries may show counts, latest import date, latest source file
  name, top category counts, duplicate-file count, and recent batch summaries.
- Candidate diagnostics may call the existing matcher only after explicit user
  action and must keep candidates as review-required hints.
- Saved ReceiptRecord diagnostics may use only merchant name, business number,
  source file name, and review status, and should report aggregate counts first.
- Business numbers shown by diagnostics must be masked as `123-**-*****`.

Rollback or correction is required if any of the following occur:

- Diagnostics automatically confirm, overwrite, or save merchant candidates.
- Diagnostics change `ReceiptRecord`, ExcelExporter sheets/columns, Processing
  History schema, matcher thresholds, default provider, NTS behavior, or OpenAI
  correction behavior.
- Raw OCR text, provider raw JSON, full local paths, phone raw values,
  representative names, raw CSV rows, API keys, raw tracebacks, or secrets are
  stored or displayed.
- Saved-record diagnostics run automatically over large history without an
  explicit button action.
- Business numbers are displayed in full instead of masked.
## Merchant Dictionary Search and Candidate Scoring Change Control

Allowed changes:

- Add a manual Settings search over `merchant_master` using bounded merchant-name
  or road-name/building-number filters.
- Add indexes that only support merchant dictionary search/matching and do not
  alter existing Processing History receipt/export schemas.
- Lower scores for very short substring fuzzy candidates unless a safe address
  hint boosts the candidate above the review threshold.
- Reduce review source preview rendering cost by showing only the selected row.

Rollback or correction is required if any of the following occur:

- Search or diagnostics expose full local paths, raw CSV rows, OCR raw text,
  provider raw JSON, representative names, phone raw values, API keys, raw
  tracebacks, or full business numbers.
- Merchant candidates automatically overwrite `ReceiptRecord.merchant_name`,
  `business_number`, `review_status`, Excel output, or Processing History rows.
- Search performs blank full-table browsing by default or makes Settings
  unusably slow on the public merchant database.

## Quality Stabilization and Review Diagnostics Change Control

Allowed changes:

- Add safe, manual Processing History diagnostics that report counts only.
- Add safe performance summaries for review dataframe generation, merchant
  candidate lookup/cache, selected source preview preparation, and merchant DB
  search query timing.
- Manually verify real PaddleOCR samples outside default pytest and report only
  safe field summaries.
- Improve selected source preview rendering and thumbnail preparation without
  changing review editing semantics.

Rollback or correction is required if any of the following occur:

- Default pytest calls real PaddleOCR, downloads OCR models, or requires live OCR
  provider access.
- Diagnostics or sample reports expose raw OCR text, provider raw JSON, full
  local paths, raw CSV rows, phone raw values, representative names, API keys,
  raw tracebacks, or full business numbers.
- Performance diagnostics write raw OCR/provider/CSV payloads to DB, UI, logs,
  tests, or Excel output.
- The change modifies existing `ReceiptRecord`, ExcelExporter sheets/columns, or
  Processing History schemas.
- Merchant/address candidates become automatically confirmed or overwrite saved
  receipt rows.
- NTS API calls or OpenAI correction are triggered automatically.

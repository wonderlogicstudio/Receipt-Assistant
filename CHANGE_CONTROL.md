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

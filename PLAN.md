# 영수증 OCR 엑셀 비서 MVP 계획

## 방향 요약

이 MVP는 로컬 Streamlit 기반의 증빙 정리 보조 도구입니다. 핵심 흐름은 파일 업로드, OCR/Parser 처리, 사용자 검수, 표준 엑셀 정리 파일 다운로드입니다.

파일럿 전에는 신규 기능 추가보다 안정화, 문서 동기화, 수동 테스트, 사용자 피드백 수집을 우선합니다.

## 완료된 기능

### 1주차

| 기능 | 상태 |
|---|---|
| Streamlit 진입점 `app/main.py` | 완료 |
| 파일 업로드 UI | 완료 |
| 안전 저장 구조 | 완료 |
| 파일명 sanitize | 완료 |
| `data/uploads/{session_id}` 저장 구조 | 완료 |
| OCR provider interface | 완료 |
| Mock OCR provider | 완료 |
| 카드 사용내역 CSV/XLSX parser | 완료 |

### 2주차

| 기능 | 상태 |
|---|---|
| ReceiptRecord 모델 | 완료 |
| OCRResult 모델 | 완료 |
| CardTransaction 모델 | 완료 |
| ReceiptParser | 완료 |
| 날짜/금액/사업자번호 정규화 | 완료 |
| 비용항목 추천 규칙 | 완료 |
| ReceiptValidator | 완료 |
| 중복 의심 탐지 | 완료 |
| 카드 사용내역 매칭 | 완료 |

### 3주차

| 기능 | 상태 |
|---|---|
| 검수 UI | 완료 |
| 검수 테이블 수정값 반영 | 완료 |
| 제외 상태 처리 | 완료 |
| ExcelExporter | 완료 |
| 업로드 → 처리 → 검수 → 다운로드 연결 | 완료 |
| 전체 로컬 경로 미노출 테스트 | 완료 |
| OCR 원문 전체 미노출 테스트 | 완료 |

### 4주차

| 기능 | 상태 |
|---|---|
| 환경변수 기반 OCR provider 선택 | 완료 |
| Azure OCR provider 구조 | 완료 |
| Azure Retry-After polling/retry 안정화 | 완료 |
| OCR 실패 진단 코드 표시 | 완료 |
| 업로드/출력 파일 cleanup 함수 | 완료 |
| cleanup 기본 dry-run 정책 | 완료 |
| 파일럿 가이드/인터뷰/피드백 문서 | 완료 |

### 5주차

| 단계 | 기능 | 상태 |
|---|---|---|
| 5주차-A | SQLite 처리 이력 저장 구조 | 완료 |
| 5주차-B | 처리 이력 목록 화면 | 완료 |
| 5주차-C | 처리 이력 상세 조회와 기존 엑셀 재다운로드 | 완료 |
| 연결 보완 | 엑셀 생성 성공 시 ProcessingJob DB 저장 | 완료 |
| 5주차-D | 읽기 전용 설정 화면 | 완료 |
| 5주차-E | 파일럿 전 통합 점검과 문서 동기화 | 진행 |

## 현재 메뉴 구조

- `새 작업`: 업로드, 처리, 검수, 엑셀 생성/다운로드
- `처리 이력`: 작업 목록, 상세 요약, 기존 export 파일 재다운로드
- `설정`: OCR/provider 상태, 보관기간, 저장소/DB 상태, cleanup dry-run 요약

## 미완료 기능

| 기능 | 상태 |
|---|---|
| 로그인/사용자 계정 | 파일럿 이후 |
| 결제 | 파일럿 이후 |
| 클라우드 배포 | 파일럿 이후 |
| 모바일 최적화 | 파일럿 이후 |
| 세무사 사무실용 관리자 기능 | 파일럿 이후 |
| 실제 OCR 정확도 대량 검증 | 파일럿 이후 |
| OCR provider 추가 확장 | 파일럿 이후 |
| 과거 작업 재검수 | 파일럿 이후 |
| 과거 엑셀 재생성 | 파일럿 이후 |
| 실제 cleanup 삭제 UI | 파일럿 이후 |

## 파일럿 전 우선순위

1. `python -m compileall app tests` 통과
2. `python -m pytest` 통과
3. 새 작업 전체 흐름 수동 확인
4. 처리 이력 저장/목록/상세/재다운로드 확인
5. 설정 화면 상태 확인
6. 엑셀 필수 시트와 검수 수정값 반영 확인
7. 전체 로컬 경로, OCR 원문 전체, raw JSON 전체 미노출 확인
8. `.env`, `data/uploads`, `data/outputs`, `data/app.db` Git 제외 확인

## 파일럿 이후 개선 후보

| 후보 | 판단 기준 |
|---|---|
| 검수 UI 개선 | 사용자가 수정 위치를 찾기 어려워하는지 |
| 비용항목 추천 규칙 보강 | 추천값이 참고용으로 충분한지 |
| 카드 매칭 사유 개선 | 후보/미매칭 사유가 이해되는지 |
| 엑셀 컬럼 조정 | 세무사 전달용 정리 파일로 충분한지 |
| 실제 OCR provider 운영 옵션 | mock 데모만으로 부족한 피드백이 반복되는지 |
| 처리 이력 상세 UX 개선 | 재다운로드 외 조회 요구가 있는지 |

## 6주차 이후 아키텍처 전환 계획

아래 계획은 1~5주차 MVP 완료 내역을 유지한 뒤 진행할 후속 아키텍처 정리입니다. 모든 항목은 아직 예정/계획 상태이며, 완료로 표시하지 않습니다.

| 주차 | 주제 | 상태 | 계획 |
|---|---|---|---|
| 6주차 | StandardOCRResult 표준 정의 | 예정 | `docs/standard_ocr_result_schema.md` 생성, SPEC.md에 `StandardOCRResult` 추가, DECISIONS.md에 Provider 표준화 ADR 추가, `tests/fixtures/standard_ocr_result/`와 `tests/fixtures/expected_receipt_record/` 샘플 JSON 추가 |
| 7주차 | Azure Adapter 표준화 | 예정 | Azure raw response를 `StandardOCRResult`로 변환하고, Azure 구조화 필드는 `key_value_candidates`와 `table_candidates`에 매핑하며 raw JSON 전체 미노출 원칙과 기존 Azure Provider 동작을 유지 |
| 8주차 | Parser/Validator 표준 입력화 | 예정 | `ReceiptParser`가 `StandardOCRResult`를 입력으로 받도록 정리하고, Parser가 Azure/PaddleOCR/ML Kit 원본 응답을 직접 보지 않게 하며 fixture 기반 Parser 테스트 추가 |
| 9주차 | PaddleOCR Local Provider PoC | 예정 | `OCR_PROVIDER=paddle` 후보를 추가하고, `PaddleOCRProvider`는 `StandardOCRResult`를 반환하도록 설계하며 PaddleOCR 미설치 환경에서도 기본 pytest가 실패하지 않게 구성 |
| 10주차 | Azure vs PaddleOCR 품질 비교 | 예정 | 같은 영수증 샘플로 날짜/상호/총금액/부가세/사업자번호/검토필요 건수, 평균 처리시간, 실패율을 비교하고 Azure fallback 기준 정리 |
| 11주차 | Local OCR Runtime / PC 설치형 구조 설계 | 예정 | 웹은 입력/검수 UI로 유지하고, OCR은 PC Local Runtime에서 수행하는 구조를 검토하며 PaddleOCR Local Edition, Docker Compose Edition, Tauri/Electron Desktop 후보 비교 |
| 12주차 | 모바일 OCR 결과 포맷 설계 | 예정 | 모바일 앱도 `StandardOCRResult`를 생성하도록 하고, Android ML Kit과 iOS Apple Vision Adapter 전략을 문서화하며 앱은 촬영/인식/간단 검수/공유 중심으로 제한 |
| 13주차 | 웹/앱/PC 통합 파일럿 준비 | 예정 | Azure 웹 MVP, PaddleOCR Local Web/PC Edition, 모바일 OCR 결과 import 흐름을 비교하는 파일럿 시나리오 준비 |

### 6주차 산출물

- `StandardOCRResult` 개념 정의
- `StandardOCRResult` 필드 초안
- `StandardOCRResult` Pydantic 모델 초안
- Mock/Azure-like/edge-case Golden Fixture 초안
- Fixture 로딩과 보안 금지 문자열 테스트
- 6주차-A: `StandardOCRResult` 문서 계약 정의
- 6주차-B: `StandardOCRResult` 모델과 fixture 초안 추가
- 6주차-C: Parser 전환 전략과 `StandardOCRParserContext` 테스트 경계 정의
- `StandardOCRParserContext` 준비
- Parser 전환 계획 문서
- fixture 기반 parser context 테스트
- Provider Adapter Contract
- Golden Fixture Comparison Strategy
- 7주차 Azure Adapter 작업 기준
- 8주차 Parser 정리 기준
- Provider Adapter 책임 범위 정의
- Parser 입력 기준 정의
- Golden Test Fixture 전략 정의
- 보안/민감정보 비노출 기준 재확인

### 6주차에서 하지 않는 것

- `PaddleOCRProvider` 구현
- `TesseractProvider` 구현
- ML Kit 앱 구현
- Apple Vision 앱 구현
- Local OCR Runtime 구현
- FastAPI 서버 구현
- Tauri/Electron 앱 구현
- 기존 `ExcelExporter` 대규모 변경
- 기존 `ReceiptRecord` 대규모 변경

### 7주차 세부 계획

| 단계 | 주제 | 상태 | 산출물 |
|---|---|---|---|
| 7주차-A | Azure Adapter 계약/문서 보완 | 계획 | Azure Adapter Contract, `provider_fields` 매핑 기준, Azure raw JSON 전체 미노출 기준, Azure raw text 전체 미노출 기준, `operation_location` 전체 URL 미저장 기준, 기존 Azure Provider 동작 유지 원칙, 7주차-B 구현 범위, 7주차-C 연결 검토 기준, 8주차 Parser 전환과의 경계 정의 |
| 7주차-B | AzureStandardOCRAdapter 구현 및 fixture 테스트 | 진행 | `app/ocr/adapters/azure_standard_adapter.py` 추가, sanitized Azure fixture 3종 기반 단위 테스트, `StandardOCRResult` 생성 검증, `provider_fields` 비민감 metadata 검증, raw JSON/raw text/`operation_location` 전체 URL 미노출 테스트 |
| 7주차-C | 기존 Azure Provider와 Adapter 연결 준비/회귀 테스트 | 진행 | Azure Adapter integration contract test, Azure Provider regression test, 선택적 bridge/helper 추가, 기존 `AzureProvider.extract()`의 `OCRResult` 반환값 유지 확인, 8주차 Parser 전환 진입 조건 정리 |

8주차 Parser 전환 시작 조건:

- 7주차 Adapter 테스트 통과
- Azure Provider 회귀 테스트 통과
- 기존 end-to-end export flow 테스트 통과
- Parser context 보안 테스트 통과
- 기존 `AzureProvider.extract()` 반환값과 기존 Parser/Exporter/DB/UI 흐름 유지 확인

### 8주차 세부 계획: Parser/Validator 표준 입력화

| 단계 | 주제 | 상태 | 산출물 |
|---|---|---|---|
| 8주차-A | Parser 표준 입력 전환 계약/문서 보완 | 진행 | Parser 표준 입력 계약, legacy raw_text Parser compatibility 원칙, `StandardOCRParserContext` 기반 Parser entry 후보, fixture 기반 Parser 테스트 기준, downstream 회귀 점검 기준, rollback 기준 |
| 8주차-B | `StandardOCRParserContext` 기반 `ReceiptParser` entry 추가 | 예정 | 기존 `ReceiptParser` public interface 유지, 새 entry 후보 `parse_standard_context(context: StandardOCRParserContext) -> ReceiptRecord` 또는 `parse_from_standard_ocr(result: StandardOCRResult) -> ReceiptRecord` 검토, 기존 raw_text 기반 Parser 경로 유지, 기존 `ReceiptRecord` 반환 구조 유지 |
| 8주차-C | fixture 기반 Parser 결과 비교 테스트 | 예정 | mock/azure-like/edge-case standard fixture, AzureStandardOCRAdapter output 기반 parser context 테스트, legacy raw_text Parser 결과와 standard context Parser 결과의 핵심 필드 비교 |
| 8주차-D | Validator/CategoryRules/CardMatcher/ExcelExporter/Processing History 회귀 점검 | 예정 | ReceiptValidator, CategoryRules, CardMatcher, ExcelExporter, Processing History 저장/조회, end-to-end export flow 유지 확인 |

8주차-A에서 하지 않는 것:

- `ReceiptParser` 코드 변경
- Parser public interface 변경
- Azure Provider 변경
- AzureStandardOCRAdapter 변경
- ExcelExporter 변경
- Processing History DB 변경
- Streamlit UI 변경
## Week 8-B Implementation Note

- Status: implemented as an isolated parser entry.
- Added `ReceiptParser.parse_standard_context(context: StandardOCRParserContext, ...) -> ReceiptRecord`.
- Added `ReceiptParser.parse_from_standard_ocr(result: StandardOCRResult, ...) -> ReceiptRecord` as a wrapper through `StandardOCRParserContext`.
- Added fixture-based smoke tests for mock, azure-like, edge-case, Azure adapter output, failed diagnostic, security, compatibility, and runtime non-wiring.
- Existing raw_text parser path, Azure Provider, Mock Provider, AzureStandardOCRAdapter, ExcelExporter, Processing History DB, and Streamlit UI remain unchanged.
- Week 8-C remains: deeper fixture-based comparison between legacy raw_text parsing and standard context parsing.
- Week 8-D remains: downstream regression check for Validator, CategoryRules, CardMatcher, ExcelExporter, and Processing History.

## Week 8-C Implementation Note

- Status: implemented as fixture-based parser comparison tests.
- Added standard parser comparison coverage for mock, azure-like, edge-case, and Azure adapter sanitized fixtures.
- Added limited legacy raw_text fixtures for core-field comparison without storing full OCR raw text.
- Verified non-amount candidate defense for quantity, approval number, footer number, and business number.
- Verified `vat_missing` and `vat_review_hint` remain review hints and are not explicit `vat_amount`.
- Verified parser output does not copy `provider_fields` raw metadata or expose raw payload/security/path patterns.
- Existing raw_text parser path, Parser public interface, Provider code, AzureStandardOCRAdapter, ExcelExporter, Processing History DB, and Streamlit UI remain unchanged.
- Week 8-D remains: downstream regression check for Validator, CategoryRules, CardMatcher, ExcelExporter, Processing History, and end-to-end export flow.

## Week 8-D Implementation Note

- Status: implemented as downstream regression safeguards.
- Added Standard Parser downstream regression coverage for ReceiptValidator, CategoryRules, CardMatcher, ExcelExporter, Processing History, provider independence, and existing end-to-end export flow.
- Verified StandardOCRParserContext-based `ReceiptRecord` objects can pass through existing downstream services without provider raw response, `provider_fields` raw metadata, raw OCR text, raw JSON, absolute local paths, endpoint, operation location, or secret exposure.
- Verified `provider="paddleocr"` candidate records are treated as ordinary `ReceiptRecord` inputs by downstream services; no PaddleOCRProvider or `paddleocr` dependency was added.
- Existing raw_text parser path, Parser public interface, Provider code, AzureStandardOCRAdapter, ExcelExporter sheet/column structure, Processing History DB schema, and Streamlit UI remain unchanged.
- 9주차 PaddleOCR Local Provider PoC can begin after the full regression suite remains passing.

## Week 9 Detailed Plan: PaddleOCR Local Provider PoC

The Week 9 work is a PoC for local OCR provider expansion. It does not replace the default provider, does not change the existing Parser/Validator/Exporter flow, and does not make PaddleOCR a required dependency.

| Step | Topic | Status | Deliverables |
|---|---|---|---|
| 9주차-A | PaddleOCR Local Provider 계약/문서 보완 | 완료 | `OCR_PROVIDER=paddle` 후보 정의, `PaddleOCRProvider` 계약, `PaddleStandardOCRAdapter` 계약, `StandardOCRResult` 반환 원칙, lazy import 원칙, paddleocr 미설치 환경 기본 pytest 통과 원칙, 이미지 우선 PoC 범위, PDF 후속 처리 원칙, opt-in 실제 OCR 테스트 전략, 10주차 Azure vs PaddleOCR 품질 비교 준비 기준 |
| 9주차-B | PaddleOCR-like Adapter 및 sanitized fixture 테스트 | 완료 | PaddleOCR-like sanitized fixture 생성, `PaddleStandardOCRAdapter` 구현, PaddleOCR-like result to `StandardOCRResult` 변환 테스트, `provider_fields` 비민감 metadata 검증, raw output 전체 미노출 테스트, 실제 paddleocr 호출 없음, `requirements.txt` 변경 없음 |
| 9주차-C | Optional PaddleOCRProvider 구현과 provider factory 후보 추가 | 완료 | optional `PaddleOCRProvider`, `OCR_PROVIDER=paddle` 후보, provider factory 후보 연결, paddleocr 미설치 시 명확한 failed/skipped 처리, lazy import, 기본 pytest 실패 방지, Parser/Validator/Exporter 변경 없음 |
| 9주차-D | 이미지 기준 opt-in Local OCR smoke test와 회귀 점검 | 완료 | `RUN_PADDLEOCR_TESTS=1` 같은 opt-in 실제 이미지 smoke test, 기본 pytest 제외, PDF 후속 처리, mock/Azure/standard parser/downstream 회귀 확인, 10주차 품질 비교 결과 기록 기준 정리 |

Week 9-A does not implement:

- `PaddleOCRProvider`
- `PaddleStandardOCRAdapter`
- `paddleocr` dependency installation
- provider factory code changes
- actual PaddleOCR import or execution
- image/PDF OCR fixture additions
- PDF conversion or PDF OCR handling
- Parser, Validator, CategoryRules, CardMatcher, ExcelExporter, Processing History DB, Streamlit UI, AzureProvider, MockProvider, or AzureStandardOCRAdapter changes

### 9주차-B 산출물

- Added `app/ocr/adapters/paddle_standard_adapter.py` with `PaddleStandardOCRAdapter` for sanitized PaddleOCR-like mapping input only.
- Added sanitized Paddle fixture files for regular, edge, and empty/failed image-style results under `tests/fixtures/paddle/`.
- Added `tests/test_paddle_standard_adapter.py` covering `StandardOCRResult` conversion, `provider_fields` safety, candidate separation, bbox/confidence normalization, parser context conversion, standard parser entry readiness, and Azure/Paddle shape comparability.
- The adapter uses `provider="paddleocr"` and `provider_fields.provider_family="paddleocr"`; `OCR_PROVIDER=paddle` remains a future provider factory candidate for 9주차-C.
- No `PaddleOCRProvider`, actual `paddleocr` import, real OCR execution, PDF handling, provider factory connection, default provider change, or `requirements.txt` change is included.

### 9주차-C 산출물

- Status: implemented as an optional provider candidate.
- Added `app/ocr/paddle_provider.py` with `PaddleOCRProvider`, returning `StandardOCRResult` through `PaddleStandardOCRAdapter`.
- Added `OCR_PROVIDER=paddle` and optional `OCR_PROVIDER=paddleocr` alias handling in the provider factory without changing the default provider.
- `paddleocr` is lazy-imported only at execution time; importing the provider and running default pytest do not require the package.
- Missing `paddleocr` returns a failed `StandardOCRResult` with a non-sensitive diagnostic code such as `paddle_not_installed`.
- PDF input returns an unsupported/deferred `StandardOCRResult`; PDF conversion is not implemented in this step.
- Added optional provider and provider factory tests without real OCR execution, image fixtures, customer files, or `requirements.txt` changes.
- Parser, Validator, CategoryRules, CardMatcher, ExcelExporter, Processing History DB, Streamlit UI, AzureProvider, MockProvider, and AzureStandardOCRAdapter remain unchanged.
- Week 9-D remains: opt-in real image OCR smoke test and regression check.

### 9주차-D 산출물

- Status: implemented as an opt-in smoke test scaffold and regression check.
- Added `tests/integration/test_paddle_ocr_provider_smoke.py`.
- The real image smoke test runs only when `RUN_PADDLEOCR_TESTS` is explicitly enabled and `PADDLEOCR_TEST_IMAGE_PATH` points to an existing local image.
- Without opt-in variables, the real OCR smoke test is skipped during default pytest.
- The smoke test validates `PaddleOCRProvider` to `StandardOCRResult`, `StandardOCRParserContext`, and the standard parser entry without checking OCR quality.
- PDF input remains unsupported/deferred and is covered without PDF conversion.
- Added `tests/fixtures/paddle_smoke/` guidance files; no real image or customer file is committed.
- Week 10 remains: Azure vs PaddleOCR quality comparison by `StandardOCRResult`, parser context, and core `ReceiptRecord` fields.

## Week 10 Detailed Plan: Azure vs PaddleOCR 품질 비교

Week 10 work compares provider quality without changing the default provider, ExcelExporter structure, Processing History schema, or Parser raw-input boundary.

| Step | Topic | Status | Deliverables |
|---|---|---|---|
| 10주차-A | 품질 비교 계약/문서 보완 | 완료 | `docs/ocr_quality_comparison_contract.md` 추가, 비교 입력 계층 정의, 핵심 필드/리포트 행 계약 정의, expected fixture 전략, 비민감 데이터 원칙, fallback 후보 조건 초안, B/C/D 범위 분리 |
| 10주차-B | 안전한 OCR 미리보기 구현 | 완료 | `StandardOCRResult.text_blocks` 기반 top-N safe preview, confidence/low-confidence/redaction 표시, PaddleOCR smoke path UI 표시 |
| 10주차-C | Azure vs PaddleOCR side-by-side 비교 리포트 구현 | 완료 | 같은 샘플을 provider별 결과로 묶어 핵심 `ReceiptRecord` 필드, OCR 상태, candidate count, review hint count, 처리시간, field present/same/match status 비교 |
| 10주차-D | 통계 요약과 Azure fallback 기준 정리 | 예정 | 샘플별/Provider별 실패율, 핵심 필드 누락률, 평균 처리시간, 검토필요율 요약과 Azure fallback 후보 기준 문서화 |

10주차-A does not implement:

- 안전한 OCR 미리보기 UI
- side-by-side comparison report code
- statistics aggregation code
- automatic Azure fallback execution
- PDF PaddleOCR handling
- Provider 변경 UI
- ExcelExporter sheet/column changes
- Processing History DB schema changes
- real Azure or real PaddleOCR execution in default pytest

10-week-B safe preview implementation note:

- Status: implemented as a safe preview layer, not a quality report layer.
- `app/ui/ocr_preview_utils.py` builds preview rows and summary from `StandardOCRResult.text_blocks`.
- The Settings PaddleOCR smoke-test box displays the existing smoke summary plus a limited safe preview table.
- Azure adapter output can use the same preview utility through `StandardOCRResult`; no Azure API execution is added.
- 10-B still does not implement side-by-side reports, statistics aggregation, `field_match_score`, fallback automation, default provider changes, ExcelExporter changes, Processing History schema changes, or PDF PaddleOCR handling.

Expected fixture strategy for Week 10:

- Expected fixture is based on core `ReceiptRecord` fields, not provider raw output.
- Same safe `sample_id` should connect Azure, PaddleOCR, and expected core-field results.
- Fixture content must use synthetic or non-sensitive samples only.
- File names are allowed; full local paths are not.
- PDF PaddleOCR expected fixtures remain deferred until PDF handling is explicitly scoped.
## Week 10-B/C Status Sync

- Week 10-B is implemented: safe OCR preview rows and summary are available from `app/ui/ocr_preview_utils.py`, and the PaddleOCR smoke path can show top-N safe text block previews without exposing full OCR text.
- Week 10-C is implemented as a per-sample side-by-side report in the settings diagnostics flow. It compares Azure and PaddleOCR only through `StandardOCRResult`, `StandardOCRParserContext`, and `ReceiptParser.parse_standard_context()` output.
- Week 10-C includes safe provider diagnostics such as `diagnostic_code` and sanitized `diagnostic_detail_code`. In local sample testing, PaddleOCR completed 10/10 image runs, while Azure may return `analyze_http_403` with `quota_or_rate_limit` when the Azure resource is currently rate-limited or quota-limited.
- PaddleOCR candidate hints are intentionally conservative. They may add clearly labeled merchant names, obvious date, business number, payment method, and labeled amount candidates, but they do not guess merchant names from arbitrary first lines or infer totals from unlabeled maximum amounts.
- Week 10-D remains planned. Aggregated statistics, average processing time summaries, failure-rate summaries, field match-rate summaries, formal `field_match_score`, and fallback recommendation rules are intentionally deferred.

## Week 10-D-prep Synthetic PaddleOCR Quality Fixtures

- Status: implemented as a preparation step for Week 10-D.
- Purpose: continue PaddleOCR parser-quality work while live Azure comparison is unstable due to quota/rate-limit responses.
- Scope: sanitized synthetic PaddleOCR line fixtures are converted through `StandardOCRResult`, `StandardOCRParserContext`, and `ReceiptParser.parse_standard_context()` before comparing selected expected `ReceiptRecord` fields.
- Fixture set: `tests/fixtures/paddle_synthetic/cases.json` covers mart/cafe/restaurant/gas/pharmacy/bookstore, explicit and missing VAT, discount and zero-payment cases, payment-method variants, business-number variants, date formats, OCR amount confusions, redacted sensitive lines, low confidence, approval-number noise, quantity noise, and footer-number noise.
- Current sample hardening: card-sales slip patterns now cover business-block merchant candidates, same-line merchant segments before valid business numbers, split total/supply/VAT labels, split `매출일`/`매장명` label-value lines on rotated receipts, compact approval date-time lines, and saved Azure-anchor core fields without live Azure calls.
- Out of scope: real Azure execution, real PaddleOCR execution in default pytest, customer files, provider raw output fixtures, formal `field_match_score`, automatic Azure fallback, statistics dashboard UI, ExcelExporter changes, Processing History schema changes, and default-provider changes.

## Review UX Quality Triage

- Status: implemented as a manual review convenience layer.
- Scope: the review screen adds priority, missing-field, and quality-check indicators derived from `ReceiptRecord`, plus status/issue filters and a safe selected-receipt detail panel.
- Purpose: help users quickly find records with missing merchant, date, business number, total amount, payment method, VAT review, sensitive-text, discount/zero-payment, or card-matching issues.
- Safety: the detail panel shows only safe parsed fields and source file names, not provider raw output, full OCR text, raw JSON, full local paths, secrets, or endpoint URLs.
- Out of scope: OCR reprocessing, automatic fallback, formal scoring, aggregate statistics UI, ExcelExporter sheet/column changes, Processing History schema changes, and provider default changes.

## New Job PaddleOCR Runtime Selection

- Status: implemented as an explicit per-run option on the New Job screen.
- Scope: users can choose `PaddleOCR Local` for the current upload batch while the configured default provider remains unchanged.
- Parser path: `StandardOCRResult` outputs are converted to `StandardOCRParserContext` and parsed through `ReceiptParser.parse_standard_context()`.
- Safety: source file names are displayed as file names only; provider raw output, full OCR text, raw JSON, full local paths, secrets, and endpoint URLs remain hidden.
- Out of scope: automatic Azure fallback, PDF PaddleOCR support, default provider changes, ExcelExporter sheet/column changes, Processing History schema changes, and real OCR execution in default pytest.

## PaddleOCR Speed Pass

- Status: implemented as a quality-preserving performance pass.
- Scope: reuse the PaddleOCR engine instance within one `PaddleOCRProvider`, avoid repeated candidate-map extraction when building `StandardOCRParserContext`, and cache repeated compact line normalization.
- Quality rule: no OCR quality shortcut was added; normalization fallback, candidate rules, parser rules, and review-required behavior remain intact.
- Safety: no provider raw output, full OCR text, raw JSON, full local paths, secrets, endpoint URLs, ExcelExporter changes, Processing History schema changes, or default provider changes.

## Review UI Receipt Source Preview

- Status: implemented as a safe review convenience layer.
- Scope: the review table shows priority, missing fields, review-reason summary, source file name, and source preview status. A selected row drives a safe source preview panel.
- Preview behavior: JPG/JPEG/PNG files under the configured upload root are shown with `st.image`; PDF files show a PDF notice instead of forced rendering.
- Selection behavior: the selected row id and row number are stored in session state, and the selected row is highlighted in a read-only selection table while the existing editable review table remains unchanged.
- Safety: preview resolution uses `stored_relative_path` only, blocks traversal and files outside `data/uploads`, and never displays full local paths, OCR raw text, provider raw JSON, or sensitive values.
- Out of scope: mobile/PWA work, OCR provider changes, PaddleOCR accuracy changes, OpenAI correction, ExcelExporter changes, Processing History schema changes, and customer test fixtures.

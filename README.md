# 영수증 OCR 엑셀 비서 MVP

## 프로젝트 개요

영수증 이미지/PDF와 카드 사용내역 CSV/XLSX를 업로드하면 OCR/Parser 결과를 만들고, 사용자가 검수한 뒤 세무사 전달용 정리 엑셀 파일을 다운로드할 수 있는 로컬 Streamlit MVP입니다.

OCR 결과, 비용항목 추천, 증빙유형 추정값은 항상 사용자가 확인해야 합니다. 이 프로젝트는 증빙 정리 보조 도구이며, 사용자 확인 없이 결과를 확정하지 않습니다.

## MVP 기능

| 구분 | 현재 구현 |
|---|---|
| 새 작업 | 파일 업로드, 안전 저장, OCR/Parser 처리, 검수 UI, 엑셀 생성/다운로드 |
| OCR | 기본 mock provider, 선택 가능한 Azure provider 구조 |
| 카드내역 | CSV/XLSX parser |
| 검수 | 날짜, 상호, 금액, 비용항목, 검수상태, 제외 처리 |
| 엑셀 | 표준 엑셀 정리 파일 생성 |
| 처리 이력 | SQLite 저장, 목록 조회, 상세 조회, 기존 엑셀 파일 재다운로드 |
| 설정 | 읽기 전용 설정/상태 확인, cleanup dry-run 요약 |
| cleanup | 수동 호출 가능한 dry-run 기본 함수 구조 |

## 현재 지원 범위

- 로컬 Streamlit 실행
- JPG, JPEG, PNG, PDF 영수증 업로드
- CSV, XLSX 카드 사용내역 업로드
- Mock OCR 기반 데모와 테스트
- Azure OCR provider 선택 실행 구조
- SQLite 기반 처리 이력 저장
- `data/outputs` 하위 export 파일 재다운로드
- 설정 화면에서 provider, 보관기간, 저장소/DB 상태 확인

## 지원하지 않는 범위

- 로그인/사용자 계정
- 결제/구독
- 클라우드 배포
- 모바일 앱
- 홈택스/카드사/회계 프로그램 연동
- 과거 작업 재검수
- 과거 엑셀 재생성
- 설정 화면에서 API key 입력 또는 provider 변경
- 설정 화면에서 실제 cleanup 삭제

## 설치 방법

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 실행 방법

```bash
streamlit run app/main.py
```

Windows 개발/진단 중에는 기존 Streamlit 서버가 같은 포트에 남아 예전 코드로 OCR smoke test가 반복 실행될 수 있습니다. 이 경우 아래 스크립트를 사용하면 `8501` 포트의 오래된 Python/Streamlit 서버를 먼저 정리한 뒤 앱을 새로 실행합니다.

```powershell
.\scripts\run_app.ps1
```

앱 메뉴:

- `새 작업`: 업로드, 처리, 검수, 엑셀 생성/다운로드
- `처리 이력`: 과거 작업 목록, 상세 조회, 기존 엑셀 재다운로드
- `설정`: 읽기 전용 환경/저장소/DB 상태 확인

## 환경변수 설정

기본 개발과 테스트는 mock provider 기준입니다.

```text
OCR_PROVIDER=mock
APP_DB_PATH=data/app.db
UPLOAD_DIR=data/uploads
OUTPUT_DIR=data/outputs
UPLOAD_RETENTION_DAYS=7
OUTPUT_RETENTION_DAYS=7
CLEANUP_DRY_RUN_DEFAULT=true
```

Azure OCR을 사용할 때만 별도 provider 설정과 key를 `.env`에 넣습니다. 실제 key는 코드나 문서에 적지 않습니다. `.env`는 Git에 올리지 않습니다.

Azure 실행에서 `proxy_error`가 반복되면 로컬 `HTTP_PROXY`/`HTTPS_PROXY` 환경변수를 타고 실패하는 상황일 수 있습니다. 직접 Azure endpoint에 접근 가능한 환경이라면 `.env`에 `AZURE_OCR_IGNORE_ENV_PROXY=true`를 설정해 Azure 요청에서 환경 프록시를 무시할 수 있습니다.

## 테스트 실행 방법

```bash
python -m compileall app tests
python -m pytest
```

주요 개별 테스트:

```bash
python -m pytest tests/test_end_to_end_export_flow.py
python -m pytest tests/test_history_utils.py
python -m pytest tests/test_history_detail_view.py
python -m pytest tests/test_settings_utils.py
```

## 샘플 사용 흐름

1. `streamlit run app/main.py`로 앱을 실행합니다.
2. `새 작업`에서 영수증 파일과 카드 사용내역 파일을 업로드합니다.
3. `파일 저장 및 처리`를 누릅니다.
4. 검수 테이블에서 OCR/Parser 결과와 검토 사유를 확인합니다.
5. 필요한 값을 직접 수정하고 제외할 항목을 표시합니다.
6. `표준 엑셀 생성`을 누릅니다.
7. 엑셀 생성 성공 시 처리 이력 DB와 `data/outputs` 하위에 결과 파일이 저장됩니다.
8. `엑셀 다운로드`로 파일을 받습니다.
9. `처리 이력`에서 방금 작업을 조회하고 상세/재다운로드를 확인합니다.
10. `설정`에서 저장소/DB 상태와 cleanup dry-run 요약을 확인합니다.

## 개인정보/파일 보관 주의사항

- 실제 카드번호 전체, 주민번호, 전화번호, 민감정보가 포함된 파일은 파일럿에 사용하지 않습니다.
- OCR raw text 전체와 raw JSON 전체는 엑셀, DB, 화면에 저장/표시하지 않는 것을 원칙으로 합니다.
- 전체 로컬 절대경로는 엑셀, DB, 화면에 표시하지 않습니다.
- `data/uploads`, `data/outputs`, `output`, `data/app.db`, `*.db`, `.env`는 Git에 올리지 않습니다.
- 업로드 파일과 출력 파일 기본 보관기간은 각각 7일입니다.
- cleanup 기본값은 `dry_run=True`이며 자동 실행하지 않습니다.

## 파일럿 테스트 안내

파일럿은 세무사 전달용 정리 파일이 실제 업무 검토에 충분한지 확인하기 위한 절차입니다. 기본 데모는 `OCR_PROVIDER=mock` 기준으로 진행하고, 실제 OCR provider는 선택적으로 별도 확인합니다.

관련 문서:

- [파일럿 가이드](docs/pilot_guide.md)
- [인터뷰 질문지](docs/interview_questions.md)
- [샘플 사용자 흐름](docs/sample_user_flow.md)
- [파일럿 피드백 템플릿](docs/pilot_feedback_template.md)

## 후속 OCR Provider 확장 방향

현재 기본 MVP 실행 방법은 그대로 유지합니다. `StandardOCRResult`는 Azure, PaddleOCR, Tesseract, Android ML Kit, iOS Apple Vision, Mock OCR 같은 후속 OCR Provider 확장을 위한 내부 표준입니다.

PaddleOCR Local Provider는 9주차 PoC 후보로 추가되었지만 기본 실행 요구사항은 아닙니다. Tesseract Provider와 Mobile OCR Adapter는 후속 계획입니다. OCR Provider가 늘어나도 Parser, Validator, CategoryRules, CardMatcher, ExcelExporter, 처리 이력 흐름은 `StandardOCRResult`를 기준으로 하나로 유지하는 방향입니다.

6주차 작업은 표준 계약과 fixture 전략을 정의하는 문서 보완 단계였습니다. PaddleOCR은 9주차 이미지 기준 PoC 후보로 분리되었고, Tesseract Provider, 모바일 앱, Provider 변경 UI는 아직 후속 범위입니다.

## 9주차 PaddleOCR Local Provider PoC 안내

기본 개발과 테스트는 계속 `OCR_PROVIDER=mock` 기준입니다. `OCR_PROVIDER=paddle`은 9주차 Local OCR PoC 후보이며, 현재 optional `PaddleOCRProvider`와 opt-in smoke test scaffold가 추가되어 있습니다.

PaddleOCR 관련 원칙:

- `paddleocr`가 설치되지 않은 환경에서도 기본 `python -m pytest`는 통과해야 합니다.
- 실제 PaddleOCR 실행은 별도 설치와 opt-in 테스트가 필요하며 기본 pytest에 포함하지 않습니다.
- 9주차 PoC는 이미지 파일 기준으로 제한하고, PDF 처리는 후속 작업으로 분리합니다.
- PaddleOCR Provider가 추가되더라도 Parser 이후 흐름은 `StandardOCRResult`와 기존 `ReceiptRecord` 기반으로 유지합니다.
- PaddleOCR raw output 전체, OCR raw text 전체, 전체 로컬 절대경로, 실제 고객 파일은 DB/화면/엑셀/로그/fixture에 남기지 않습니다.
### 9주차-D PaddleOCR opt-in smoke test

기본 회귀 테스트는 계속 아래 명령만으로 실행합니다.

```bash
python -m pytest
```

실제 PaddleOCR 이미지 smoke test는 명시적으로 opt-in할 때만 실행합니다.

```powershell
$env:RUN_PADDLEOCR_TESTS = "1"
$env:PADDLEOCR_TEST_IMAGE_PATH = "<local-safe-sample-image>"
python -m pytest tests/integration/test_paddle_ocr_provider_smoke.py
```

- smoke test는 OCR 품질 평가가 아니라 `PaddleOCRProvider` 실행 경로가 `StandardOCRResult`로 안전하게 끝나는지 확인하는 용도입니다.
- 테스트 이미지는 저장소에 커밋하지 말고, 합성 이미지 또는 비민감 샘플만 사용합니다.
- 결과를 공유할 때는 파일명만 기록하고 전체 로컬 경로는 기록하지 않습니다.
- PDF는 아직 PaddleOCR smoke test 범위가 아니며 unsupported/deferred 상태를 유지합니다.

### 9주차-C Optional PaddleOCRProvider 후보

- `OCR_PROVIDER=paddle` 후보가 추가되었지만 기본 개발/테스트 provider는 변경되지 않았습니다.
- `OCR_PROVIDER=paddleocr` alias도 같은 optional provider 후보로 취급합니다.
- `PaddleOCRProvider`는 `StandardOCRResult`를 반환하며 `PaddleStandardOCRAdapter`를 통해 결과를 정규화합니다.
- `paddleocr` 패키지는 필수 의존성이 아니며, 설치되지 않은 환경에서도 provider import와 기본 `python -m pytest`가 통과해야 합니다.
- `paddleocr` 미설치 상태에서 `extract()`를 호출하면 raw traceback 대신 `paddle_not_installed` 계열 diagnostic code가 있는 failed result를 반환할 수 있습니다.
- PDF 입력은 아직 지원하지 않으며 `paddle_pdf_not_supported` 계열의 deferred/failed result로 처리합니다.
- 실제 이미지 OCR smoke test는 9주차-D에서 opt-in 방식으로 분리합니다.

## 10주차 Azure vs PaddleOCR 품질 비교 안내

10주차-A는 품질 비교 계약과 문서 보완 단계입니다. 이후 10주차-B 안전한 OCR 미리보기와 10주차-C side-by-side 비교 리포트가 Settings 진단 흐름에 구현되었습니다. 통계 요약, formal `field_match_score`, Azure fallback 정책/자동화는 10주차-D 범위로 남겨둡니다.

비교 기준은 Provider raw output이 아니라 `StandardOCRResult`, `StandardOCRParserContext`, 기존 `ReceiptRecord`입니다. 비교 리포트에는 파일명, 상태 코드, 후보 수, 검토 필요 사유, 핵심 필드 일치 여부 같은 비민감 요약만 남기며 OCR raw text 전체, raw JSON 전체, 전체 로컬 절대경로, 실제 고객 파일은 포함하지 않습니다.

Expected fixture는 실제 OCR raw output이나 실제 고객 파일이 아니라 합성/비민감 샘플의 `ReceiptRecord` 핵심 필드 기준선으로 둡니다. PDF PaddleOCR fixture와 통계/정책 집계는 후속 단계입니다.

자세한 계약은 [Azure vs PaddleOCR 품질 비교 계약](docs/ocr_quality_comparison_contract.md)을 기준으로 합니다.
### Week 10-B Safe OCR Preview

10-B adds a safe OCR preview for the PaddleOCR smoke-test path. The preview is built only from `StandardOCRResult.text_blocks`, shows a limited number of rows, includes confidence and low-confidence flags, and keeps sensitive lines as `[REDACTED]`.

The same preview utility is provider-neutral, so Azure adapter output can use it later through `StandardOCRResult` without passing Azure raw JSON or PaddleOCR raw output into the UI. This step does not add side-by-side reports, statistics summaries, `field_match_score`, automatic Azure fallback, default provider changes, ExcelExporter changes, Processing History schema changes, or PDF PaddleOCR handling.
### Week 10-C Side-by-side Comparison Report

Week 10-C adds an explicit settings-screen diagnostic for comparing one non-sensitive sample image through Azure and PaddleOCR. The report follows the Week 10-A contract:

`Provider execution -> StandardOCRResult -> StandardOCRParserContext -> ReceiptParser.parse_standard_context() -> ReceiptRecord -> side-by-side comparison report`

The comparison shows provider-level per-sample metrics and core parsed receipt fields side by side. It does not store or display provider raw output, full OCR text, raw JSON, full local paths, Azure endpoint URLs, operation URLs, secrets, or raw tracebacks. Week 10-B safe preview remains available for OCR text block preview, and Week 10-C does not change the default production provider flow.

The report also shows per-field match status (`matched`, `mismatched`, `azure_only`, `paddle_only`, `both_missing`) and a per-sample field match summary for manual review. These are diagnostic flags only; Week 10-C still does not calculate a formal score or fallback recommendation.

Azure failures may include a sanitized `diagnostic_detail_code`, for example `quota_or_rate_limit` for an HTTP 403 quota/rate-limit response. Raw Azure error messages, endpoint URLs, operation URLs, keys, request IDs, and tracebacks are not displayed.

PaddleOCR now generates only conservative candidate hints from safe OCR lines: obvious dates, business numbers, payment methods, and labeled amounts. It does not guess merchant names or infer totals from unlabeled maximum amounts.

Week 10-D remains the future step for statistics aggregation, average processing time, failure rate, field match-rate summaries, formal field match scoring, and Azure fallback policy rules. These are not automated by the Week 10-C report.
## Week 10-D-prep: Synthetic PaddleOCR Quality Fixtures

Azure OCR quota/rate-limit issues can block live Azure comparisons, so PaddleOCR
parser quality can also be improved with safe synthetic fixtures. The fixtures in
`tests/fixtures/paddle_synthetic/` are not customer receipts, provider raw output,
or full OCR text dumps. They are sanitized line-level inputs that are converted to
`StandardOCRResult`, then parsed through `StandardOCRParserContext` and
`ReceiptParser.parse_standard_context()`.

This path is for conservative regression work only: explicitly labeled merchant
names, labeled dates, business numbers, payment methods, labeled amounts,
explicit VAT/supply values, redacted sensitive lines, and numeric noise guards.
It does not call Azure, does not run
real PaddleOCR in default pytest, and does not change the default provider,
Excel export sheets/columns, or processing history schema.

### Review UX quality triage

The review table now includes safe triage columns for review priority, missing
core fields, and quality-check flags. Users can filter by review status or issue
type and inspect one selected receipt through a safe detail panel that shows only
the source file name, parsed core fields, and review reasons.

This convenience layer is for manual review only. It does not display provider
raw output, full OCR text, raw JSON, full local paths, secrets, or endpoint URLs,
and it does not change OCR provider selection, Excel export sheets/columns, or
Processing History schema.

### New Job PaddleOCR Runtime Selection

The New Job screen now includes `PaddleOCR Local` in the per-run OCR provider
selector. This does not change the configured default provider; it only applies
to the current upload batch when the user explicitly selects it.

When selected, PaddleOCR results follow the safe standard path:

`PaddleOCRProvider -> StandardOCRResult -> StandardOCRParserContext -> ReceiptParser.parse_standard_context() -> ReceiptRecord`

The flow keeps PDF handling unsupported/deferred for PaddleOCR, does not expose
provider raw output, full OCR text, raw JSON, full local paths, secrets, or
endpoint URLs, and does not change Excel export sheets/columns or Processing
History schema.

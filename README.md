# 영수증 OCR 엑셀 비서 MVP

## 2026-10-19 GS 오류 수정·선택 V5 비교 앱

구매·환불 안내문 상호 오탐과 수량·합계 열 결합을 보완했습니다. 기존 GPU 엔진은 고정 기준 **76/88 유지, 기존 일치 항목 퇴행 0**입니다. 새 한국어 PP-OCRv5는 문제 GS 사진의 **GS THE FRESH / 26,390원 / 부가세 2,398원**을 추출했지만 기존 기준은 **74/88**이어서 기본 엔진으로 교체하지 않았습니다.

프로젝트 폴더의 **영수증 비서 V5 실행.vbs**는 별도 비교 앱(기본 `http://127.0.0.1:8502`)을 엽니다. 화면에서 **GPU 가속 시도**를 선택하고 원본을 다시 처리하세요. **영수증 비서 V5 종료.vbs**로 종료합니다. 일반 실행 파일·기존 세션·DB는 유지하며, V5 데이터는 `data/paddle_v5/`로 분리합니다. 선택 설치 명령·측정값·남은 퇴행은 [GS·V5 비교 보고서](docs/ocr_gsfresh_v5_comparison.md)에 정리했습니다. V5는 전체 정확도 개선이 확인된 정식 대체 엔진이 아닙니다.

## 2026-10-19 로컬 후보 계약·좌표 점검

명시 상호·금액 후보의 유효성, 가로 세액 열, 회전/확대 보완 좌표를 보완했습니다. 기존 고정 88항목은 **76개 일치 유지**이며 100% 미달입니다. 추가 사진의 세액 회복과 기존 점수는 구분합니다. 평가용 비교 자료는 스캔에 필요한 매장별 등록 정보가 아닙니다. [변경·퇴행 되돌림·검증·남은 오류](docs/ocr_contract16_followup.md).

## 2026-10-19 상호 열 경계·합계 숫자 영역 재확인

같은 행의 대표자 정보를 상호에 합쳐 버리는 경계를 수정하고, 불완전한 합계 숫자 조각은 최대 두 행의 해당 영역만 로컬 PaddleOCR로 다시 읽습니다. 실제 문제 사진의 합계는 1,000 → 10,000원, 부가세는 909원 유지입니다. 상호는 추출됐지만 기존 기준과 첫 글자 차이는 불일치로 남겼습니다. 기존 16장의 일치값 퇴행은 없으며 과거 결과는 자동 정정하지 않습니다. [범위·근거·한계](docs/ocr_label_total_followup.md).

## 2026-10-19 명시 라벨·숫자 포함 상호 후속 개선

실제 앱 대조에서 발견한 엑셀 상호의 슬래시 잘림도 수정했습니다. 16개 팝업과 실제 다운로드 엑셀의 128개 필드 일치를 확인했으며, 기존 이력·이전 엑셀은 자동 수정하지 않습니다.

기존 8장은 **39/47 → 40/47**, 사용자가 지적한 별도 문제 사진 4장은 **18/29 → 25/29**입니다. 새 미사용 4장은 **24/30 → 24/30**으로 일반 품질 향상을 입증하지 못했습니다. 기존 일치값 퇴행과 미표기 오탐 증가는 없지만 100%에는 미달합니다. 대괄호 상호·숫자 포함 이름·합계 우선 선택·과세매출 연결을 보완하고, 원본 숫자 영역에서 명시 0을 다시 읽습니다. 누락 금액 계산·정답 사전·새 모델은 추가하지 않았습니다. [고정 기준·실패별 결과·테스트·시간·호출 수](docs/ocr_quality_12_followup.md).

## 2026-10-19 상세 검수 닫기·같은 행 재열기

팝업 오른쪽 위 **X**, ESC 또는 하단 **닫기**로 닫을 수 있습니다. 같은 행을 다시 클릭하거나 더블클릭해도 열리도록 표 선택을 새로 만듭니다. 초안·선택 영수증·필터는 유지하지만 표 헤더 정렬·열 폭·내부 스크롤은 초기화될 수 있습니다. 현재 서버가 예전 모듈을 유지하면 재시작이 필요하며, 이때 미저장 세션은 초기화될 수 있습니다. 동일 8장의 실제 앱 경로에서 상호는 6장 일치·1장 오인식·1장 누락입니다. [원인·실제 화면·검증](docs/review_runtime_followup.md).

## 2026-10-19 남은 OCR 오류 후속 개선

기존 8장의 값 있는 필드는 **38/47 → 39/47**, 기존 일치 항목 퇴행 0개입니다. 누락 날짜 1개를 복원하고 별도 결제수단 오탐 1개를 제거했습니다. 47/47에는 도달하지 못했으며 8개 오류가 남습니다. 개선에 사용하지 않은 4장은 **20/25 → 20/25**로 같아 일반 품질 향상을 입증하지 못했습니다. 기준 파일의 한글 저장 오류를 복원한 동일 기준으로 전후 코드를 재평가했습니다. 8장 처리시간은 단일 관측에서 45.98초 → 48.99초였습니다. [항목별 원인·검증·한계](docs/ocr_remaining_followup.md).

## 2026-10-19 원본 전체 보기·행 클릭

표의 행 안에서 원하는 셀을 클릭하면 상세 검수가 바로 열립니다. 기존 **상세 검수 열기** 버튼도 유지합니다. 원본은 창 높이에 맞춰 전체를 표시하며 오른쪽 입력 영역만 필요할 때 스크롤합니다. 하단 버튼은 비교 영역 밖에 유지합니다. 긴 영수증은 전체 보기에서 글자가 작아질 수 있습니다. 저장 전 입력을 확인한 뒤 앱을 종료·실행하면 새 화면이 반영됩니다. [시안·실제 화면·검증](docs/review_image_fit.md).

## 2026-10-19 실패 항목 후속 개선

동일 사진 8장의 판독 가능 47개 값은 **31개 → 38개 일치**로 늘었습니다. 반복 구분자, 상호 라벨·별도 열, 날짜 조립, 한 행의 세액 분리를 고쳤습니다. 누락 세액만 최대 8구간 재인식으로 보완하고 기존 값을 덮어쓰지 않습니다. 위치 관계가 없는 다음 블록의 금액을 세액으로 가져오거나 카드 주변의 원 금액을 총액으로 추측하던 경로도 막았습니다.

양성 실패 9개와 빈칸 결제수단 오탐 1개가 남고 재인식으로 처리시간도 늘었습니다. 별도 사진의 정확도를 검증한 결과가 아니며 사용자 검수가 필요합니다. 원본·판독 기준·과거 DB·엑셀은 바꾸지 않았습니다. [실패 16개 분석·개선·재평가](docs/ocr_failure_followup.md).

## 2026-10-19 OCR 신뢰성 감사

파일명별 정답 덮어쓰기, 사업자번호·브랜드에 의한 상호 치환, 미표기 합계·누락 0 생성 경로를 제거했습니다. 특정 상품명 제외와 브랜드 허용 예외도 정리했습니다. 상호 DB는 후보 조회에 남기며 엑셀 생성으로 자동 학습하지 않습니다. 실제 사진의 항목 선택 오류는 남아 있어 사용자 검수가 필요합니다.

[감사·수정·이미지 평가 기록](docs/ocr_integrity_audit.md). 반복 평가는 `.venv-ocr\Scripts\python.exe scripts/evaluate_local_receipts.py --reference output/quality_refs/visual_reference.json --gpu`로 실행합니다. 판독 기준·이미지는 로컬에만 두고 결과에는 일치 여부만 기록합니다. 기존 저장 결과는 자동 정정하지 않습니다.

## 2026-10-19 검수 화면 정리

전체 영수증을 통일된 표에서 먼저 확인하고, 행 선택 또는 표 아래의 영수증 선택 후 **상세 검수 열기**를 누릅니다. 큰 팝업 안에서 왼쪽 원본과 오른쪽 표준 수정 서식을 비교합니다. 팝업의 **이전 / 다음 / 닫기 / 저장 / 저장 후 다음**으로 이동하며, 원본과 입력 영역을 스크롤해도 하단 버튼 위치는 유지됩니다. 검수상태 필터의 **검토필요만 보기**로 대상을 좁힐 수 있습니다.

사용일자·상호·사업자번호·할인금액·공급가액·부가세·결제금액·결제수단을 확인하고 저장합니다. 표·입력란·합계·엑셀 금액은 천 단위 콤마를 표시하며, 입력란은 입력을 마치고 다른 칸으로 이동하거나 Enter를 누를 때 정리됩니다. 표의 미표기 금액은 `—`, 명시된 0원은 `0`입니다. 중복의심 `Y`는 비교 대상 표시이며 자동 제외하지 않습니다. 파일명과 추가 추출값은 팝업의 접힌 상세정보에서 확인합니다. 저장 메타데이터 표, 중복 수정 화면, 기본 후보 점수·성능 표시는 제외했습니다.

팝업에서 입력 중인 초안은 **이번 작업 세션**에서 영수증별로 유지됩니다. 저장한 값만 전체 표·엑셀에 반영하며 잘못된 금액 형식은 저장을 막습니다. 상단 X·ESC·바깥 영역 또는 하단 닫기로 닫아도 같은 세션에서 초안을 다시 확인할 수 있습니다. 서버 재시작·브라우저 세션 종료까지 보존하는 기능은 아닙니다. 합성 시안을 먼저 제시한 뒤 구현했습니다. [일괄 표·팝업 검수 변경 기록](docs/batch_review_ui.md), [닫기·재열기 후속 검증](docs/review_runtime_followup.md).

공급가액·부가세와 할인 누락값을 차액으로 채우지 않습니다. 빈칸과 명시된 0원을 구별하며 면세로 자동 판단하지 않습니다. 기존 8개 엑셀 시트와 컬럼은 유지하고 추정공급가액·추정부가세 컬럼은 비웁니다. 검수값을 저장하면 이전 다운로드 파일을 해제하므로 엑셀을 다시 생성해 주세요. 카드내역 미업로드는 매칭 0건과 구분합니다.

기존 DB와 이전 엑셀은 다시 쓰지 않았습니다. 모바일 앱과 날짜별 누적 저장 전환은 후속 범위입니다. [변경·검증 기록](docs/review_ux_refinement.md).

변경 후에도 예전 화면이 보이면 프로젝트의 종료 파일로 앱을 종료한 다음 실행 파일로 다시 열고 브라우저를 새로고침해 주세요. 서버를 재시작하면 저장 전 세션 입력은 초기화될 수 있습니다. 선택형 GPU 환경은 이미지 미디어 응답 호환을 위해 Streamlit 1.60.0/Starlette 1.7.0 조합을 사용합니다. [실제 화면 적용 점검](docs/review_live_verification.md).

## 개발 에이전트: Ponytail

이 프로젝트 전용 Ponytail 스킬 6개를 `.agents/skills/`에 설치했습니다. 다음 대화부터 `ponytail 스킬로 작업해줘`, `ponytail-review로 현재 변경을 검토해줘`, `ponytail-audit로 소스를 점검해줘`처럼 요청할 수 있습니다.

기존 `AGENTS.md`의 제품 범위, OCR 표준 계약, 개인정보 보호와 테스트 기준을 유지하며 보조 원칙으로 사용합니다. `.codex/hooks.json`의 프로젝트 전용 hook이 대화 시작/재개, 새 요청, 하위 에이전트 시작 시 설치된 Ponytail 원칙과 작업 전 점검 항목을 전달합니다. 수정 전 호출부·기존 Python/OCR/GPU 환경 확인과 수정 후 관련 검증을 상기합니다.

hook 등록과 Codex `/hooks` 화면의 신뢰·활성 확인을 마쳤습니다. 새 대화부터 적용되며, 다른 PC에서는 프로젝트와 hook 신뢰 검토가 다시 필요합니다. 자동 리팩터링·전체 감사·전체 테스트 실행 또는 전역 플러그인 설치를 의미하지 않습니다. [hook 등록·검증 기록](docs/ponytail_hooks_setup.md).

설치 커밋, 사용 범위와 검증: [Ponytail 설치 기록](docs/ponytail_setup.md).

## 2026-10-18 데이터 정리 설계안

다음 문서는 차기 설계이며 현재 구현된 기능·엑셀 양식을 설명하는 부분과 구분합니다.

- [세무사 전달용 통일 양식 변경안](docs/receipt_standardization_proposal.md): 거래처 정보·거래일시·금액 의미, 포인트/상품권/복합결제, 명시 세액과 참고값.
- [상호 보정 정리안](docs/merchant_resolution_design.md): OCR 추출값·DB 후보·사용자 선택값 분리와 특정 거래처 고정 규칙 이전 단계.
- [날짜별 누적 저장 설계안](docs/receipt_accumulation_design.md): 스캔 후 저장, 중복 의심·수정버전·모바일/PC 연결 방향.

이번 변경은 문서 정리만 포함합니다. 현재 코드·DB·8개 엑셀 시트·버전값은 바꾸지 않았고 모바일 동기화/공개 서비스는 구현되지 않았습니다.

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

### Windows: 더블클릭으로 실행/종료

최초 설치로 실행 환경을 준비한 뒤 프로젝트 폴더의 **`영수증 비서 실행.vbs`**를 더블클릭합니다. 명령어 입력 없이 앱이 백그라운드에서 시작되고 기본 브라우저가 열립니다. 실행기는 `.venv-ocr`가 있으면 이를 우선 사용하고, 없으면 기본 `.venv`를 사용합니다.

- 이미 실행 중이면 같은 앱을 다시 엽니다. 코드를 바꿨다면 종료 후 다시 실행합니다.
- 종료하려면 **`영수증 비서 종료.vbs`**를 더블클릭합니다. 브라우저 창만 닫으면 앱은 계속 실행됩니다.
- 기본 주소는 `http://127.0.0.1:8501`입니다. 포트가 사용 중이면 `8511`까지 빈 포트를 찾아 브라우저로 엽니다. 다른 프로그램은 종료하지 않습니다.
- `.env`의 기존 OCR/저장소 설정을 사용합니다. 실행기는 패키지 설치, 모델 다운로드, OCR 요청을 하지 않습니다.
- 실행 상태는 Git에서 제외되는 `output/local_app/state.json`에 PID·시작시각·포트만 저장합니다. 종료 시 PID·시작시각·프로젝트 실행 명령이 모두 일치하는 프로세스만 종료합니다.
- Windows Script Host를 사용할 수 없는 PC에서는 `scripts/run_app.cmd`를 더블클릭합니다. 종료는 아래 PowerShell 명령을 사용할 수 있습니다.

```powershell
.\scripts\run_app.ps1 -Action Stop
```

이 실행기는 현재 PC의 로컬 웹 실행용이며 Windows 시작 시 자동 실행되지는 않습니다. 프로젝트 폴더를 옮기면 바탕화면 바로가기의 대상도 갱신해야 합니다. Python 3.11 이상과 `requirements.txt`를 설치한 `.venv`가 기본 환경입니다. PaddleOCR/GPU 사용 환경은 아래 안내를 따릅니다.

### PaddleOCR/GPU 선택 환경

`paddle_not_installed`는 현재 앱을 실행하는 Python에서 PaddleOCR을 import하지 못했다는 뜻입니다. 다른 Python에 설치되어 있어도 현재 앱에서는 사용할 수 없습니다. GPU 사용에는 GPU용 Paddle 빌드와 정상 CUDA 런타임이 필요합니다.

Windows Python 3.11에서 선택 환경을 준비하는 명령:

```powershell
py -3.11 -m venv .venv-ocr
.\.venv-ocr\Scripts\python.exe -m pip install -r requirements-paddle-gpu.txt
```

`.venv-ocr`가 있으면 실행기는 기본 앱 패키지와 Paddle/PaddleOCR import를 확인한 뒤 이 환경으로 시작합니다. OCR 환경이 손상되면 안내를 표시하며, OCR 없는 `.venv`로 조용히 전환하지 않습니다. 이미 실행 중인 서버에는 환경 변경이 적용되지 않으므로 종료 후 다시 실행합니다.

이 선택 환경은 PaddleOCR 2.7.3, GPU Paddle 2.6.2, NumPy 1.26.4, Streamlit 1.60.0 조합입니다. 기본 `requirements.txt`는 OCR 의존성을 포함하지 않습니다. `PaddleOCR Local`과 `GPU 가속 시도`는 새 작업 화면에서 선택하며, provider 기본값과 CPU 기본 모드는 변경하지 않습니다. 선택 패키지 설치는 드라이버 설치나 OCR 모델 다운로드를 포함하지 않습니다.

### 터미널에서 실행

Windows에서는 아래 명령도 같은 실행기를 사용합니다.

```powershell
.\scripts\run_app.ps1
.\scripts\run_app.ps1 -Action Status -NoDialogs
```

macOS/Linux 또는 가상환경을 직접 활성화한 경우:

```bash
streamlit run app/main.py
```

앱 메뉴:

- `새 작업`: 업로드, 처리, 검수, 엑셀 생성/다운로드
- `처리 이력`: 과거 작업 목록, 상세 조회, 기존 엑셀 재다운로드
- `설정`: 읽기 전용 환경/저장소/DB 상태 확인

## 환경변수 설정

기본 개발과 테스트는 mock provider 기준입니다.

```text
OCR_PROVIDER=mock
PADDLE_USE_GPU=false
PADDLE_USE_ANGLE_CLS=false
PADDLE_LANG=korean
PADDLE_SHOW_LOG=false
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

1. Windows에서는 `영수증 비서 실행.vbs`를 더블클릭하거나 위 실행 명령으로 앱을 엽니다.
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

## Merchant Dictionary Diagnostics

Settings includes a manual merchant dictionary diagnostic section for operator checks. It can show safe aggregate counts for `merchant_master`, `merchant_alias`, import batches, duplicate import logs, latest import file name, and top category counts.

The matcher test form accepts a synthetic merchant name, optional business number, and optional address hint. Results are review candidates only. Business numbers are masked, and the diagnostic output does not include raw OCR text, provider raw JSON, full local paths, phone numbers, representative names, or raw CSV rows.

Saved receipt diagnostics use only safe Processing History fields: merchant name, business number, source file name, and review status. The output is aggregate counts and limited safe samples, and it does not change `ReceiptRecord`, ExcelExporter sheets/columns, or existing Processing History schema.
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

When `PaddleOCR Local` is selected, the New Job screen also offers a per-run
execution mode. `CPU stable mode` is the default. `GPU acceleration attempt`
passes `use_gpu=True` only for the current batch and shows safe Paddle device
diagnostics; if the installed Paddle build cannot use CUDA, the UI blocks the
GPU run and asks the user to choose CPU mode.

When selected, PaddleOCR results follow the safe standard path:

`PaddleOCRProvider -> StandardOCRResult -> StandardOCRParserContext -> ReceiptParser.parse_standard_context() -> ReceiptRecord`

The flow keeps PDF handling unsupported/deferred for PaddleOCR, does not expose
provider raw output, full OCR text, raw JSON, full local paths, secrets, or
endpoint URLs, and does not change Excel export sheets/columns or Processing
History schema.

### Review UI source preview

The review screen now supports a safe selected-row source preview. Reviewers can
choose a row, see it highlighted, and compare the parsed fields with the original
receipt file. JPG/JPEG/PNG files are previewed with `st.image`; PDF files show a
safe notice instead of forced rendering.

The preview uses `stored_relative_path` only, resolves files under the configured
upload root, blocks traversal or files outside `data/uploads`, and displays file
names only. It does not expose OCR raw text, provider raw JSON, full local paths,
secrets, endpoint URLs, or sensitive raw values.

### Merchant candidate dictionary

The app can maintain a local SQLite merchant candidate dictionary from public
store data and user review aliases. This is a review aid only: merchant
candidates do not automatically overwrite `ReceiptRecord.merchant_name` or
`ReceiptRecord.business_number`.

Public store CSV import stores only a minimal summary: merchant name, branch
name, coarse area hint, category names, source row hash, and import batch id.
Representative names, phone numbers, full OCR text, provider raw JSON, and full
local paths are not stored.

Optional National Tax Service business status lookup uses
`NTS_BUSINESS_API_KEY` from `.env` and is limited to OCR-detected business
numbers. It is not a full business-number download path and does not provide tax
or filing judgment.

Import a downloaded public store CSV locally:

```bash
python scripts/import_public_merchants.py path/to/public_store.csv --encoding utf-8-sig
```

The command prints the CSV file name, batch id, imported row count, and skipped
row count only.

The Settings screen also provides a merchant dictionary CSV import box for
multiple public CSV files. Files are imported sequentially through a temporary
file and are not retained after import.

For very large files, prefer the CLI command over browser upload. Streamlit must
upload the file through the browser first, while the CLI reads the local file
directly and uses bulk SQLite inserts.

The CLI and Settings import result show a safe performance summary: file name,
batch id, scanned row count, imported/skipped counts, duplicate-file status,
elapsed seconds, and rows per second. They do not show full local paths or raw
CSV rows.

The Settings upload path allows public merchant CSV files up to 400MB per file.
This is configured in `.streamlit/config.toml` with `server.maxUploadSize = 400`.
Restart Streamlit after changing this value. Near the 400MB limit, the CLI import
is still recommended because it avoids browser upload overhead.

Only these public-store CSV columns are imported:

```text
상호명, 지점명, 상권업종대분류명, 상권업종중분류명, 상권업종소분류명,
도로명, 건물본번지, 건물부번지, 건물명, 도로명주소
```

The importer ignores all other columns, including representative and phone
columns. It stores road-address fields for matching hints, but review and Excel
outputs do not expose full address candidates. The default encoding is
`utf-8-sig` for UTF-8 files with or without BOM; `cp949` is available for older
CSV files.

OCR-derived road-address hints may be extracted from safe parser lines and used
only to boost merchant candidate scores during review. These hints are transient
matching inputs: they do not overwrite `ReceiptRecord`, are not added to Excel
columns or sheets, and are not stored as raw OCR text.

### Review alias learning

When users create the reviewed Excel output, the app may add safe reviewed
merchant names to `merchant_alias` with `source=review`. If the reviewed merchant
name differs from the parser's original merchant name, the original parsed name
may also be kept as an alias for future candidate matching.

Alias learning stores only merchant alias fields plus optional normalized
business number and nullable `merchant_master_id`. It does not store raw OCR
text, provider raw JSON, full local paths, representative names, phone raw
values, or full addresses. Learned aliases remain review candidates only and do
not automatically overwrite future `ReceiptRecord` values.
## Merchant Dictionary Search

Settings includes a manual merchant dictionary search for operators. It accepts
either a merchant-name query or a road-name plus building-number query, then
shows only safe summary fields: merchant name, branch name, category summary,
road hint, business-number presence, and source.

The search does not expose full local paths, raw CSV rows, OCR raw text,
provider raw JSON, representative names, phone raw values, or full business
numbers. For large public merchant data, avoid blank or broad searches; use
specific merchant names or road-name/building-number pairs.

### Safe sample quality checks

Real PaddleOCR receipt-image checks are manual/opt-in only. Default pytest must
not call real PaddleOCR, download OCR models, or process customer files.

When checking real samples, compare one image at a time against the visible
receipt fields and report only a safe summary: file name, expected visible
merchant/date/amount/payment method, parsed fields, address-hint presence, top
merchant candidate summary, and mismatch status. Do not print or store full OCR
raw text, provider raw output, provider raw JSON, full local paths, phone raw
values, representative names, or raw CSV rows.

Processing History may contain stale rows from earlier parser versions. Quality
reports should distinguish current-code reprocessing results from existing DB
rows instead of treating old stored results as current parser regressions.

## 2026-10-19 PaddleOCR 정보 전달 보완

연락처와 같은 줄의 상호·사업자번호 보존, 제목 분리, 약한 총액 후보 재검토 및 원본 영역 재인식을 보완했습니다. 고정 평가에서 기존 엔진 76/88 유지, V5 74/88 → 75/88이며 100%는 아닙니다. [결과와 미완료 항목](docs/ocr_fieldflow_followup.md).

V5 실행기는 검수 DB와 별도로 `data/app.db` 사전을 읽기 전용 조회합니다. 직접 실행 시 선택적 환경변수 `MERCHANT_LOOKUP_DB_PATH`를 지정하며, 미설정이면 기존 검수 DB를 조회합니다. 현재 사전에는 사업자번호 등록이 없어 번호만으로 상호를 찾을 수 없습니다. DB 후보는 사용자가 선택해 초안에 적용하고 기존 저장 버튼으로 반영합니다. 기본 모델은 변경하지 않았습니다.

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

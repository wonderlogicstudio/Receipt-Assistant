# 영수증 OCR 엑셀 비서 MVP

## 프로젝트 개요

영수증 이미지/PDF와 카드 사용내역 엑셀/CSV를 업로드하면 OCR/Parser 결과를 검수하고, 세무사 전달용 표준 엑셀 정리 파일을 다운로드할 수 있는 증빙 정리 보조 도구입니다.

이 MVP의 핵심은 사람이 확인하기 쉬운 엑셀 산출물입니다. OCR 결과와 비용항목은 검수 전 참고값이며, 사용자가 최종 확인한 값이 엑셀에 반영됩니다.

## MVP 기능

| 구분 | 기능 |
|---|---|
| 업로드 | JPG, JPEG, PNG, PDF, XLSX, CSV 업로드 |
| OCR | 기본 데모용 Mock OCR Provider, 선택 가능한 Azure Provider 구조 |
| 파싱 | OCR 결과를 ReceiptRecord로 구조화 |
| 카드내역 | CSV/XLSX 카드 사용내역을 표준 데이터로 변환 |
| 검증 | 필수값 누락, 금액 확인 필요, 중복 의심, 카드 매칭 상태 표시 |
| 검수 | Streamlit 검수 테이블에서 값 수정과 제외 처리 |
| 엑셀 | 정리내역, 월별요약, 비용항목별요약, 검토필요, 카드대조, 원본파일목록, 처리로그, 제외내역 시트 생성 |
| 파일 정리 | 업로드/출력 파일 수동 cleanup 함수 제공, 기본 dry run |

## 현재 지원 범위

- 로컬 Streamlit 웹 MVP
- Mock OCR 기준 데모와 테스트
- 이미지/PDF 영수증 업로드
- 카드 사용내역 CSV/XLSX 업로드
- 사용자 검수 후 엑셀 다운로드
- 업로드 파일과 출력 파일의 수동 정리 함수

## 지원하지 않는 범위

- 홈택스 연동
- 카드사 API 연동
- 로그인/권한관리
- 결제/구독
- 네이티브 모바일 앱
- 회계 프로그램 API 연동
- 클라우드 배포 운영
- 전문가 판단 영역의 결론 제공

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

앱 화면은 다음 순서로 사용합니다.

1. `1단계: 파일 업로드`
2. `파일 저장 및 처리`
3. `3단계: 검수`
4. `표준 엑셀 생성`
5. `엑셀 다운로드`

## 환경변수 설정

`.env.example`을 참고해 로컬 `.env`를 만들 수 있습니다. 실제 key 값은 `.env`에만 넣고 Git에 올리지 않습니다.

기본 데모와 테스트는 Mock OCR 기준입니다.

```text
OCR_PROVIDER=mock
UPLOAD_DIR=data/uploads
OUTPUT_DIR=data/outputs
UPLOAD_RETENTION_DAYS=7
OUTPUT_RETENTION_DAYS=7
CLEANUP_DRY_RUN_DEFAULT=true
```

실제 OCR Provider를 사용할 때만 별도 OCR 서비스 설정값을 `.env`에 넣습니다.

## 테스트 실행 방법

```bash
python -m compileall app tests
python -m pytest
```

## 샘플 사용 흐름

1. 개인정보를 제거하거나 더미 처리한 영수증 이미지/PDF와 카드 사용내역 CSV/XLSX를 준비합니다.
2. 앱을 실행합니다.
3. 파일을 업로드하고 `파일 저장 및 처리`를 누릅니다.
4. 검수 테이블에서 날짜, 상호, 금액, 비용항목 추천값, 검토필요 사유를 확인합니다.
5. 필요한 값을 수정하고 제외할 행은 제외 상태로 바꿉니다.
6. `표준 엑셀 생성`을 누른 뒤 `엑셀 다운로드`로 파일을 저장합니다.
7. 엑셀 파일을 열어 필수 시트와 수정값 반영 여부를 확인합니다.

자세한 흐름은 [sample_user_flow.md](docs/sample_user_flow.md)를 참고합니다.

## 개인정보/파일 보관 주의사항

- 실제 카드번호 전체, 주민번호, 전화번호, 민감정보가 포함된 파일은 파일럿에 사용하지 않습니다.
- 테스트 파일은 개인정보 제거 또는 더미 처리를 권장합니다.
- OCR 원문 전체와 raw JSON 전체는 엑셀에 쓰지 않습니다.
- 전체 로컬 경로는 엑셀에 쓰지 않습니다.
- `.env`는 Git에 올리지 않습니다.
- `data/uploads`, `data/outputs`, `output`의 실제 파일은 Git에 올리지 않습니다.
- 업로드 파일 기본 보관기간은 7일입니다.
- 출력 파일 기본 보관기간은 7일입니다.
- cleanup 기본값은 `dry_run=True`이며 자동 실행되지 않습니다.

## 파일럿 테스트 안내

파일럿 목적은 실제 업무 흐름에서 표준 엑셀 정리 파일이 충분히 이해하기 쉽고 시간을 줄이는지 확인하는 것입니다. 기본 데모는 `OCR_PROVIDER=mock` 기준으로 진행합니다.

파일럿 문서:

- [pilot_guide.md](docs/pilot_guide.md)
- [interview_questions.md](docs/interview_questions.md)
- [sample_user_flow.md](docs/sample_user_flow.md)
- [pilot_feedback_template.md](docs/pilot_feedback_template.md)

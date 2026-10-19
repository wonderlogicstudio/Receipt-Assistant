# 사용자 중심 검수 화면 정리

2026-10-19. 기존 미커밋 작업을 보존한 상태에서 사용자 승인 범위만 변경했다. 커밋·푸시는 수행하지 않았다.

후속 실제 화면 검증: 기존 서버의 이전 모듈 사용과 이미지 HTTP 응답 오류를 수정했다. [실제 브라우저 검증 기록](review_live_verification.md)을 참고한다. 아래 798개 테스트와 시각 검수 미수행 표시는 최초 소스 변경 시점의 기록이다.

## 1. 생성·수정 파일

- 생성: `app/ui/receipt_form.py`, `tests/test_receipt_form.py`, 이 기록.
- 화면: `app/ui/review_view.py`, `app/ui/streamlit_app.py`, `app/ui/summary_view.py`.
- 파싱·출력: `app/parser/receipt_parser.py`, `app/parser/normalizers.py`, `app/exporter/excel_exporter.py`.
- 회귀: `tests/test_review_view.py`, `tests/test_receipt_parser.py`, `tests/test_receipt_parser_standard_comparison.py`, `tests/test_paddle_synthetic_quality_fixtures.py`, `tests/test_excel_exporter.py`, `tests/test_standard_parser_excel_export_regression.py`, `tests/fixtures/paddle_synthetic/cases.json`.
- 동기화: README, PLAN, SPEC, CHECKLIST, CHANGE_CONTROL, DECISIONS.

## 2. 구현 기능

영수증 선택 후 원본과 표준 수정 서식을 함께 표시한다. 사용일자·상호·사업자번호·할인·공급가액·부가세·결제금액·결제수단과 중복의심을 중심으로 검수한다. 파일명과 추가 추출금액은 접힌 상세정보로 옮겼다. 상호 후보는 사용자가 요청할 때 이름만 표시한다. 저장 메타데이터 표, 별도 선택/하이라이트/수정 화면과 기본 성능·후보 점수는 제거했다.

중복의심 Y는 자동 제외하지 않는다. 카드내역 미업로드/매칭 미실행을 0건과 구분한다. 수정 저장은 다른 영수증을 보존하고 기존 다운로드 파일을 해제한다. 사용자에게는 다른 영수증으로 이동하기 전에 저장하도록 안내한다.

## 3. 구조

기존 OCR Provider → StandardOCRResult/Parser context → ReceiptRecord → 검수 → ExcelExporter 계층을 유지한다. 작은 서식 모듈만 추가하고 신규 패키지는 설치하지 않았다. 사용되지 않는 중복 화면 경로와 역산 함수를 제거했다.

명시 공급가액·부가세만 사용하며 누락 할인/최종금액을 차액으로 생성하지 않는다. 원본의 0원과 미표기를 구분한다. 기존 엑셀 8개 시트와 컬럼은 유지하고 추정 세액 셀을 비운다. 과거 레코드에 추정 세액이 남아 있어도 새로 내보낼 때는 비운다. Provider/GPU와 DB 구조는 변경하지 않았다.

## 4. 테스트 명령

```powershell
.venv-ocr\Scripts\python.exe -m compileall -q app tests
.venv-ocr\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short --disable-warnings
```

## 5. 테스트 결과

compileall 통과. 전체 pytest **798 passed / 2 skipped / 100 warnings**, 34.05초. 실제 OCR opt-in 테스트는 기본 실행에서 건너뛴다. 경고는 기존 Paddle/protobuf deprecation이다.

AppTest로 단일 원본/서식 공간, 상호 수정 저장, 파일명 비노출, 수정 후 이전 다운로드 해제, 카드 미업로드와 0건 구분을 확인했다. 단위·회귀 테스트로 사업자번호/할인 수정, 선택 외 레코드와 순서 보존, 명시 0원, 중복 자동 제외 금지, 누락 세액/할인/최종금액 비생성, StandardOCR·Azure adapter·Parser·Validator·Exporter·end-to-end 흐름을 확인했다.

작업 시작 사본과 해시 비교로 이번 범위 외 기존 Python 파일과 PaddleOCRProvider의 기존 수정이 보존되었음을 확인했다. 실제 고객 파일 재처리와 브라우저 시각 검수는 수행하지 않았다.

## 6. 문서 동기화

CHANGE_CONTROL에 승인 범위를 기록하고 README/PLAN/SPEC/CHECKLIST/DECISIONS를 갱신했다. 정책 기준일은 2026-10-19이며 아래의 과거 참고 세액 추정 설명보다 새 정책을 우선한다. 모델/DB 스키마 변경은 없다.

## 7. 남은 리스크와 모바일 방향

- 누락값 계산 제거는 인식 정확도 개선을 보증하지 않는다. Provider의 기존 후보 추출과 상호 보정은 유지되며 원본 대조가 필요하다.
- 현재 화면의 주 결제금액은 기존 `total_amount`다. 기존 실제결제액 우선 추출 의미는 유지한다. 사용자가 금액을 직접 변경하면 엑셀의 총금액과 최종결제금액(`final_amount`)에 함께 반영하고, `paid_amount`는 별도 대조값으로 보존한다. 수정하지 않은 원래 금액의 관계는 자동 변경하지 않는다. 포인트·상품권·복합결제의 새 통일 계약은 후속 전환이다.
- 기존 DB·이전 엑셀은 재작성하지 않았다. 검수 중 저장하지 않고 다른 영수증을 선택하면 입력 중인 값은 보존되지 않는다. 기본 행별 표 편집은 단일 서식으로 대체했다.
- 모바일 앱은 구현하지 않았다. 표준 필드 계약, 검증 규칙/합성 fixture, 카드 매칭과 엑셀 생성의 서버/PC 계층은 재사용할 수 있다. 모바일 화면과 기기 OCR 어댑터는 별도 구현하며 Python/CUDA 환경 전체를 앱에 포함할 필요는 없다.
- 측정 당시 Python 제품 소스는 약 0.7 MiB, `.venv-ocr`는 약 2.83 GiB, 로컬 `data`는 약 3.82 GiB였다. 개발 실행환경과 누적 데이터 크기는 앱 다운로드 용량과 다르다. 데이터는 임의 삭제하지 않았다.
- 보리의 현재 35 MB 표기와 내부 SDK는 직접 확인하지 못했다. 배포 앱 크기만으로 서버 사용 여부·모델 크기·품질을 단정하지 않는다. 모바일 OCR의 예시인 [ML Kit 공식 문서](https://developers.google.com/ml-kit/vision/text-recognition/v2/android)는 문자 체계/아키텍처별 약 4 MB의 번들 증가 또는 동적 모델 다운로드 구성을 설명한다. 이는 보리의 SDK를 확인한 근거가 아니다.

## 8. 추천 커밋 메시지

`feat: streamline receipt review and preserve missing amounts`

현재 작업 트리에는 이 작업 전 변경도 함께 있다. 커밋 시 범위를 확인하여 작은 단위로 나눈다.

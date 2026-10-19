# GS 긴 영수증 오류 수정과 로컬 PP-OCRv5 비교

2026-10-19. 기존 사용자 변경을 보존했다. 유료 API, 정답 주입, 금액 역산은 사용하지 않았다. 기본 엔진은 교체하지 않았다.

## 확인된 결과

사용자가 보고한 GS 사진을 로컬에서 재처리했다.

| 항목 | 기존 환경 / 수정 전 | 격리된 V5 환경 / 수정 후 |
|---|---|---|
| 상호 | 구매·환불 안내문 일부를 선택 | GS THE FRESH |
| 최종결제금액 | 누락 | 26,390 |
| 부가세 | 2,398 | 2,398 |
| 공급가액 | 누락 | 누락 유지 |

‘과세’ 숫자를 공급가액으로 임의 재분류하지 않았다. 상호·금액은 모델이 읽은 값이며 브랜드 사전이나 상수로 넣지 않았다. 기존 엔진의 동일 금액 영역 재인식은 26,399로 오독했다. 새 모델의 다른 영역도 26,30으로 오독했으므로, 한 영역의 성공만으로 전체 품질을 판단하지 않았다.

같은 거래의 다른 촬영본에서도 V5는 최종금액 26,390과 부가세 2,398을 추출했다. 그 촬영본의 상호는 누락됐다. 날짜·거래번호가 같은 재촬영이며 **새로운 독립 영수증 검증으로 집계하지 않는다**.

## 평가 기준과 전체 비교

기존 16장과 이번 GS 1장을 처리했다. 기존 평가 파일 3개의 정답·항목·이미지 해시를 변경하지 않았다. 기존 기준이 있는 11장의 88항목으로만 점수를 비교한다. 이 중 표시된 값 71항목과 미표기 기대값 17항목이 있다. 나머지 6장은 정식 점수 없이 관찰·전달 검증 대상으로 구분한다. 이번에 새로운 정답 파일을 쓰지 않았으며 평가 자료는 인식 코드로 전달하지 않는다.

| 단계 | 기존 고정 기준 일치 | 의미 |
|---|---:|---|
| 수정 전 기존 GPU 엔진 | 76/88 | 기존 기준선 |
| 공통 수정 후 기존 GPU 엔진 | 76/88 | 기존 일치 항목 퇴행 0 |
| 새 GPU 모델 최초 전체 비교 | 73/88 | GS 회복과 별개로 기존 항목 퇴행 발생 |
| 숫자 열 분리 수정 후 새 GPU 모델 | 74/88 | 수량·합계 결합 오류 1항목 회복 |

새 모델을 기본 엔진으로 승격하지 않는다. 100%를 달성하지 못했다. V5에서 기존 정답 4개가 퇴행하고 2개가 회복된 결과다. 남은 차이는 상호 오독·누락, 날짜 누락, 잘못 채운 금액 등을 포함한다. 음식점 첫 글자에 관한 기존 기준의 논점도 이번에 바꾸지 않았다.

기존 엔진의 최종 집계는 일치 76·누락 9·오답 3, V5는 일치 74·누락 9·오답 5다. 미표기 기대 항목 17개의 오입력은 두 환경 모두 0이며, 표시된 값만의 일치는 기존 59/71·V5 57/71이다. 잘못 채운 값 문제는 해결되지 않았다.

대표 퇴행에는 총액 대신 POS 번호의 음수 접미부를 선택한 사례가 있다. 명시 POS 식별자 제외와 상품표 제목 방어를 추가했지만, 이 실제 사진의 오답은 아직 남았다. 합성 테스트 통과를 실제 사진 회복으로 보고하지 않는다.

## 유지한 변경

1. `app/core/receipt_evidence.py`: 구매점포·기간·교환·환불이 포함된 안내문 조각을 상호 후보에서 제외한다. 매장명을 넣는 규칙이 아니다.
2. `app/ocr/paddle_provider.py`: 좌표상 떨어진 수량·금액 열을 하나의 숫자로 붙이지 않는다. 인접한 숫자 조각의 기존 결합은 유지한다. 상품표의 ‘금액’ 제목과 명시 POS 식별자도 방어한다.
3. `app/ocr/paddle_v5_engine.py`: SDK 3.x 실행 결과를 기존 Provider 내부 형식으로 연결한다. 인식된 `rec_polys`와 텍스트·점수를 함께 사용하고 길이가 다르면 실패한다. 원본 SDK 객체를 Parser에 넘기지 않는다.
4. 설치된 SDK가 3.x일 때만 위 실행 경로를 사용한다. `.venv-ocr`의 기존 SDK 2.7.3/GPU 2.6.2는 보존했다. 기본 provider와 기본 실행 파일은 유지한다.
5. `scripts/local_app.ps1`: `-Runtime v5` 선택 실행과 별도 상태·DB·업로드·산출물 경로를 지원한다. 네이티브 stderr 경고만으로 정상 환경을 거부하던 Windows 사전 검사도 종료 코드 기준으로 고쳤다.
6. 합성 테스트는 실제와 다른 매장·숫자를 사용한다. 반복된 결제금액을 승인번호와 구분하고, 숫자 열 분리·인접 조각·음수 환불·SDK 경계·실행 환경 분리를 검증한다.

효과가 없었던 추가 전체 이미지 분할과 영문 헤더 재인식 실험은 제거했다. 기존 Parser, ReceiptRecord, StandardOCRResult, StandardOCRParserContext, ExcelExporter 시트·컬럼·버전 계약은 바꾸지 않았다.

## 실행과 복구

프로젝트 폴더의 **영수증 비서 V5 실행.vbs**로 비교 앱을 연다. 기본 주소는 `http://127.0.0.1:8502`이며 사용 중이면 다음 빈 포트를 선택한다. 화면에서 **GPU 가속 시도**를 선택하고 원본을 새로 업로드·처리한다. 이전 DB 결과는 자동 정정하지 않는다.

종료는 **영수증 비서 V5 종료.vbs**다. 일반 실행·종료 파일은 기존 환경을 계속 사용한다. V5의 DB와 파일은 `data/paddle_v5/`, 프로세스 상태는 `output/local_app_v5/`다. 모두 Git 제외 대상이다. 두 앱은 검수 세션을 공유하지 않는다.

새 PC에서의 선택 설치(Windows Python 3.11, 검증한 NVIDIA CUDA 11.8 휠):

```powershell
py -3.11 -m venv .venv-paddle-v5
.venv-paddle-v5\Scripts\python.exe -m pip install paddlepaddle-gpu==3.2.2 --index-url https://www.paddlepaddle.org.cn/packages/stable/cu118/ --extra-index-url https://pypi.org/simple
.venv-paddle-v5\Scripts\python.exe -m pip install -r requirements-paddle-v5.txt
```

모델·GPU 라이브러리의 로컬 다운로드가 필요하다. 영수증은 모델 서버로 전송하지 않는다. 이번 PC에서 CUDA GPU 추론은 완료됐고 `pip check`도 통과했다. cuDNN 세부 버전에 관한 런타임 경고가 있었으므로 다른 PC의 GPU 호환성까지 보증하지 않는다.

## 검증과 성능

- 기본 환경 전체 테스트: **1,019 passed, 3 skipped**. 실제 OCR은 기본 pytest에 포함하지 않는다.
- 새 SDK 설치 환경의 Provider·표준 계약·엑셀 흐름: **85 passed**.
- `compileall app tests`, `git diff --check`, 새 환경 `pip check`를 확인했다.
- 실제 StandardOCRResult 17건을 앱 처리 함수·검수 표·상세 입력값·8시트 ExcelExporter까지 전달해 **136필드 보존**을 대조했다. 이는 정답률이 아니라 계층 간 전달 확인이다.
- 최초 17장 전체 측정: 기존 GPU **85.33초 / 85회**, V5 GPU **84.31초 / 82회**. 모델 초기화 포함 단일 실행 관찰값이다.
- 최종 기존 엔진 재처리: **82.49초 / 85회**, **76/88 유지·기존 일치 항목 퇴행 0**.
- 최종 숫자 열 수정 후 V5의 OCR 결과 캐시를 비운 재측정: **72.23초 / 79회**. 엔진은 이미 메모리에 있으므로 최초 실행과 직접 속도 향상률로 비교하지 않는다.
- 최종 POS 필터·SDK 테스트 추가 후 새 프로세스에서 다시 처리해 **74/88 유지, 81.08초 / 79회**, GS **9.55초 / 12회**를 확인했다. 같은 실제 결과의 표·상세 입력값·엑셀 전달 대조도 재실행했다.
- 해당 GS 사진: 기존 전체 **12.86초 / 12회**; 최종 V5 워밍 상태 **9.32초 / 12회**. 별도 프로세스의 첫 실행은 **16.70초**였다. ROI 추론 시간과 전체 처리시간을 혼용하지 않는다.
- CPU V5 실험은 전체 재시도 포함 약 **215.85초**, 단일 패스 약 **20.73초**였다. CPU 결과를 GPU 비교 수치와 합치지 않는다.
- 결과 캐시로 재생한 중간 실행 시간은 성능 집계에서 제외했다. 실제 원문·raw output은 보고서나 fixture에 저장하지 않았다.

실제 브라우저에서는 별도 앱의 실행·Paddle 선택·GPU 선택까지만 확인했다. Edge 확장의 파일 URL 접근 권한이 꺼져 있어 자동 파일 업로드가 차단됐다. **실제 브라우저의 표·팝업·다운로드 성공까지 확인했다고 주장하지 않는다.** 동일 실제 결과의 함수 단계 전달 검증은 위와 같이 수행했다.

검증 명령:

```powershell
.venv\Scripts\python.exe -m compileall -q app tests
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --disable-warnings --tb=short
.venv-paddle-v5\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_paddle_v5_engine.py tests/test_paddle_provider_optional.py tests/test_receipt_candidate_contract.py tests/test_standard_parser_excel_export_regression.py tests/test_end_to_end_export_flow.py --disable-warnings --tb=short
.venv-paddle-v5\Scripts\python.exe -m pip check
git diff --check
```

## 품질을 더 올릴 대안과 다음 판단

권장 순서는 **후보 선택 오류 제거 → 필요한 원본 영역 재인식 → 모델별 독립 검증 → 보조 모델 검토**다.

- 같은 이미지의 로컬 OCR 결과를 메모리에서 재생해 추출 코드 변경부터 검증한다. 읽힌 글자가 맞는데 값이 틀리면 모델을 반복 호출하지 않는다.
- 누락뿐 아니라 이미 채워진 금액의 라벨·영역·좌표·식별자 근거를 점검한다. 수량·상품금액·세액·POS/승인번호를 배제하고 충돌은 검수 사유로 남긴다. 수치 합계를 맞추려고 값을 만들지 않는다.
- PP-OCRv5는 이번 GS의 유효한 대안이지만 전체 교체 근거는 부족하다. 기존 정답 퇴행을 해소한 뒤, 이번 개발에서 보지 않은 서로 다른 영수증으로 다시 검증해야 한다.
- 로컬 문서용 VLM은 복잡한 배치의 후보 제안용 다음 실험으로 가능하다. 원본 영역의 직접 근거와 독립 비교가 필요하며, 자동 정답 보정기로 연결하지 않는다. 이번에는 설치·성능·품질을 검증하지 않았다.
- 촬영 단계에서 영수증 전체가 평평하게 보이도록 안내하고 원본 해상도를 유지하는 것도 병행한다. 이번 재촬영에서도 상호 누락이 있으므로 촬영 안내만으로 해결됐다고 볼 수 없다.

참고: [공식 PP-OCRv5 다국어 설명](https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html), [공식 SDK 3.x 전환 안내](https://www.paddleocr.ai/main/en/update/upgrade_notes.html). 공식 벤치마크 수치를 이 프로젝트의 정확도로 사용하지 않는다.

## 변경 파일

- 운영 코드: `app/core/receipt_evidence.py`, `app/ocr/paddle_provider.py`, 새 `app/ocr/paddle_v5_engine.py`.
- 실행/설치: `scripts/local_app.ps1`, 새 `requirements-paddle-v5.txt`, 새 `영수증 비서 V5 실행.vbs`와 `영수증 비서 V5 종료.vbs`, `.gitignore`.
- 테스트: 새 `tests/test_receipt_instructions.py`, 새 `tests/test_paddle_v5_engine.py`, `tests/test_paddle_receipt_rows.py`, `tests/test_receipt_candidate_contract.py`, `tests/test_local_app_launcher.py`.
- 문서: 이 보고서, README, PLAN, SPEC, CHECKLIST, CHANGE_CONTROL, DECISIONS.

작업 시작 스냅샷과 비교해 그 밖의 기존 코드 변경을 보존했다. 커밋·푸시는 하지 않았다. 추천 커밋 메시지: `fix: separate receipt amount columns and add isolated local OCR comparison`.

# 상세 검수: 원본 전체 보기와 행 클릭

2026-10-19. 사용자 요청: 잘리는 원본을 한 번에 보고 팝업을 화면 높이에 맞추며, 표 행 클릭으로도 상세 검수를 연다. 기존 상세 검수 열기 버튼은 유지한다. 합성 HTML 시안을 먼저 보여준 뒤 적용했다.

## 1. 생성·수정 파일

- `app/ui/review_view.py`: 전체 이미지 비율 유지, 팝업/입력 영역 높이, 셀 클릭과 영수증 연결, 닫은 뒤 재선택.
- `tests/test_review_view.py`, `tests/test_receipt_form.py`: 첫 행·임의 셀·빈/범위 밖 선택·재열기 회귀.
- README, PLAN, SPEC, CHECKLIST, CHANGE_CONTROL, DECISIONS와 이 문서.
- 시안·합성 실화면 이미지는 Git에서 제외한 `output/review_fit_preview.png`, `output/review_fit_actual_large.png`, `output/review_fit_actual_768.png`에 보관했다.

## 2. 구현 기능

왼쪽 원본은 창 높이와 이미지 비율에 맞춰 축소하여 위부터 아래까지 표시한다. 가로 폭에 강제로 맞춘 큰 이미지를 520px 영역에서 잘라 보이던 구성을 제거했다. 팝업 상하 여백을 줄이고 화면 크기에 맞춰 높이를 사용한다. 오른쪽 서식은 필요할 때 내부에서만 스크롤하며 하단의 이전/다음/닫기/저장/저장 후 다음은 비교 영역 밖에 유지한다.

표의 데이터 셀을 클릭하면 해당 행의 영수증을 연다. Streamlit 1.60에서 단일 행 선택만 켜면 셀 클릭은 행 선택 이벤트가 아니므로, 단일 셀 선택 이벤트의 원래 행 위치를 사용한다. 첫 행도 열리고 닫은 행도 다시 클릭할 수 있도록 복귀 시 표 선택만 비운다. 선택한 영수증과 초안·필터·표 위치는 유지한다. 기존 버튼과 선택 상자도 유지한다.

## 3. 구조와 경계

새 패키지나 OCR 호출을 추가하지 않았다. 기존 원본 경로 검증, EXIF 정리와 이미지 payload를 재사용한다. 이미지를 자르거나 원본 파일을 수정하지 않고 표시 배율만 바꾼다. CSS는 상세 팝업과 이름 붙인 비교 영역으로 한정했다.

초안·저장·엑셀 무효화·이전/다음·검수 의미와 표준 OCR/Parser/Validator/DB/Exporter 계약은 바꾸지 않았다. 고객 파일·사용 중인 앱 세션은 재처리/재시작하지 않았다.

## 4. 검증 명령

```powershell
.venv\Scripts\python.exe -B -m compileall -q app tests
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_review_view.py tests/test_receipt_form.py tests/test_streamlit_app.py tests/test_excel_exporter.py tests/test_end_to_end_export_flow.py --disable-warnings --tb=short
git -c core.whitespace=cr-at-eol diff --check
```

## 5. 결과

- 관련 **96 passed**, 기존 datetime 등 경고 137건. compileall 통과.
- 행 선택이 팝업을 열지 않던 문제를 수정 전 두 회귀에서 재현하고 통과시켰다. 원래 행 위치, 첫 행, 빈/범위 밖 선택, 셀 클릭, 버튼 진입·초안·검수 저장·엑셀을 확인했다.
- 실제 Chrome의 별도 로컬 합성 화면에서 첫 행 클릭으로 자동 열기, 닫은 뒤 같은 행 클릭으로 재열기, 기존 버튼 열기를 확인했다.
- 1718×1256과 1280×768에서 긴 합성 영수증의 위·아래 끝이 모두 보였다. 768px 창에서 팝업 하단은 약 742px, 저장 후 다음 버튼 하단은 약 718px로 화면 안에 있었다.
- 오른쪽 영역을 스크롤해도 이미지 위쪽 좌표와 버튼 위치는 유지됐다. 원본 전체 보기 배율은 이미지 종횡비를 보존했다.

## 6. 문서 동기화

기존 520px 독립 스크롤 설명을 이 후속 정책으로 보완했다. README/SPEC에 사용 방법, 나머지 관리 문서에 범위·결과·한계를 기록했다. 기존 UI 기록은 이전 시점의 결과로 보존했다.

## 7. 남은 위험·미검증 범위

긴 영수증을 낮은 창에서 한 번에 표시하면 글자가 작아진다. 별도 확대 컨트롤은 이번에 추가하지 않았다. 모바일·매우 낮은 창과 브라우저별 차이는 검증하지 않았다. PDF 원본 표시 지원 범위도 기존과 같다. 합성 화면으로 검증했으며 고객 사진 OCR을 다시 실행하지 않았다.

사용 중인 서버는 기존 모듈을 사용할 수 있으므로 저장하지 않은 입력을 확인한 뒤 프로젝트 실행/종료 파일로 다시 시작해야 한다. 재시작 시 세션 초안이 사라질 수 있다. 기존 DB·엑셀·OCR 결과는 바꾸지 않았으며 커밋·푸시하지 않았다.

## 8. 추천 커밋 메시지

`fix: fit receipt preview and open review from table cells`

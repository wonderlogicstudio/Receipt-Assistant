# PaddleOCR/GPU 실행 환경 복구

2026-10-19. 증상: 더블클릭 앱에서 `paddle_not_installed`, GPU 모드 사용 불가.

## 1. 생성/수정한 파일 목록

- 수정: `.gitignore`, `scripts/local_app.ps1`, `tests/test_local_app_launcher.py`.
- 추가: `requirements-paddle-gpu.txt`, 이 기록.
- 문서 반영: `README.md`, `CHECKLIST.md`, `CHANGE_CONTROL.md`, `DECISIONS.md`.
- 로컬 설치: Git에서 제외하는 `.venv-ocr/`. 앱 소스와 기본 `requirements.txt`는 변경하지 않았다.

## 2. 구현한 기능 요약

OCR 패키지가 없는 Python 3.13 기본 가상환경을 고정 사용하던 실행기를 수정했다. Python 3.11 OCR 환경이 있으면 그 환경을 우선하고, 손상되면 명시적으로 실패 안내를 표시한다. 기존 웹 전용 가상환경은 유지한다.

## 3. 주요 구조 설명

기존 Python 3.10의 PaddleOCR 2.7.3/GPU Paddle 2.6.2는 import, CUDA 인식 및 작은 GPU 텐서 연산에 성공했다. RTX 3060 드라이버가 인식되므로 이번 증상의 원인은 실행 환경 선택이었다.

프로젝트 최소 Python 3.11 기준에 맞춰 `.venv-ocr`를 준비했다. 현재 PC의 등록된 Python 3.11 실행 별칭은 동작하지 않아 [CPython 공식 문서가 안내하는 NuGet 배포](https://docs.python.org/3.11/using/windows.html#the-nuget-org-packages)의 Python 3.11.9를 이 폴더 내부 runtime으로 사용했다. 전역 설치와 드라이버는 변경하지 않았다.

선택 환경은 `requirements-paddle-gpu.txt`의 PaddleOCR 2.7.3, GPU Paddle 2.6.2, NumPy 1.26.4, Streamlit 1.60.0을 사용한다. GPU Paddle의 protobuf 제약을 만족하도록 웹 패키지 버전을 고정했다. 실행 시에는 import만 검사하고 OCR 모델을 내려받거나 추론하지 않는다.

기존 Provider, 표준 OCR 계약, Parser, Validator, 엑셀 및 이력 구조는 유지한다. 새 작업의 provider와 GPU 선택은 기존 UI를 사용한다.

## 4. 테스트 명령어

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_local_app_launcher.py -q -p no:cacheprovider
.\.venv-ocr\Scripts\python.exe -m pip check
.\.venv-ocr\Scripts\python.exe -m compileall -q app tests
.\.venv-ocr\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

실제 OCR은 기본 pytest와 별도로, 기존 캐시 모델만 허용하고 네트워크 다운로드를 차단한 수동 검사로 수행했다. 임시 합성 이미지에는 테스트 상호, 날짜, 합계만 그렸다. OCR 원문/JSON/전체 파일 경로를 출력하지 않고 상태·진단 코드·block 수·추론 GPU 설정만 보고했다. 고객 파일은 사용하지 않았다.

## 5. 테스트 결과

- 실행기 테스트 15 passed: OCR 환경 우선 선택, 웹 전용 환경 호환, 손상된 OCR 환경의 실패 처리 및 기존 시작/종료 안전성.
- OCR 환경 `pip check`: 충돌 없음. compileall: 통과.
- 전체 pytest: 784 passed / 2 skipped / 100 warnings, 35.57초. 경고는 Paddle/protobuf의 deprecated API 등이며 실제 OCR 선택 테스트는 기본 실행에서 제외됐다.
- GPU 빌드=true, GPU 1개, GPU 텐서 연산=true.
- 합성 CPU OCR: completed, diagnostic 없음, block 5개, detector GPU=false.
- 합성 GPU OCR: completed, diagnostic 없음, block 5개, detector GPU=true.
- AppTest: PaddleOCR Local/GPU 선택 시 예외와 GPU 빌드 경고 차단 없음.
- 서버 재시작 후 실제 프로세스의 Python이 `.venv-ocr`에 속하며 health 응답이 정상임을 확인했다.
- 의도한 실행기·실행기 테스트 변경을 제외한 기존 소스/테스트/설정 132개가 사전 해시와 일치했다.

## 6. 문서 동기화 여부

README에 선택 환경 설치·재시작 안내, CHANGE_CONTROL과 DECISIONS에 환경 복구 결정, CHECKLIST에 실제 검증 범위를 기록했다. 제품 범위·데이터 모델·엑셀 계약·표준 테스트 명령이 바뀌지 않아 PLAN/SPEC/AGENTS는 유지했다.

## 7. 남은 리스크

고객이 보고한 영수증 이미지는 재처리하지 않았으므로 개별 이미지 정확도는 미검증이다. 합성 OCR 성공은 세무상 적격성이나 모든 양식의 인식 성공을 의미하지 않는다. GPU 사용은 새 작업 화면의 `PaddleOCR Local` → `GPU 가속 시도`에서 선택한다. 새로운 PC는 별도 GPU 런타임과 모델 준비가 필요하다.

## 8. 추천 커밋 메시지

`fix: launch app with the optional PaddleOCR GPU environment`

이번 작업에서 커밋/푸시는 실행하지 않았다.

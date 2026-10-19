# 상호 열 경계·불완전 합계 조각 후속 수정

2026-10-19. 사용자가 실제 앱의 상호 빈칸과 최종결제금액 1,000원을 보고했다. 범위는 해당 실패를 일으킨 Provider 공통 경계 두 곳이며 전체 요청서의 구현을 뜻하지 않는다.

## 원인과 수정

- 같은 행의 `상호: 이름 대표자: 사람`이 한 문자열로 결합돼 이름 전체가 잡음으로 제외됐다. 명시된 다음 필드 라벨과 콜론에서 상호 값을 끝낸다. 콜론이 있는 일반 이름을 임의 분할하지 않는다.
- 총합계가 `10`과 `00` 두 검출 조각으로 읽혔고 공백 제거로 1,000원 후보가 만들어졌다. 숫자를 생성하지 않고, 명시 합계 행에서 세 자리 그룹 규칙이 깨진 여러 숫자 블록만 최대 두 행 다시 읽는다. 숫자 블록 좌표의 기울기로 영역을 보정하고 EXIF 회전 후 같은 로컬 PaddleOCR에 인식 전용으로 전달한다.
- 새 인식이 순수 금액 형식·신뢰도 0.97 이상일 때만 해당 행 출처의 기존 합계/최종금액 후보를 교체한다. 다른 출처의 합계는 남겨 Parser가 충돌을 검토하게 한다. 관측된 0원도 유지한다. 유효한 세 자리 그룹은 추가 호출하지 않는다.
- 정답·상호 사전·번호·사진명·해시·금액의 정답 주입, 역산, 모델/의존성 교체, 유료 API 호출은 추가하지 않았다.

## 실제 사진 결과

동일 원본·엔진·설정으로 합계 1,000 → 10,000, 부가세 909 → 909다. 상호는 빈칸 → OCR 관측값으로 회복했으나, 기존 고정 기준과 첫 글자가 달라 **불일치를 그대로 유지**한다. 정답지는 고치지 않았다.

단일 사진 측정은 20.24초/6호출 → 19.77초/7호출이다. 초기화·실행 편차가 있어 속도 향상이라고 주장하지 않는다. 추가 호출 1회는 총합계 숫자 영역의 인식 전용 호출이다.

기존 16장 재평가에서 이전 일치값의 퇴행은 0이다. 원래 8장 기준은 40/47 유지, 확장 기준 40/49 유지, 문제 사진은 25/29 유지다. 이전 별도 검증 사진은 24/30 → 25/30이지만 이번 수정에 사용했으므로 이제 개발 자료다. 새 미사용 사진에 대한 일반화 검증은 아니다. 이름 누락 → 오답도 개선 일치로 세지 않았다.

평가 요약은 기존 파일을 덮어쓰지 않고 `output/quality_runs/quality12_label_total_*.json`과 `label_total_*.json`으로 구분한다. 원본 파일과 기존 DB/엑셀을 자동 수정하지 않는다.

## 계약과 검증

수정: `app/ocr/paddle_provider.py`, `tests/test_paddle_label_total_recovery.py`, 필수 문서와 이 기록. 표준 OCR 모델/Parser/Validator/ReceiptRecord/UI/엑셀 시트·컬럼·버전은 바꾸지 않는다. Provider raw response를 Parser에 전달하지 않는다.

```powershell
.venv\Scripts\python.exe -B -m compileall -q app tests scripts
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --disable-warnings --tb=short
.venv-ocr\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_paddle_label_total_recovery.py tests/test_paddle_numeric_rows.py tests/test_paddle_receipt_rows.py tests/test_paddle_identity_integrity.py
.venv-ocr\Scripts\python.exe -B output/probe_label_total.py app_verified
.venv-ocr\Scripts\python.exe -B output/run_quality12.py label_total dev problems validation
git -c core.whitespace=cr-at-eol diff --check
```

최종 검증: compileall·diff check 통과, 기본 **942 passed / 3 skipped**(경고 1,061개), OCR 환경 관련 **38 passed**. 실제 같은 원본에서 얻은 StandardOCRResult를 앱 처리 함수에 전달하고 표·검수 서식·기존 8개 시트 엑셀의 금액 대조 assert를 통과했다. 이 대조를 포함한 마지막 관측은 21.91초/7호출이다. 초기 단독 OCR 측정과 직접 성능 비교하지 않는다.

사용자의 `지금 재시작` 승인 후 프로젝트 전용 실행기로 종료·시작했다. 8501 running과 health HTTP 200/ok를 확인했다. 새 Chrome 로컬 앱 화면에서 이번 처리 Provider를 PaddleOCR Local, 실행 모드를 GPU 가속으로 선택했고 `cuda_compiled=True, device=gpu_0`를 확인했다. 기존 저장 DB/엑셀은 보존한다. 화면 증거는 로컬 `output/label_total_restart.png`다.

브라우저는 새 작업 대기 상태이며 재업로드·재처리는 하지 않았다. 기존 화면의 잘못된 값이 자동 정정됐다고 주장하지 않는다. 위 실제 원본의 프로그램상 앱 처리·표·서식·엑셀 대조와 브라우저 재처리를 구분한다.

## 남은 범위

재인식이 실패하면 기존 불완전 후보가 남을 수 있으며 검수가 필요하다. 상호 첫 글자, 사업자번호 누락 등은 해결했다고 주장하지 않는다. 최근 검토한 다른 Parser 오류·포인트·복합결제·평가 기준 사전 검사도 이번 두 곳의 수정에 포함되지 않는다.

기존 사용 중 세션·과거 처리 결과는 코드만 바꿔 자동 정정되지 않는다. 서버 재시작과 새 처리가 필요할 수 있으며 미저장 세션은 사전 안내 없이 초기화하지 않는다. 커밋·푸시는 하지 않는다.

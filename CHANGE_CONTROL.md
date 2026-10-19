# 변경 관리 규칙

## CC-2026-10-19-GSFRESH: 공통 오류 수정과 격리된 V5 비교

사용자의 GS 상호·최종금액 오류 개선 및 대안 검증 요청 범위다. 안내문 상호 오탐과 분리된 숫자 열 결합을 수정하고, SDK 3.x bridge·선택 requirements·별도 실행 모드만 추가한다. Provider 결과는 기존 표준 계약을 사용하며 Parser·Validator·Exporter에 raw SDK 입력을 추가하지 않는다.

기본 엔진은 76/88 유지, V5는 74/88이므로 기본 교체를 보류한다. 기존 Python 환경·앱 세션·DB·모델/엑셀 계약은 보존한다. V5 실행만 별도 `data/paddle_v5/`와 `output/local_app_v5/`를 사용한다. 실제 사진·정답·raw output은 커밋하지 않고 유료 API·금액 역산·상호/사업자번호 답 주입을 추가하지 않는다. 후속 모델 승격은 기존 정답 퇴행 해소와 독립 실사진 검증 근거가 필요하다. [검증과 한계](docs/ocr_gsfresh_v5_comparison.md).

## CC-2026-10-19-CONTRACT16: 로컬 후보 계약·보완 좌표 후속

승인된 로컬 PaddleOCR 개선 범위에서 유효 후보·명시 총액 보존·세액 열·회전/확대 좌표·평가 사전 검사를 보완한다. 기존 계약/엑셀 시트·컬럼·버전·사용자 변경은 유지한다. 실사진 정답 퇴행을 만든 행 기울기 실험과 거래/판매금액의 공급가액 재분류는 채택하지 않았다.

후속 제안: Parser context에 제한된 후보 출처/좌표를 보존하려면 표준 계약 테스트·명세를 함께 변경해야 한다. 포인트 사용액과 복수 결제별 금액의 별도 저장/매칭에는 모델·엑셀·카드대조 영향 검토가 필요하다. 이번 변경에서 기존 필드에 억지로 넣지 않는다. [근거·제약](docs/ocr_contract16_followup.md).

## CC-2026-10-19-LABEL-TOTAL: 실제 상호 누락·총합계 오인식 국소 수정

사용자가 최신 화면의 상호 빈칸과 총합계 1,000원을 보고했다. 로컬 PaddleOCR로 재현하고 상호의 다음 명시 필드 경계와 불완전 숫자 블록 재인식만 Provider에서 수정한다. 특정 상호/금액 정답 주입·누락 숫자 생성·유료 API·모델/엑셀 계약 변경은 금지한다. 기존 작업 파일은 별도 사본/해시로 보존했다. 실제 합계 10,000원과 기존 부가세를 확인했지만 상호 첫 글자 불일치는 점수에서 유지한다. 기존 16장 일치값 퇴행은 없으며 새 검증 자료 성적은 아니다. 과거 DB·엑셀·세션을 자동 정정하지 않는다. [검증과 적용 상태](docs/ocr_label_total_followup.md).

## CC-2026-10-19-OCR-12: 증거 기반 추출과 별도 4장 검증

실제 앱/엑셀 대조에서 상호의 `/`를 경로로 오인하는 기존 출력 버그를 추가 발견해 합성 실패 재현 후 수정했다. 절대경로/수식 보호와 시트/컬럼 호환은 유지한다. 최신 앱 재시작·재처리 후 팝업 16개와 다운로드 엑셀 128개 필드 일치를 확인했다. 최종 전체 933 passed / 3 skipped이며, 이전 이력/엑셀은 자동 재작성하지 않는다.

사용자가 기존 8장·추가 4장과 문제 사진의 실제 원인 분석, 정답 주입 금지, 명시 값만 추출, 회귀·실제 앱/엑셀 확인을 지시했다. 기존 미커밋 변경을 보존하고 Provider의 명시 같은 행 증거·제한된 숫자 재인식을 검증한 뒤 Parser의 숫자 포함 상호/후보 충돌을 별도 검증했다. 모델/외부 서비스/기본 설정/표준 계약/기존 DB/엑셀 구조는 유지한다.

기존 39/47 → 40/47, 문제 사진 18/29 → 25/29, 새 검증 24/30 → 24/30이며 퇴행 0이다. 문제 사진 기준의 전화번호/사업자번호 옮김 오류는 버전을 나누고 전후 코드를 동일 정정 기준으로 재실행해 공개한다. 100% 미달과 처리 비용 증가를 숨기지 않는다. 전체 932 passed / 3 skipped, OCR 관련 127 passed. 사전 안내 후 8501을 재시작하며 실제 앱 검증은 별도 증거로 기록한다. 커밋/푸시/외부 배포는 하지 않는다. [상세](docs/ocr_quality_12_followup.md).

## CC-2026-10-19-REVIEW-RUNTIME: 닫기·같은 행 재열기와 실행 적용 점검

사용자가 닫기 버튼 부재, 더블클릭 미작동, 상호 누락을 보고했다. 합성 시안을 먼저 제시하고 기본 X/ESC 닫기와 닫힘 callback, 표 위젯 revision을 추가했다. 동일 셀 재열기 실패를 실제 Chrome과 회귀로 재현했다. 기존 초안·선택 영수증·필터·OCR/엑셀 계약은 유지하며 표 정렬/내부 스크롤 초기화 제약을 공개한다. Provider/Parser/DB는 수정하지 않는다.

현재 서버의 예전 모듈과 소스 차이를 확인했다. 현재 앱 8장 재평가의 상호는 6일치·1오인식·1누락이다. 전체 908 passed / 2 skipped, 관련 97 passed. 이후 사용자 "지금 재시작" 승인 후 8501을 종료·시작하고 running 상태와 실제 새 작업 화면을 확인했다. 기존 Azure 기본값·저장 자료는 유지했고 커밋·푸시는 하지 않았다. [근거](docs/review_runtime_followup.md).

## CC-2026-10-19-OCR-REMAINING: 남은 9개·결제수단 오탐과 별도 검증

사용자가 기존 정답 보존, 하드코딩/역산 금지, 반복 개선, 미사용 사진 별도 검증·시간/오탐 비교를 지시했다. 기존 변경을 보존하고 Provider의 날짜 전용 좁은 구간 재인식과 회귀를 먼저 진행한 뒤 Parser의 분리 법령 결제수단 오탐을 별도로 수정·검증했다. 전체 분할 축소에서 발견한 새 세액 오탐을 회귀로 남기고 최종 적용에서 제외했다. 모델·Adapter·표준 계약·엑셀·UI·DB·의존성은 바꾸지 않는다.

기존 8장 38/47 → 39/47, 일치값 퇴행 0, 별도 오탐 1 → 0. 개발에 사용하지 않은 4장 20/25 → 20/25다. 한글 기준 저장 오류를 복원해 두 버전을 같은 기준으로 재평가했고 평가 도구에 손상 기준 사전 거부를 추가했다. 기본 907 passed / 2 skipped, OCR 관련 594 passed. 47/47 미달·처리시간 증가·남은 위험을 기록했다. [전체 근거](docs/ocr_remaining_followup.md). 커밋·푸시·배포·원본/이력 재작성은 범위 밖이다.

## CC-2026-10-19-REVIEW-FIT: 원본 전체 표시와 셀 클릭 진입

사용자가 팝업 이미지 잘림을 개선하고 창 높이를 활용해 전체를 보여주며 행 클릭으로도 팝업을 열도록 요청했다. 기존 상세 검수 열기 버튼은 유지한다. 합성 시안을 먼저 제시한 뒤 UI·관련 회귀만 수정했다. 원본 비율·입력 영역 높이·원래 행 ID 연결·복귀 시 재선택을 보완한다.

OCR/Parser/Validator/DB/Exporter·의존성·고객 파일·기존 미커밋 변경은 유지한다. 기존 사용자 세션 재시작·자료 재처리·모바일·별도 확대 컨트롤·커밋·푸시는 포함하지 않는다. 관련 96개 테스트와 데스크톱 두 크기 시각 검증을 통과했다. [범위·결과](docs/review_image_fit.md).

## CC-2026-10-19-OCR-FOLLOWUP: 실패 16개 원인 분석과 공통 추출 개선

사용자 지시: 실패 16개를 개별 분석하고 하드코딩 없이 공통 인식·추출 로직을 개선·재평가한다. 기존 8장·해시·판독 기준을 유지한다. Provider 개선과 관련 회귀를 먼저 확인하고, Parser의 다음 블록 세액 차용을 별도 단계에서 수정·검증했다. 추가 검토에서 드러난 무라벨 원 금액 추측을 삭제하고 회전 재인식 시 기존 상호 손실을 막았다.

공통 구분자·상호 열/라벨·날짜·항목 경계를 수정하고 최대 8구간의 누락 세액 보완만 추가한다. 모델·의존성·UI·Adapter·표준 계약·DB/엑셀 구조를 바꾸지 않으며 실제 판독값을 운영 코드에 전달하지 않는다. 기존 text wrapper 호환은 유지한다. 원본·과거 결과·미커밋 변경을 보존하고 새 사진 처리·외부 API·모바일·배포·커밋·푸시는 포함하지 않는다.

검증: 기본 894 passed / 2 skipped, OCR 환경 핵심 285 passed. 실제 31/47 → 38/47, 기존 일치값 퇴행 0. 양성 실패 9개와 별도 빈칸 오탐 1개가 남는다. 재인식으로 시간도 늘었다. [개별 원인·조치·검증·위험](docs/ocr_failure_followup.md).

## CC-2026-10-19-OCR-INTEGRITY: 정답 주입 제거와 전체 경로 감사

사용자가 Ponytail 원칙 재확인, 상호·사업자번호 하드코딩 전체 검토, 실제 이미지 비교·수정·반복 테스트와 기존 버그 수정을 지시했다. 정답 주입·고정 신원 치환·금액 생성 경로를 제거하고 좌표·명시 라벨 기반 추출을 보완한다. 중복, 카드 충돌, 자동 학습, 저장 경계, 숫자 파싱 오류도 재현 후 수정한다. 운영 코드와 분리된 로컬 평가 도구를 추가한다.

각 단계에서 관련 회귀를 실행하며 기존 미커밋 변경을 보존한다. 모델·엑셀 계약 변경, 과거 DB·엑셀 일괄 정정, 원본 삭제, 모바일·외부 API·배포·커밋·푸시는 포함하지 않는다. [결함별 조치와 검증](docs/ocr_integrity_audit.md).

## CC-2026-10-19-BATCH-REVIEW: 전체 표와 팝업 검수

사용자 승인: 합성 데이터의 전체 목록/좌측 원본·우측 서식 팝업 시안을 먼저 제시했고 사용자가 "시안대로 진행"을 선택했다. 전체 영수증 표, 표 아래 선택과 상세 검수, 팝업 내 이전/다음/저장/저장 후 다음, 검토필요 필터와 진행 표시를 구현한다. 금액은 천 단위 콤마로 표시하고 입력 정수 형식을 검증한다. 미표기/0원, 중복의심·자동 제외 금지, 세액 역산 금지는 유지한다.

팝업 내 미저장 입력은 이번 세션의 초안으로 보존하고 저장할 때만 ReceiptRecord와 다운로드에 반영한다. 기존 미커밋 파일을 사본/해시로 보존하고 UI·관련 테스트·문서만 변경한다. OCR/GPU·Parser·DB·엑셀 구조·외부 서비스는 변경하지 않는다. 시안과 구현 화면을 구분하고 합성 자료로 실제 브라우저를 검증한다. 고객 파일 처리·커밋·푸시는 수행하지 않는다.

검증: compileall 통과, 전체 pytest 822 passed / 2 skipped / 100 warnings. 실제 Chrome에서 합성 10건 전체 표·행 선택·팝업 재열기 초안·저장 후 다음·검토필요 필터와 원래 목록 위치 유지를 확인했다. 작업 시작 해시 대비 OCR/Parser/Exporter/Core/Validator/History와 선택 의존성은 보존됐다. 상세: [변경·검증 기록](docs/batch_review_ui.md).

## CC-2026-10-19-REVIEW-LIVE: 실제 화면 반영과 원본 미리보기 복구

사용자 보고: 소스 변경 후에도 기존 검수 화면이 표시된다. 실행 중인 앱에서 합성 파일과 Mock OCR로 기존 메타데이터·하이라이트·수정 표가 그대로 나타남을 재현했다. 프로젝트 전용 실행기로 서버를 재시작하여 최신 모듈을 적용한다. 저장 파일/DB는 유지하지만 저장 전 세션 입력은 초기화될 수 있음을 안내한다.

재시작 후 새 통합 화면은 확인했으나 이미지 HTTP 요청이 500으로 실패했다. Streamlit 1.60.0과 Starlette 1.9.0의 압축 응답 순서 불일치를 합성 HTTP 회귀 테스트 4개로 재현했다. 공통 requirements에 호환 Starlette 1.7.0을 고정하고 현재 선택형 GPU 실행 환경의 해당 패키지만 변경했다. 제품 Parser/Provider/DB 계약은 변경하지 않았다. 실제 브라우저에서 원본 이미지 700×800 정상 로딩과 서식, 접힌 상세정보, 기존 표 제거를 검증했다. compileall·pip check 통과, 전체 pytest 802 passed / 2 skipped / 100 warnings. 고객 파일 처리·DB 이력 생성·커밋·푸시는 수행하지 않았다. [검증 기록](docs/review_live_verification.md).

## CC-2026-10-19-REVIEW-UX: 사용자 중심 검수 화면과 명시 세액 정책

사용자 승인: 저장 메타데이터/진단 점수는 기본 화면에서 제외하고 원본·선택·상세·수정을 통합한다. 사용일자·상호·사업자번호·할인·공급가액·부가세·결제금액·결제수단·중복의심을 중심으로 검수한다. 누락값을 역산하거나 미표기를 0원/면세로 바꾸지 않는다. 카드내역 미업로드와 매칭 0건을 구분한다.

현재 작업 트리의 기존 미커밋 소스는 로컬 격리 사본과 해시로 보존한 뒤 해당 변경만 적용한다. UI 통합 후 사용되지 않는 화면 경로를 정리한다. Provider/GPU/원본 보관정책/기존 DB와 과거 출력은 변경하지 않는다. 세액 추정의 생성·노출 중단과 exporter 호환은 별도 단계로 검증한다. `ReceiptRecord`의 기존 결제금액 의미는 자동 재해석하지 않는다. 포인트·상품권 등이 있는 경우 기존 거래합계/실제결제액을 상세에서 구분한다. 모바일 앱 자체는 구현하지 않는다.

검증: compileall 통과, 전체 pytest 798 passed / 2 skipped / 100 warnings. 누락 할인/최종금액의 차액 생성도 제거했고 기존 추정 세액은 새 엑셀에서 공란 처리한다. 고객 파일과 기존 DB는 재처리하지 않았다. [파일 목록·구조·검증·제약](docs/review_ux_refinement.md).

## CC-2026-10-19-PONYTAIL-HOOKS: 프로젝트 전용 자동 원칙 로딩

요청: 설치한 Ponytail 원칙을 작업 전에 자동으로 불러오도록 hook을 등록한다.

`.codex/hooks.json`에 SessionStart/UserPromptSubmit/SubagentStart 3개를 등록하고, `scripts/ponytail_hook.js`가 기존 설치 스킬과 영수증 프로젝트의 작업 전 점검 항목을 추가 context로 반환한다. 프로젝트의 기존 규칙과 사용자 지시를 유지하며, 수정 전 호출부와 작동 환경을 확인하고 수정 후 필요한 검증을 수행하도록 상기한다. hook 자체는 앱을 수정하거나 OCR·테스트·네트워크 요청을 실행하지 않으며 stdin의 요청/대화 내용을 저장·출력하지 않는다. 프로젝트 밖에서는 context를 전달하지 않는다.

Codex의 공식 `/hooks` 화면에서 3개 모두 신뢰·활성 상태를 확인했다. hook 정의를 바꾸면 재검토가 필요하며 신뢰 우회 옵션은 사용하지 않았다. Node.js가 필요하다. 전역 hook과 전역 플러그인은 추가하지 않았다. 카드 매칭은 의미 설명을 위한 읽기 전용 확인만 수행했다.

검증과 파일 목록: [Ponytail hook 등록 기록](docs/ponytail_hooks_setup.md).

## CC-2026-10-19-OCR-RUNTIME: 더블클릭 실행의 PaddleOCR/GPU 환경 복구

요청: 기존에는 동작하던 PaddleOCR이 `paddle_not_installed`로 실패하고 GPU 모드도 사용할 수 없는 원인을 확인하고 복구한다.

원인: 새 실행기는 기본 의존성만 설치한 Python 3.13 `.venv`를 고정 사용했다. 기존 Python 3.10에는 PaddleOCR 2.7.3과 GPU Paddle 2.6.2가 있으며 CUDA 인식·GPU 텐서 연산을 통과했다. 프로젝트의 Python 3.11 이상 기준에 맞춰 Python 3.11.9 `.venv-ocr`를 별도로 준비하고, 실행기가 선택 환경을 우선하도록 수정한다.

선택 의존성은 별도 `requirements-paddle-gpu.txt`로 분리한다. GPU Paddle 2.6.2의 protobuf 제약에 맞는 Streamlit 1.60.0과 NumPy 1.26.4를 사용한다. 현재 PC의 Python 3.11 실행 별칭은 사용할 수 없어 공식 CPython NuGet 배포를 프로젝트 내부 runtime으로 준비했다. 전역 Python, 기존 3.10/3.13 환경과 NVIDIA 드라이버는 변경하지 않는다. `.venv-ocr`는 Git에서 제외한다.

변경 범위는 실행 환경 선택·선택 의존성·실행기 회귀 테스트와 문서다. PaddleOCRProvider, Parser, Validator, ExcelExporter 및 처리 이력 코드는 변경하지 않는다. 기존 `.env`와 OCR 기본값은 유지한다. 실제 OCR 확인은 기존 모델 캐시와 합성 이미지로 수동 실행하며 기본 pytest에 추가하지 않는다. 고객 영수증은 재처리하지 않는다.

검증(2026-10-19):

- `.venv-ocr`의 `pip check`는 의존성 충돌 없음, compileall 통과. 현재 작업 트리의 전체 pytest는 784 passed / 2 skipped / 100 warnings, 35.57초. 기본 테스트에 실제 OCR 실행을 추가하지 않았다.
- 별도 수동 합성 이미지 검사에서 CPU/GPU 모두 `completed`, text block 5개, diagnostic 없음. 실제 detector config의 GPU 사용은 CPU=false, GPU=true이며 GPU 텐서 연산도 통과했다. 모델 다운로드를 차단하고 기존 캐시 모델만 사용했다.
- 임시 저장소의 AppTest에서 PaddleOCR Local과 GPU 모드를 선택했을 때 예외나 GPU 빌드 경고에 의한 차단이 없었다.
- 실행기 서버를 종료·재시작하고 health 응답 및 실제 Python 실행 파일이 `.venv-ocr`에 속함을 확인했다. 기존 `.env`·앱/Parser/Provider/Exporter 코드와 사전 작업 파일 132개는 해시 비교로 변경되지 않았음을 확인했다.
- 고객 영수증 재처리와 실제 이미지의 추출 정확도 평가는 수행하지 않았다. 상세: [OCR 환경 복구 기록](docs/ocr_runtime_recovery.md).

## CC-2026-10-19-PONYTAIL: 프로젝트 전용 Ponytail 스킬 설치

요청: 소스 정리에 앞서 Ponytail을 설치한다.

공식 `DietrichGebert/ponytail` 커밋 `09c434ab73ca43761c5d8b0c5d341926c2fba710`의 스킬 6개를 `.agents/skills/`에 설치했다. MIT 라이선스와 출처·SHA-256 manifest를 함께 보관한다. `AGENTS.md`를 교체하거나 전역 플러그인/lifecycle hook을 등록하지 않는다. 기존 제품 규칙과 검증 기준에 추가되는 보조 지침으로 사용한다.

스킬 파일 6개는 고정 커밋 원본과 byte 단위로 일치한다. 제품 소스·테스트·실행기·기존 `AGENTS.md`·`.env`는 작업 전후 해시 비교로 보존 여부를 확인한다. 앱 동작과 산출물 계약은 변경하지 않으며 소스 정리·전체 감사·커밋/푸시는 이번 설치에 포함하지 않는다. 상세 기록: [Ponytail 설치](docs/ponytail_setup.md).

## CC-2026-10-19: Windows 더블클릭 로컬 실행

요청: 매번 명령어를 입력하지 않고 로컬 앱을 실행할 수 있게 한다.

범위: 실행/종료 VBS 진입점, 공통 PowerShell 실행기, 기존 실행 스크립트 위임, 바탕화면 바로가기와 실행기 테스트. 기존 포트의 Python 프로세스를 이름만 보고 종료하는 동작은 제거한다. 앱은 loopback으로만 실행하며 이미 실행 중이면 재사용한다. 종료 시 PID·시작시각·프로젝트 명령 일치를 검증한다. 실패 안내에는 예외 원문·OCR 원문·비밀값·전체 로컬 경로를 넣지 않는다.

OCR Provider 기본값, Parser, Validator, Exporter, 데이터 모델/버전, 기존 DB/파일 및 미커밋 수정은 이 작업에서 변경하지 않는다. 패키지 자동 설치, 실제 OCR 호출, 시작 프로그램 등록, 클라우드 배포는 추가하지 않는다. 기존 `.env` 설정은 유지한다. 다른 PC에서는 README의 최초 환경 설치가 필요하다.

검증(2026-10-19):

- 현재 작업 트리에서 `.venv` Python 3.13으로 `python -m compileall -q app tests` 통과, `python -m pytest -q -p no:cacheprovider`는 781 passed / 2 skipped. 기존 datetime 관련 경고 931건이 있다. 선택형 실제 OCR 테스트는 실행하지 않았다.
- 실행기 테스트 12개가 반복 실행, 포트 충돌 회피, 오래된 PID/다른 명령의 종료 거부, 정상 종료, 환경 누락, 시작 실패 정리, 공백 경로 인자 및 상태 파일을 확인했다.
- 임시 저장소·mock 환경에서 실제 서버 시작/재사용/종료와 health 응답을 확인했다. AppTest에서 업로드 화면에 예외가 없음을 확인했다. 브라우저 화면의 시각 검수 및 OCR 품질 평가는 수행하지 않았다.
- 바탕화면 실행/종료 바로가기를 만들고 실행 바로가기로 기존 `.env` 설정의 로컬 서버가 기동하는 것을 확인했다. 기존 미커밋 소스/테스트 5개는 작업 전후 SHA-256 비교로 보존 여부를 확인했다.

## CC-2026-10-18: 통일 양식·상호 보정·누적 저장 설계

요청: 세무사 전달에 유용한 양식을 포인트 사용·할인·복합결제까지 구분해 정리하고, 상호 보정 및 날짜별 누적 저장 방향을 문서화한다.

상태: 설계 문서 작성. 구현·DB migration·출력 계약 변경은 미수행.

산출물:

- [통일 양식 변경안](docs/receipt_standardization_proposal.md)
- [상호 보정 정리안](docs/merchant_resolution_design.md)
- [누적 저장 설계안](docs/receipt_accumulation_design.md)

현행과 충돌하는 의미는 차기 계약에서 분리한다. 기존 `total_amount`를 새 거래합계로 일괄 매핑하지 않고, 특정 거래처 자동 치환을 새 후보 정책과 혼동하지 않는다. 현재 원본/출력 보관 설정과 수동 dry-run 동작도 이번 문서로 바뀌지 않는다.

후속 구현은 계약/fixture → Provider와 분리된 Parser/모델 매핑 → 저장/revision → 검수 UI → Exporter 순서의 작은 작업으로 나눈다. 상호 규칙 정리와 누적 저장은 각각 별도 단위로 진행한다. 전환별 compileall·기본 pytest와 관련 회귀, schema/parser/validator 버전 영향 점검을 수행한다.

현행 코드·미커밋 수정·기존 DB/파일·8개 시트는 보존한다. 실제 고객 파일 재처리, 기존 이력 값 재해석, 과거 엑셀 재생성, 데이터 삭제, 모바일 앱 구현, 인증/결제, 클라우드 배포는 이번 작업에 포함하지 않는다.

문서 정리 검증(2026-10-18):

- 문서 11개의 상대 파일 링크 35개, 공백·코드 블록 형식 점검: 통과.
- 변경 문서 `git diff --check`: 통과.
- `python -m compileall -q app tests`: 통과. Python 소스 123개의 메모리 내 구문 컴파일도 오류 없음.
- `python -m pytest`: 현재 실행 Python에 pytest가 없어 실행하지 못함. 테스트 통과로 기록하지 않는다. 의존성 설치·실제 OCR 호출은 수행하지 않았다.

커밋 전 검증(2026-10-19):

- 프로젝트 기준에 맞는 Python 3.13 격리 환경을 준비하고 `requirements.txt` 의존성만 설치했다. PaddleOCR·CUDA·실제 OCR 호출은 추가하지 않았다.
- 기준 커밋 `e400fdb`와 문서 11개만 담은 격리 사본에서 `python -m compileall -q app tests` 통과, `python -m pytest -q -p no:cacheprovider`는 761 passed, 2 skipped였다.
- 이 결과는 커밋 대상 트리 검증이며 로컬의 미커밋 OCR/Parser/테스트 수정까지 검증한 결과는 아니다. 해당 수정과 로컬 데이터는 문서 커밋에서 제외한다.

## Week 9-A PaddleOCR Provider PoC Change Control

- Adding `PaddleOCRProvider` is a Provider expansion change.
- PaddleOCRProvider implementation and Parser changes must be separate work items.
- PaddleOCRProvider implementation and ExcelExporter or Processing History changes must be separate work items.
- Do not add `paddleocr` directly to `requirements.txt` without an explicit dependency decision; prefer optional dependency or separate install documentation.
- Default pytest must pass without PaddleOCR installed.
- PaddleOCR raw output must not be passed directly to Parser, Validator, CategoryRules, CardMatcher, or ExcelExporter.
- Full PaddleOCR raw output, full OCR raw text, full local absolute paths, actual customer files, and actual sensitive values must not be stored or displayed in DB, Excel, UI, logs, fixtures, or test output.
- Week 9-B is adapter/fixture only and must not connect provider factory.
- Week 9-C may add an optional provider and provider factory candidate, but actual OCR execution must stay out of default pytest.
- Week 9-D may add opt-in smoke tests only; PDF handling remains out of Week 9 scope.

Rollback criteria:

- Default pytest fails when PaddleOCR is not installed.
- Default app startup fails.
- `OCR_PROVIDER=mock` flow fails.
- Existing Azure Provider flow fails.
- Parser, Validator, CategoryRules, CardMatcher, or ExcelExporter imports or consumes PaddleOCR raw output directly.
- Full raw output, full OCR text, endpoint, key, token, secret, or full local absolute path exposure occurs.
- Heavy OCR dependency is added to `requirements.txt` and breaks the default environment.
- Actual PaddleOCR OCR test runs in default pytest.
- PDF handling is pulled into Week 9 scope.

## 1. 목적

이 문서는 영수증 OCR 엑셀 비서 MVP의 범위, 문서, 코드 변경을 안전하게 관리하기 위한 기준입니다.

## 2. 고정 방향

MVP의 고정 방향은 다음과 같습니다.

```text
영수증 이미지/PDF + 카드 사용내역 CSV/XLSX 업로드
→ OCR/Parser 처리
→ 사용자 검수
→ 세무사 전달용 표준 엑셀 정리 파일 다운로드
→ 처리 이력 조회와 기존 export 파일 재다운로드
```

MVP는 증빙 정리 보조 도구입니다. 사용자 확인 없이 결과를 확정하지 않습니다.

## 3. 문서 변경이 필요한 경우

| 변경 내용 | 함께 확인할 문서 |
|---|---|
| 실행 방법 변경 | README.md, AGENTS.md |
| MVP 범위 변경 | README.md, PLAN.md, DECISIONS.md |
| 데이터 모델 변경 | SPEC.md, tests |
| 엑셀 시트/컬럼 변경 | SPEC.md, CHECKLIST.md, docs/sample_output_schema.md |
| 처리 이력 DB 구조 변경 | SPEC.md, PLAN.md |
| 화면 메뉴 변경 | README.md, PLAN.md, CHECKLIST.md |
| 파일럿 절차 변경 | docs/pilot_guide.md, docs/sample_user_flow.md |
| 테스트 명령 변경 | README.md, AGENTS.md |
| OCR Provider 추가/변경 | SPEC.md, CHECKLIST.md, docs/standard_ocr_result_schema.md |
| StandardOCRResult schema_version 변경 | SPEC.md, CHECKLIST.md, tests/fixtures |

## 4. 변경 절차

1. 관련 문서와 코드를 먼저 확인한다.
2. 기능 변경이 필요한지, 문서 동기화만 필요한지 구분한다.
3. MVP 범위를 넓히는 변경은 바로 구현하지 않고 결정 기록을 남긴다.
4. 코드 변경이 있으면 테스트를 함께 작성하거나 기존 테스트를 확인한다.
5. 주요 결정은 DECISIONS.md에 기록한다.
6. `python -m compileall app tests`와 `python -m pytest`를 실행한다.
7. Git 변경사항에 민감 파일이 포함되지 않았는지 확인한다.
8. OCR Provider 원본 응답 구조가 바뀌어도 Parser 입력 계약은 `StandardOCRResult`로 유지한다.
9. `StandardOCRResult` `schema_version` 변경 시 fixture와 문서도 함께 업데이트한다.
10. Parser/Validator 버전 변경 시 `parser_version`/`validator_version` 기록 필요 여부를 확인한다.

## 5. 금지되는 변경

명시적 요청 없이 아래 작업을 진행하지 않습니다.

- 로그인/권한관리
- 결제 기능
- 클라우드 배포
- 모바일 앱
- 홈택스/카드사 연동
- 회계 프로그램 API 연동
- 과거 작업 재검수
- 과거 엑셀 재생성
- 실제 cleanup 삭제 버튼
- API key 입력 UI
- OCR Provider 변경 UI
- OpenAI API 기반 전체 자동 보정
- 장기 파일 보관 전제 기능

OCR Provider 독립화 기준:

- OCR Provider 추가는 범위 확장 변경으로 봅니다.
- Provider 추가 시 SPEC.md, PLAN.md, CHECKLIST.md, DECISIONS.md를 함께 확인합니다.
- Parser가 provider raw response에 직접 의존하는 변경은 금지합니다.
- `StandardOCRResult` 스키마 변경 시 Golden Test Fixture 영향도를 확인합니다.
- OCR raw JSON 전체, OCR raw text 전체, 전체 로컬 절대경로, API key, 실제 고객 파일이 노출되는 변경은 금지합니다.
- `ReceiptParser` 입력을 `StandardOCRResult` 또는 `StandardOCRParserContext`로 바꾸는 작업은 영향도 있는 구조 변경으로 봅니다.
- Parser 전환 시 SPEC.md, CHECKLIST.md, DECISIONS.md, tests를 함께 확인합니다.
- Provider Adapter 변경과 Parser 변경은 가능하면 별도 커밋으로 분리합니다.
- `ExcelExporter`, Processing History DB, Streamlit UI 변경은 별도 변경으로 분리합니다.
- Azure Adapter 구현은 Provider 독립화 구조 변경으로 봅니다.
- Azure Adapter 변경 시 SPEC.md, CHECKLIST.md, DECISIONS.md, tests를 함께 확인합니다.
- Azure Adapter 구현, Azure Provider 연결, Parser 전환은 가능하면 별도 커밋으로 분리합니다.
- Azure Provider 변경과 Parser 변경은 한 작업에서 동시에 하지 않습니다.
- Azure raw response를 Parser에 직접 전달하는 변경은 금지합니다.
- `provider_fields`에 raw JSON 전체를 넣는 변경은 금지합니다.
- Azure endpoint 전체 URL, API key, `operation_location` 전체 URL이 화면/DB/엑셀/로그/fixture에 노출되는 변경은 금지합니다.
- 기존 Azure Provider 동작을 바꾸는 경우에는 회귀 테스트와 변경 사유를 남깁니다.
- Azure Provider에 Adapter를 연결하는 작업은 기존 OCR 흐름에 영향을 줄 수 있으므로 회귀 테스트가 필요합니다.
- `AzureProvider.extract()` 반환 타입 변경은 별도 주요 변경으로 보며, 7주차-C에서는 금지합니다.
- Azure Adapter bridge/helper 추가는 운영 흐름에 연결하지 않는 경우 낮은 위험 변경으로 봅니다.
- Parser 전환은 8주차 작업으로 분리합니다.
- 8주차 Parser 전환 전에는 Azure Provider 회귀 테스트와 end-to-end export flow 테스트가 통과해야 합니다.
- rollback 기준은 기존 Azure Provider 테스트 실패, end-to-end export flow 실패, Parser/Exporter/DB/UI 변경 발생, raw JSON/raw text/endpoint/`operation_location` 노출 발생입니다.

Parser 표준 입력 전환 기준:

- `ReceiptParser` 입력 변경은 핵심 구조 변경으로 봅니다.
- Parser 전환 시 SPEC.md, CHECKLIST.md, DECISIONS.md, tests를 함께 확인합니다.
- Parser 전환과 ExcelExporter 변경은 별도 커밋으로 분리합니다.
- Parser 전환과 Processing History DB 변경은 별도 커밋으로 분리합니다.
- Parser 전환과 Streamlit UI 변경은 별도 커밋으로 분리합니다.
- 기존 raw_text Parser 경로 제거는 별도 결정과 회귀 테스트 통과 후 진행합니다.
- Parser가 provider raw response를 직접 import하거나 참조하는 변경은 금지합니다.
- Parser 입력에 raw JSON 전체, raw text 전체, endpoint, key, 전체 경로가 들어가는 변경은 금지합니다.
- 8주차-B에서는 새 Parser entry 추가만 허용하고 downstream 구조 변경은 하지 않습니다.
- 8주차-C에서는 fixture 비교 테스트를 중심으로 하고 ExcelExporter 변경은 하지 않습니다.
- 8주차-D에서 downstream 회귀를 점검하되, 구조 변경이 필요하면 별도 작업으로 분리합니다.

Parser 전환 rollback 기준:

- 기존 end-to-end export flow 실패
- 기존 Parser 테스트 실패
- ExcelExporter 테스트 실패
- Processing History 테스트 실패
- `ReceiptRecord` 핵심 필드 누락 증가
- raw JSON/raw text 전체 노출 발생
- provider raw response가 Parser로 전달됨
- `AzureProvider.extract()` 반환값 변경 발생
- Processing History DB schema 변경 발생
- 기존 raw_text Parser 경로 삭제 발생

이번 단계에서 금지되는 변경:

- `PaddleOCRProvider` 실제 구현
- `TesseractProvider` 실제 구현
- ML Kit 앱 구현
- Apple Vision 앱 구현
- FastAPI 서버 구현
- Tauri/Electron 앱 구현
- Provider 변경 UI 구현
- API key 입력 UI 구현
- 기존 Processing History DB 대규모 변경
- 기존 `ExcelExporter` 대규모 변경

## 6. 보안 기준

문서, 코드, 테스트, 화면, DB, 엑셀에는 아래 정보가 노출되면 안 됩니다.

- `.env` 내용
- API key, secret, token, password
- Azure endpoint 전체 URL
- 전체 로컬 절대경로
- OCR raw text 전체
- provider raw JSON 전체
- 카드 사용내역 원문 전체
- 실제 카드번호 전체
- 주민번호, 전화번호 등 민감정보
- 실제 고객 파일

## 7. 문서 동기화 전용 작업

코드 기능 변경 없이 문서만 현재 구현과 맞추는 경우:

1. README.md, PLAN.md, SPEC.md, CHECKLIST.md, DECISIONS.md, CHANGE_CONTROL.md를 확인한다.
2. app/, tests/, requirements.txt, .env.example, .gitignore, docs/를 읽기 전용으로 확인한다.
3. 실제 구현과 다른 문서만 수정한다.
4. 구현되지 않은 기능을 구현된 것처럼 쓰지 않는다.
5. 문서에 실제 key, 개인정보, 전체 로컬 경로, 실제 파일명을 넣지 않는다.
6. 수정 후 compileall과 pytest를 실행한다.

## 8. 커밋 전 확인

```bash
python -m compileall app tests
python -m pytest
git status
git diff --check
```

확인 항목:

- `.env`가 포함되지 않는다.
- `data/uploads`, `data/outputs`, `output` 실제 파일이 포함되지 않는다.
- `data/app.db`, `*.db`가 포함되지 않는다.
- 실제 고객 파일이나 실제 영수증 파일이 포함되지 않는다.
- 테스트가 통과한다.
## Week 9-C PaddleOCRProvider Candidate Change Control

- Adding `PaddleOCRProvider` and provider factory support for `OCR_PROVIDER=paddle` is allowed only as an optional provider candidate.
- The default OCR provider must remain unchanged.
- `paddleocr` must remain an optional dependency and must not be added to `requirements.txt` in this step.
- Provider import, provider factory import, and default pytest must pass without `paddleocr` installed.
- Real OCR execution must stay out of default pytest and move to a 9-D opt-in smoke test.
- PDF conversion and multi-page handling remain deferred.
- Roll back or disable the candidate path if provider factory import fails, mock/Azure provider creation breaks, default pytest requires `paddleocr`, or raw PaddleOCR output/full local paths are exposed.

## Week 9-D PaddleOCR Smoke Test Change Control

- Actual PaddleOCR OCR execution may only be added behind an explicit opt-in flag.
- Default pytest must skip real OCR and must pass without `paddleocr` installed.
- Smoke tests must not commit or require real customer images.
- Smoke test reports must not include full local paths, raw traceback, raw output, or environment dumps.
- PDF handling remains deferred; adding PDF conversion is out of scope.
- Roll back or disable the smoke test if it runs without opt-in, exposes raw output/path data, or breaks existing mock/Azure/parser/downstream regressions.

## Week 10-A Azure vs PaddleOCR Quality Comparison Contract Change Control

- 10-A is a contract and documentation step only.
- Quality comparison must use `StandardOCRResult`, `StandardOCRParserContext`, and existing `ReceiptRecord` fields.
- Provider raw output, full OCR raw text, full local absolute paths, endpoints, operation locations, API keys, secrets, tokens, and raw tracebacks must not become report inputs or outputs.
- `provider_fields` may be used only for non-sensitive count/flag metadata and adapter diagnostic summaries.
- Expected fixtures must use synthetic or non-sensitive samples and expected core `ReceiptRecord` fields instead of provider raw output.
- Safe OCR preview, side-by-side report generation, statistics aggregation, and fallback automation must remain separate 10-B/C/D work items.
- PDF PaddleOCR handling remains deferred.
- Existing Parser raw-text compatibility path, ExcelExporter structure, Processing History DB schema, default provider, and provider factory behavior must not change in 10-A.
- Default pytest must not run real Azure or real PaddleOCR execution for this contract step.

Rollback criteria:

- Any document describes safe preview, side-by-side report generation, statistics summary, or Azure fallback automation as already implemented.
- Any comparison contract requires provider raw output, full OCR raw text, full local absolute paths, actual customer files, or secrets.
- Any expected fixture strategy requires actual customer files or full provider raw payloads.
- Any code change in 10-A alters default provider behavior, Excel columns/sheets, Processing History schema, or Parser raw-input boundaries.
## Week 10-B Safe OCR Preview Change Control

- 10-B may add a provider-neutral safe preview utility for `StandardOCRResult.text_blocks`.
- 10-B may display the safe preview in the Settings PaddleOCR smoke-test box after an opt-in smoke run.
- The preview must expose only limited safe rows, confidence labels, low-confidence flags, redaction flags, safe category labels, and summary counts.
- The preview must not display, persist, export, or log provider raw output, full OCR raw text, raw JSON, full local absolute paths, endpoint URLs, operation-location URLs, secrets, tokens, raw tracebacks, or actual customer files.
- The preview utility may support Azure adapter results through `StandardOCRResult`; it must not add real Azure API execution to default tests or UI flows.
- 10-B must not implement side-by-side comparison, statistics aggregation, `field_match_score`, automatic Azure fallback execution, provider default changes, ExcelExporter sheet/column changes, Processing History schema changes, Parser raw-input changes, or PDF PaddleOCR handling.

Rollback criteria:

- Revert the 10-B preview changes if any UI/log/test fixture exposes full OCR raw text, provider raw JSON, full local paths, secrets, endpoint URLs, or raw tracebacks.
- Revert if the preview path starts calling real Azure/PaddleOCR during default pytest.
- Revert if the change modifies default provider selection, ExcelExporter output structure, Processing History DB schema, or Parser raw-input boundaries.
- Revert if 10-B documentation claims side-by-side reports, statistics, `field_match_score`, or Azure fallback automation are implemented.
## Week 10-C Side-by-side Report Change Control

Week 10-C is limited to a diagnostic side-by-side report for one explicit sample image. It may add UI helpers, sanitized comparison utilities, and fixture-based tests. It must not change the production OCR default, Excel export format, Processing History schema, parser raw-input boundary, or provider adapter contracts.

Rollback or correction is required if the change introduces any of the following:

- Provider raw output, full OCR text, raw JSON, full local paths, Azure endpoint URLs, operation URLs, secrets, or raw tracebacks in UI, DB, Excel, logs, fixtures, or test output.
- Default pytest execution that calls real Azure APIs, downloads PaddleOCR models, or runs real PaddleOCR OCR.
- A Parser path that accepts provider raw response objects instead of `StandardOCRParserContext`.
- A formal field match score, aggregate statistics, fallback recommendation, or automatic Azure retry policy before Week 10-D.
- Any ExcelExporter column/sheet change, Processing History DB schema change, or production provider default change.

Safe diagnostic detail codes are allowed for provider failures when they are sanitized categories only, for example `quota_or_rate_limit` for Azure HTTP 403 quota/rate-limit responses. Roll back or correct the change if raw Azure error messages, endpoint URLs, operation URLs, request headers, keys, raw tracebacks, or provider payloads are exposed as diagnostic details.

## Week 10-D-prep Synthetic PaddleOCR Fixture Change Control

Week 10-D-prep may add synthetic sanitized PaddleOCR line fixtures, expected
`ReceiptRecord` baselines, and fixture-driven parser tests. It may improve parser
or Paddle candidate rules only when the rule is conservative and label-based.

Allowed improvements:

- Merchant candidates from explicit labels such as `상호`, `상호명`, `매장명`,
  `가맹점명`, and `점포명`.
- Date, business-number, payment-method, labeled amount, explicit supply/VAT, and
  amount OCR-character normalization rules.
- Security tests that reject raw payload keys, full paths, endpoints, secrets,
  tokens, and sensitive full values.

Rollback or correction is required if any of the following occur:

- Default pytest calls live Azure, imports/executes real PaddleOCR, or downloads
  OCR models.
- Fixture files include customer receipts, provider raw output, full OCR text,
  raw JSON, full local paths, endpoints, secrets, tokens, full card numbers, full
  phone numbers, resident registration numbers, passwords, or WiFi passwords.
- Parser changes guess merchant names from unlabeled first lines, infer totals
  from unlabeled maximum amounts, force broken business numbers into valid
  shapes, or use redacted sensitive lines as candidates.
- Existing parser, adapter, ExcelExporter, Processing History, provider default,
  or side-by-side comparison regressions fail.
- The change implements automatic Azure fallback, formal `field_match_score`,
  aggregate statistics UI, ExcelExporter sheet/column changes, or Processing
  History schema changes.

## Review UX Quality Triage Change Control

Review UX triage may add safe, derived review indicators and filters from
`ReceiptRecord` only. It may not call OCR providers, reprocess files, or change
the persisted history/export contracts.

Allowed changes:

- Derived review priority, missing-field, and quality-check labels.
- Status and issue filters for the existing review table.
- Safe selected-receipt detail panels that show parsed fields and source file
  names only.

Rollback or correction is required if any of the following occur:

- The review UI displays provider raw output, full OCR text, raw JSON, full local
  paths, endpoint URLs, operation URLs, secrets, tokens, or raw tracebacks.
- Filtering causes hidden review rows to be dropped or overwritten.
- The change modifies ExcelExporter sheets/columns, Processing History schema,
  default OCR provider selection, automatic fallback behavior, or formal quality
  scoring.

## New Job PaddleOCR Runtime Selection Change Control

The New Job screen may expose `PaddleOCR Local` as an explicit per-run OCR
provider option. This is a runtime override only and must not change the
configured default provider.

Allowed changes:

- Add `paddle`/`paddleocr` to the New Job runtime provider selection allowlist.
- Route `StandardOCRResult` outputs through `StandardOCRParserContext` before
  parsing.
- Show a short PaddleOCR PDF unsupported/deferred note when selected.
- Store and display source file names only.

Rollback or correction is required if any of the following occur:

- The configured default OCR provider changes.
- Default pytest runs real PaddleOCR, downloads OCR models, or requires
  `paddleocr` to be installed.
- Provider raw output, full OCR text, raw JSON, full local paths, secrets,
  endpoint URLs, operation URLs, or raw tracebacks are displayed, persisted,
  logged, or added to fixtures.
- Parser receives PaddleOCR raw output or any provider raw response object.
- ExcelExporter sheets/columns or Processing History schema change.
- Automatic Azure fallback, formal `field_match_score`, or PDF PaddleOCR support
  is implemented as part of this change.

## PaddleOCR Speed Pass Change Control

Performance work may reduce repeated local computation only when parsed output
quality and review behavior are preserved.

Allowed changes:

- Reuse a `PaddleOCRProvider` OCR engine instance for multiple images in the same
  provider instance.
- Cache pure text normalization helpers with bounded caches.
- Avoid repeated extraction of the same standard OCR candidate map during parser
  context construction.

Rollback or correction is required if any of the following occur:

- OCR quality, parser field extraction, candidate generation, validation,
  review-required behavior, or safe diagnostics regress.
- A performance shortcut disables image normalization fallback, candidate hints,
  parser checks, or validator checks.
- Default pytest runs real PaddleOCR, downloads OCR models, or requires
  `paddleocr`.
- Provider raw output, full OCR text, raw JSON, full local paths, secrets,
  endpoint URLs, operation URLs, or raw tracebacks are exposed.
- Default provider behavior, ExcelExporter sheets/columns, Processing History
  schema, automatic Azure fallback, formal scoring, or PDF PaddleOCR handling
  changes.

## Review UI Receipt Source Preview Change Control

Review source preview may help reviewers compare parsed fields with the original
receipt file, but it must stay inside the safe upload boundary and must not alter
export or history contracts.

Allowed changes:

- Add review priority, missing-field, review-reason summary, source file name,
  and source-preview status columns.
- Store selected receipt id and selected row number in session state.
- Highlight the selected row in a read-only selection table.
- Preview JPG/JPEG/PNG files only after resolving them under the configured
  upload root.
- Show a PDF notice instead of forcing PDF rendering.

Rollback or correction is required if any of the following occur:

- The UI displays full local paths, OCR raw text, provider raw JSON, raw provider
  output, endpoint URLs, secrets, raw tracebacks, or sensitive raw values.
- Source preview can open files outside `data/uploads` or accepts traversal
  paths.
- Review edits, exclusion handling, ExcelExporter sheets/columns, Processing
  History schema, default provider behavior, automatic fallback, or formal score
  behavior changes.
- The change adds mobile/PWA features, OCR provider changes, PaddleOCR accuracy
  changes, OpenAI correction, or customer test files.

## PaddleOCR Split Label Quality Hardening Change Control

PaddleOCR parser-quality hardening may add conservative label-based candidate
rules when a synthetic fixture demonstrates a missing field that is visibly
present on a receipt.

Allowed changes:

- Recognize split `매출일`/`매출일자` label-value date lines when the nearby value is
  a valid `YYYYMMDD` or short labeled date.
- Recognize split `매장명` label-value merchant lines only after an explicit
  merchant label and only when the nearby value is not a date, amount, business
  number, phone number, card number, or known non-merchant label.
- Recognize unlabeled merchant segments immediately before a valid business
  number only when the segment passes merchant-like checks and is not an
  identifier, address, amount, date, phone, card, approval, tax, or total label.
- Recognize compact `YYYYMMDD HH:MM[:SS]` approval date-time patterns only with
  nearby date/time labels such as `승인시간`, `승인일시`, `거래일시`, or `매출일`.
- Add synthetic sanitized PaddleOCR fixture cases and unit tests only.

Rollback or correction is required if any of the following occur:

- Merchant names are guessed from arbitrary unlabeled lines.
- Dates are inferred from unrelated identifiers, approval numbers, or invalid
  calendar values.
- Actual customer images, full OCR text, provider raw output, raw JSON, full
  local paths, secrets, or endpoint URLs are added to fixtures, logs, UI, DB, or
  Excel output.
- Default pytest runs real Azure or real PaddleOCR, downloads OCR models, or
  requires `paddleocr`.

## Merchant Candidate Dictionary Change Control

- Adding merchant candidate tables is allowed only as separate dictionary data.
  Existing `receipt_records`, `processing_jobs`, and ExcelExporter contracts must
  remain compatible.
- Public store CSV import may store merchant name, branch name, coarse area hint,
  category names, source row hash, and batch id only.
- `merchant_master.business_number` must remain nullable because public store
  data is not a full business-number source.
- Candidate matching may rank business-number exact, alias, and fuzzy name
  candidates, but must return review-required hints only.
- NTS business status API may be used only for OCR-detected business numbers and
  must read `NTS_BUSINESS_API_KEY` from `.env`.

Rollback or correction is required if any of the following occur:

- Representative names, phone raw values, full addresses, full OCR text,
  provider raw JSON, raw API responses, full local paths, secrets, or tracebacks
  are stored or displayed.
- Merchant candidates automatically overwrite receipt merchant name, business
  number, or review status.
- Private site crawling, mass business-number collection, true-name verification,
  tax judgment, ExcelExporter sheet/column changes, or Processing History receipt
  schema changes are introduced in this step.

## Merchant Road Address Hint Change Control

- Public merchant CSV import may read only `상호명`, `지점명`, category columns,
  `도로명`, `건물본번지`, `건물부번지`, `건물명`, and `도로명주소`.
- Road-address fields may be stored in `merchant_master` for matching hints and
  duplicate detection.
- OCR-derived road-address hints may be extracted only from safe parser lines and
  used as transient candidate scoring inputs.
- Same-file detection must use allowed-column content only so unrelated CSV
  columns do not affect duplicate decisions.
- The Settings UI may import multiple CSV files sequentially but must retain no
  original CSV file after import.
- The Settings UI may raise the Streamlit browser-upload limit to 400MB per CSV
  file, but larger files must be rejected safely and the CLI path should remain
  the preferred path for near-limit imports.

Rollback or correction is required if any of the following occur:

- Representative names, phone raw values, raw CSV rows, full local paths, OCR raw
  text, provider raw JSON, or API keys are stored or displayed.
- Full address candidates are added to Excel output or used as automatic
  confirmation.
- Address-only matches overwrite `ReceiptRecord.merchant_name`,
  `business_number`, or `review_status`.
- OCR-derived address hints are stored in `ReceiptRecord`, Excel output,
  Processing History receipt rows, logs, or raw parser warnings.
- Phone, representative, business-number, approval/card, amount, or date lines
  are treated as address hints.
- Public CSV originals under `data/gov` or `govdata` are committed.
- Files larger than the configured 400MB UI limit are imported, retained, or
  reported with full local paths instead of a safe skip/error.

## Merchant Review Alias Learning Change Control

- Review alias learning may add safe reviewed merchant names to
  `merchant_alias` with `source=review`.
- It may link aliases to `merchant_master` only when business-number exact,
  normalized merchant-name exact, or a high-confidence master name match is
  available.
- It must skip uncertain master links by keeping `merchant_master_id` nullable.
- It must skip empty names, too-short names, mostly numeric/symbolic values,
  business-number patterns, phone-number patterns, representative labels,
  amount lines, dates, card identifiers, and approval identifiers.
- Repeated review saves must not keep appending the same
  `normalized_alias_name + business_number + source` row.

Rollback or correction is required if any of the following occur:

- Learned aliases automatically overwrite future `ReceiptRecord.merchant_name`,
  `business_number`, or `review_status`.
- Alias learning changes ExcelExporter sheets/columns or existing Processing
  History receipt schema.
- Raw OCR text, provider raw JSON, full local paths, representative names, phone
  raw values, full addresses, API keys, or raw tracebacks are stored or shown.
- Alias learning failure blocks review save, Excel generation, or download.
- Private crawling, mass business-number collection, NTS automatic calls, or
  OpenAI automatic correction are introduced in this step.

## Public Merchant CSV Import Performance Change Control

- Public merchant CSV import may use chunked `executemany` and one transaction
  per import batch.
- Import-time SQLite PRAGMA settings are allowed only for safe local bulk import
  performance, such as WAL, `synchronous=NORMAL`, and `temp_store=MEMORY`.
- Import result summaries may include file name, batch id, scanned/imported/
  skipped counts, duplicate-file status, elapsed seconds, and rows per second.
- Duplicate-file detection must continue to use allowed-column content hash.
- Duplicate-row detection must continue to use allowed-column row hash.

Rollback or correction is required if any of the following occur:

- A failed import leaves partial `merchant_master` rows or duplicate source logs.
- CLI/UI summaries expose full local paths, raw CSV rows, representative names,
  phone raw values, blocked columns, OCR raw text, provider raw JSON, API keys,
  or raw tracebacks.
- Bulk import changes existing `ReceiptRecord`, ExcelExporter, or Processing
  History receipt schemas.
- Address or merchant candidates become automatically confirmed.
- Public CSV originals under `data/gov` or `govdata` are committed.

## Merchant Dictionary Diagnostics Change Control

- Merchant diagnostics may read `merchant_master`, `merchant_alias`,
  `merchant_source_log`, and safe Processing History receipt fields.
- Dictionary summaries may show counts, latest import date, latest source file
  name, top category counts, duplicate-file count, and recent batch summaries.
- Candidate diagnostics may call the existing matcher only after explicit user
  action and must keep candidates as review-required hints.
- Saved ReceiptRecord diagnostics may use only merchant name, business number,
  source file name, and review status, and should report aggregate counts first.
- Business numbers shown by diagnostics must be masked as `123-**-*****`.

Rollback or correction is required if any of the following occur:

- Diagnostics automatically confirm, overwrite, or save merchant candidates.
- Diagnostics change `ReceiptRecord`, ExcelExporter sheets/columns, Processing
  History schema, matcher thresholds, default provider, NTS behavior, or OpenAI
  correction behavior.
- Raw OCR text, provider raw JSON, full local paths, phone raw values,
  representative names, raw CSV rows, API keys, raw tracebacks, or secrets are
  stored or displayed.
- Saved-record diagnostics run automatically over large history without an
  explicit button action.
- Business numbers are displayed in full instead of masked.
## Merchant Dictionary Search and Candidate Scoring Change Control

Allowed changes:

- Add a manual Settings search over `merchant_master` using bounded merchant-name
  or road-name/building-number filters.
- Add indexes that only support merchant dictionary search/matching and do not
  alter existing Processing History receipt/export schemas.
- Lower scores for very short substring fuzzy candidates unless a safe address
  hint boosts the candidate above the review threshold.
- Reduce review source preview rendering cost by showing only the selected row.

Rollback or correction is required if any of the following occur:

- Search or diagnostics expose full local paths, raw CSV rows, OCR raw text,
  provider raw JSON, representative names, phone raw values, API keys, raw
  tracebacks, or full business numbers.
- Merchant candidates automatically overwrite `ReceiptRecord.merchant_name`,
  `business_number`, `review_status`, Excel output, or Processing History rows.
- Search performs blank full-table browsing by default or makes Settings
  unusably slow on the public merchant database.

## Quality Stabilization and Review Diagnostics Change Control

Allowed changes:

- Add safe, manual Processing History diagnostics that report counts only.
- Add safe performance summaries for review dataframe generation, merchant
  candidate lookup/cache, selected source preview preparation, and merchant DB
  search query timing.
- Manually verify real PaddleOCR samples outside default pytest and report only
  safe field summaries.
- Improve selected source preview rendering and thumbnail preparation without
  changing review editing semantics.

Rollback or correction is required if any of the following occur:

- Default pytest calls real PaddleOCR, downloads OCR models, or requires live OCR
  provider access.
- Diagnostics or sample reports expose raw OCR text, provider raw JSON, full
  local paths, raw CSV rows, phone raw values, representative names, API keys,
  raw tracebacks, or full business numbers.
- Performance diagnostics write raw OCR/provider/CSV payloads to DB, UI, logs,
  tests, or Excel output.
- The change modifies existing `ReceiptRecord`, ExcelExporter sheets/columns, or
  Processing History schemas.
- Merchant/address candidates become automatically confirmed or overwrite saved
  receipt rows.
- NTS API calls or OpenAI correction are triggered automatically.

## 2026-10-19 PaddleOCR 정보 전달 후속 변경

사용자가 요청한 로컬 OCR 품질·기존 사전 검수 활용 범위에서 Provider 보완과 읽기 전용 조회/수동 후보 적용을 구현했다. Parser 및 표준 OCR/엑셀 스키마 의미는 유지했다. DB 조회 설정은 선택적 추가이며 V5 검수 데이터는 분리한다. 기본 모델 전환, 유료 API, 정답 주입, 금액 역산, 로컬 LLM 필수화는 포함하지 않았다. 기존 사용자 변경을 보존했다. [보고서](docs/ocr_fieldflow_followup.md).

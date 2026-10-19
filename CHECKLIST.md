# 파일럿 전 체크리스트

## 2026-10-19 GS·V5 비교 검증

- [x] 기존 사용자 변경·기본 GPU 환경·OCR/엑셀 계약 보존.
- [x] 안내문 상호 오탐, 숫자 열 경계, 인접 숫자 조각, 반복 결제액과 승인번호의 합성 테스트.
- [x] SDK 3.x 좌표/텍스트 길이·lazy 실행·SDK 선택·런처 환경/데이터 분리 테스트.
- [x] 전체 기본 테스트 1,019 passed / 3 skipped; 새 SDK 환경 계약·엑셀 85 passed.
- [x] 기본 엔진 실제 재처리 76/88 유지, 기존 정답 퇴행 0; V5 74/88로 승격 보류.
- [x] 실제 OCR 결과 17건의 앱 처리/표/상세 입력값/8시트 엑셀 136필드 전달 대조.
- [x] V5 실제 GPU 추론·pip check·별도 앱 실행 확인.
- [ ] 브라우저 실제 파일 업로드 후 표·팝업·다운로드 대조: Edge 확장 파일 URL 권한으로 차단.
- [ ] V5의 기존 정답 퇴행 해소, 새로운 독립 영수증 검증, 100% 목표 달성.

[평가 범위·실측·남은 문제](docs/ocr_gsfresh_v5_comparison.md).

## 2026-10-19 후보 계약·보완 좌표 검증

- [x] 명시 상호·유효 금액 후보·총액 보존·포인트/할인 구분·가로 세액 열 합성 회귀.
- [x] 회전·자르기·확대 좌표 복원과 평가 자료 형식/중복 사전 검사.
- [x] 실제 16장 처리, 기존 76/88 유지·퇴행 0. 앱 처리 128개 필드 보존과 표·서식·8개 시트 엑셀 대조.
- [ ] 100% 인식·새 미사용 4장 검증·전체 후보 출처/좌표 Parser 비교는 미완료.

[단계별 결과와 검증 범위](docs/ocr_contract16_followup.md).

## 2026-10-19 상호·총합계 후속 수정

- [x] 같은 행 상호/대표자 경계, 이름 안 콜론, 불완전 합계 영역 재인식, 낮은 신뢰도 거부·다른 합계 출처 보존 합성 회귀.
- [x] 동일 원본에서 합계 1,000 → 10,000원, 부가세 909원 유지. 상호 첫 글자 차이는 불일치로 유지.
- [x] 기존 16장 일치값 퇴행 0. 원래 8장 40/47·문제 사진 25/29 유지.
- [ ] 새 미사용 사진 일반화·상호 첫 글자 해결·기존 처리 결과 자동 정정은 미완료/범위 밖.

[범위·최종 테스트·앱 적용 상태](docs/ocr_label_total_followup.md).

## 2026-10-19 실제 사진 후속 품질

- [x] 기존 기준 보존, 중복 거래 제외한 별도 4장 선정, 수정 전/후 동일 엔진 평가
- [x] 명시 라벨·숫자 포함 상호·동순위 충돌·누락 0원·긴 문서 후반 회귀
- [x] 전체 933 passed / 3 skipped, OCR 관련 128 passed, 기존 정답 퇴행 0
- [x] 실제 앱 16개 팝업·엑셀 128개 필드 일치, 상호 슬래시 잘림 수정 및 경로/수식 보호
- [x] 기존 39/47 → 40/47, 문제 사진 18/29 → 25/29, 미사용 24/30 → 24/30과 시간/호출 공개
- [ ] 100% 일치 및 미사용 사진의 품질 향상 입증 — 미달, 완료로 간주하지 않음

[기준 정정 이력·항목별 결과·실행 검증](docs/ocr_quality_12_followup.md).

## 2026-10-19 닫기·행 재열기 실제 검증

- [x] 상단 X 활성화와 표 위젯 갱신 회귀를 수정 전 실패로 확인.
- [x] Chrome 1280×600에서 X·ESC 닫기, 같은 셀 단일/더블클릭 재열기, 초안 보존 확인.
- [x] 실제 앱 처리 경로의 동일 8장 상호: 6일치·1오인식·1누락. 정답 주입 복원 없음.
- [x] 전체 908 passed / 2 skipped, 관련 97 passed. compileall·diff check 통과.
- [x] 사용자 "지금 재시작" 승인 후 8501 종료·시작, running 상태·새 작업 화면 확인. 기존 Azure 기본값 유지, 과거 DB·엑셀 재작성하지 않음.

표 정렬 초기화와 실행 적용 범위: [후속 기록](docs/review_runtime_followup.md).

## 2026-10-19 남은 OCR 9개·오탐 검증

- [x] 기존 8장·판독 기준 해시 유지, 38/47 재현 후 39/47. 기존 일치 항목 퇴행 0개.
- [x] 단독 카드 법령 조각 오탐 1 → 0. 실제 결제 행과 빈칸/0원 보존 회귀.
- [x] 날짜 전용 재인식에서 세액을 채우지 못하도록 격리. 전체 분할 축소의 새 세액 오탐은 최종 소스에서 제외.
- [x] 별도 4장의 최초 판독값을 유지하되 한글 저장 오류를 복원하고 전후 코드를 같은 기준으로 재평가. 20/25 → 20/25, 퇴행 0개. 손상 기준 사전 거부 테스트 추가.
- [x] 기본 907 passed / 2 skipped, OCR 환경 관련 594 passed. compileall·diff check 통과.
- [x] 시간·남은 오류·실패한 실험을 함께 기록. 8장 45.98초 → 48.99초의 단일 관측.
- [ ] 기존 8장 47/47, 별도 사진 일반화, 전체 69장·모바일·대량 처리 품질은 입증하지 못함.

항목별 근거·재현 명령: [후속 평가](docs/ocr_remaining_followup.md).

## 2026-10-19 원본 전체 보기·표 클릭

- [x] 합성 시안 선전달, 원본 전체 비율 유지와 팝업/서식 높이 조정.
- [x] 첫 행·셀 클릭·같은 행 재열기, 기존 상세 검수 버튼 유지.
- [x] 관련 96개 회귀와 compileall 통과; Chrome 1718×1256 / 1280×768에서 원본 끝·하단 버튼·서식 내부 스크롤 확인.
- [ ] 모바일·아주 낮은 창·별도 확대 UI 검증/구현.

상세: [검증 기록](docs/review_image_fit.md).

## 2026-10-19 실패 16개 후속 검증

- [x] 사진 해시·판독 기준·기존 제외 항목을 유지하고 16개 원인/조치를 익명 번호로 기록.
- [x] 구분자·상호 열/라벨·세액 경계·날짜 조립·재인식 출처/실패 보존 회귀.
- [x] 무라벨 원 금액 추측 삭제, 표준 context의 다음 블록 세액 차용 차단, legacy text 호환.
- [x] 기본 894 passed / 2 skipped, OCR 환경 핵심 285 passed. 실제 38/47, 기존 일치값 퇴행 0.
- [ ] 남은 양성 실패 9개와 빈칸 결제수단 오탐 1개 해결.
- [ ] 별도 사진·모바일·대량 처리·재인식 비용의 독립 검증.

실행 명령과 한계: [후속 분석](docs/ocr_failure_followup.md). passing test 수는 실제 정확도가 아니다.

## 2026-10-19 신뢰성 감사

- [x] 파일명 정답 주입·고정 상호 치환·특정 상호 오탈자 정답표 제거
- [x] 미표기 합계·누락 0 생성 제거, 명시값·빈칸·0원 회귀
- [x] 좌표·EXIF·안내·작은 세액·일시 마스킹 회귀
- [x] 중복 그룹·승인번호 충돌·자동 별칭 학습·저장 경계·숫자 파싱 결함 수정
- [x] 해시 기반 로컬 평가 및 정답 미전달·결과값 미노출 테스트
- [ ] 실제 상호·세액 품질 개선과 별도 검증 자료 확보
- [ ] 검수 수정 후 파생 상태 재계산
- [ ] 원본 만료 실제 운영, 모바일·대량 배치 검증

최종 수치는 [감사 기록](docs/ocr_integrity_audit.md)을 따른다.

## 2026-10-19 일괄 표·팝업 검수

- [x] 구현 전 전체 목록/상세 팝업 합성 시안을 전달하고 사용자 "시안대로 진행" 응답 확인.
- [x] 10건 전체 표, 원본파일명/점수 비노출, 숫자형 유지와 천 단위 콤마·미표기 `—` 표시.
- [x] 행 선택과 표 아래 영수증 선택 연결, 팝업의 좌측 원본/우측 서식 및 하단 버튼.
- [x] 이전/다음·저장 후 다음·닫기, 영수증별 세션 초안과 저장된 레코드 분리.
- [x] 잘못된 금액/소수/구분자/안전 범위 초과 저장 차단, 0원·누락·음수 보존.
- [x] 저장 후 표/진행 건수 갱신, 필터 적용 후 이동 대상 보존, 이전 엑셀 다운로드 해제.
- [x] 실제 Chrome에서 합성 10건, 행 선택, 닫기·재열기의 `123,456` 초안 복원, 저장 후 다음, 확인완료 1건/검토필요 9건 필터 확인.
- [x] compileall 및 전체 pytest 822 passed / 2 skipped / 100 warnings. OCR/Parser/Exporter/DB 계약 변경 없음.

결과와 제약: [일괄 표·팝업 검수 기록](docs/batch_review_ui.md).

## 2026-10-19 실제 실행 화면 재검증

- [x] 실제 브라우저에서 예전 모듈을 사용하는 서버의 기존 화면을 재현하고 프로젝트 전용 실행기로 재시작했다.
- [x] 원본 이미지 HTTP 응답 오류를 재현한 후 호환 Starlette 1.7.0 제약을 공통 requirements에 추가했다.
- [x] PNG/JPEG 및 identity/gzip 응답 회귀 테스트 4개를 추가했다. 수정 전 4개 실패, 수정 후 4개 통과.
- [x] 합성 영수증/Mock OCR로 원본 이미지와 통합 서식이 나란히 표시되는 것을 실제 Chrome에서 확인했다.
- [x] compileall·pip check 통과. 전체 pytest 802 passed / 2 skipped / 100 warnings.

상세: [실제 화면 적용 기록](docs/review_live_verification.md).

## 2026-10-19 통합 검수와 명시 금액

- [x] 선택 영수증의 원본과 표준 수정 서식 통합, 기본 메타데이터/후보 점수/성능 표시 제거.
- [x] 상호·사업자번호·할인·세액·결제수단 수정과 선택 외 레코드 보존 회귀 테스트.
- [x] 빈칸과 명시 0원 구분, 중복의심 자동 제외 금지, 수정 후 이전 엑셀 다운로드 해제.
- [x] 누락 공급가액·부가세·할인 및 할인 차감 최종금액의 계산 생성 제거.
- [x] 과거 레코드의 추정 세액도 새 엑셀에서 공란 처리, 기존 시트/컬럼 유지.
- [ ] 고객 영수증의 인식 정확도 평가와 모바일 기기 검증은 별도 수행.

검증 명령과 결과: [검수 화면 정리 기록](docs/review_ux_refinement.md).

## 2026-10-19 PaddleOCR/GPU 실행 환경 복구

- [x] 기존 Python 3.10에 PaddleOCR 2.7.3/GPU Paddle 2.6.2가 있으며 CUDA·GPU 텐서 연산을 통과함을 확인했다.
- [x] 실행기의 `.venv-ocr` 우선 선택, 기본 환경 호환, 손상된 OCR 환경의 오류 처리를 테스트했다.
- [x] Python 3.11 선택 환경의 CPU/GPU 합성 OCR이 모두 completed이며, 실제 detector 추론 GPU 설정이 각각 false/true임을 확인했다. 기존 캐시 모델만 사용했다.
- [x] `pip check`·compileall 통과, 전체 pytest 784 passed / 2 skipped. GPU 모드의 AppTest 선택이 차단되지 않음을 확인했다.
- [x] 서버를 재시작하고 실제 실행 파일이 `.venv-ocr`에 속하는지 확인했다. 기존 고객 영수증은 재처리하지 않았다.

## 2026-10-19 Windows 로컬 실행기

- [x] 프로젝트 `.venv`로 시작하며 경로에 공백이 있어도 실행 인자를 유지한다.
- [x] 반복 실행은 같은 앱을 재사용하고 사용 중인 다른 포트의 프로세스를 종료하지 않는다.
- [x] 종료는 PID·시작시각·프로젝트 실행 명령을 확인하며 오래된 상태의 다른 프로세스는 종료하지 않는다.
- [x] 실행기 테스트는 임시 상태와 합성 프로세스를 사용하며 실제 OCR 요청을 하지 않는다.
- [x] 실제 서버 시작/재사용/종료와 바탕화면 실행 바로가기의 서버 기동을 확인했다. 임시 저장소·mock 설정의 업로드 화면은 AppTest로 확인했다.
- [x] compileall 통과, 기본 pytest 781 passed / 2 skipped. 실제 OCR 정확도·고객 자료 재처리는 검증 범위에서 제외했다.

## 2026-10-18 설계 문서와 후속 수용 기준

아래 구현 항목은 설계 문서 작성과 구분한다. 체크되지 않은 항목은 현재 지원을 의미하지 않는다.

- [x] [통일 양식](docs/receipt_standardization_proposal.md), [상호 보정](docs/merchant_resolution_design.md), [누적 저장](docs/receipt_accumulation_design.md) 설계안을 작성했다.
- [ ] 연락처·주소·거래시각이 허용 필드 계약, 검수, 저장, 엑셀까지 보존된다.
- [ ] 거래합계와 당일 금전결제액이 구분되고 포인트 수/원화 명시액, 사용/적립, 할인/결제/역할미확인을 구분한다.
- [ ] 포인트·상품권 전액 결제, 전액 할인, 거스름돈, 복합결제, 혼합 세액, 외화, 취소/부분환불을 합성 사례로 검증했다.
- [ ] 명시 공급가액·부가세를 결제액으로 덮어쓰지 않고 참고 추정값을 합계에서 분리한다.
- [ ] 특정 거래처 고정 치환을 전수 목록화하고 후보 이전 전후 회귀를 비교했다.
- [ ] OCR 추출값·DB 후보·사용자 선택값·출처를 구분하며 잘못된 지점 자동 선택을 막는다.
- [ ] 사용자 별칭 저장은 명시적 선택과 작업공간 범위를 따른다.
- [ ] 스캔 후 미검수 저장과 엑셀 생성이 분리되고 재전송·재OCR이 새 거래를 중복 생성하지 않는다.
- [ ] 날짜미확인·날짜수정·동시수정 충돌·중복 증빙·원본 만료·출력 후 수정을 검증했다.
- [ ] 기존 값의 legacy_unknown 처리, 기존 이력·8개 시트 호환, 출력 스냅샷을 검증했다.
- [ ] 실제 모델/버전 변경 시 SPEC·CHECKLIST·fixture를 동기화하고 Parser/Validator/Exporter/end-to-end 회귀를 통과했다.

실제 OCR 정확도와 세무상 적격성은 위 구조 테스트 통과와 별도로 확인해야 한다.

## 1. 공통 원칙

| 체크 | 항목 |
|---|---|
| [ ] | OCR 결과는 항상 검수 대상으로 안내된다 |
| [ ] | 비용항목은 추천값과 최종 입력값이 구분된다 |
| [ ] | 원본 파일 장기 보관을 전제로 하지 않는다 |
| [ ] | API key, secret, token이 코드와 문서에 없다 |
| [ ] | 전체 로컬 경로가 화면/DB/엑셀에 노출되지 않는다 |
| [ ] | OCR 원문 전체와 raw JSON 전체가 화면/DB/엑셀에 노출되지 않는다 |
| [ ] | 민감문구 감지 건은 실제 값이 아니라 category만 화면/DB/엑셀에 표시된다 |
| [ ] | README/PLAN/SPEC/CHECKLIST가 현재 코드와 충돌하지 않는다 |

## 2. 새 작업 흐름

| 체크 | 항목 |
|---|---|
| [ ] | `streamlit run app/main.py`로 앱이 실행된다 |
| [ ] | `새 작업` 메뉴가 표시된다 |
| [ ] | 영수증 이미지/PDF 업로드가 가능하다 |
| [ ] | 카드 사용내역 CSV/XLSX 업로드가 가능하다 |
| [ ] | Mock OCR 처리가 가능하다 |
| [ ] | Azure OCR 선택 시 네트워크와 API key 설정이 필요하다는 점을 알고 있다 |
| [ ] | `파일 저장 및 처리` 중 버튼이 비활성화되고 진행 상태가 표시된다 |
| [ ] | 검수 UI가 표시된다 |
| [ ] | 할인전금액, 할인금액, 최종결제금액, 실제결제금액, 금액판단기준, 금액검토사유를 확인할 수 있다 |
| [ ] | 부가세 명시값과 참고 추정값이 구분되어 표시된다 |
| [ ] | 민감문구감지와 민감문구유형은 실제 값 없이 category만 표시된다 |
| [ ] | 검수 테이블 수정값이 엑셀에 반영된다 |
| [ ] | 제외 상태가 제외내역 시트에 반영된다 |
| [ ] | 표준 엑셀 생성이 가능하다 |
| [ ] | 엑셀 다운로드가 가능하다 |
| [ ] | 엑셀 파일이 열린다 |

## 3. 엑셀 산출물

| 체크 | 항목 |
|---|---|
| [ ] | 정리내역 시트가 있다 |
| [ ] | 월별요약 시트가 있다 |
| [ ] | 비용항목별요약 시트가 있다 |
| [ ] | 검토필요 시트가 있다 |
| [ ] | 카드대조 시트가 있다 |
| [ ] | 원본파일목록 시트가 있다 |
| [ ] | 처리로그 시트가 있다 |
| [ ] | 제외내역 시트가 있다 |
| [ ] | OCR 원문 전체가 엑셀에 없다 |
| [ ] | raw JSON 전체가 엑셀에 없다 |
| [ ] | 전체 로컬 경로가 엑셀에 없다 |
| [ ] | 할인 후 0원 결제 건은 총금액 0으로 남고 자동 제외되지 않는다 |
| [ ] | 추정부가세는 명시 부가세 합계에 자동 합산되지 않는다 |
| [ ] | 민감문구 감지 건은 실제 값 없이 category만 표시된다 |

## 3-1. 실제 OCR 금액/민감문구 확인

| 체크 | 항목 |
|---|---|
| [ ] | 할인금액이 있는 영수증에서 할인전금액, 할인금액, 최종결제금액이 분리된다 |
| [ ] | 받은금액 또는 합계금액이 0인 할인 영수증은 총금액 0으로 표시된다 |
| [ ] | 상품권/포인트/카드결제 혼재 영수증에서 최종결제금액과 실제결제금액을 구분해 검토할 수 있다 |
| [ ] | 수량 1, 3, 10 같은 숫자가 할인금액이나 실제결제금액으로 들어가지 않는다 |
| [ ] | 카드/승인번호 같은 긴 숫자가 할인금액으로 들어가지 않는다 |
| [ ] | 결제금액 기준 같은 설명 문구 뒤의 푸터 숫자가 실제결제금액으로 들어가지 않는다 |
| [ ] | 부가세 미표기 영수증은 명시 부가세가 비어 있고 참고 추정값이 별도 컬럼에 표시된다 |
| [ ] | WiFi PW, 비밀번호, 카드번호 전체 등 민감문구 가능성이 있는 값은 원문이 표시되지 않는다 |
| [ ] | Azure OCR 사용 시 사업자번호, 전화/TEL, 카드결제/현금결제 관련 context line이 Parser에 필요한 범위로 반영된다 |

## 4. 처리 이력

| 체크 | 항목 |
|---|---|
| [ ] | 엑셀 생성 성공 직후 ProcessingJob이 DB에 저장된다 |
| [ ] | 같은 작업에서 엑셀 생성 버튼을 반복 눌러도 불필요한 job이 계속 쌓이지 않는다 |
| [ ] | `처리 이력` 메뉴가 표시된다 |
| [ ] | 처리 이력 목록이 최신순으로 표시된다 |
| [ ] | 방금 저장된 작업이 목록에서 조회된다 |
| [ ] | 상세 화면에서 작업 요약이 표시된다 |
| [ ] | 상세 화면에서 ReceiptRecord 요약이 표시된다 |
| [ ] | 상세 화면에서 CardTransaction 요약이 표시된다 |
| [ ] | 상세 화면에서 ExportFile 목록이 표시된다 |
| [ ] | 기존 엑셀 파일 재다운로드가 가능하다 |
| [ ] | export 파일이 없을 때 안전한 안내 메시지가 표시된다 |
| [ ] | 과거 작업 재검수 기능은 표시되지 않는다 |
| [ ] | 과거 엑셀 재생성 기능은 표시되지 않는다 |

## 5. 설정 화면

| 체크 | 항목 |
|---|---|
| [ ] | `설정` 메뉴가 표시된다 |
| [ ] | 현재 OCR provider를 확인할 수 있다 |
| [ ] | API key 값은 표시되지 않는다 |
| [ ] | Azure endpoint 전체 URL은 표시되지 않는다 |
| [ ] | 업로드/출력 보관기간을 확인할 수 있다 |
| [ ] | 저장소 파일 수와 총 용량을 확인할 수 있다 |
| [ ] | DB 접근 가능 여부와 처리 이력 건수를 확인할 수 있다 |
| [ ] | 처리 이력 연결 상태를 확인할 수 있다 |
| [ ] | cleanup dry-run 요약을 확인할 수 있다 |
| [ ] | 실제 cleanup 삭제 버튼은 없다 |
| [ ] | provider 변경 UI는 없다 |
| [ ] | API key 입력 UI는 없다 |

## 6. 깨끗한 상태/기존 상태 점검

| 체크 | 항목 |
|---|---|
| [ ] | `data/app.db`가 없는 상태에서도 앱이 실행된다 |
| [ ] | DB가 없는 상태에서 처리 이력 화면이 빈 상태를 안전하게 표시한다 |
| [ ] | DB가 없는 상태에서 설정 화면이 오류 없이 표시된다 |
| [ ] | 기존 DB가 있는 상태에서 목록/상세/재다운로드가 동작한다 |
| [ ] | 새 작업 → 처리 이력 → 상세 → 설정 → 새 작업 이동 중 session_state 오류가 없다 |
| [ ] | cleanup dry-run이 실제 파일을 삭제하지 않는다 |

## 7. Git/민감 파일 점검

| 체크 | 항목 |
|---|---|
| [ ] | `.env`가 Git 변경사항에 없다 |
| [ ] | `data/uploads` 실제 파일이 Git 변경사항에 없다 |
| [ ] | `data/outputs` 실제 파일이 Git 변경사항에 없다 |
| [ ] | `output` 실제 파일이 Git 변경사항에 없다 |
| [ ] | `data/app.db` 또는 `*.db`가 Git 변경사항에 없다 |
| [ ] | 실제 고객 파일이나 실제 영수증 파일이 Git 변경사항에 없다 |
| [ ] | `git diff --check`가 통과한다 |

## 8. 테스트

```bash
python -m compileall app tests
python -m pytest
python -m pytest tests/test_end_to_end_export_flow.py
python -m pytest tests/test_history_utils.py
python -m pytest tests/test_history_detail_view.py
python -m pytest tests/test_settings_utils.py
```

| 체크 | 항목 |
|---|---|
| [ ] | compileall 통과 |
| [ ] | 전체 pytest 통과 |
| [ ] | end-to-end export flow 테스트 통과 |
| [ ] | history utils 테스트 통과 |
| [ ] | history detail 테스트 통과 |
| [ ] | settings utils 테스트 통과 |

## 9. 테스트 실패 기록

| 항목 | 기록 |
|---|---|
| 실패 명령 |  |
| 실패 테스트 |  |
| 실패 위치 |  |
| 원인 추정 |  |
| 즉시 수정 여부 |  |
| 파일럿 진행 가능 여부 |  |
| 다음 액션 |  |

## 10. Standard Core / Provider 독립화 체크리스트

| 체크 | 항목 |
|---|---|
| [ ] | Parser가 provider raw response를 직접 import하지 않는가 |
| [ ] | Parser 입력은 `StandardOCRResult` 기준인가 |
| [ ] | Azure Adapter는 Azure raw response를 `StandardOCRResult`로 변환하는가 |
| [ ] | Mock Provider도 `StandardOCRResult` fixture를 만들 수 있는가 |
| [ ] | PaddleOCR, Tesseract, ML Kit, Apple Vision은 향후 Adapter만 추가하면 Parser 흐름을 재사용할 수 있는가 |
| [ ] | OCR raw JSON 전체가 DB/화면/엑셀/로그에 노출되지 않는가 |
| [ ] | OCR raw text 전체가 DB/화면/엑셀/로그에 노출되지 않는가 |
| [ ] | 전체 로컬 절대경로가 DB/화면/엑셀/로그에 노출되지 않는가 |
| [ ] | `StandardOCRResult` fixture 테스트 계획이 있는가 |
| [ ] | Golden Test Fixture로 provider와 무관하게 Parser 결과를 비교할 수 있는가 |
| [ ] | `ReceiptRecord`와 `ExcelExporter` 구조를 불필요하게 대규모 변경하지 않았는가 |
| [ ] | `StandardOCRResult` Pydantic 모델 생성 테스트가 있는가 |
| [ ] | Mock/Azure-like/edge-case fixture를 모델로 로딩하는 테스트가 있는가 |
| [ ] | fixture의 `source_block_ids`가 실제 `text_blocks.block_id`와 연결되는가 |
| [ ] | `quantity`, `approval_number`, `footer_number` 후보가 `total_amount` 후보와 분리되어 있는가 |
| [ ] | `StandardOCRParserContext`에 `raw_json`/`raw_text`/`provider_raw_response`가 없는가 |
| [ ] | `StandardOCRParserContext`가 fixture에서 안전하게 생성되는가 |
| [ ] | `business_number`가 금액 후보와 분리되는가 |
| [ ] | `vat_missing`, `vat_review_hint`가 명시 부가세와 분리되는가 |
| [ ] | `StandardOCRParserContext` 테스트가 있는가 |
| [ ] | Golden Fixture context shape 비교가 가능한가 |
| [ ] | 기존 end-to-end 테스트가 깨지지 않는가 |
| [ ] | 기존 `ExcelExporter` 산출물 구조가 변경되지 않았는가 |
| [ ] | 기존 Processing History DB schema가 변경되지 않았는가 |

## 11. Local OCR Runtime 점검

| 체크 | 항목 |
|---|---|
| [ ] | `OCR_PROVIDER=paddle` 설정 후보가 문서화되어 있는가 |
| [ ] | PaddleOCR 미설치 시 앱이 안전하게 실패하거나 명확한 안내를 하는가 |
| [ ] | Local OCR Runtime은 전체 로컬 절대경로를 화면/DB/엑셀에 노출하지 않는가 |
| [ ] | 대량 처리 시 평균 처리시간을 측정할 수 있는가 |
| [ ] | Azure fallback 조건이 정의되어 있는가 |

## 11-1. Azure Adapter 표준화 체크리스트

| 체크 | 항목 |
|---|---|
| [ ] | Azure raw response가 Parser로 직접 전달되지 않는다 |
| [ ] | Azure SDK response object를 Parser가 import하지 않는다 |
| [ ] | Azure raw JSON 전체가 `StandardOCRResult`에 저장되지 않는다 |
| [ ] | Azure raw text 전체가 `StandardOCRResult`에 저장되지 않는다 |
| [ ] | `provider_fields`가 raw JSON 저장소로 사용되지 않는다 |
| [ ] | `provider_fields`에는 비민감 metadata와 adapter 진단 요약만 들어간다 |
| [ ] | `tests/test_azure_standard_adapter.py`에서 `provider_fields` 금지 키와 count/flag metadata를 검증한다 |
| [ ] | sanitized Azure fixture 3종으로 성공/edge/failed 변환을 검증한다 |
| [ ] | Azure endpoint 전체 URL이 화면/DB/엑셀/로그/fixture에 없다 |
| [ ] | `operation_location` 전체 URL이 화면/DB/엑셀/로그/fixture에 없다 |
| [ ] | API key, secret, token이 코드/문서/fixture에 없다 |
| [ ] | Azure field는 `StandardOCRTextBlock`, `StandardOCRKeyValueCandidate`, `StandardOCRTableCandidate`로 정규화된다 |
| [ ] | `quantity`, `approval_number`, `footer_number`, `business_number`가 amount candidate와 분리된다 |
| [ ] | `vat_missing`, `vat_review_hint`가 명시 부가세와 분리된다 |
| [ ] | Azure `diagnostic_code`/`warnings`는 비민감 코드와 짧은 메시지만 포함한다 |
| [ ] | 기존 Azure Provider 동작은 유지된다 |
| [ ] | 기존 `AzureProvider.extract()` 반환값이 변경되지 않았다 |
| [ ] | 기존 Azure Provider public interface가 유지된다 |
| [ ] | Azure Provider 테스트가 실제 Azure API key 없이 통과한다 |
| [ ] | Azure Adapter integration contract test가 있다 |
| [ ] | Adapter output이 `StandardOCRParserContext`로 변환된다 |
| [ ] | Adapter output이 기존 `ReceiptParser`에 직접 연결되지 않았다 |
| [ ] | `provider_fields`가 parser context로 그대로 전달되지 않는다 |
| [ ] | Azure Provider 연결과 Parser 전환이 분리되어 있다 |
| [ ] | 8주차 Parser 전환 진입 조건이 문서화되어 있다 |
| [ ] | 기존 `ReceiptParser` 동작은 유지된다 |
| [ ] | 기존 `ExcelExporter` 산출물 구조는 유지된다 |
| [ ] | 기존 Processing History DB schema는 유지된다 |
| [ ] | 기존 end-to-end export flow 테스트가 깨지지 않는다 |

## 11-2. Parser 표준 입력 전환 체크리스트

| 체크 | 항목 |
|---|---|
| [ ] | `ReceiptParser`가 Provider raw response를 직접 받지 않는다 |
| [ ] | `ReceiptParser`가 Azure SDK response object를 import하지 않는다 |
| [ ] | `ReceiptParser`가 PaddleOCR/Tesseract/ML Kit/Apple Vision 원본 구조를 직접 참조하지 않는다 |
| [ ] | `StandardOCRParserContext` 기반 Parser entry 추가 계획이 있다 |
| [ ] | 기존 raw_text 기반 Parser 경로를 즉시 삭제하지 않는다 |
| [ ] | compatibility wrapper 전략이 문서화되어 있다 |
| [ ] | Parser 입력에 `raw_json`/`raw_text`/`provider_raw_response`/`full_ocr_text`가 없다 |
| [ ] | Parser 입력에 endpoint/`operation_location`/API key/전체 로컬 절대경로가 없다 |
| [ ] | `quantity`, `approval_number`, `footer_number`, `business_number`가 amount candidate와 분리된다 |
| [ ] | `vat_missing`, `vat_review_hint`가 명시 부가세와 분리된다 |
| [ ] | mock fixture 기반 Parser 테스트 계획이 있다 |
| [ ] | azure-like fixture 기반 Parser 테스트 계획이 있다 |
| [ ] | Azure Adapter output 기반 Parser 테스트 계획이 있다 |
| [ ] | edge-case fixture 기반 Parser 테스트 계획이 있다 |
| [ ] | legacy raw_text Parser 결과와 standard context Parser 결과의 핵심 필드 비교 계획이 있다 |
| [ ] | 기존 `ReceiptRecord` 구조가 대규모로 변경되지 않는다 |
| [ ] | 기존 `ExcelExporter` 산출물 구조가 변경되지 않는다 |
| [ ] | 기존 Processing History DB schema가 변경되지 않는다 |
| [ ] | 기존 end-to-end export flow 테스트가 유지된다 |
| [ ] | 8주차-D에서 Validator/CategoryRules/CardMatcher/ExcelExporter/Processing History 회귀 테스트가 실행된다 |

## 12. Mobile OCR Standard 점검

| 체크 | 항목 |
|---|---|
| [ ] | 모바일 앱도 `StandardOCRResult`를 생성하는 방향인가 |
| [ ] | Android ML Kit과 iOS Apple Vision 결과를 Adapter로 변환하는 전략이 있는가 |
| [ ] | 앱은 상세 검수/처리 이력/카드내역 대조 전체를 처음부터 구현하지 않는가 |
| [ ] | 앱에서 생성한 JSON/ZIP을 웹/PC에서 이어 처리하는 후보가 문서화되어 있는가 |

## Week 8-B Parser Entry Checkpoints

| Check | Item |
|---|---|
| [ ] | `ReceiptParser.parse_standard_context(...)` exists and returns `ReceiptRecord`. |
| [ ] | `ReceiptParser.parse_from_standard_ocr(...)` routes through `StandardOCRParserContext`. |
| [ ] | Existing `ReceiptParser.parse(...)` signature and raw_text path remain unchanged. |
| [ ] | New parser entry is not wired to Streamlit, AzureProvider, MockProvider, or provider factory. |
| [ ] | Mock standard fixture can produce a `ReceiptRecord` through the new entry. |
| [ ] | Azure-like standard fixture can produce separated gross/discount/final/paid amount fields. |
| [ ] | Edge-case fixture keeps quantity, approval number, footer number, and business number out of amount candidates. |
| [ ] | Azure adapter output can become `StandardOCRParserContext` and then `ReceiptRecord`. |
| [ ] | Failed or partial context becomes a review-required record with non-sensitive warnings. |
| [ ] | Parser output does not expose raw JSON, raw text, provider raw response, endpoint, operation location, API key, token, secret, or absolute local paths. |
| [ ] | 8-C still needs deeper legacy-vs-standard fixture comparison tests. |
| [ ] | 8-D still needs downstream Validator/Exporter/History regression checks. |

## Week 8-C Parser Fixture Comparison Checkpoints

| Check | Item |
|---|---|
| [ ] | `tests/test_receipt_parser_standard_comparison.py` compares standard parser output across mock, azure-like, edge-case, and Azure adapter fixtures. |
| [ ] | Limited legacy raw_text fixtures exist under `tests/fixtures/parser_legacy/` for core-field comparison only. |
| [ ] | Legacy raw_text parser path and `ReceiptParser.parse(...)` public interface remain unchanged. |
| [ ] | Standard parser output keeps quantity, approval number, footer number, and business number out of amount fields. |
| [ ] | `vat_missing` and `vat_review_hint` do not populate explicit `vat_amount`. |
| [ ] | Failed Azure adapter output becomes a review-required record with non-sensitive warnings. |
| [ ] | Sensitive categories are category-only and do not expose raw sensitive values. |
| [ ] | `provider_fields` raw metadata is not copied to `ReceiptRecord`. |
| [ ] | Parser output does not expose raw JSON, raw text, provider raw response, endpoint, operation location, API key, token, secret, or absolute local paths. |
| [ ] | Downstream-ready `ReceiptRecord` shape is present, but Validator/CategoryRules/CardMatcher/ExcelExporter/Processing History regression remains 8-D scope. |

## Week 8-D Downstream Regression Checkpoints

| Check | Item |
|---|---|
| [ ] | Standard Parser records pass through `ReceiptValidator` without provider raw response or raw payload exposure. |
| [ ] | `CategoryRules` still works from `ReceiptRecord.merchant_name` and does not consume `StandardOCRResult` or provider raw response. |
| [ ] | `CardMatcher` still works from `ReceiptRecord` and `CardTransaction`, including amount/non-amount separation. |
| [ ] | `ExcelExporter` creates the existing sheet set and keeps existing summary/review headers. |
| [ ] | Excel output does not expose OCR raw text, provider raw JSON, `provider_fields`, endpoint, operation location, API key, token, secret, or absolute local paths. |
| [ ] | Processing History save/read works with Standard Parser records without DB schema changes. |
| [ ] | Processing History rows do not store provider raw JSON, raw OCR text, `provider_fields`, or absolute local paths. |
| [ ] | Provider independence test confirms `provider="paddleocr"` candidate records pass downstream without special casing. |
| [ ] | `requirements.txt` does not add PaddleOCR or Tesseract dependencies during 8-D. |
| [ ] | Existing raw_text parser path, Provider code, AzureStandardOCRAdapter, ExcelExporter structure, Processing History DB schema, and Streamlit UI remain unchanged. |
| [ ] | Existing end-to-end export flow remains passing. |
| [ ] | 9주차 PaddleOCR Local Provider PoC entry conditions are documented. |

## Week 9-A PaddleOCR Local Provider PoC Checklist

| Check | Item |
|---|---|
| [ ] | `OCR_PROVIDER=paddle` candidate is documented, but the default provider is not changed. |
| [ ] | `PaddleOCRProvider` must return `StandardOCRResult`. |
| [ ] | `PaddleStandardOCRAdapter` is responsible for converting PaddleOCR-like output into `StandardOCRResult`. |
| [ ] | `ReceiptParser` does not receive PaddleOCR raw output. |
| [ ] | `ReceiptValidator`, `CategoryRules`, `CardMatcher`, and `ExcelExporter` do not receive PaddleOCR raw output. |
| [ ] | `paddleocr` import must be lazy and optional. |
| [ ] | Default pytest must pass when `paddleocr` is not installed. |
| [ ] | Default pytest must not download models, call network resources, or run actual PaddleOCR. |
| [ ] | Actual PaddleOCR OCR tests are opt-in only. |
| [ ] | Week 9 PoC is image-first, limited to JPG/JPEG/PNG-style inputs. |
| [ ] | PDF processing is deferred to follow-up work. |
| [ ] | PaddleOCR raw output is not stored in DB, Excel, UI, logs, fixtures, or test output. |
| [ ] | Full OCR raw text is not stored in DB, Excel, UI, logs, fixtures, or test output. |
| [ ] | Full local absolute paths are not stored in `StandardOCRResult`, DB, Excel, UI, logs, fixtures, or test output. |
| [ ] | `provider_fields` is not used as a raw output store. |
| [ ] | Week 9-B adapter fixtures are sanitized/dummy data, not actual customer files or full raw PaddleOCR output. |
| [ ] | Week 9-C provider implementation remains optional dependency based. |
| [ ] | Week 9-D actual OCR smoke test is gated by an explicit opt-in environment variable. |
| [ ] | 10주차 Azure vs PaddleOCR comparison uses `StandardOCRResult`, `StandardOCRParserContext`, and `ReceiptRecord` fields, not provider raw output. |

## Week 9-B PaddleOCR-like Adapter Fixture Checklist

| Check | Item |
|---|---|
| [x] | `PaddleStandardOCRAdapter` converts sanitized PaddleOCR-like mapping input to `StandardOCRResult`. |
| [x] | Regular, edge, and empty/failed sanitized Paddle fixture files exist under `tests/fixtures/paddle/`. |
| [x] | Adapter output uses `provider="paddleocr"` and `engine_runtime="pc_local"`. |
| [x] | `provider_fields` contains only non-sensitive metadata and count/flag values. |
| [x] | Fixture and output tests reject raw output, raw OCR text, image/model/absolute paths, endpoint, key, token, secret, and password exposure. |
| [x] | `quantity`, `approval_number`, `footer_number`, and `business_number` remain non-amount candidates. |
| [x] | `vat_missing` and `vat_review_hint` remain review hints, not explicit `vat_amount`. |
| [x] | Paddle-like bbox and confidence values are normalized into `StandardOCRTextBlock`. |
| [x] | Empty/failed Paddle-like results carry non-sensitive `diagnostic_code` and warning context. |
| [x] | Adapter output can build `StandardOCRParserContext` and can be parsed by the standard parser entry in tests. |
| [x] | 9주차-B does not add `PaddleOCRProvider`, actual `paddleocr` import, actual OCR execution, PDF handling, provider factory changes, default provider changes, or `requirements.txt` changes. |
## Week 9-C Optional PaddleOCRProvider Checklist

- [x] `PaddleOCRProvider` is added as an optional provider candidate.
- [x] `PaddleOCRProvider` returns `StandardOCRResult`.
- [x] `PaddleOCRProvider` reuses `PaddleStandardOCRAdapter`.
- [x] `paddleocr` is not imported at module top level.
- [x] Provider import and provider construction do not require `paddleocr` to be installed.
- [x] Missing `paddleocr` is reported as a failed `StandardOCRResult` with a non-sensitive diagnostic code.
- [x] Warnings do not include raw traceback, full local path, model path, or environment details.
- [x] PDF input is marked unsupported/deferred without adding PDF conversion code.
- [x] Provider factory supports `OCR_PROVIDER=paddle` and optional `paddleocr` alias.
- [x] Default provider remains unchanged.
- [x] Provider factory tests do not execute real OCR.
- [x] `requirements.txt` is not changed and no `paddleocr` dependency is added.
- [x] Parser, Validator, CategoryRules, CardMatcher, ExcelExporter, Processing History DB, and Streamlit UI remain unchanged.
- [x] 9-D opt-in smoke test entry conditions are documented.

## Week 9-D Opt-In Local OCR Smoke Test Checklist

- [x] Real PaddleOCR image smoke test is opt-in only.
- [x] Smoke test skips unless `RUN_PADDLEOCR_TESTS` is explicitly enabled.
- [x] Smoke test skips unless `PADDLEOCR_TEST_IMAGE_PATH` is configured.
- [x] Smoke test skips when the configured file is missing or not a supported image extension.
- [x] Smoke test skips when `paddleocr` is not installed.
- [x] Default pytest does not run real OCR.
- [x] Smoke test validates `StandardOCRResult` output, not provider raw output.
- [x] Smoke test validates parser context conversion.
- [x] Smoke test validates the standard parser entry can be called without provider raw output.
- [x] PDF input remains unsupported/deferred without PDF conversion.
- [x] No real customer image or real OCR image fixture is committed.
- [x] Smoke test failure classification is documented as environment/provider/security/quality.
- [x] 10-week Azure vs PaddleOCR comparison remains a separate follow-up.

## Week 10-A Azure vs PaddleOCR Quality Comparison Contract Checklist

- [x] Quality comparison uses `StandardOCRResult`, `StandardOCRParserContext`, and `ReceiptRecord`, not provider raw output.
- [x] `docs/ocr_quality_comparison_contract.md` defines the comparison purpose, scope, input contract, metrics, and fallback candidate signals.
- [x] Core comparison fields include date, merchant, business number, total amount, VAT fields, payment fields, review status, warnings, confidence, and provider status.
- [x] Report row contract excludes provider raw JSON, full OCR raw text, full local absolute paths, endpoint, operation location, API key, token, secret, and raw traceback.
- [x] Sample set rules require synthetic or non-sensitive test data and file-name-only reporting.
- [x] Expected fixture strategy is defined around safe `sample_id` and core `ReceiptRecord` fields, not provider raw output.
- [x] Report row contract includes low-confidence line counting as a future comparison signal.
- [x] PDF PaddleOCR handling remains deferred.
- [x] 10-A does not implement safe OCR preview UI.
- [x] 10-A does not implement side-by-side report code.
- [x] 10-A does not implement statistics aggregation or automatic Azure fallback execution.
- [x] Existing ExcelExporter sheet/column structure remains unchanged.
- [x] Existing Processing History DB schema remains unchanged.
## Week 10-B Safe OCR Preview Checklist

- [x] Safe preview rows are built from `StandardOCRResult.text_blocks`, not provider raw output.
- [x] PaddleOCR smoke-test results can display a limited preview in Settings.
- [x] Azure adapter output can reuse the same preview utility through `StandardOCRResult`.
- [x] Preview rows include line order, page index, block id, text, confidence label, low-confidence flag, sensitive category, and redaction flag.
- [x] Preview summary includes provider, status, diagnostic code, source file name, text block count, preview line count, low-confidence line count, redacted line count, max lines, and low-confidence threshold.
- [x] Sensitive lines remain `[REDACTED]`.
- [x] Full OCR raw text, provider raw output, raw JSON, full local absolute paths, endpoints, keys, secrets, tokens, and raw tracebacks are not displayed or stored.
- [x] No raw text download or full OCR preview download is added.
- [x] Side-by-side reports, statistics aggregation, `field_match_score`, fallback automation, provider default changes, ExcelExporter changes, Processing History schema changes, and PDF PaddleOCR handling remain out of scope.
- [x] Default pytest does not call real Azure or real PaddleOCR execution.
## Week 10-C Azure vs PaddleOCR Side-by-side Report

- [x] Side-by-side report utility compares only `StandardOCRResult`, `StandardOCRParserContext`, and parsed `ReceiptRecord` output.
- [x] Provider failure details use sanitized `diagnostic_detail_code` categories only, not raw provider messages or payloads.
- [x] Settings UI requires an explicit single-image upload and button press before Azure/PaddleOCR execution.
- [x] Provider summary includes per-sample elapsed time, status, diagnostic code, text block count, candidate count, review hint count, sensitive category count, warning count, full-result low-confidence count, and redacted count.
- [x] Core `ReceiptRecord` field rows include Azure/Paddle values plus `azure_present`, `paddle_present`, and `is_same` flags for Week 10-D reuse.
- [x] Default provider flow, ExcelExporter sheets/columns, and Processing History DB schema are unchanged.
- [x] No raw provider output, full OCR text, raw JSON, full local paths, Azure endpoint URLs, operation URLs, secrets, raw tracebacks, customer files, or raw OCR fixtures are added.
- [x] No default pytest path calls real Azure or real PaddleOCR.
- [ ] Week 10-D statistics, formal score, aggregate fallback criteria, and fallback recommendation rules remain unimplemented by design.

## Week 10-D-prep Synthetic PaddleOCR Quality Fixtures

- [x] Synthetic PaddleOCR fixture README added.
- [x] Synthetic cases added with safe `synthetic_` sample ids and file names.
- [x] Fixture lines are sanitized `paddle_lines`, not provider raw output.
- [x] Expected baselines compare selected `ReceiptRecord` core fields only.
- [x] Forbidden payload keys and strings are checked in fixture, standard result, parser context, and parsed record output.
- [x] Sensitive scenarios use `[REDACTED]` and safe category names only.
- [x] Basic merchant/date/business/payment/labeled-amount/VAT cases are covered.
- [x] Discount, zero-payment, OCR amount correction, amount spacing, low confidence, approval-number noise, quantity noise, and footer-number noise cases are covered.
- [x] Card-sales slip sample pattern is covered with business-block merchant extraction and split total/supply/VAT label-value lines.
- [x] Rotated receipt-style split `매출일` and `매장명` label-value lines are covered without customer image fixtures.
- [x] Unlabeled same-line merchant segments before valid business numbers are covered with synthetic fixtures.
- [x] Compact `YYYYMMDD` approval date-time lines are covered without treating approval numbers as dates.
- [x] Saved Azure-anchor core fields are tested without a live Azure call.
- [x] Default pytest does not call live Azure.
- [x] Default pytest does not import or execute real PaddleOCR.
- [x] ExcelExporter sheets/columns, Processing History schema, default provider, automatic fallback, formal score, and statistics UI remain unchanged.

## Review UX Quality Triage

- [x] Review table shows manual triage columns for priority, missing fields, and quality-check flags.
- [x] Review screen supports status and issue filters without dropping hidden rows when edits are saved.
- [x] Selected-receipt detail panel shows only safe parsed fields and source file names.
- [x] Detail and table views do not expose provider raw output, full OCR text, raw JSON, full local paths, secrets, or endpoint URLs.
- [x] ExcelExporter sheets/columns, Processing History schema, default provider, automatic fallback, formal score, and statistics UI remain unchanged.

## New Job PaddleOCR Runtime Selection

- [x] New Job per-run OCR provider selector includes `PaddleOCR Local`.
- [x] Configured default OCR provider remains unchanged.
- [x] PaddleOCR Local shows a per-run CPU/GPU execution option with CPU as the default.
- [x] GPU mode uses safe Paddle CUDA/device diagnostics and blocks the run when CUDA is unavailable.
- [x] `paddle` and `paddleocr` selections resolve as explicit runtime overrides.
- [x] `StandardOCRResult` provider output is parsed through `StandardOCRParserContext`.
- [x] The UI and processing result use source file names only, not full local paths.
- [x] Provider raw output, full OCR text, raw JSON, secrets, endpoint URLs, and raw tracebacks are not displayed.
- [x] PaddleOCR PDF handling remains unsupported/deferred.
- [x] Default pytest does not run real PaddleOCR or download OCR models.
- [x] ExcelExporter sheets/columns and Processing History schema remain unchanged.

## PaddleOCR Speed Pass

- [x] PaddleOCR engine instance is reused within one provider instance.
- [x] Standard OCR parser context builds the candidate map once before splitting amount and non-amount candidates.
- [x] Repeated compact line normalization uses a bounded cache.
- [x] No quality-reducing shortcut disables normalization fallback, candidate hints, parser checks, validation, or review-required behavior.
- [x] Default pytest still does not run real PaddleOCR or download OCR models.
- [x] ExcelExporter sheets/columns, Processing History schema, default provider, automatic fallback, and formal score remain unchanged.

## Review UI Receipt Source Preview

- [x] Review table includes review priority, missing fields, review-reason summary, source file name, and source preview status.
- [x] Review priority uses HIGH, MEDIUM, and LOW labels.
- [x] Missing fields show core field names such as `transaction_date`, `merchant_name`, `total_amount`, and `expense_category`.
- [x] Default review table order is HIGH, then MEDIUM, then LOW while preserving original order within each priority.
- [x] Selected receipt id and selected row number are stored in session state.
- [x] Selected row is highlighted in a read-only selection table.
- [x] JPG/JPEG/PNG source files under the upload root can be previewed with `st.image`.
- [x] PDF source files show a safe PDF notice without forced rendering.
- [x] Source preview blocks path traversal and files outside `data/uploads`.
- [x] Full local paths, OCR raw text, provider raw JSON, and sensitive raw values are not displayed.
- [x] Existing review editing, exclusion, Excel export, and Processing History flows remain unchanged.

## Merchant Candidate Dictionary

- [x] `merchant_master`, `merchant_alias`, and `merchant_source_log` tables are created without changing existing receipt/export schemas.
- [x] Public store CSV import stores allowed summary fields only.
- [x] Representative names, phone raw values, full OCR text, provider raw JSON, and full local paths are not stored by merchant import or matching.
- [x] Merchant name normalization handles whitespace, symbols, and common legal entity labels.
- [x] Business-number normalization accepts only 10 digits and formats `000-00-00000`.
- [x] Business-number exact match is ranked before fuzzy name candidates.
- [x] Alias candidates are returned as review hints.
- [x] Candidates do not automatically overwrite `ReceiptRecord.merchant_name`, `business_number`, or `review_status`.
- [x] Review UI candidate columns are read-only hints.
- [x] NTS business status client reads the API key from `.env` and safely skips when the key is missing.
- [x] NTS lookup is limited to OCR-detected business-number status checks and does not implement mass collection, true-name verification, or tax judgment.
- [x] ExcelExporter sheets/columns remain unchanged and candidate details are not exported.
- [x] CSV import reads only `상호명`, `지점명`, category, road name, building number, building name, and road-address columns.
- [x] CSV import supports UTF-8/UTF-8 BOM by default and CP949 as an exception path.
- [x] Same allowed-column file content is skipped as a duplicate file.
- [x] Same allowed-column row content is skipped as a duplicate row.
- [x] Road-address hints can boost merchant candidate scores without automatic confirmation.
- [x] Structured address-only matches can be shown as low-score review candidates when merchant/business-number fields are missing.
- [x] OCR safe lines can provide transient road-address hints for candidate scoring without changing `ReceiptRecord` or Excel output.
- [x] Phone, representative, business-number, approval/card, amount, and date lines are not treated as address hints.
- [x] Settings UI can import multiple merchant CSV files sequentially and displays only file-name/count/batch summaries.
- [x] Settings UI and Streamlit config allow merchant CSV uploads up to 400MB per file and reject larger files safely.
- [x] `data/gov` and `govdata` public CSV originals are excluded from Git.
- [x] Public merchant CSV import reports scanned/imported/skipped counts, duplicate-file status, elapsed seconds, and rows per second.
- [x] Public merchant CSV import uses chunked SQLite bulk inserts inside one import transaction.
- [x] Duplicate rows are skipped through allowed-column row hashes without per-row DB SELECT checks.
- [x] Duplicate files are skipped by allowed-column file hash before the second import pass.
- [x] CLI and Settings import summaries show only file names and safe counts, not full paths or raw CSV rows.
- [x] Reviewed merchant names can be accumulated in `merchant_alias` as `source=review`.
- [x] Review alias learning skips empty, too-short, mostly numeric, business-number, phone, representative, amount, date, card, and approval-like values.
- [x] Repeated review saves do not duplicate the same `normalized_alias_name + business_number + source` alias.
- [x] Alias learning failure does not block Excel generation or review save flow.
- [x] Alias learning does not store raw OCR text, provider raw JSON, full local paths, representative names, phone raw values, or full addresses.
- [x] Learned aliases remain review candidates and do not automatically overwrite `ReceiptRecord` fields.
- [x] Merchant dictionary diagnostics run only after an explicit button action.
- [x] Dictionary diagnostics show safe counts, latest file name, top categories, and recent batch summaries without full paths.
- [x] Candidate diagnostics mask business numbers and keep `review_required=True`.
- [x] Saved ReceiptRecord diagnostics use only merchant name, business number, source file name, and review status.
- [x] Diagnostic output excludes raw OCR text, provider raw JSON, phone raw values, representative names, raw CSV rows, full local paths, API keys, and tracebacks.
- [x] Merchant diagnostics do not change ExcelExporter sheets/columns, Processing History schema, or `ReceiptRecord` values.
- [x] Review source selection does not repeatedly re-query the same merchant candidates within a Streamlit session.
## Merchant Dictionary Search Quality Check

- [x] Settings merchant dictionary search requires a merchant-name query or road-name plus building-number query.
- [x] Search result rows show safe summaries only and do not include full local paths, raw CSV rows, phone raw values, representative names, OCR raw text, provider raw JSON, or full business numbers.
- [x] Review selected-row source preview renders only the selected row summary instead of styling the full review dataframe.
- [x] Short public-store substring candidates need address support before they pass the fuzzy threshold.
- [x] Address-only candidates remain low-score review hints and never overwrite `ReceiptRecord`.

## Quality Stabilization and Safe Diagnostics

- [x] Real PaddleOCR sample checks are manual/opt-in only and are not included in default pytest.
- [x] Key 25/26 samples were visually checked one by one and compared against current parser output with safe summaries only.
- [x] Existing Processing History rows are distinguished from latest-code reprocessing results.
- [x] Processing History safety diagnostics count forbidden columns and path-like values without displaying raw values.
- [x] Review UI performance summary includes dataframe generation, candidate lookup/cache, and preview preparation timing.
- [x] Source preview thumbnail fallback does not expose full local paths when image loading fails.
- [x] Settings merchant dictionary search uses bounded queries and default limit 50.
- [x] Merchant DB search summaries show allowed fields only and exclude raw OCR, provider raw JSON, raw CSV rows, phone raw values, representative names, full local paths, and full business numbers.
- [x] No ReceiptRecord schema, ExcelExporter sheet/column, Processing History schema, default provider, NTS automatic call, or OpenAI automatic correction change was introduced.

## 2026-10-19 정보 전달·후보 재검토

- [x] 연락처 마스킹 후 같은 줄 상호·사업자 보존 합성 회귀
- [x] 제목/상호 분리, 짧은 지점명 조각의 보수적 처리
- [x] 기존 총액의 명시 근거 비교, 원본 행 재인식, 0/누락 구분
- [x] 읽기 전용 사전 및 명시적 후보 선택 UI 테스트
- [x] 기본 테스트 1,043 통과 / 3 skip; V5 최종 88 통과
- [x] 실제 17건의 앱 함수·표·상세 입력·8시트 엑셀 136필드 전달 대조
- [x] 개발에 사용하지 않은 4장 별도 평가, 결과 확인 후 인식 코드 재조정 없음
- [x] 8502 V5 앱 재시작·GPU 시작 화면 확인, 8501 세션 유지
- [ ] 고정 평가 100% 및 남은 상호·금액·공급가액 오류 해결
- [ ] 실제 브라우저 업로드·팝업·엑셀 다운로드 전체 검증
- [ ] 로컬 문서 AI 효과/설치 부담 및 기본 모델 도입 검증

[수치와 리스크](docs/ocr_fieldflow_followup.md).

# 검수 화면 실제 적용 확인

2026-10-19. 사용자가 기존 화면이 그대로 보인다고 보고하여 실행 중인 앱을 확인했다.

## 1. 생성·수정 파일

생성: `tests/test_streamlit_media_runtime.py`, 이 문서.
수정: `requirements.txt`, README, CHECKLIST, CHANGE_CONTROL, `docs/review_ux_refinement.md`.
제품 Python 소스·기존 Parser/Provider/Exporter·DB는 이 후속 점검에서 수정하지 않았다.

## 2. 수행한 수정

실제 Chrome에서 합성 영수증과 Mock OCR로 기존 저장 메타데이터 표·행 하이라이트·중복 수정 표가 표시됨을 확인했다. 실행 중인 서버가 이전 모듈을 사용하고 있었다. 프로젝트 전용 실행기로 서버를 재시작한 뒤 통합 서식이 표시됐다. 기존 저장 파일과 DB는 유지되며 저장 전 세션 입력은 재시작으로 초기화될 수 있음을 안내했다.

실제 화면 검사에서 원본 미리보기 이미지가 깨지는 HTTP 500도 발견했다. Streamlit 1.60.0의 미디어 응답 처리와 설치된 Starlette 1.9.0의 압축 응답 순서가 맞지 않았다. 공통 requirements에 `starlette==1.7.0`을 고정하고 현재 `.venv-ocr` 환경의 해당 패키지만 변경했다. 웹 라이브러리 코드를 직접 패치하거나 접근 보호 설정을 해제하지 않았다.

## 3. 구조

기존 `st.image`와 메모리 미디어 경로를 유지한다. HTTP 응답 시작 메시지보다 이미지 본문이 먼저 전송되는 호환 오류를 의존성 제약으로 해결했다. 새로운 이미지 저장소·별도 정적 파일 공개 경로·OCR 구현은 추가하지 않았다. 기본 실행과 GPU 실행은 동일한 공통 requirements의 호환 제약을 사용한다.

공식 upstream 응답 처리 비교: [Starlette 1.7.0](https://github.com/Kludex/starlette/blob/1.7.0/starlette/middleware/gzip.py), [Starlette 1.8.0](https://github.com/Kludex/starlette/blob/1.8.0/starlette/middleware/gzip.py). 설치 환경의 동일 경로에서도 차이를 확인하고 회귀 테스트로 검증했다.

## 4. 테스트 명령

```powershell
.venv-ocr\Scripts\python.exe -m pip check
.venv-ocr\Scripts\python.exe -m compileall -q app tests
.venv-ocr\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short --disable-warnings
```

## 5. 테스트 결과

- 새 PNG/JPEG × identity/gzip HTTP 회귀 4개: 수정 전 모두 실패, 수정 후 모두 통과.
- compileall 통과, pip check 의존성 충돌 없음.
- 전체 pytest: **802 passed / 2 skipped / 100 warnings**, 33.56초. 실제 OCR opt-in 테스트는 실행하지 않았다.
- Python 3.11.9, Streamlit 1.60.0, CUDA 빌드 true 및 gpu:0 진단을 확인했다. Paddle 패키지·드라이버는 변경하지 않았다.
- 실제 Chrome에서 합성 원본 이미지 naturalWidth=700/naturalHeight=800 정상 로딩과 오른쪽 표준 서식을 확인했다. 저장 메타데이터 표·행 하이라이트·별도 수정 표·후보 점수·Review perf 표시가 사라졌다. 카드내역은 미업로드/미실행으로 표시된다.
- 표준 서식의 날짜·상호·사업자번호·할인·공급가액·부가세·최종결제금액·결제수단·중복의심, 접힌 상세정보와 검수값 저장을 확인했다. 업로드 영역의 파일명은 사용자가 업로드한 파일을 구별하기 위해 유지한다.
- 합성 Mock 작업의 검수 화면만 열었으며 엑셀 생성·처리 이력 DB 저장은 실행하지 않았다.

## 6. 문서 동기화

README에 변경 후 서버 재시작/새로고침 방법과 세션 초기화 주의점을 추가했다. CHECKLIST와 CHANGE_CONTROL에 실제 검증 결과를 기록하고 최초 구현 기록에서 이 문서를 연결했다. 제품 데이터 모델·엑셀 계약·업무 방향 변경은 없다.

## 7. 남은 리스크

실제 고객 영수증의 OCR 품질, PDF 미리보기와 모바일 기기는 이번 점검 대상이 아니다. 열어둔 검증 탭은 합성 파일을 Mock OCR로 처리한 화면이다. 새 작업에서 사용할 실제 OCR 방식은 사용자가 선택해야 한다. 기본 `.env`는 바꾸지 않았다.

웹 라이브러리를 올릴 때 새 미디어 HTTP 테스트를 실행해야 한다. AppTest 통과와 서버 health 200만으로 이미지의 실제 브라우저 로딩을 보증할 수 없었다. 서버 소스 변경 뒤 기존 화면이 남으면 종료/실행 파일로 재시작한다. 저장 전 검수 입력이 초기화될 수 있다.

## 8. 추천 커밋 메시지

`fix: pin compatible media response runtime for receipt previews`

이번 점검에서는 커밋·푸시를 수행하지 않았다.

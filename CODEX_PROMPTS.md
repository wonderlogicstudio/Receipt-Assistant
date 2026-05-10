# CODEX_PROMPTS.md

# Codex 요청 프롬프트 모음

이 문서는 Codex 또는 Claude Code에 그대로 붙여 넣을 수 있는 작업 요청서입니다.

사용자가 공유한 기존 명령 스타일을 기준으로 작성했습니다.

핵심 형식:

```text
이번 작업 목표:
작업 범위:
구현 조건:
테스트:
완료 기준:
이번 단계에서 하지 말 것:
완료 후 출력:
추천 커밋 메시지:
```

---

## 0. 공통 시작 프롬프트

```text
이 프로젝트는 “영수증 OCR 엑셀 비서”다.

목표는 영수증 이미지/PDF와 카드 사용내역 엑셀을 업로드하면 OCR API로 데이터를 추출하고, 사용자가 검수한 뒤 세무사 전달용 표준 엑셀과 월별 요약 시트를 다운로드할 수 있는 반자동 웹 도구를 만드는 것이다.

중요 원칙:
1. OCR 결과는 확정값이 아니라 검수 대상이다.
2. 비용항목은 확정이 아니라 추천이다.
3. 세무 신고, 공제 가능 여부, 자동 분개를 확정하지 않는다.
4. 원본 파일은 장기 보관하지 않는다.
5. 개인정보가 로그에 남지 않게 한다.
6. 엑셀 산출물이 제품의 핵심이다.
7. OpenAI API는 MVP 필수 의존성이 아니다.
8. 작업 중 README.md, PLAN.md, SPEC.md와 구현 방향이 달라지면 CHANGE_CONTROL.md 기준으로 변경 제안을 먼저 출력한다.

작업 전 README.md, PLAN.md, AGENTS.md, SPEC.md, CHECKLIST.md, GIT_WORKFLOW.md, CHANGE_CONTROL.md, DECISIONS.md를 읽고 현재 요구사항을 이해한 뒤 진행해라.
```

---

## 1. 문서 초기 세팅 요청

```text
이번 작업은 영수증 OCR 엑셀 비서 MVP의 문서 기반 개발 준비 단계다.

이번 작업 목표:
README.md, PLAN.md, AGENTS.md, SPEC.md, CHECKLIST.md, GIT_WORKFLOW.md, CHANGE_CONTROL.md, DECISIONS.md를 기준으로 프로젝트 방향을 이해하고, 실제 구현 전에 필요한 기본 파일을 세팅한다.

작업 범위:
- .gitignore
- requirements.txt
- .env.example
- app/ 폴더 기본 구조
- data/uploads/.gitkeep
- data/outputs/.gitkeep
- data/samples/.gitkeep
- tests/ 폴더 기본 구조

구현 조건:
1. README.md의 권장 폴더 구조를 따른다.
2. data/uploads와 data/outputs는 git에 원본 파일이 올라가지 않도록 .gitignore를 작성한다.
3. .env.example에는 실제 키를 넣지 않는다.
4. requirements.txt에는 4주 MVP에 필요한 최소 패키지만 넣는다.
5. 아직 Streamlit 화면 구현은 최소화한다.
6. 아직 실제 OCR API는 호출하지 않는다.
7. 아직 OpenAI API Provider는 구현하지 않는다.

테스트:
1. python -m compileall app tests 통과
2. python -m pytest 실행 가능 상태 확인

완료 기준:
1. 기본 폴더 구조 생성
2. requirements.txt 생성
3. .env.example 생성
4. .gitignore 생성
5. 빈 테스트 실행 가능

이번 단계에서 하지 말 것:
- 실제 OCR API 호출
- 홈택스/카드사 연동
- 로그인/결제 구현
- 모바일 앱 구현
- Excel exporter 본구현

완료 후 출력:
1. 생성/수정한 파일 목록
2. 폴더 구조 요약
3. 설치 명령어
4. 테스트 명령어
5. 테스트 결과
6. 추천 커밋 메시지

추천 커밋 메시지:
chore: initialize receipt OCR assistant project structure
```

---

## 2. 1주차-A: 파일 업로드와 안전 저장

```text
이번 작업은 1주차의 첫 번째 구현 단계다.

이번 작업 목표:
Streamlit에서 영수증 이미지/PDF와 카드 사용내역 엑셀/CSV 파일을 업로드하고, 안전한 파일명으로 세션별 폴더에 저장할 수 있게 한다.

작업 범위:
- app/main.py
- app/storage/file_store.py
- app/core/config.py
- tests/test_file_store.py
- 필요 시 app/core/exceptions.py

구현 조건:
1. Streamlit 메인 화면을 만든다.
2. 업로드 허용 확장자는 jpg, jpeg, png, pdf, xlsx, csv로 제한한다.
3. 파일명 sanitize 함수를 구현한다.
4. 파일은 data/uploads/{session_id}/ 아래 저장한다.
5. 저장된 파일에는 원본 파일명과 저장 파일명을 매핑할 수 있어야 한다.
6. 파일 크기 제한 설정값을 config에서 관리한다.
7. 허용되지 않은 확장자는 예외 처리한다.
8. 원본 파일 전체 경로를 화면에 노출하지 않는다.
9. 개인정보성 파일 내용은 로그에 출력하지 않는다.

테스트:
1. 정상 파일명이 안전하게 변환되는지 확인
2. 위험한 파일명(../, 특수문자 등)이 안전하게 처리되는지 확인
3. 허용 확장자만 저장되는지 확인
4. 비허용 확장자는 예외가 발생하는지 확인
5. session_id별 폴더가 분리되는지 확인

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest tests/test_file_store.py 통과
3. Streamlit 화면에서 파일 업로드 가능

이번 단계에서 하지 말 것:
- OCR API 호출
- Parser 구현
- Excel exporter 구현
- 로그인/결제 구현
- 모바일 전용 UI 구현

완료 후 출력:
1. 생성/수정한 파일 목록
2. FileStore 구조
3. 파일명 sanitize 기준
4. 보안상 주의사항
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add file upload and safe local storage
```

---

## 3. 1주차-B: OCR Provider 인터페이스와 Mock OCR

```text
이번 작업은 1주차의 두 번째 구현 단계다.

이번 작업 목표:
실제 OCR API에 바로 의존하지 않도록 OCRProvider 인터페이스와 MockOCRProvider를 구현한다.

작업 범위:
- app/ocr/base.py
- app/ocr/mock_provider.py
- app/core/models.py 또는 app/core/ocr_models.py
- tests/test_mock_ocr_provider.py
- 필요 시 app/core/enums.py

구현 조건:
1. OCRProvider 추상 클래스를 만든다.
2. extract(file_path: str) -> OCRResult 형태의 인터페이스를 제공한다.
3. OCRResult에는 최소 아래 필드를 포함한다.
   - id
   - source_file_id
   - provider
   - raw_text
   - raw_json
   - confidence
   - status
   - error_message
   - created_at
4. MockOCRProvider는 실제 API 호출 없이 샘플 OCR 결과를 반환한다.
5. MockOCRProvider는 파일 확장자에 따라 성공/실패 케이스를 테스트할 수 있어야 한다.
6. OCR 실패 시 status=failed와 error_message를 반환한다.
7. OCR 원문을 로그에 출력하지 않는다.

테스트:
1. MockOCRProvider가 정상 OCRResult를 반환하는지 확인
2. provider 값이 mock으로 저장되는지 확인
3. 실패 케이스에서 status=failed가 되는지 확인
4. OCRResult 필수 필드가 채워지는지 확인

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest tests/test_mock_ocr_provider.py 통과
3. 기존 테스트가 깨지지 않아야 함

이번 단계에서 하지 말 것:
- 실제 OCR API 호출
- OpenAI API 호출
- Parser 구현
- Excel exporter 구현
- 검수 UI 구현

완료 후 출력:
1. 생성/수정한 파일 목록
2. OCRProvider 구조
3. OCRResult 구조
4. MockOCRProvider 동작 방식
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add OCR provider interface and mock provider
```

---

## 4. 1주차-C: 카드 사용내역 파서

```text
이번 작업은 1주차의 세 번째 구현 단계다.

이번 작업 목표:
카드 사용내역 엑셀 또는 CSV를 업로드하면 표준 CardTransaction 데이터로 변환할 수 있게 한다.

작업 범위:
- app/parser/card_statement_parser.py
- app/parser/normalizers.py
- app/core/models.py
- tests/test_card_statement_parser.py
- 필요 시 data/samples/sample_card_statement.csv

구현 조건:
1. CardTransaction 모델을 구현한다.
2. 카드 사용내역 파일의 컬럼명이 서로 달라도 표준 컬럼으로 매핑할 수 있게 한다.
3. 최소 표준 컬럼은 아래와 같다.
   - transaction_date
   - merchant_name
   - total_amount
   - card_name
   - approval_number
   - source_file_name
4. 날짜 정규화 함수를 구현한다.
5. 금액 정규화 함수를 구현한다.
6. 쉼표, 원, 공백이 포함된 금액도 숫자로 변환한다.
7. 필수 컬럼이 부족하면 명확한 예외를 발생시킨다.
8. 테스트용 샘플에는 실제 개인정보를 넣지 않는다.

테스트:
1. CSV 카드내역을 표준 DataFrame으로 변환하는지 확인
2. XLSX 카드내역을 표준 DataFrame으로 변환하는지 확인
3. 금액 문자열이 int로 변환되는지 확인
4. 날짜 문자열이 date로 변환되는지 확인
5. 필수 컬럼이 없으면 예외가 발생하는지 확인

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest tests/test_card_statement_parser.py 통과
3. 1주차 기존 테스트가 깨지지 않아야 함

이번 단계에서 하지 말 것:
- OCR Parser 구현
- 카드사 API 연동
- Excel exporter 구현
- 검수 UI 구현
- 결제/로그인 구현

완료 후 출력:
1. 생성/수정한 파일 목록
2. CardTransaction 모델 구조
3. 카드 컬럼 매핑 기준
4. 정규화 규칙
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add card statement parser
```

---

## 5. 2주차-A: ReceiptRecord 모델과 OCR Parser

```text
이번 작업은 2주차의 첫 번째 구현 단계다.

이번 작업 목표:
Mock OCR 결과 또는 OCR 원문을 표준 ReceiptRecord로 변환하는 Parser를 구현한다.

작업 범위:
- app/core/models.py
- app/core/enums.py
- app/parser/receipt_parser.py
- app/parser/normalizers.py
- tests/test_receipt_parser.py

구현 조건:
1. ReceiptRecord 모델을 추가한다.
2. ReceiptRecord에는 SPEC.md의 필드를 반영한다.
3. EvidenceType, ReviewStatus, CardMatchStatus enum을 추가한다.
4. OCR raw_text에서 날짜, 상호, 총액, 부가세, 사업자번호를 추출하는 기본 Parser를 구현한다.
5. Parser는 완벽할 필요 없지만 실패 시 검토필요 상태로 넘겨야 한다.
6. 날짜/금액/사업자번호 정규화는 별도 함수로 분리한다.
7. total_amount가 없으면 review_status=needs_review가 되어야 한다.
8. merchant_name이 없으면 review_status=needs_review가 되어야 한다.

테스트:
1. 샘플 OCR raw_text가 ReceiptRecord로 변환되는지 확인
2. 금액 문자열이 정수로 변환되는지 확인
3. 날짜 문자열이 date로 변환되는지 확인
4. 필수값 누락 시 needs_review가 되는지 확인
5. OCR 원문이 있어도 로그에 출력하지 않는지 확인 가능한 구조인지 검토

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest tests/test_receipt_parser.py 통과
3. 기존 테스트가 깨지지 않아야 함

이번 단계에서 하지 말 것:
- 실제 OCR API 호출
- LLM/OpenAI 보정 구현
- Excel exporter 구현
- 세무 판단 로직 구현

완료 후 출력:
1. 생성/수정한 파일 목록
2. ReceiptRecord 모델 구조
3. Parser 동작 방식
4. 정규화 규칙
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add receipt record model and OCR parser
```

---

## 6. 2주차-B: 검증 규칙과 비용항목 추천

```text
이번 작업은 2주차의 두 번째 구현 단계다.

이번 작업 목표:
ReceiptRecord에 대해 필수값 누락, 금액 불일치, 부가세 미확인, 비용항목 추천을 처리한다.

작업 범위:
- app/validator/receipt_validator.py
- app/classifier/category_rules.py
- app/classifier/merchant_dictionary.py
- tests/test_receipt_validator.py
- tests/test_category_rules.py
- 필요 시 app/core/models.py

구현 조건:
1. ReceiptValidator 클래스를 구현한다.
2. 날짜, 상호, 총액 누락 시 review_status=needs_review가 되게 한다.
3. supply_amount + vat_amount와 total_amount가 불일치하면 review_reasons에 금액불일치를 추가한다.
4. vat_amount가 없으면 부가세미확인을 review_reasons에 추가한다.
5. CategoryRules 클래스를 구현한다.
6. 상호명/키워드 기반으로 추천비용항목을 설정한다.
7. 추천비용항목은 확정값이 아니라 추천값으로만 저장한다.
8. 분류할 수 없으면 미분류로 둔다.
9. 세무 신고, 공제 가능 여부, 자동 분개 확정 표현을 코드/문서/UI에 넣지 않는다.

테스트:
1. 필수값 누락 검증 확인
2. 금액 불일치 검증 확인
3. 부가세 미확인 검증 확인
4. 상호명 기반 비용항목 추천 확인
5. 미분류 처리 확인

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest tests/test_receipt_validator.py tests/test_category_rules.py 통과
3. 기존 테스트가 깨지지 않아야 함

이번 단계에서 하지 말 것:
- 자동 분개 구현
- 세무 공제 가능 여부 판단
- OpenAI API 호출
- Excel exporter 구현

완료 후 출력:
1. 생성/수정한 파일 목록
2. Validator 구조
3. 비용항목 추천 기준
4. 검토필요 처리 기준
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add receipt validation and category recommendation rules
```

---

## 7. 2주차-C: 중복 탐지와 카드 매칭

```text
이번 작업은 2주차의 세 번째 구현 단계다.

이번 작업 목표:
영수증 간 중복 의심 건을 탐지하고, 카드 사용내역과 영수증을 매칭한다.

작업 범위:
- app/validator/duplicate_checker.py
- app/validator/card_matcher.py
- tests/test_duplicate_checker.py
- tests/test_card_matcher.py
- 필요 시 app/core/models.py

구현 조건:
1. DuplicateChecker 클래스를 구현한다.
2. 날짜, 금액, 상호 유사도를 기준으로 중복 후보를 찾는다.
3. 중복은 확정하지 않고 중복의심 review_reason만 추가한다.
4. CardMatcher 클래스를 구현한다.
5. 카드내역과 영수증의 날짜, 금액, 상호명을 기준으로 매칭한다.
6. 매칭 상태는 matched, candidate, unmatched로 구분한다.
7. 날짜가 ±1일이고 금액이 같으면 candidate로 처리한다.
8. 매칭 결과가 ReceiptRecord.card_match_status에 반영되게 한다.

테스트:
1. 동일 날짜/금액/상호는 중복 후보로 표시되는지 확인
2. 비슷한 상호명도 후보로 잡히는지 확인
3. 완전 다른 건은 중복으로 표시되지 않는지 확인
4. 카드내역과 정확히 일치하면 matched가 되는지 확인
5. 날짜 ±1일이면 candidate가 되는지 확인
6. 후보가 없으면 unmatched가 되는지 확인

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest tests/test_duplicate_checker.py tests/test_card_matcher.py 통과
3. 기존 테스트가 깨지지 않아야 함

이번 단계에서 하지 말 것:
- 카드사 API 연동
- 카드 승인내역 자동 조회
- 자동 확정 처리
- Excel exporter 구현

완료 후 출력:
1. 생성/수정한 파일 목록
2. DuplicateChecker 구조
3. CardMatcher 구조
4. 매칭 기준
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add duplicate detection and card matching
```

---

## 8. 3주차-A: 검수 UI

```text
이번 작업은 3주차의 첫 번째 구현 단계다.

이번 작업 목표:
Streamlit 화면에서 OCR/Parser 결과를 사용자가 검수하고 수정할 수 있게 한다.

작업 범위:
- app/main.py
- app/ui/review_view.py
- app/ui/summary_view.py
- 필요 시 app/core/models.py
- tests는 가능한 범위에서 유틸 함수 중심으로 작성

구현 조건:
1. 업로드 후 ReceiptRecord 목록을 테이블로 표시한다.
2. 사용자가 사용일자, 상호, 금액, 부가세, 추천비용항목, 검수상태, 비고를 수정할 수 있게 한다.
3. 검수상태는 확인완료, 검토필요, 제외 중 선택한다.
4. 검토사유를 화면에서 볼 수 있어야 한다.
5. 카드매칭 상태를 화면에서 볼 수 있어야 한다.
6. 원본 파일명은 표시하되 전체 로컬 경로는 표시하지 않는다.
7. OCR 원문은 필요 시 접었다 펼칠 수 있게 하되 기본 노출은 최소화한다.

테스트:
1. UI 함수 중 데이터 변환 로직은 테스트한다.
2. 검수상태 변경이 데이터에 반영되는지 확인한다.
3. 제외 상태 데이터가 exporter에서 제외 가능하도록 구조화되어 있는지 확인한다.

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest 통과
3. Streamlit에서 검수 테이블 확인 가능

이번 단계에서 하지 말 것:
- 로그인/권한관리
- 모바일 전용 UI
- 결제 기능
- 실제 OCR API 추가

완료 후 출력:
1. 생성/수정한 파일 목록
2. 검수 UI 구조
3. 수정 가능한 컬럼 목록
4. 검토필요 표시 방식
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add receipt review UI
```

---

## 9. 3주차-B: Excel Exporter

```text
이번 작업은 3주차의 두 번째 구현 단계다.

이번 작업 목표:
검수된 ReceiptRecord와 CardTransaction을 기반으로 세무사 전달용 표준 엑셀 파일을 생성한다.

작업 범위:
- app/exporter/excel_exporter.py
- tests/test_excel_exporter.py
- 필요 시 app/core/models.py
- 필요 시 docs/sample_output_schema.md

구현 조건:
1. ExcelExporter 클래스를 구현한다.
2. 출력 파일은 .xlsx 형식이어야 한다.
3. 필수 시트를 생성한다.
   - 01_정리내역
   - 02_월별요약
   - 03_비용항목별요약
   - 04_검토필요
   - 05_카드대조
   - 06_원본파일목록
   - 07_OCR원문
4. 01_정리내역에는 SPEC.md의 표준 컬럼을 반영한다.
5. 제외 상태의 건은 별도 처리하거나 정리내역에서 구분한다.
6. 금액 컬럼은 숫자 형식으로 저장한다.
7. 날짜 컬럼은 yyyy-mm-dd 형식으로 저장한다.
8. 원본파일목록에는 전체 로컬 경로를 넣지 않는다.
9. 검토필요 시트에는 review_status=needs_review 또는 review_reasons가 있는 건을 출력한다.
10. Excel 파일이 실제로 열릴 수 있어야 한다.

테스트:
1. Excel 파일이 생성되는지 확인
2. 필수 시트가 모두 있는지 확인
3. 01_정리내역 컬럼이 SPEC.md와 일치하는지 확인
4. 월별요약 합계가 맞는지 확인
5. 검토필요 건이 04_검토필요에 들어가는지 확인
6. 전체 로컬 경로가 엑셀에 포함되지 않는지 확인

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest tests/test_excel_exporter.py 통과
3. 기존 테스트가 깨지지 않아야 함

이번 단계에서 하지 말 것:
- PDF 보고서 생성
- PPT 생성
- 이메일 발송
- 세무 신고 파일 생성
- 회계 프로그램 API 연동

완료 후 출력:
1. 생성/수정한 파일 목록
2. ExcelExporter 구조
3. 생성되는 시트 목록
4. 주요 컬럼 목록
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add standard excel exporter
```

---

## 10. 3주차-C: 다운로드 흐름 연결

```text
이번 작업은 3주차의 세 번째 구현 단계다.

이번 작업 목표:
Streamlit 검수 화면에서 사용자가 최종 엑셀 파일을 다운로드할 수 있도록 전체 흐름을 연결한다.

작업 범위:
- app/main.py
- app/ui/review_view.py
- app/exporter/excel_exporter.py
- app/storage/file_store.py
- tests/test_end_to_end_export_flow.py

구현 조건:
1. 업로드된 파일이 Mock OCR을 거쳐 ReceiptRecord로 변환된다.
2. 사용자가 검수 화면에서 데이터를 수정할 수 있다.
3. 수정된 데이터로 ExcelExporter를 호출한다.
4. 사용자가 웹에서 .xlsx 파일을 다운로드할 수 있다.
5. 다운로드 파일명은 receipt_summary_YYYYMMDD_HHMMSS.xlsx 형식을 따른다.
6. 다운로드 후 원본 파일 삭제는 아직 자동으로 하지 말고, cleanup 함수만 준비한다.

테스트:
1. 샘플 OCR 결과로 엑셀 파일 생성까지 흐름이 동작하는지 확인
2. 수정된 검수 데이터가 엑셀에 반영되는지 확인
3. 다운로드 파일명이 규칙을 따르는지 확인

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest 통과
3. Streamlit에서 업로드→검수→다운로드 흐름이 동작

이번 단계에서 하지 말 것:
- 실제 OCR API 연결
- 로그인/결제 구현
- 모바일 전용 기능
- 홈택스/카드사 연동

완료 후 출력:
1. 생성/수정한 파일 목록
2. 전체 흐름 설명
3. 다운로드 파일명 규칙
4. 테스트 명령어
5. 테스트 결과
6. 추천 커밋 메시지

추천 커밋 메시지:
feat: connect review flow to excel download
```

---

## 11. 4주차-A: 실제 OCR Provider 1개 연결

```text
이번 작업은 4주차의 첫 번째 구현 단계다.

이번 작업 목표:
Mock OCR 외에 실제 OCR API Provider 1개를 연결한다. 우선 CLOVA OCR 또는 Azure Document Intelligence 중 하나만 구현한다.

작업 범위:
- app/ocr/clova_provider.py 또는 app/ocr/azure_provider.py
- app/ocr/provider_factory.py
- app/core/config.py
- .env.example
- tests/test_ocr_provider_factory.py
- 필요 시 tests/test_clova_provider.py 또는 tests/test_azure_provider.py

구현 조건:
1. OCR Provider는 환경변수로 선택할 수 있어야 한다.
2. 기본값은 mock이어야 한다.
3. 실제 OCR API key는 .env에서 읽는다.
4. API key를 코드에 하드코딩하지 않는다.
5. API 호출 실패, 타임아웃, 잘못된 응답을 안전하게 처리한다.
6. 실제 API 통합 테스트는 기본 pytest에서 자동 실행되지 않도록 한다.
7. 원본 파일 내용과 OCR 원문을 로그에 출력하지 않는다.
8. Provider 응답은 OCRResult로 변환한다.

테스트:
1. provider_factory가 mock provider를 반환하는지 확인
2. 환경변수에 따라 실제 provider 객체를 생성하는지 확인
3. API key가 없으면 명확한 설정 오류가 발생하는지 확인
4. 실패 응답이 OCRResult(status=failed) 또는 명확한 예외로 처리되는지 확인

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest 통과
3. 기본 테스트가 실제 API 키 없이도 통과해야 함

이번 단계에서 하지 말 것:
- OpenAI API 보정 구현
- OCR Provider 여러 개 동시 구현
- 대량 배치 처리
- 모바일 카메라 업로드
- 결제 기능

완료 후 출력:
1. 생성/수정한 파일 목록
2. OCR Provider 선택 구조
3. 필요한 환경변수
4. API 실패 처리 기준
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add configurable OCR provider integration
```

---

## 12. 4주차-B: 파일 정리와 보관기간 제어

```text
이번 작업은 4주차의 두 번째 구현 단계다.

이번 작업 목표:
업로드 원본 파일과 출력 파일을 안전하게 정리할 수 있는 cleanup 기능을 구현한다.

작업 범위:
- app/storage/cleanup.py
- app/storage/file_store.py
- app/core/config.py
- tests/test_cleanup.py
- README.md 또는 CHECKLIST.md 필요 시 수정

구현 조건:
1. 업로드 파일 보관 기간을 설정값으로 관리한다.
2. 지정 기간이 지난 업로드 파일을 삭제하는 함수를 구현한다.
3. 지정 기간이 지난 출력 파일을 삭제하는 함수를 구현한다.
4. 삭제 대상 경로는 data/uploads, data/outputs 하위로 제한한다.
5. 경로 traversal 위험을 방지한다.
6. 삭제 결과는 개인정보 없이 파일 수와 상태만 기록한다.
7. 사용자가 수동 삭제를 실행할 수 있는 함수 구조를 둔다.

테스트:
1. 보관 기간이 지난 파일이 삭제되는지 확인
2. 보관 기간 이내 파일은 삭제되지 않는지 확인
3. data/uploads 밖 경로 삭제가 차단되는지 확인
4. 삭제 결과가 요약값으로 반환되는지 확인

완료 기준:
1. python -m compileall app tests 통과
2. python -m pytest tests/test_cleanup.py 통과
3. 기존 테스트가 깨지지 않아야 함

이번 단계에서 하지 말 것:
- 클라우드 스토리지 삭제 구현
- 사용자 계정별 보관 정책 구현
- 결제 플랜별 보관 정책 구현

완료 후 출력:
1. 생성/수정한 파일 목록
2. cleanup 구조
3. 보관기간 설정값
4. 삭제 안전장치
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
feat: add upload and output cleanup controls
```

---

## 13. 4주차-C: 파일럿 준비 문서와 최종 점검

```text
이번 작업은 4주차의 세 번째 작업이며 MVP 파일럿 전 최종 점검 단계다.

이번 작업 목표:
개발된 MVP를 실제 사용자에게 테스트할 수 있도록 문서, 체크리스트, 샘플 사용 흐름을 정리한다.

작업 범위:
- README.md
- PLAN.md
- CHECKLIST.md
- docs/pilot_guide.md
- docs/interview_questions.md
- docs/sample_user_flow.md
- 필요 시 DECISIONS.md

구현 조건:
1. README.md의 실행 방법이 실제 코드와 일치해야 한다.
2. PLAN.md의 완료/미완료 기능을 최신화한다.
3. CHECKLIST.md의 4주차 항목을 최신화한다.
4. pilot_guide.md에는 파일럿 대상, 준비물, 테스트 절차, 성공 기준을 작성한다.
5. interview_questions.md에는 세무사, 1인 사업자, 소상공인용 질문을 나눠 작성한다.
6. sample_user_flow.md에는 업로드→검수→다운로드 단계별 화면 흐름을 정리한다.
7. 코드 변경은 최소화하고 문서 중심으로 작업한다.

테스트:
1. python -m compileall app tests 통과
2. python -m pytest 통과
3. README 실행 명령이 맞는지 확인

완료 기준:
1. 파일럿 가이드 작성 완료
2. 인터뷰 질문지 작성 완료
3. 사용자 흐름 문서 작성 완료
4. 전체 테스트 통과
5. 문서와 코드 불일치 없음

이번 단계에서 하지 말 것:
- 신규 기능 추가
- OCR Provider 추가
- 모바일 앱 구현
- 결제 기능 구현
- 홈택스/카드사 연동

완료 후 출력:
1. 생성/수정한 파일 목록
2. 파일럿 진행 방식
3. 인터뷰 질문 요약
4. 현재 MVP 사용 방법
5. 테스트 명령어
6. 테스트 결과
7. 추천 커밋 메시지

추천 커밋 메시지:
docs: prepare pilot guide and MVP validation checklist
```

---

## 14. 문서 동기화 요청 프롬프트

```text
이번 작업은 코드 구현이 아니라 문서 동기화 점검이다.

이번 작업 목표:
현재 코드 상태와 README.md, PLAN.md, SPEC.md, CHECKLIST.md, AGENTS.md가 서로 일치하는지 확인하고 필요한 문서 수정안을 제안한다.

작업 범위:
- README.md
- PLAN.md
- SPEC.md
- CHECKLIST.md
- AGENTS.md
- DECISIONS.md
- CHANGE_CONTROL.md

검토 조건:
1. README.md의 실행 방법이 실제 파일 구조와 맞는지 확인한다.
2. PLAN.md의 완료 기능과 실제 구현이 맞는지 확인한다.
3. SPEC.md의 데이터 모델과 코드 모델이 맞는지 확인한다.
4. SPEC.md의 엑셀 시트와 ExcelExporter 구현이 맞는지 확인한다.
5. CHECKLIST.md의 체크 항목이 현재 단계에 맞는지 확인한다.
6. 방향 변경이 있었으면 DECISIONS.md에 기록되어 있는지 확인한다.

완료 기준:
1. 불일치 목록 출력
2. 수정이 필요한 문서 목록 출력
3. 문서 수정이 필요한 경우 수정 적용
4. 코드 변경은 하지 않음

이번 단계에서 하지 말 것:
- 코드 기능 추가
- 테스트 로직 변경
- MVP 범위 변경

완료 후 출력:
1. 검토한 문서 목록
2. 발견한 불일치
3. 수정한 문서 목록
4. 남은 이슈
5. 추천 커밋 메시지

추천 커밋 메시지:
docs: synchronize MVP documentation with implementation
```

---

## 15. 안전한 커밋 요청 프롬프트

```text
현재 변경사항을 커밋하기 전에 점검해줘.

작업 목표:
테스트를 실행하고, 커밋해도 되는 변경인지 확인한 뒤 추천 커밋 메시지를 제시한다.

작업 범위:
- git status
- git diff --stat
- python -m compileall app tests
- python -m pytest

조건:
1. 테스트가 실패하면 커밋하지 말고 실패 원인을 요약해라.
2. .env, data/uploads, data/outputs, 실제 영수증 파일이 포함되어 있으면 커밋하지 마라.
3. 문서 변경이 필요한 코드 변경인지 확인해라.
4. 커밋은 사용자가 명시적으로 요청한 경우에만 수행해라.

완료 후 출력:
1. git status 요약
2. git diff --stat 요약
3. 테스트 결과
4. 커밋 가능 여부
5. 제외해야 할 파일이 있는지 여부
6. 추천 커밋 메시지
```

---

## 16. 자동 커밋까지 맡길 때의 프롬프트

```text
테스트가 통과하면 이번 작업 범위에 해당하는 파일만 git commit까지 수행해줘.

조건:
1. 먼저 git status와 git diff --stat을 보여줘.
2. python -m compileall app tests를 실행해라.
3. python -m pytest를 실행해라.
4. 테스트가 실패하면 절대 커밋하지 마라.
5. .env, data/uploads, data/outputs, 실제 고객 파일은 절대 커밋하지 마라.
6. 이번 작업 범위와 무관한 파일은 커밋하지 마라.
7. 커밋 메시지는 아래 메시지를 사용해라.

커밋 메시지:
<여기에 커밋 메시지 입력>

완료 후 출력:
1. 실행한 테스트 명령어
2. 테스트 결과
3. 커밋 해시
4. 커밋에 포함된 파일 목록
5. 남은 변경사항 여부
```

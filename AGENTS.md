# AGENTS.md

# Coding Agent Instructions

이 파일은 Codex, Claude Code, Cursor 등 AI 코딩 에이전트가 이 프로젝트를 수정할 때 반드시 따라야 할 기준입니다.

---

## 1. Project Context

프로젝트명: 영수증 OCR 엑셀 비서

목표:
영수증 이미지/PDF와 카드 사용내역 엑셀을 업로드하면 OCR API로 데이터를 추출하고, 사용자가 검수한 뒤 세무사 전달용 표준 엑셀 파일과 월별 요약 시트를 다운로드할 수 있는 반자동 웹 도구를 만든다.

이 프로젝트는 전문가 판단 영역을 대신하는 서비스가 아니다. 증빙 정리 보조와 세무사 전달용 표준 엑셀 정리에 집중한다.

---

## 2. Non-Negotiable Product Rules

반드시 지켜야 할 규칙입니다.

1. OCR 결과는 항상 검수 대상이다.
2. 비용항목은 “추천”으로만 표시한다.
3. 증빙유형은 “추정”으로만 표시한다.
4. 전문가 판단 영역으로 오인될 수 있는 완료/확정형 표현을 UI, 코드, 문서에 넣지 않는다.
5. 원본 파일은 장기 보관하지 않는다.
6. 개인정보성 데이터가 로그에 남으면 안 된다.
7. API key, secret key는 코드에 하드코딩하지 않는다.
8. 엑셀 산출물이 핵심 제품이다. Excel exporter 테스트를 중요하게 다룬다.
9. 기능을 추가할 때는 테스트를 함께 작성한다.
10. MVP에서는 업로드, OCR, 검수, 엑셀 다운로드 흐름을 우선한다.
11. 모바일 앱은 웹 MVP 검증 후 진행한다.
12. OpenAI API는 MVP 필수 의존성이 아니다. LLM Provider 인터페이스만 열어둘 수 있다.

---

## 3. Required Reading Before Work

작업 전 아래 문서를 읽고 현재 범위를 확인한다.

1. README.md
2. PLAN.md
3. SPEC.md
4. CHECKLIST.md
5. CHANGE_CONTROL.md
6. DECISIONS.md

문서와 코드가 충돌하면 임의로 방향을 바꾸지 말고, CHANGE_CONTROL.md 기준으로 변경 제안을 만든다.

---

## 4. Allowed MVP Stack

- Python 3.11+
- Streamlit
- pandas
- openpyxl
- Pydantic
- python-dotenv
- pytest
- SQLite 또는 local JSON
- Mock OCR Provider
- 실제 OCR Provider 1개

나중에 가능한 스택:

- FastAPI
- Next.js
- Supabase
- Background worker
- PWA

---

## 5. Project Structure Rules

새 파일을 만들 때는 README.md의 폴더 구조를 따른다.

금지:

1. 루트에 임시 스크립트를 무분별하게 만들지 않는다.
2. 테스트 없는 핵심 로직을 만들지 않는다.
3. OCR API 호출 코드를 UI 안에 직접 넣지 않는다.
4. Excel 생성 로직을 Streamlit 화면 코드에 직접 넣지 않는다.
5. 개인정보 원문을 print/logger로 출력하지 않는다.

권장:

1. OCR은 `app/ocr/` 아래 Provider로 분리한다.
2. 파싱은 `app/parser/` 아래 둔다.
3. 검증은 `app/validator/` 아래 둔다.
4. 엑셀 생성은 `app/exporter/` 아래 둔다.
5. 테스트는 기능별로 `tests/` 아래 둔다.

OCR Provider 확장 규칙:

1. 모든 OCR Provider 작업은 `StandardOCRResult` 계약을 따라야 한다.
2. Provider raw response를 Parser, Validator, Exporter로 직접 넘기지 않는다.
3. Parser는 provider SDK나 provider raw JSON 구조를 import하지 않는다.
4. OCR Adapter는 provider raw response를 `StandardOCRResult`로 변환하는 책임만 가진다.
5. `ReceiptRecord`와 `ExcelExporter`는 기존 MVP 산출물과 호환되도록 유지한다.
6. 새 Provider를 추가할 때는 fixture와 테스트를 함께 추가한다.
7. OCR raw text 전체와 raw JSON 전체를 print/logger/DB/엑셀/화면에 남기지 않는다.
8. `schema_version`, `parser_version`, `validator_version` 변경 시 SPEC.md와 CHECKLIST.md를 함께 업데이트한다.
9. Provider Adapter 작업 전에는 `app/core/standard_ocr.py` 모델과 `tests/fixtures/standard_ocr/` fixture를 먼저 확인한다.
10. Parser 전환 작업 시 `StandardOCRParserContext`를 우선 확인한다.
11. Provider raw response를 Parser로 넘기는 변경은 금지한다.
12. Parser 전환은 end-to-end 테스트와 ExcelExporter 회귀 테스트를 통과해야 한다.
13. raw text/raw JSON 전체 노출을 디버깅 목적으로도 추가하지 않는다.
14. 기존 raw_text Parser 경로를 제거하기 전 compatibility wrapper와 회귀 테스트를 준비한다.
15. Provider Adapter 작업은 Parser 변경과 분리해서 진행한다.
16. Azure 관련 작업 시 Azure raw response를 Parser로 직접 넘기지 않는다.
17. Azure SDK response object를 Parser, Validator, Exporter에서 import하지 않는다.
18. Azure Adapter는 `StandardOCRResult`를 반환하는 별도 계층으로 둔다.
19. `provider_fields`는 비민감 metadata와 adapter 진단 요약만 담는다.
20. `provider_fields`를 raw JSON 저장소처럼 사용하지 않는다.
21. Azure endpoint 전체 URL, API key, `operation_location` 전체 URL을 로그/화면/테스트 fixture에 남기지 않는다.
22. Azure Provider 동작 변경과 Parser 전환은 한 작업에서 동시에 하지 않는다.
23. Adapter 구현, Provider 연결, Parser 전환은 별도 작업으로 진행한다.
24. Azure Adapter 작업 후 compileall, pytest, StandardOCR 관련 테스트, end-to-end export flow 테스트를 실행한다.
25. Azure Adapter 단위 테스트에서는 실제 Azure API를 호출하지 않는다.
26. Azure Adapter fixture에는 실제 Azure raw JSON 전체나 실제 고객 파일을 넣지 않는다.
27. AzureStandardOCRAdapter 추가만으로 기존 `AzureProvider.extract()` 반환값을 바꾸지 않는다.
28. Azure Adapter를 구현했더라도 기존 `AzureProvider.extract()` 반환값을 임의로 변경하지 않는다.
29. 실제 Azure API 호출 테스트를 기본 pytest에 넣지 않는다.
30. Azure key가 없어도 기본 테스트가 통과해야 한다.
31. Adapter output을 Parser에 직접 연결하기 전 `StandardOCRParserContext` 테스트를 먼저 통과해야 한다.
32. 8주차 Parser 전환 전에는 Azure Provider regression test, Adapter test, parser context test, end-to-end export flow test를 확인한다.
33. `provider_fields`를 Parser context로 그대로 전달하지 않는다.
34. Parser 작업 시 provider raw response를 직접 받는 코드를 추가하지 않는다.
35. Azure/PaddleOCR/Tesseract/ML Kit/Apple Vision SDK 객체를 `ReceiptParser`에서 import하지 않는다.
36. Parser 표준 입력은 `StandardOCRParserContext`를 우선 사용한다.
37. 기존 raw_text Parser 경로는 즉시 삭제하지 않는다.
38. Parser 전환 시 `ReceiptRecord`와 `ExcelExporter` 구조를 대규모로 바꾸지 않는다.
39. Parser entry 추가, fixture 비교 테스트, downstream 회귀 점검은 별도 단계로 진행한다.
40. Parser 전환 작업 후 standard OCR tests, azure adapter tests, parser tests, validator tests, exporter tests, end-to-end export flow tests를 실행한다.
41. raw text/raw JSON 전체를 디버깅 목적으로 print/logger에 남기지 않는다.
42. Provider raw response를 Parser로 전달하는 코드를 발견하면 변경을 중단하고 보고한다.
43. PaddleOCR 작업 시 PaddleOCR raw output을 Parser, Validator, CategoryRules, CardMatcher, ExcelExporter로 직접 넘기지 않는다.
44. `PaddleOCRProvider`는 `StandardOCRResult`를 반환해야 한다.
45. `paddleocr` import는 lazy import로 처리하고, paddleocr 미설치 환경에서도 기본 pytest가 통과해야 한다.
46. 실제 PaddleOCR OCR 테스트는 opt-in으로 분리하고, 기본 테스트에서 모델 다운로드나 네트워크 호출이 발생하지 않게 한다.
47. PDF 처리는 9주차 PaddleOCR PoC 범위가 아니며 후속 작업으로 분리한다.
48. PaddleOCRProvider 작업 중 ReceiptParser, Validator, ExcelExporter, Processing History를 동시에 변경하지 않는다.
49. PaddleOCR raw output 전체, OCR raw text 전체, 전체 로컬 절대경로를 로그, fixture, DB, 엑셀, 화면, 테스트 출력에 남기지 않는다.
50. 9주차-B는 adapter/fixture only, 9주차-C는 optional provider, 9주차-D는 opt-in smoke test로 분리한다.
51. 10주차 품질 비교는 `StandardOCRResult`/`StandardOCRParserContext`/`ReceiptRecord` 기준으로 수행하고 raw output 기준으로 비교하지 않는다.

---

## 6. Commands

### Setup

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

### Run App

```bash
streamlit run app/main.py
```

### Tests

```bash
python -m compileall app tests
python -m pytest
```

---

## 7. Git Commit Rules

작업은 작은 단위로 커밋한다.

커밋 전 반드시 실행:

```bash
python -m compileall app tests
python -m pytest
```

테스트가 실패하면 커밋하지 않는다.

커밋 메시지 형식:

```text
feat: add file upload and safe local storage
fix: handle invalid receipt files safely
test: add excel exporter test coverage
docs: update MVP roadmap and scope
chore: initialize project structure
```

기능 단위가 클 경우 여러 커밋으로 나눈다.

---

## 8. Documentation Sync Rule

코드 변경이 아래 항목에 영향을 주면 문서도 함께 수정한다.

| 변경 내용 | 함께 수정할 문서 |
|---|---|
| 실행 방법 변경 | README.md |
| MVP 범위 변경 | README.md, PLAN.md, CHANGE_CONTROL.md |
| 데이터 모델 변경 | SPEC.md |
| 엑셀 시트/컬럼 변경 | SPEC.md, CHECKLIST.md |
| 테스트 명령 변경 | README.md, AGENTS.md |
| 작업 방향 변경 | DECISIONS.md, CHANGE_CONTROL.md |

문서 변경 없이 기능만 바꾸지 않는다.

---

## 9. Scope Control

이번 단계에서 하지 말라고 명시된 기능은 구현하지 않는다.

특히 아래 기능은 명시적 지시 없이는 구현하지 않는다.

- 홈택스 연동
- 카드사 자동 연동
- 로그인/결제
- 다중 사용자 권한관리
- 네이티브 모바일 앱
- 전문가 판단 영역의 결론 제공
- 회계 판단 결과의 확정 표현
- OpenAI API 전체 자동 보정
- 장기 파일 보관

---

## 10. Completion Report Format

작업 완료 후 아래 형식으로 보고한다.

```text
1. 생성/수정한 파일 목록
2. 구현한 기능 요약
3. 주요 구조 설명
4. 테스트 명령어
5. 테스트 결과
6. 문서 동기화 여부
7. 남은 리스크
8. 추천 커밋 메시지
```
## Week 9-C Optional PaddleOCRProvider Agent Addendum

- PaddleOCRProvider work may add a provider factory candidate, but it must not change the default provider.
- Do not top-level import `paddleocr`; use lazy import inside the provider execution path.
- Missing `paddleocr` must be handled with a non-sensitive `StandardOCRResult` diagnostic instead of breaking default pytest.
- Do not add real OCR smoke tests to default pytest; keep them opt-in for 9-D.
- Do not add PDF conversion, image fixtures, customer files, or `requirements.txt` OCR dependencies in 9-C.

## Week 9-D Opt-In PaddleOCR Smoke Test Agent Addendum

- Real PaddleOCR smoke tests must be opt-in only and skipped by default pytest.
- Do not print or report full local image paths; use file names only.
- Do not commit real customer images or real OCR raw output.
- Keep PDF handling unsupported/deferred in 9-D.
- Classify smoke test failures as environment, provider, security, or quality failures.
- Keep Azure vs PaddleOCR quality comparison as a separate 10-week task.

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

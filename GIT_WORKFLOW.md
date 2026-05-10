# GIT_WORKFLOW.md

# Git 운영 가이드

## 1. 기본 원칙

이 프로젝트는 1인 개발 프로젝트이지만, 기능 단위로 작게 커밋합니다.

좋은 커밋은 아래 조건을 만족합니다.

1. 하나의 목적만 가진다.
2. 테스트가 통과한다.
3. 문서 변경이 필요하면 함께 반영한다.
4. 롤백 가능한 크기로 나눈다.
5. 비밀키와 원본 고객 파일을 포함하지 않는다.

---

## 2. 브랜치 전략

간단하게 시작합니다.

```text
main        안정 버전
mvp/week1   1주차 작업
mvp/week2   2주차 작업
mvp/week3   3주차 작업
mvp/week4   4주차 작업
```

처음에는 `main`에서 직접 작업해도 되지만, Codex 작업이 길어지면 주차별 브랜치를 권장합니다.

---

## 3. 커밋 메시지 규칙

```text
chore: initialize project structure
feat: add file upload and safe local storage
feat: add OCR provider interface and mock provider
feat: add card statement parser
fix: handle invalid file extension safely
test: add card parser tests
docs: update MVP plan and checklist
```

접두어 기준:

| 접두어 | 의미 |
|---|---|
| feat | 기능 추가 |
| fix | 버그 수정 |
| test | 테스트 추가/수정 |
| docs | 문서 수정 |
| chore | 환경설정/구조/기타 |
| refactor | 동작 변경 없는 구조 개선 |

---

## 4. 커밋 전 명령어

```bash
python -m compileall app tests
python -m pytest
git status
```

테스트 실패 시 커밋하지 않습니다.

---

## 5. 1주차 커밋 예시

```bash
git checkout -b mvp/week1

git add README.md PLAN.md AGENTS.md SPEC.md CHECKLIST.md CODEX_PROMPTS.md GIT_WORKFLOW.md CHANGE_CONTROL.md DECISIONS.md
git commit -m "docs: define receipt OCR assistant MVP plan"

git add app/main.py app/core/config.py requirements.txt .env.example .gitignore
git commit -m "chore: initialize streamlit MVP app"

git add app/storage/file_store.py tests/test_file_store.py
git commit -m "feat: add safe upload file storage"

git add app/ocr/base.py app/ocr/mock_provider.py tests/test_mock_ocr_provider.py
git commit -m "feat: add OCR provider interface and mock provider"

git add app/parser/card_statement_parser.py tests/test_card_statement_parser.py
git commit -m "feat: add card statement parser"
```

---

## 6. Codex에게 커밋을 맡길 때의 규칙

Codex에게 커밋까지 맡길 경우 프롬프트에 아래 조건을 넣습니다.

```text
테스트가 통과한 경우에만 git commit까지 수행해줘.
커밋 전 git diff --stat과 git status를 출력해줘.
.env, data/uploads, data/outputs, 실제 고객 파일은 절대 커밋하지 마.
커밋 메시지는 작업 범위에 맞게 하나만 사용해줘.
```

더 안전한 방식은 Codex가 추천 커밋 메시지만 출력하고, 사용자가 직접 커밋하는 것입니다.

---

## 7. 금지 커밋 대상

`.gitignore`에 포함해야 합니다.

```text
.env
.venv/
__pycache__/
.pytest_cache/
data/uploads/*
data/outputs/*
!data/uploads/.gitkeep
!data/outputs/.gitkeep
*.log
*.tmp
.DS_Store
```

---

## 8. 주차 종료 태그

각 주차가 완료되면 태그를 남길 수 있습니다.

```bash
git tag mvp-week1-complete
git tag mvp-week2-complete
git tag mvp-week3-complete
git tag mvp-week4-complete
```

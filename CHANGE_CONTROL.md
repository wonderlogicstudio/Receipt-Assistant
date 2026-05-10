# 변경 관리 규칙

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

## 4. 변경 절차

1. 관련 문서와 코드를 먼저 확인한다.
2. 기능 변경이 필요한지, 문서 동기화만 필요한지 구분한다.
3. MVP 범위를 넓히는 변경은 바로 구현하지 않고 결정 기록을 남긴다.
4. 코드 변경이 있으면 테스트를 함께 작성하거나 기존 테스트를 확인한다.
5. 주요 결정은 DECISIONS.md에 기록한다.
6. `python -m compileall app tests`와 `python -m pytest`를 실행한다.
7. Git 변경사항에 민감 파일이 포함되지 않았는지 확인한다.

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

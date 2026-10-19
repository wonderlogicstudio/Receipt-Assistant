# Ponytail 자동 원칙 로딩 hook 등록

등록일: 2026-10-19.

## 1. 생성/수정한 파일 목록

- 추가: `.codex/hooks.json`, `scripts/ponytail_hook.js`, `tests/test_ponytail_hook.py`, 이 기록.
- 수정: `README.md`, `CHANGE_CONTROL.md`, `DECISIONS.md`, `docs/ponytail_setup.md`.
- Codex 공식 hook 화면에서 이번 프로젝트 hook 3개의 신뢰를 등록했다. 전역 hook 정의나 전역 플러그인을 추가하지 않았다.

## 2. 구현한 기능 요약

대화 시작/재개/압축 복구, 새 요청, 하위 에이전트 시작 때 프로젝트에 설치한 Ponytail 원칙과 작업 전 점검 항목을 자동 전달한다. 스킬을 매번 직접 요청하지 않아도 기본 원칙을 context에 포함한다. 사용자가 명시적으로 정한 모드/off 지시는 유지한다.

## 3. 주요 구조 설명

Codex의 [프로젝트 hook 규약](https://learn.chatgpt.com/docs/hooks)에 따라 `.codex/hooks.json`을 사용한다. SessionStart/UserPromptSubmit/SubagentStart마다 동일한 Node adapter를 다른 이벤트 인자로 호출한다. Git root를 인자로 안전하게 조회하므로 프로젝트 경로의 공백과 하위 폴더 실행을 지원한다.

adapter는 설치된 `.agents/skills/ponytail/SKILL.md`를 읽고 YAML header를 제외한 원칙과 다음 항목을 JSON additionalContext로 반환한다.

- 기존 사용자 변경, AGENTS, OCR 계약 및 엑셀 호환 보존.
- 수정 전 영향 경로와 호출부 확인, 최소 변경 선택.
- 실행/의존성 변경 전 기존 Python, OCR 패키지와 CPU/GPU 환경 확인.
- 수정 후 관련 검증과 미검증 범위 보고, 민감 데이터/전체 경로 비노출.

프로젝트 내부에서만 실행하며 hook 자체는 파일 변경, OCR, 네트워크, 전체 감사 또는 테스트를 실행하지 않는다. stdin은 저장·출력하지 않고 버린다. Node.js와 Git이 필요하다. 기본 context 한도는 이벤트마다 약 2,000 token, timeout은 5초다. 공식 Ponytail 플러그인의 전역 모드 저장·band/board 기능을 설치한 것은 아니다.

## 4. 테스트 명령어

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_ponytail_hook.py -q -p no:cacheprovider
node --check scripts/ponytail_hook.js
```

추가로 실제 Codex CLI의 `/hooks`에서 프로젝트 source·각 command·신뢰 상태와 활성 수를 확인했다. 검증용 CLI에는 모델 작업을 요청하지 않았다.

## 5. 테스트 결과

- hook 테스트 8 passed: 이벤트 3종의 응답 계약, 점검 원칙 포함, 요청 내용 비노출, 프로젝트 외부 비활성, 스킬 누락 시 안전한 오류, 등록 command의 하위 폴더 실행.
- Node 구문 검사 통과.
- 공식 `/hooks` 화면: SessionStart 1 installed / 1 active, UserPromptSubmit 1/1, SubagentStart 1/1. 검토 대기 항목 없음.
- 신뢰 우회 flag를 사용하거나 hook 신뢰 파일을 직접 편집하지 않았다.
- 설치 전후 해시 비교로 기존 앱/OCR/매칭 소스·테스트·실행기·AGENTS·환경설정 135개가 그대로임을 확인했다.
- 신뢰 등록 후 새 CLI 세션에서 hook 재검토 경고 없이 시작됨을 확인했다. 모델 작업은 요청하지 않았으며 실제 모델이 점검을 수행했다는 증거로 해석하지 않는다.
- 변경은 hook adapter와 설정에 한정되어 앱 전체 pytest는 반복 실행하지 않았다. 수정 문서의 `git diff --check`를 통과했다.

## 6. 문서 동기화 여부

README, 최초 스킬 설치 기록, CHANGE_CONTROL, DECISIONS에 현재 구성을 반영했다. 앱 동작·데이터 모델·산출물 계약·기본 테스트 명령과 AGENTS는 바꾸지 않았다.

## 7. 남은 리스크

새 대화에서 프로젝트의 신뢰된 config layer가 로드되어야 적용된다. 다른 PC나 변경된 hook 정의에는 Codex의 신뢰 검토가 다시 필요하다. 원칙 주입은 실제 감사·테스트 수행의 증거가 아니며, 필요한 검증은 작업 내용에 따라 별도로 실행해야 한다.

## 8. 추천 커밋 메시지

`chore: register project-local Ponytail preflight hooks`

이번 작업에서 커밋/푸시는 수행하지 않았다.

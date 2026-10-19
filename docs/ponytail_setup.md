# Ponytail 프로젝트 전용 설치 기록

설치일: 2026-10-19.

후속 변경: 아래는 최초 스킬 설치 당시의 기록이다. 이후 사용자의 요청으로 프로젝트 전용 lifecycle hook을 별도로 등록하고 신뢰·활성 상태를 확인했다. 현재 hook 구성과 범위는 [hook 등록 기록](ponytail_hooks_setup.md)을 따른다. 원본 스킬 파일과 고정 커밋은 유지했다.

## 1. 생성/수정한 파일 목록

추가:

- `.agents/skills/ponytail/SKILL.md`
- `.agents/skills/ponytail-review/SKILL.md`
- `.agents/skills/ponytail-audit/SKILL.md`
- `.agents/skills/ponytail-debt/SKILL.md`
- `.agents/skills/ponytail-gain/SKILL.md`
- `.agents/skills/ponytail-help/SKILL.md`
- `.agents/skills/LICENSE-ponytail.txt`
- `.agents/skills/ponytail-installation.json`
- `docs/ponytail_setup.md`

수정: `README.md`, `CHANGE_CONTROL.md`, `DECISIONS.md`의 설치·사용 안내.

## 2. 구현한 기능 요약

기본 코드 작업 원칙과 변경 리뷰, 전체 감사, 보류 항목 수집, upstream 측정 결과 안내, 사용법 스킬을 설치했다. 앱 기능이나 OCR 동작은 변경하지 않았다.

## 3. 주요 구조 설명

- 공식 저장소: [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail).
- 설치 기준: 커밋 `09c434ab73ca43761c5d8b0c5d341926c2fba710`.
- 위치: 이 프로젝트의 `.agents/skills/`. 전역 설치가 아니다.
- 방식: Codex `skill-installer`의 `install-skill-from-github.py`로 6개 경로를 명시해 설치했다.
- 원본 스킬은 수정하지 않았으며 MIT 라이선스를 함께 보관한다.
- 출처·커밋·설치일·스킬별 SHA-256은 `ponytail-installation.json`에 기록한다.
- 기존 `AGENTS.md`의 제품 경계, 표준 OCR 계약, 개인정보 보호와 테스트 기준을 유지한다.
- 자동 실행 hook, band/board, 전역 모드 설정과 플러그인 등록은 포함하지 않는다.

다음 대화부터 `ponytail-audit 스킬로 소스를 점검해줘` 또는 `ponytail-review로 현재 변경을 검토해줘`라고 요청한다. 스킬 목록 갱신은 호스트의 재탐색 시점에 따르므로 목록에 나타나지 않으면 같은 프로젝트에서 새 대화를 열어 확인한다. 플러그인 이름 공간의 명령이나 자동 활성화를 설치 결과로 간주하지 않는다.

## 4. 테스트 명령어

이번 설치는 스킬/문서 추가이므로 앱의 pytest를 다시 실행하지 않았다. 설치 검증은 Python 표준 라이브러리의 assert 검사로 수행했다.

1. 공식 고정 커밋의 ZIP을 받아 각 스킬 디렉터리의 파일 목록과 설치 파일 목록을 비교한다.
2. 각 파일의 byte 내용과 SHA-256, 스킬 frontmatter의 name/description을 확인한다.
3. MIT 라이선스를 확인하고 manifest의 모든 해시를 다시 계산해 비교한다.
4. 설치 전 저장한 앱/테스트/실행기·AGENTS·환경설정 해시와 현재 값을 비교한다.
5. 수정 문서의 `git diff --check`를 실행한다.

## 5. 테스트 결과

- 공식 원본과 스킬 파일 6/6의 목록·byte 내용이 일치했다.
- 스킬 이름/설명 frontmatter와 MIT 라이선스 검증을 통과했다.
- manifest에 기록한 스킬 6개와 라이선스의 해시 재검증을 통과했다.
- 설치 전후 해시 비교에서 기존 제품 소스·테스트·실행기·AGENTS·환경설정 파일 134개가 변경되지 않았음을 확인했다.
- 수정 문서의 `git diff --check`를 통과했다.
- 전체 앱 회귀, 실제 OCR 호출, 모델 다운로드와 고객 파일 처리는 수행하지 않았다.

## 6. 문서 동기화 여부

README, CHANGE_CONTROL, DECISIONS에 프로젝트 전용 설치와 사용 범위를 반영했다. 제품 범위·데이터 모델·엑셀 계약·테스트 명령은 바뀌지 않아 PLAN/SPEC/CHECKLIST/AGENTS를 변경하지 않았다.

## 7. 남은 리스크

스킬 설치는 코드 품질 개선이나 리팩터링 검증 결과가 아니다. 원본 보조 스킬의 플러그인/hook 관련 설명은 이번 설치 범위와 구분해야 한다. 기존 미커밋 소스와 실행기 작업은 보존하며, 별도 코드 정리는 변경 단위별 호출부 확인과 회귀 검증을 거쳐야 한다.

## 8. 추천 커밋 메시지

`chore: install project-local Ponytail skills`

이 작업에서 커밋/푸시는 실행하지 않았다.

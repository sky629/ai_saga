# 스펙 주도 Ralph workflow 정착

## 1. Metadata

- Mode: `sub-agent`
- Handoff Type: `phase`
- Title: 스펙 주도 Ralph workflow 정착
- Owner: Codex
- Status: `done`
- Related Branch:
- Related Worktree:
- Related Files:
  - `AGENTS.md`
  - `README.md`
  - `docs/spec_driven_ralph_workflow.md`
  - `docs/PRD_TEMPLATE.md`

## 2. Input

- Request summary:
  - 스펙 주도 개발을 하고 싶음
  - 스펙을 먼저 정하고 에이전트들이 Ralph loop로 개발/테스트/검증을 반복하길 원함
- Preconditions:
  - 기존 저장소는 `Execution orchestration mode: sub-agent`
  - `.omx/plans/` 하위에 기존 계획 문서가 존재함
- Dependencies:
  - `AGENTS.md`
  - `README.md`
  - `TEAM_OPERATIONS_GUIDE.md`
  - `WORKTREE_GUIDE.md`

## 3. Scope

- In scope:
  - 저장소 기본 개발 흐름을 스펙 주도 + Ralph loop 기준으로 문서화
  - PRD 템플릿 추가
  - 운영 문서에서 해당 흐름을 참조 가능하게 연결
- Out of scope:
  - 특정 기능 구현 시작
  - 실제 Ralph execution 상태 파일 생성
  - team/worktree 자동화 스크립트 추가
- Allowed write scope:
  - `AGENTS.md`
  - `README.md`
  - `docs/**`
  - `.omx/plans/**`
- Forbidden write scope:
  - `app/**`
  - `tests/**`

## 4. Decisions and Contract

- Confirmed decisions:
  - 큰 기능은 PRD를 먼저 작성한다.
  - PRD를 완료 기준으로 삼아 Ralph loop를 돈다.
  - 넓은 요청은 planning/consensus 후 PRD를 고정한다.
  - handoff는 활성 PRD와 현재 slice를 가리켜야 한다.
- API/schema/contract version:
  - 운영 프로세스 문서 변경
- Assumptions:
  - 사용자가 말한 `palph loop`는 `ralph loop` 의도다.

## 5. Work Summary

- What changed:
  - `AGENTS.md`에 spec-driven development 기본 규칙 추가
  - `README.md`에 권장 개발 프로세스 추가
  - 저장소 전용 workflow 문서 추가
  - `docs/PRD_TEMPLATE.md` 추가
- What was inspected:
  - 기존 orchestration 규칙
  - `.omx/plans/` 기존 문서 구조
- Remaining work:
  - 실제 기능 요청 시 해당 템플릿으로 첫 PRD 생성

## 6. Validation

- Tests run:
  - `git diff --check`
- Lint/format checks:
  - 문서 변경만 있어 런타임 lint/format 미실행
- Manual verification:
  - 링크/경로/문서 간 참조 확인
  - `.omx`가 gitignored라 템플릿은 `docs/PRD_TEMPLATE.md`에 두도록 조정
  - Swagger 경로가 실제 앱 설정과 일치하는지 확인

## 7. Risks and Open Questions

- Known risks:
  - 실제 Ralph 자동화가 세션 scope를 만들면 기능 slug 우선 규칙과 충돌 없는지 재확인 필요
- Open questions:
  - 없음
- Blockers:
  - 없음

## 8. Next Handoff

- Next owner: Codex
- Next recommended action:
  - 다음 기능 요청 시 `.omx/plans/prd-{slug}.md`를 먼저 만들고 해당 PRD를 기준으로 구현 시작
- Done criteria for receiver:
  - 저장소 운영 문서만 읽어도 스펙 주도 + Ralph loop 흐름을 따라갈 수 있음

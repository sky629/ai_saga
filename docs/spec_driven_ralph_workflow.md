# 스펙 주도 Ralph Workflow

이 문서는 AI Saga 저장소에서 기능 개발을 진행할 때 기본으로 따를
스펙 주도 개발 흐름을 정의한다.

## 목적

- 채팅 지시문만으로 바로 구현하지 않는다.
- 먼저 스펙을 고정하고, 그 스펙을 완료 기준으로 삼는다.
- 구현은 Ralph loop로 반복하며 테스트와 검증을 함께 통과시킨다.
- 완료 선언은 테스트 통과와 독립 검증 근거가 있을 때만 가능하다.

## 기본 원칙

1. 큰 기능은 반드시 PRD에서 시작한다.
2. PRD 없는 구현은 예외적 소규모 수정에서만 허용한다.
3. 새 동작은 항상 RED -> GREEN -> REFACTOR 순서를 따른다.
4. acceptance criteria는 모두 테스트 가능해야 한다.
5. 메인 에이전트는 스펙, 통합, 최종 판단을 소유한다.
6. 서브에이전트는 bounded scope만 가진다.
7. 병렬 구현은 write scope가 분리될 때만 허용한다.

## 표준 산출물

- PRD: `.omx/plans/prd-{slug}.md`
- Planning: `.omx/plans/{slug}_planning.md`
- Design: `.omx/plans/{slug}_design.md`
- Test Plan: `.omx/plans/{slug}_test_plan.md`
- QA Checklist: `.omx/plans/{slug}_qa_checklist.md`
- Ralph Progress Ledger:
  `.omx/state/{scope}/ralph-progress.json`
- Handoff: `docs/handoffs/YYYYMMDD-<topic>.md`

작업 규모가 작으면 PRD만으로 충분할 수 있다. 여러 단계가 있는
기능이면 planning, design, test plan, QA checklist까지 만든다.

`.omx/`는 작업 중 생성되는 로컬 산출물 경로로 사용하고, 템플릿과
규칙 문서는 저장소에 버전 관리되는 `docs/`에 둔다.

`{scope}`는 기본적으로 기능 slug를 뜻한다. 예를 들어
`feat/session-cache` 작업이면 progress ledger는
`.omx/state/session-cache/ralph-progress.json`을 사용한다. 세션
전용 scope를 도입한 자동화가 있다면 그 세션 scope를 우선한다.

## 언제 무엇을 시작할지

### 1. 요청이 넓거나 모호할 때

먼저 계획을 수렴한다.

- 권장 진입: `$plan --consensus`
- 결과물: 범위, 비범위, acceptance criteria, 위험, 검증 계획
- 출력 위치: `.omx/plans/`

이 단계에서는 구현하지 않는다. 합의된 계획을 만든 뒤 PRD를
고정한다.

### 2. 요청이 충분히 구체적일 때

바로 PRD를 만든다.

- 권장 진입: `$ralph-init "<feature description>"`
- 결과물: `.omx/plans/prd-{slug}.md`

## PRD 필수 항목

PRD에는 최소한 아래 항목이 있어야 한다.

- 문제 정의
- 목표
- 비목표
- 사용자 스토리 또는 업무 시나리오
- 테스트 가능한 acceptance criteria
- 기술 제약
- 위험과 완화책
- 검증 방법

권장 추가 항목:

- 데이터 모델 영향
- API 계약
- 롤아웃/마이그레이션 고려사항
- 관측성 요구사항

## Ralph Loop 실행 규칙

스펙이 승인되면 `$ralph` loop로 실행한다.

1. PRD에서 다음 story slice 또는 acceptance criterion 하나를 고른다.
2. 해당 동작을 증명하는 실패 테스트를 먼저 작성한다.
3. 최소 구현으로 테스트를 통과시킨다.
4. 관련 단위 테스트, 통합 테스트, 필요 시 E2E를 실행한다.
5. black/isort/flake8 등 품질 게이트를 통과시킨다.
6. verifier/reviewer/architect 성격의 독립 검증을 수행한다.
7. 차단 이슈가 있으면 다시 수정하고 같은 검증을 반복한다.
8. 남은 acceptance criteria가 0개가 될 때까지 반복한다.

독립 검증은 아래 순서로 해석한다.

- 기본: 별도 reviewer/verifier 성격 에이전트가 검증한다.
- 소규모 단독 작업: 메인 에이전트의 분리된 review pass로 대체할 수
  있다.
- 고위험/아키텍처/병렬 작업: 별도 검증 에이전트 없이는 완료로
  닫지 않는다.

## 이 저장소에서의 권장 실행 순서

1. 스펙 수렴
   - 넓은 요구: `$plan --consensus`
   - 구체 요구: `$ralph-init`
2. PRD 고정
3. 필요 시 planning/design/test plan/qa checklist 추가
4. handoff 문서에 PRD 경로와 현재 소유 범위 기록
5. `$ralph` loop로 구현
6. 최종 검증
7. handoff와 PRD 상태를 완료로 갱신

## 병렬 에이전트 규칙

- 병렬 구현 전제:
  - 스펙 고정
  - API 계약 고정
  - write scope 분리
  - 메인 에이전트가 공유 파일 소유
- 서브에이전트는 다음 종류에 적합하다:
  - 독립 조사
  - 분리된 파일 집합 구현
  - 테스트/검증 병렬 수행
  - 리뷰/리스크 검토
- 공유 파일:
  - 중앙 라우터 등록
  - 공용 설정
  - lockfile
  - handoff/PRD 최종 통합

병렬 구현이나 고위험 작업은 `WORKTREE_GUIDE.md`에 따라 별도
worktree를 사용한다.

## 완료 조건

아래를 모두 만족해야 완료로 본다.

- PRD acceptance criteria가 모두 충족됨
- 관련 테스트가 최신 상태로 통과함
- lint/format checks가 통과함
- blocking review finding이 없음
- handoff 문서와 PRD 상태가 최신임

문서/프로세스 전용 변경은 예외적으로 런타임 테스트를 생략할 수
있다. 이 경우에는 아래를 validation에 남겨야 한다.

- 왜 runtime test가 비적용인지
- 어떤 문서/경로/참조 일관성을 확인했는지
- 어떤 review pass로 독립 검증을 대체했는지

## 시작 템플릿

새 기능은 아래 파일을 복제해서 시작한다.

- PRD 템플릿:
  `docs/PRD_TEMPLATE.md`
- Handoff 템플릿:
  `docs/HANDOFF_TEMPLATE.md`

## 메모

- 작은 버그 수정이나 단일 문서 수정은 PRD를 생략할 수 있다.
- 다만 기능 추가, 계약 변경, 리팩터링, 마이그레이션, 병렬 작업은
  PRD와 Ralph loop를 기본으로 한다.

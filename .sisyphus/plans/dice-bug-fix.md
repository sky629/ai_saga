# 주사위 결과 미반영 버그 수정

## TL;DR

> **Quick Summary**: 주사위 실패 시 LLM이 성공 내러티브를 생성하는 버그 수정. 액션 프롬프트에 주사위 결과 포함 + LLM `dice_applied` 자체 판단 + 서버사이드 state_changes 가드레일 추가.
>
> **Deliverables**:
> - LLM 프롬프트 개선 (시스템 + 액션 프롬프트 모두에 dice 반영)
> - LLM JSON 응답에 `dice_applied: boolean` 필드 추가
> - 서버사이드 state_changes 필터링 (실패 시 location/items_gained 차단)
> - 일상 행동 시 dice_result=null 반환 (프론트엔드 자동 패널 숨김)
>
> **Estimated Effort**: Short
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Task 1/2 → Task 3

---

## Context

### Original Request
"건물 밖으로 나가는 액션에서 주사위에 실패했는데 응답으로 온 내용은 나가졌어"
— 주사위 판정이 실패인데도 LLM이 성공한 것처럼 내러티브를 생성하는 버그.

### Root Cause Analysis
1. **프롬프트 위치 문제**: `dice_result_section`이 SYSTEM_PROMPT_TEMPLATE 내부에만 있고 ACTION_PROMPT_TEMPLATE에는 없음. LLM은 시스템 프롬프트 상단보다 최근 메시지(액션 프롬프트)에 집중하므로 주사위 결과를 무시.
2. **무조건 적용**: 모든 액션에 `DiceCheckType.COMBAT`로 하드코딩. "건물 밖으로 나가기" 같은 일상 행동에도 주사위 체크 발생.
3. **서버 검증 부재**: LLM이 주사위 실패를 무시하고 location을 변경해도 서버에서 차단하지 않음.

### Interview Summary
**Key Discussions**:
- 선별 적용: LLM이 `dice_applied: true/false`로 자체 판단 (추가 LLM 호출 없음)
- 서버 안전장치: `dice_applied=true + 실패` 시 location/items_gained 차단
- 프론트엔드: dice_applied=false면 dice_result=null → 패널 자동 숨김 (변경 불필요)

---

## Work Objectives

### Core Objective
주사위 판정 결과가 LLM 내러티브와 서버 state_changes에 **일관되게** 반영되도록 수정.

### Concrete Deliverables
- `app/llm/prompts/game_master.py` — 시스템/액션 프롬프트 개선
- `app/game/domain/services/game_master_service.py` — dice_applied 추출 + state_changes 필터링 메서드
- `app/game/application/use_cases/process_action.py` — 통합 로직 수정
- 관련 테스트 파일 업데이트

### Definition of Done
- [ ] `uv run pytest` → ALL PASS
- [ ] `uv run black app/ tests/ --check` → PASS
- [ ] `uv run isort app/ tests/ --check` → PASS
- [ ] `uv run flake8 app/ tests/` → PASS

### Must Have
- 주사위 실패 시 LLM이 실패 내러티브를 생성하도록 프롬프트 개선
- 주사위 실패 시 서버에서 location 변경 차단
- 주사위 실패 시 서버에서 items_gained 차단
- 일상 행동(이동, 대화 등)에는 주사위 패널 미표시
- LLM JSON 응답에 `dice_applied` 필드 추가

### Must NOT Have (Guardrails)
- LLM 추가 호출 금지 (1회 호출 유지)
- DiceCheckType 분류 로직 변경 금지 (LLM 판단으로 대체)
- DB 스키마 변경 금지
- 프론트엔드 코드 변경 금지 (dice_result=null 시 패널 이미 숨겨짐)
- 데미지 계산 로직 변경 금지
- `as any`, `@ts-ignore` 사용 금지
- 빈 except 블록 금지
- console.log / print 프로덕션 코드 금지 (logger 사용)

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: YES (TDD)
- **Framework**: pytest + pytest-asyncio

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Domain/Application**: Use Bash (uv run pytest) — Run tests, assert PASS
- **Prompt changes**: Manual inspection via test output showing prompt content

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — independent changes):
├── Task 1: Prompt improvements (game_master.py) [quick]
├── Task 2: Domain service — dice_applied extraction + state_changes filtering [quick]

Wave 2 (After Wave 1 — integration):
├── Task 3: ProcessActionUseCase integration [deep]

Wave FINAL (After ALL tasks — verification):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality + test run [unspecified-high]
├── Task F3: Scope fidelity check [deep]
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1    | —         | 3      | 1    |
| 2    | —         | 3      | 1    |
| 3    | 1, 2      | F1-F3  | 2    |
| F1   | 3         | —      | FINAL|
| F2   | 3         | —      | FINAL|
| F3   | 3         | —      | FINAL|

### Agent Dispatch Summary

- **Wave 1**: 2 tasks — T1 → `quick`, T2 → `quick`
- **Wave 2**: 1 task — T3 → `deep`
- **Wave FINAL**: 3 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `deep`

---

## TODOs

- [ ] 1. LLM 프롬프트 개선 — dice_applied 응답 필드 + 액션 프롬프트 주사위 정보

  **What to do**:
  - RED: `tests/unit/domain/test_game_master_prompt.py`에 테스트 추가:
    - `test_system_prompt_contains_dice_applied_in_json_format`: SYSTEM_PROMPT_TEMPLATE에 `dice_applied` 필드가 JSON 예시에 포함되어 있는지 확인
    - `test_action_prompt_contains_dice_result`: `build_action_prompt()`에 `dice_result_section` 파라미터를 추가하고, 호출 시 dice result 텍스트가 액션 프롬프트에 포함되는지 확인
    - `test_action_prompt_without_dice_result`: dice_result_section 미전달 시 빈 문자열로 처리되는지 확인
  - GREEN: `app/llm/prompts/game_master.py` 수정:
    1. **SYSTEM_PROMPT_TEMPLATE 수정**:
       - JSON 응답 형식에 `"dice_applied": false` 필드 추가 (state_changes와 같은 레벨)
       - 주사위 판정 규칙 강화: "dice_applied가 true이면 반드시 주사위 결과에 따라 서술해야 합니다" 추가
       - 규칙 추가: "일상적 행동(단순 이동, 대화, 관찰)은 dice_applied를 false로 설정합니다"
       - 규칙 추가: "전투, 위험한 행동, 기술 사용, 잠입, 탈출 등 불확실한 행동은 dice_applied를 true로 설정합니다"
    2. **ACTION_PROMPT_TEMPLATE 수정**:
       - `{dice_result_section}` 플레이스홀더 추가 (## 플레이어 행동 바로 위에)
       - "위 주사위 판정 결과를 참고하여 행동의 성공/실패를 판단하세요" 문구 추가
    3. **`build_action_prompt()` 함수 수정**:
       - `dice_result_section: str = ""` 파라미터 추가
       - ACTION_PROMPT_TEMPLATE.format()에 dice_result_section 전달
    4. **`GameMasterPrompt.build_action()` 메서드 수정**:
       - `dice_result_section` 파라미터 추가 (선택적)
       - build_action_prompt()에 전달

  **Must NOT do**:
  - SYSTEM_PROMPT_TEMPLATE의 주사위 판정 결과 섹션 제거 금지 (시스템 + 액션 양쪽 모두에 있어야 함)
  - LLM 호출 횟수 변경 금지

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 단일 파일 수정 + 테스트 파일 1개. 프롬프트 텍스트 변경이 주된 작업.
  - **Skills**: []
    - 외부 스킬 불필요

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `app/llm/prompts/game_master.py:12-63` — SYSTEM_PROMPT_TEMPLATE 전체. JSON 응답 형식(L47-59)에 `dice_applied` 필드 추가. 주사위 판정 규칙(L39-44) 강화.
  - `app/llm/prompts/game_master.py:65-74` — ACTION_PROMPT_TEMPLATE 전체. `{dice_result_section}` 플레이스홀더 추가 위치.
  - `app/llm/prompts/game_master.py:123-150` — `build_action_prompt()` 함수. `dice_result_section` 파라미터 추가.
  - `app/llm/prompts/game_master.py:213-220` — `GameMasterPrompt.build_action()` 메서드. dice_result_section 전달 추가.

  **Test References**:
  - `tests/unit/domain/test_game_master_prompt.py` — 기존 프롬프트 테스트. 새 테스트를 같은 패턴으로 추가.

  **WHY Each Reference Matters**:
  - SYSTEM_PROMPT_TEMPLATE: JSON 예시에 `dice_applied` 필드 추가하고 규칙 텍스트 강화
  - ACTION_PROMPT_TEMPLATE: LLM이 가장 집중하는 부분에 주사위 결과를 넣어야 무시하지 않음
  - build_action_prompt: 함수 시그니처에 파라미터 추가 필요
  - build_action: GameMasterPrompt dataclass에서 dice_result_section을 전달하는 진입점

  **Acceptance Criteria**:

  - [ ] Test file: `tests/unit/domain/test_game_master_prompt.py` — 새 테스트 3개
  - [ ] `uv run pytest tests/unit/domain/test_game_master_prompt.py -v` → ALL PASS

  **QA Scenarios:**

  ```
  Scenario: SYSTEM_PROMPT_TEMPLATE에 dice_applied 포함
    Tool: Bash (uv run pytest)
    Preconditions: 수정된 game_master.py
    Steps:
      1. uv run pytest tests/unit/domain/test_game_master_prompt.py::test_system_prompt_contains_dice_applied_in_json_format -v
      2. Assert test PASS
    Expected Result: dice_applied가 JSON 응답 형식에 포함됨
    Failure Indicators: test FAIL, "dice_applied" not found in template
    Evidence: .sisyphus/evidence/task-1-system-prompt-dice-applied.txt

  Scenario: ACTION_PROMPT에 주사위 결과 포함
    Tool: Bash (uv run pytest)
    Preconditions: 수정된 game_master.py
    Steps:
      1. uv run pytest tests/unit/domain/test_game_master_prompt.py::test_action_prompt_contains_dice_result -v
      2. Assert test PASS
    Expected Result: build_action_prompt()에 dice_result_section 전달 시 출력에 포함
    Failure Indicators: test FAIL, dice result text not found in action prompt
    Evidence: .sisyphus/evidence/task-1-action-prompt-dice-result.txt

  Scenario: ACTION_PROMPT에 주사위 결과 미전달 시 빈 처리
    Tool: Bash (uv run pytest)
    Preconditions: 수정된 game_master.py
    Steps:
      1. uv run pytest tests/unit/domain/test_game_master_prompt.py::test_action_prompt_without_dice_result -v
      2. Assert test PASS
    Expected Result: dice_result_section 미전달 시 빈 문자열로 처리
    Failure Indicators: test FAIL
    Evidence: .sisyphus/evidence/task-1-action-prompt-no-dice.txt
  ```

  **Commit**: YES
  - Message: `fix(prompts): 주사위 결과를 액션 프롬프트에 포함하고 dice_applied 응답 필드 추가`
  - Files: `app/llm/prompts/game_master.py`, `tests/unit/domain/test_game_master_prompt.py`
  - Pre-commit: `uv run pytest tests/unit/domain/test_game_master_prompt.py -v`

- [ ] 2. Domain Service — dice_applied 추출 + state_changes 실패 시 필터링

  **What to do**:
  - RED: `tests/unit/domain/test_game_master_service.py`에 테스트 추가:
    - `test_extract_dice_applied_true`: parsed JSON에 `dice_applied: true`가 있으면 True 반환
    - `test_extract_dice_applied_false`: parsed JSON에 `dice_applied: false`가 있으면 False 반환
    - `test_extract_dice_applied_missing`: `dice_applied` 필드 없으면 False 반환 (safe default)
    - `test_filter_state_changes_on_failure_blocks_location`: 실패 시 location을 None으로
    - `test_filter_state_changes_on_failure_blocks_items_gained`: 실패 시 items_gained를 [] 로
    - `test_filter_state_changes_on_failure_preserves_hp_change`: 실패 시 hp_change 유지
    - `test_filter_state_changes_on_failure_preserves_items_lost`: 실패 시 items_lost 유지
    - `test_filter_state_changes_on_success_no_change`: 성공 시 state_changes 변경 없음
  - GREEN: `app/game/domain/services/game_master_service.py`에 static 메서드 2개 추가:
    1. `extract_dice_applied(parsed: dict) -> bool`: `parsed.get("dice_applied", False)` 반환
    2. `filter_state_changes_on_dice_failure(state_changes: StateChanges) -> StateChanges`: location=None, items_gained=[] 로 필터링된 새 StateChanges 반환. hp_change, items_lost, experience_gained, npcs_met, discoveries는 유지.

  **Must NOT do**:
  - 기존 `extract_state_changes()` 메서드 수정 금지 (새 메서드 추가만)
  - StateChanges value object 수정 금지

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 단일 도메인 서비스에 static 메서드 2개 추가 + 테스트. 순수 로직.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `app/game/domain/services/game_master_service.py:136-155` — `extract_state_changes()` 메서드. 같은 패턴으로 `extract_dice_applied()` 추가.
  - `app/game/domain/value_objects/game_state.py:65-89` — `StateChanges` 모델. frozen=True이므로 `model_copy(update={...})`로 새 인스턴스 생성.

  **Test References**:
  - `tests/unit/domain/test_game_master_service.py` — 기존 도메인 서비스 테스트 패턴.

  **WHY Each Reference Matters**:
  - extract_state_changes: 같은 클래스에 같은 패턴으로 새 메서드를 추가하므로 참고
  - StateChanges: frozen 모델이므로 필터링 시 model_copy로 새 인스턴스 생성해야 함

  **Acceptance Criteria**:

  - [ ] Test file: `tests/unit/domain/test_game_master_service.py` — 새 테스트 8개
  - [ ] `uv run pytest tests/unit/domain/test_game_master_service.py -v` → ALL PASS

  **QA Scenarios:**

  ```
  Scenario: dice_applied 추출 정상 동작
    Tool: Bash (uv run pytest)
    Preconditions: GameMasterService에 extract_dice_applied 메서드 추가됨
    Steps:
      1. uv run pytest tests/unit/domain/test_game_master_service.py -k "dice_applied" -v
      2. Assert 3 tests PASS (true, false, missing)
    Expected Result: 3 passed
    Failure Indicators: test FAIL
    Evidence: .sisyphus/evidence/task-2-dice-applied-extraction.txt

  Scenario: 실패 시 state_changes 필터링
    Tool: Bash (uv run pytest)
    Preconditions: GameMasterService에 filter_state_changes_on_dice_failure 메서드 추가됨
    Steps:
      1. uv run pytest tests/unit/domain/test_game_master_service.py -k "filter_state_changes" -v
      2. Assert 5 tests PASS (blocks_location, blocks_items_gained, preserves_hp, preserves_items_lost, success_no_change)
    Expected Result: 5 passed
    Failure Indicators: test FAIL, location not None, items_gained not empty
    Evidence: .sisyphus/evidence/task-2-state-changes-filter.txt
  ```

  **Commit**: YES
  - Message: `feat(domain): state_changes 필터링 및 dice_applied 추출 메서드 추가`
  - Files: `app/game/domain/services/game_master_service.py`, `tests/unit/domain/test_game_master_service.py`
  - Pre-commit: `uv run pytest tests/unit/domain/test_game_master_service.py -v`

- [ ] 3. ProcessActionUseCase 통합 — 서버사이드 가드레일 + 조건부 dice_result

  **What to do**:
  - RED: `tests/unit/application/test_process_action_dice.py` 테스트 수정/추가:
    - `test_dice_applied_true_and_failure_blocks_location`: LLM이 dice_applied=true + 실패 dice 결과 시 location 변경이 session에 적용되지 않음
    - `test_dice_applied_true_and_failure_blocks_items_gained`: 같은 조건에서 items_gained 차단
    - `test_dice_applied_true_and_success_allows_location`: dice_applied=true + 성공 시 정상 적용
    - `test_dice_applied_false_returns_null_dice_result`: dice_applied=false 시 응답의 dice_result가 None
    - `test_dice_applied_true_returns_dice_result`: dice_applied=true 시 응답에 dice_result 포함
    - `test_dice_result_section_in_action_prompt`: build_action() 호출 시 dice_result_section이 전달됨
  - GREEN: `app/game/application/use_cases/process_action.py` `_handle_normal_turn()` 수정:
    1. **dice_result_section을 액션 프롬프트에 전달**: `prompt.build_action()` 호출 시 `dice_result_section` 전달 (현재는 시스템 프롬프트에만 전달)
    2. **dice_applied 추출**: LLM 응답 파싱 후 `GameMasterService.extract_dice_applied(parsed)` 호출
    3. **실패 시 state_changes 필터링**: `if dice_applied and not dice_result.is_success:` → `state_changes = GameMasterService.filter_state_changes_on_dice_failure(state_changes)` 적용
    4. **조건부 dice_result 응답**: `dice_applied=False`이면 `dice_result_response = None`으로 설정
    5. **기존 fumble/death 로직**: `dice_applied=True`일 때만 fumble 데미지 적용

  **Must NOT do**:
  - DiceService.perform_check() 호출 자체를 조건부로 변경 금지 (항상 굴림)
  - 기존 캐릭터 HP/인벤토리 업데이트 로직 구조 변경 금지
  - 기존 테스트가 깨지지 않도록 backward-compatible하게 수정

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 복잡한 통합 로직. process_action.py의 여러 부분을 조율하며 기존 테스트와의 호환성 유지 필요.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (Sequential)
  - **Blocks**: F1, F2, F3
  - **Blocked By**: Task 1, Task 2

  **References**:

  **Pattern References**:
  - `app/game/application/use_cases/process_action.py:227-244` — 현재 dice_result 생성 + 프롬프트 구성 부분. 여기에 dice_result_section을 build_action()에 전달하는 로직 추가.
  - `app/game/application/use_cases/process_action.py:257-268` — LLM 응답 파싱 후 state_changes 추출/적용 부분. 여기 다음에 dice_applied 체크 + 필터링 삽입.
  - `app/game/application/use_cases/process_action.py:424-437` — dice_result_response 생성 부분. dice_applied 조건부 처리.
  - `app/game/application/use_cases/process_action.py:358-370` — fumble/death 로직. dice_applied=True 조건 추가.

  **API/Type References**:
  - `app/game/domain/services/game_master_service.py` — `extract_dice_applied(parsed)`, `filter_state_changes_on_dice_failure(state_changes)` (Task 2에서 생성)
  - `app/llm/prompts/game_master.py` — `build_action_prompt(dice_result_section=...)`, `GameMasterPrompt.build_action(dice_result_section=...)` (Task 1에서 수정)

  **Test References**:
  - `tests/unit/application/test_process_action_dice.py` — 기존 주사위 관련 테스트. 같은 mock 패턴으로 새 테스트 추가.
  - `tests/unit/application/test_process_action.py` — 기존 ProcessAction 테스트. mock_repo 패턴 참고. LLM 응답 mock에 dice_applied 필드 추가 필요할 수 있음.

  **WHY Each Reference Matters**:
  - L227-244: dice 관련 코드가 시작되는 지점. 여기서 dice_result_section을 build_action에도 전달
  - L257-268: 파싱된 결과를 state_changes로 변환하는 지점. 필터링을 여기에 삽입
  - L424-437: 응답 구성 지점. dice_applied 조건부 처리
  - L358-370: fumble/death 로직. dice_applied 조건 추가해 일상 행동에서 fumble 미적용

  **Acceptance Criteria**:

  - [ ] `uv run pytest tests/unit/application/test_process_action_dice.py -v` → ALL PASS
  - [ ] `uv run pytest tests/unit/application/ -v` → ALL PASS (기존 테스트 깨지지 않음)
  - [ ] `uv run pytest -v` → ALL PASS (전체 테스트)

  **QA Scenarios:**

  ```
  Scenario: 주사위 실패 시 location 변경 차단 (핵심 버그 수정 검증)
    Tool: Bash (uv run pytest)
    Preconditions: Task 1, 2 완료. process_action.py에 가드레일 적용.
    Steps:
      1. uv run pytest tests/unit/application/test_process_action_dice.py::test_dice_applied_true_and_failure_blocks_location -v
      2. Assert test PASS — mock LLM returns dice_applied=true, location="outside", but dice_result.is_success=False → session.current_location unchanged
    Expected Result: 1 passed — location이 변경되지 않음
    Failure Indicators: test FAIL — location이 "outside"로 변경됨 (버그 미수정)
    Evidence: .sisyphus/evidence/task-3-location-block.txt

  Scenario: 일상 행동 시 dice_result=null
    Tool: Bash (uv run pytest)
    Preconditions: Task 1, 2 완료.
    Steps:
      1. uv run pytest tests/unit/application/test_process_action_dice.py::test_dice_applied_false_returns_null_dice_result -v
      2. Assert test PASS — mock LLM returns dice_applied=false → response.dice_result is None
    Expected Result: 1 passed — dice_result가 None
    Failure Indicators: test FAIL — dice_result가 여전히 설정됨
    Evidence: .sisyphus/evidence/task-3-null-dice-result.txt

  Scenario: 전체 테스트 회귀 확인
    Tool: Bash (uv run pytest)
    Preconditions: 모든 수정 완료
    Steps:
      1. uv run pytest -v
      2. Assert ALL PASS (기존 209개 + 새 테스트)
    Expected Result: 0 failures
    Failure Indicators: 기존 테스트 중 FAIL 발생
    Evidence: .sisyphus/evidence/task-3-full-regression.txt
  ```

  **Commit**: YES
  - Message: `fix(action): 주사위 실패 시 서버사이드 가드레일 적용`
  - Files: `app/game/application/use_cases/process_action.py`, `tests/unit/application/test_process_action_dice.py`
  - Pre-commit: `uv run pytest -v`

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality + Full Test Run** — `unspecified-high`
  Run `uv run black app/ tests/ --check && uv run isort app/ tests/ --check && uv run flake8 app/ tests/ && uv run pytest -v`. Review changed files for code quality issues.
  Output: `Black [PASS/FAIL] | isort [PASS/FAIL] | flake8 [PASS/FAIL] | Tests [N pass/N fail] | VERDICT`

- [ ] F3. **Scope Fidelity Check** — `deep`
  For each task: verify "What to do" matches actual implementation. Check no files outside scope were modified. Verify "Must NOT do" compliance.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Commit 1** (after Task 1): `fix(prompts): 주사위 결과를 액션 프롬프트에 포함하고 dice_applied 응답 필드 추가`
  - Files: `app/llm/prompts/game_master.py`, `tests/unit/domain/test_game_master_prompt.py`
- **Commit 2** (after Task 2): `feat(domain): state_changes 필터링 및 dice_applied 추출 메서드 추가`
  - Files: `app/game/domain/services/game_master_service.py`, `tests/unit/domain/test_game_master_service.py`
- **Commit 3** (after Task 3): `fix(action): 주사위 실패 시 서버사이드 가드레일 적용`
  - Files: `app/game/application/use_cases/process_action.py`, `tests/unit/application/test_process_action_dice.py`

---

## Success Criteria

### Verification Commands
```bash
uv run pytest -v                              # Expected: ALL PASS
uv run black app/ tests/ --check              # Expected: All done!
uv run isort app/ tests/ --check              # Expected: no output (clean)
uv run flake8 app/ tests/                     # Expected: no output (clean)
```

### Final Checklist
- [ ] 주사위 실패 시 LLM이 실패 내러티브 생성 (프롬프트 강화)
- [ ] 주사위 실패 시 location 변경 서버에서 차단
- [ ] 주사위 실패 시 items_gained 서버에서 차단
- [ ] dice_applied=false 시 dice_result=null 반환
- [ ] 기존 209개 테스트 + 새 테스트 모두 PASS
- [ ] lint/format 전부 clean

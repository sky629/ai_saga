# TRPG d20 주사위 시스템

## TL;DR

> **Quick Summary**: AI Saga 게임에 D&D 스타일 d20 주사위 판정 시스템을 추가합니다. 모든 플레이어 액션에 서버가 1d20 + 레벨 수정치 vs DC를 판정하고, 결과를 LLM 프롬프트에 포함시켜 내러티브에 반영합니다. 프론트엔드에 주사위 결과 패널을 추가합니다.
>
> **Deliverables**:
> - DiceService 도메인 서비스 (d20 롤, DC 테이블, 수정치 계산, 데미지 다이스)
> - DiceResult / DiceCheckType 값 객체
> - ProcessActionUseCase에 주사위 통합 (+ Scenario 로딩 선행 수정)
> - LLM 프롬프트 템플릿에 주사위 결과 컨텍스트 추가
> - GameActionResponse에 dice_result 필드 추가
> - HP=0 시 자동 게임 오버 (EndingType.DEFEAT)
> - 프론트엔드 DiceResultPanel 컴포넌트
> - 전 레이어 TDD 테스트
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 1,2,3 (VOs+Service) → Task 5 (Scenario fix) → Task 6 (UseCase integration) → Task 7 (Prompt) → Task 9 (Frontend)

---

## Context

### Original Request
AI Saga 게임에서 적과 싸우거나 이벤트가 발생했을 때 TRPG 주사위 룰을 적용하고 싶습니다. D&D 스타일 d20 시스템을 적용하여, 서버가 주사위를 굴리고 LLM이 결과를 반영한 내러티브를 생성하는 구조입니다.

### Interview Summary
**Key Discussions**:
- **주사위 시스템**: D&D d20 (1d20 + 수정치 vs DC) 확정
- **수정치**: 레벨 기반 (D&D 5e 숙련 보너스 스타일: (level-1)//4 + 2)
- **DC**: 서버 룰 테이블 (EASY=8, NORMAL=12, HARD=15, NIGHTMARE=18)
- **LLM 호출**: Option A — 1회 호출, 서버가 DC+롤 결정 후 결과를 프롬프트에 포함
- **액션 분류**: 항상 주사위 (모든 액션에 롤, DC 낮으면 거의 항상 성공)
- **데미지**: 레벨 기반 다이스 (Lv1-2=1d4, Lv3-4=1d6, Lv5-6=1d8, Lv7-8=1d10, Lv9+=1d12)
- **크리티컬(20)**: 데미지 주사위 2배 (2dX)
- **펌블(1)**: 자동 실패 + 자신에게 1d4 데미지
- **HP=0**: 즉시 게임 오버 (EndingType.DEFEAT)
- **hp_change 충돌**: 서버 주사위 결과가 LLM의 hp_change를 OVERRIDE
- **프론트엔드**: 결과 패널만 (텍스트 배지, 애니메이션 없음)
- **테스트**: TDD 필수 (RED → GREEN → REFACTOR)

**Research Findings**:
- ProcessActionUseCase가 현재 1회 LLM 호출 + JSON 파싱 구조 (narrative + options + state_changes)
- GameMasterService는 순수 도메인 서비스 (@staticmethod 패턴)
- CharacterStats에 level 필드 존재 (hp, max_hp, level, experience, current_experience)
- ScenarioDifficulty enum 존재하지만 ProcessActionUseCase에서 미사용 (TODO 주석 line 208)
- 프론트엔드는 별도 레포 (ai_saga_front/)

### Metis Review
**Identified Gaps** (addressed):
- **액션 분류 방식**: "항상 주사위" 선택으로 해결 — 분류 로직 불필요
- **HP=0 처리**: "즉시 게임 오버" 선택으로 해결
- **hp_change 충돌**: 서버 OVERRIDE로 해결
- **Scenario 미로딩**: 선행 태스크로 fix
- **DC/수정치/데미지 숫자**: D&D 5e 기반 기본값 적용
- **크리티컬/펌블 효과**: 구체적 규칙 확정
- **LLM이 주사위 결과 무시 위험**: 프롬프트에 강한 지시문 추가로 완화

---

## Work Objectives

### Core Objective
서버 사이드 d20 주사위 판정 시스템을 구축하여, 모든 플레이어 액션에 대해 주사위 결과(성공/실패/크리티컬/펌블)를 생성하고, LLM이 해당 결과를 내러티브에 반영하도록 합니다.

### Concrete Deliverables
- `app/game/domain/value_objects/dice.py` — DiceResult, DiceCheckType 값 객체
- `app/game/domain/services/dice_service.py` — DiceService 도메인 서비스
- `app/game/application/use_cases/process_action.py` — 주사위 통합 수정
- `app/llm/prompts/game_master.py` — 프롬프트에 주사위 결과 섹션 추가
- `app/game/presentation/routes/schemas/response.py` — dice_result 필드 추가
- `tests/unit/domain/test_dice_service.py` — 주사위 서비스 단위 테스트
- `tests/unit/domain/test_dice_value_objects.py` — 값 객체 단위 테스트
- `tests/unit/application/test_process_action_dice.py` — 통합 단위 테스트
- 프론트엔드: `DiceResultPanel` 컴포넌트 + 타입 업데이트 (별도 레포)

### Definition of Done
- [ ] `uv run pytest` — ALL tests pass (기존 + 신규)
- [ ] `uv run black --check app/ tests/ && uv run isort --check app/ tests/ && uv run flake8 app/ tests/` — lint pass
- [ ] API 응답에 dice_result 필드 포함 (Optional)
- [ ] 프론트엔드에서 주사위 결과 패널 표시

### Must Have
- d20 롤 (1-20 범위)
- 레벨 기반 수정치 계산: (level-1)//4 + 2
- DC 테이블: EASY=8, NORMAL=12, HARD=15, NIGHTMARE=18
- 크리티컬(nat 20): 자동 성공 + 데미지 2배
- 펌블(nat 1): 자동 실패 + 자신 1d4 데미지
- 데미지 다이스: Lv1-2=1d4, Lv3-4=1d6, Lv5-6=1d8, Lv7-8=1d10, Lv9+=1d12
- 서버 주사위 결과가 LLM의 hp_change를 OVERRIDE
- HP=0 시 EndingType.DEFEAT로 즉시 게임 종료
- 모든 액션에 주사위 롤 (DC 낮으면 거의 항상 성공)
- API 응답에 dice_result 포함 (Optional 필드)
- 프론트엔드 결과 패널 (텍스트 배지)
- TDD 전 레이어

### Must NOT Have (Guardrails)
- D&D 6대 능력치 (STR/DEX/CON/INT/WIS/CHA) — 미래 확장 예정
- 3D/CSS 주사위 애니메이션
- 방어력(AC) / 방어 롤
- 이니셔티브 / 턴 오더 메카닉
- 스펠 슬롯, 특수 능력, 스킬 트리
- 2회 LLM 호출 아키텍처
- DB에 주사위 결과 별도 저장 (API 응답으로만 전달)
- ProcessActionUseCase의 주사위 통합 외 리팩터링
- LLM 응답 JSON 스키마 변경 (입력 프롬프트만 수정)
- 멀티플레이어 주사위
- 주사위 히스토리/로그 별도 테이블

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: TDD (RED → GREEN → REFACTOR)
- **Framework**: pytest (async with pytest-asyncio)
- **If TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Domain/Application layer**: Use Bash (`uv run pytest`) — Run tests, verify pass/fail
- **API layer**: Use Bash (curl) — Send requests, assert status + response fields
- **Frontend**: Use Playwright — Navigate, interact, assert DOM, screenshot

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation value objects + domain service):
├── Task 1: DiceResult, DiceCheckType 값 객체 [quick]
├── Task 2: DiceService 도메인 서비스 (d20, DC, modifier, damage) [deep]
└── Task 3: HP=0 게임 오버 로직 추가 [quick]

Wave 2 (After Wave 1 — integration prerequisites):
├── Task 4: Scenario 로딩 fix (ProcessActionUseCase 선행 수정) [quick]
├── Task 5: LLM 프롬프트 템플릿에 주사위 결과 섹션 추가 [quick]
└── Task 6: GameActionResponse에 dice_result 필드 추가 [quick]

Wave 3 (After Wave 2 — core integration):
└── Task 7: ProcessActionUseCase에 주사위 통합 [deep]

Wave 4 (After Wave 3 — frontend):
├── Task 8: 프론트엔드 API 타입 업데이트 [quick]
└── Task 9: DiceResultPanel 컴포넌트 + GameSession 통합 [visual-engineering]

Wave FINAL (After ALL tasks — verification):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Real manual QA [unspecified-high]
└── Task F4: Scope fidelity check [deep]

Critical Path: Task 1,2 → Task 4,5,6 → Task 7 → Task 8,9 → F1-F4
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 3 (Waves 1 & 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 2, 6, 7 | 1 |
| 2 | 1 | 7 | 1 |
| 3 | — | 7 | 1 |
| 4 | — | 7 | 2 |
| 5 | — | 7 | 2 |
| 6 | 1 | 7, 8 | 2 |
| 7 | 1, 2, 3, 4, 5, 6 | 8, 9 | 3 |
| 8 | 6, 7 | 9 | 4 |
| 9 | 8 | F1-F4 | 4 |
| F1-F4 | ALL | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 → `quick`, T2 → `deep`, T3 → `quick`
- **Wave 2**: 3 tasks — T4 → `quick`, T5 → `quick`, T6 → `quick`
- **Wave 3**: 1 task — T7 → `deep`
- **Wave 4**: 2 tasks — T8 → `quick`, T9 → `visual-engineering`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.

- [ ] 1. DiceResult, DiceCheckType 값 객체 생성

  **What to do**:
  - TDD RED: `tests/unit/domain/test_dice_value_objects.py` 작성
    - DiceCheckType enum: COMBAT, SKILL, SOCIAL, EXPLORATION (str, Enum)
    - DiceResult frozen Pydantic BaseModel:
      - `roll: int` (1-20)
      - `modifier: int`
      - `total: int` (roll + modifier)
      - `dc: int`
      - `is_success: bool` (total >= dc)
      - `is_critical: bool` (roll == 20)
      - `is_fumble: bool` (roll == 1)
      - `check_type: DiceCheckType`
      - `damage: Optional[int] = None`
      - `display_text: str` (property: "🎲 1d20+2 = 15 vs DC 12 → 성공!")
    - 테스트: 불변성, 성공/실패 판정, 크리티컬/펌블 플래그, display_text 포맷
  - TDD GREEN: `app/game/domain/value_objects/dice.py` 구현
  - TDD REFACTOR: 정리
  - `app/game/domain/value_objects/__init__.py`에 export 추가

  **Must NOT do**:
  - 능력치(STR/DEX 등) 필드 추가 금지
  - DB 모델이나 ORM 매퍼 생성 금지

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 단일 파일에 간단한 Pydantic 모델 + enum 생성
  - **Skills**: []
    - 도메인 레이어 순수 Python, 특수 스킬 불필요
  - **Skills Evaluated but Omitted**:
    - `playwright`: 프론트엔드 무관
    - `git-master`: 단순 커밋

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 2, 6, 7
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `app/game/domain/value_objects/game_state.py` — StateChanges frozen Pydantic 모델 패턴 (이 패턴을 따라 DiceResult 구조화)
  - `app/game/domain/value_objects/scenario_difficulty.py` — ScenarioDifficulty(str, Enum) 패턴 (DiceCheckType enum에 이 패턴 적용)
  - `app/game/domain/value_objects/__init__.py` — re-export 패턴 (새 값 객체를 여기에 추가)

  **Test References**:
  - `tests/unit/domain/test_game_session_entity.py` — 도메인 단위 테스트 패턴 (no mocks, 순수 비즈니스 로직 검증)

  **Acceptance Criteria**:
  - [ ] `uv run pytest tests/unit/domain/test_dice_value_objects.py -v` → ALL PASS
  - [ ] DiceResult는 frozen (수정 시 FrozenInstanceError)
  - [ ] DiceCheckType는 4개 값: COMBAT, SKILL, SOCIAL, EXPLORATION

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: DiceResult 성공 판정
    Tool: Bash (uv run pytest)
    Preconditions: 테스트 파일 작성 완료
    Steps:
      1. uv run pytest tests/unit/domain/test_dice_value_objects.py::TestDiceResult::test_success_when_total_meets_dc -v
      2. Assert test passes: roll=15, modifier=2, total=17, dc=12 → is_success=True
    Expected Result: 1 passed, 0 failed
    Failure Indicators: AssertionError on is_success
    Evidence: .sisyphus/evidence/task-1-dice-result-success.txt

  Scenario: DiceResult 크리티컬 및 펌블 판정
    Tool: Bash (uv run pytest)
    Preconditions: 테스트 파일 작성 완료
    Steps:
      1. uv run pytest tests/unit/domain/test_dice_value_objects.py -k "critical or fumble" -v
      2. Assert: roll=20 → is_critical=True, roll=1 → is_fumble=True
    Expected Result: 2+ passed, 0 failed
    Failure Indicators: is_critical/is_fumble flag incorrect
    Evidence: .sisyphus/evidence/task-1-dice-result-critical-fumble.txt

  Scenario: DiceResult display_text 포맷
    Tool: Bash (uv run pytest)
    Preconditions: 테스트 파일 작성 완료
    Steps:
      1. uv run pytest tests/unit/domain/test_dice_value_objects.py -k "display_text" -v
      2. Assert: display_text contains "1d20+{modifier}" and "vs DC {dc}" and result text
    Expected Result: 1 passed, 0 failed
    Failure Indicators: display_text format mismatch
    Evidence: .sisyphus/evidence/task-1-dice-result-display.txt
  ```

  **Commit**: YES
  - Message: `feat(game): add DiceResult and DiceCheckType value objects`
  - Files: `app/game/domain/value_objects/dice.py`, `app/game/domain/value_objects/__init__.py`, `tests/unit/domain/test_dice_value_objects.py`
  - Pre-commit: `uv run pytest tests/unit/domain/test_dice_value_objects.py`

- [ ] 2. DiceService 도메인 서비스 생성

  **What to do**:
  - TDD RED: `tests/unit/domain/test_dice_service.py` 작성
    - `roll_d20() -> int`: 1-20 범위 랜덤 롤
    - `calculate_modifier(level: int) -> int`: (level-1)//4 + 2
    - `get_dc(difficulty: ScenarioDifficulty) -> int`: EASY=8, NORMAL=12, HARD=15, NIGHTMARE=18
    - `get_damage_dice(level: int) -> tuple[int, int]`: (개수, 면수) — Lv1-2=(1,4), Lv3-4=(1,6), Lv5-6=(1,8), Lv7-8=(1,10), Lv9+=(1,12)
    - `roll_damage(level: int, is_critical: bool) -> int`: 데미지 롤, 크리티컬이면 2dX
    - `roll_fumble_damage() -> int`: 1d4 자해 데미지
    - `perform_check(level: int, difficulty: ScenarioDifficulty) -> DiceResult`: 전체 판정 수행
    - 테스트: mock random으로 결정론적 테스트, 경계값 (레벨 1/5/9, DC 경계)
  - TDD GREEN: `app/game/domain/services/dice_service.py` 구현
    - 모든 메서드 `@staticmethod`
    - `random.randint` 사용 (테스트에서 mock)
  - TDD REFACTOR: 정리
  - `app/game/domain/services/__init__.py`에 export 추가

  **Must NOT do**:
  - DI 컨테이너에 등록 금지 (순수 도메인 서비스, static 호출)
  - 능력치 기반 수정치 계산 금지 (level만 사용)
  - 외부 I/O 금지

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 게임 밸런스에 영향을 미치는 핵심 도메인 로직, 경계값/확률 테스트 필요
  - **Skills**: []
    - 순수 Python 도메인 서비스, 특수 스킬 불필요
  - **Skills Evaluated but Omitted**:
    - `playwright`: 프론트엔드 무관

  **Parallelization**:
  - **Can Run In Parallel**: YES (Task 1과 동시 시작 가능, 단 DiceResult import 필요하므로 Task 1 완료 후 GREEN 단계 진행)
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Task 7
  - **Blocked By**: Task 1 (DiceResult 타입 사용)

  **References**:

  **Pattern References**:
  - `app/game/domain/services/game_master_service.py` — @staticmethod 패턴의 도메인 서비스 (이 구조를 그대로 따름)
  - `app/game/domain/services/__init__.py` — 서비스 re-export 패턴

  **API/Type References**:
  - `app/game/domain/value_objects/scenario_difficulty.py:ScenarioDifficulty` — DC 매핑에 사용할 enum (EASY/NORMAL/HARD/NIGHTMARE)
  - Task 1의 `DiceResult`, `DiceCheckType` — 반환 타입으로 사용

  **Test References**:
  - `tests/unit/domain/test_game_master_service.py` — 도메인 서비스 테스트 패턴 (mock 없이 순수 로직 테스트)

  **Acceptance Criteria**:
  - [ ] `uv run pytest tests/unit/domain/test_dice_service.py -v` → ALL PASS
  - [ ] roll_d20는 1-20 범위 (mock random으로 검증)
  - [ ] calculate_modifier(1) == 2, calculate_modifier(5) == 3, calculate_modifier(9) == 4
  - [ ] get_dc(EASY) == 8, get_dc(NORMAL) == 12, get_dc(HARD) == 15, get_dc(NIGHTMARE) == 18
  - [ ] get_damage_dice(1) == (1,4), get_damage_dice(3) == (1,6), get_damage_dice(9) == (1,12)
  - [ ] perform_check 크리티컬(roll=20): is_critical=True, is_success=True, damage 2배
  - [ ] perform_check 펌블(roll=1): is_fumble=True, is_success=False, 자해 데미지 존재

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: d20 롤 범위 검증
    Tool: Bash (uv run pytest)
    Preconditions: DiceResult VO 완성 (Task 1)
    Steps:
      1. uv run pytest tests/unit/domain/test_dice_service.py::TestDiceService::test_roll_d20_range -v
      2. mock random.randint to return 1, then 20, verify both in range
    Expected Result: 1 passed
    Failure Indicators: roll outside 1-20 range
    Evidence: .sisyphus/evidence/task-2-d20-roll-range.txt

  Scenario: 레벨별 수정치 계산
    Tool: Bash (uv run pytest)
    Preconditions: 서비스 구현 완료
    Steps:
      1. uv run pytest tests/unit/domain/test_dice_service.py -k "modifier" -v
      2. Assert: level 1→+2, level 4→+2, level 5→+3, level 9→+4
    Expected Result: all modifier tests pass
    Failure Indicators: wrong modifier value for any level
    Evidence: .sisyphus/evidence/task-2-modifier-calculation.txt

  Scenario: 크리티컬 히트 (nat 20)
    Tool: Bash (uv run pytest)
    Preconditions: 서비스 구현 완료
    Steps:
      1. uv run pytest tests/unit/domain/test_dice_service.py -k "critical" -v
      2. mock random to return 20 for d20
      3. Assert: is_critical=True, is_success=True, damage uses 2x dice
    Expected Result: critical tests pass
    Failure Indicators: is_critical not True when roll=20
    Evidence: .sisyphus/evidence/task-2-critical-hit.txt

  Scenario: 펌블 (nat 1)
    Tool: Bash (uv run pytest)
    Preconditions: 서비스 구현 완료
    Steps:
      1. uv run pytest tests/unit/domain/test_dice_service.py -k "fumble" -v
      2. mock random to return 1 for d20
      3. Assert: is_fumble=True, is_success=False, self_damage > 0
    Expected Result: fumble tests pass
    Failure Indicators: is_fumble not True when roll=1, or no self damage
    Evidence: .sisyphus/evidence/task-2-fumble.txt
  ```

  **Commit**: YES
  - Message: `feat(game): add DiceService domain service with d20 mechanics`
  - Files: `app/game/domain/services/dice_service.py`, `app/game/domain/services/__init__.py`, `tests/unit/domain/test_dice_service.py`
  - Pre-commit: `uv run pytest tests/unit/domain/test_dice_service.py`

- [ ] 3. HP=0 게임 오버 로직 추가

  **What to do**:
  - 참고: `CharacterStats`에 이미 `is_alive` 프로퍼티 존재 (`character.py:96-99`, `hp > 0` 체크). 이를 활용함.
  - TDD RED: `tests/unit/domain/test_game_master_service.py`에 HP=0 체크 테스트 추가
    - `GameMasterService.should_end_game_by_death(character: CharacterEntity) -> bool`: `not character.is_alive`이면 True
    - 기존 `CharacterStats.is_alive` 프로퍼티를 재활용하여 중복 로직 방지
  - TDD GREEN: `app/game/domain/services/game_master_service.py`에 `@staticmethod` 메서드 추가
  - TDD REFACTOR: 정리
  - 참고: 실제 게임 오버 트리거는 Task 7 (UseCase 통합)에서 처리

  **Must NOT do**:
  - ProcessActionUseCase 수정 금지 (Task 7에서 처리)
  - '빈사' 상태나 부활 메카닉 추가 금지
  - 기존 should_end_game 메서드 수정 금지 (새 메서드 추가)
  - CharacterStats.is_alive 프로퍼티 중복 구현 금지 (기존 것 활용)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 기존 서비스에 @staticmethod 1개 추가, 기존 is_alive 활용
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 프론트엔드 무관

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 7
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `app/game/domain/services/game_master_service.py:should_end_game()` — 기존 게임 종료 체크 패턴 (이 패턴을 따라 HP 기반 종료 체크 추가)

  **API/Type References**:
  - `app/game/domain/entities/character.py:96-99` — CharacterStats.is_alive 프로퍼티 (hp > 0 체크, 이걸 활용)
  - `app/game/domain/entities/character.py:144-147` — CharacterEntity.is_alive 프로퍼티 (stats.is_alive and is_active 체크)
  - `app/game/domain/value_objects/ending_type.py:EndingType` — DEFEAT 값 참조

  **Test References**:
  - `tests/unit/domain/test_game_master_service.py` — 기존 GameMasterService 테스트 (여기에 새 테스트 케이스 추가)

  **Acceptance Criteria**:
  - [ ] `uv run pytest tests/unit/domain/test_game_master_service.py -v` → ALL PASS (기존 + 신규)
  - [ ] should_end_game_by_death(character with hp=0) → True
  - [ ] should_end_game_by_death(character with hp=1) → False
  - [ ] should_end_game_by_death(character with hp=-5) → True (take_damage에서 min 0이므로 사실상 0)

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: HP=0 사망 판정
    Tool: Bash (uv run pytest)
    Preconditions: GameMasterService에 메서드 추가 완료
    Steps:
      1. uv run pytest tests/unit/domain/test_game_master_service.py -k "death" -v
      2. Assert: HP=0 character → True, HP=1 character → False
    Expected Result: all death check tests pass
    Failure Indicators: wrong return value at HP boundary
    Evidence: .sisyphus/evidence/task-3-hp-death-check.txt

  Scenario: 기존 테스트 회귀 없음
    Tool: Bash (uv run pytest)
    Preconditions: 새 메서드 추가 완료
    Steps:
      1. uv run pytest tests/unit/domain/test_game_master_service.py -v
      2. Assert: ALL existing tests still pass
    Expected Result: 0 failures, 0 errors
    Failure Indicators: any existing test fails
    Evidence: .sisyphus/evidence/task-3-no-regression.txt
  ```

  **Commit**: YES
  - Message: `feat(game): add HP zero death check to GameMasterService`
  - Files: `app/game/domain/services/game_master_service.py`, `tests/unit/domain/test_game_master_service.py`
  - Pre-commit: `uv run pytest tests/unit/domain/test_game_master_service.py`

- [ ] 4. Scenario 로딩 fix (ProcessActionUseCase 선행 수정)

  **What to do**:
  - TDD RED: `tests/unit/application/test_process_action.py`에 scenario 로딩 테스트 추가
    - ProcessActionUseCase 생성자에 `scenario_repository: ScenarioRepositoryInterface` 추가
    - `_handle_normal_turn`에서 `session.scenario_id`로 시나리오 로딩
    - 로딩된 시나리오의 `difficulty`, `name`, `world_setting` 사용
  - TDD GREEN:
    - `app/game/application/ports/__init__.py`에 ScenarioRepositoryInterface import 확인
    - `app/game/application/use_cases/process_action.py` 수정:
      1. 생성자에 `scenario_repository` 파라미터 추가
      2. `_handle_normal_turn`에서 `self._scenario_repo.get_by_id(session.scenario_id)` 호출
      3. `GameMasterPrompt`에 scenario.name, scenario.world_setting 전달 (기존 TODO 해결)
    - `app/game/container.py` 수정: ProcessActionUseCase 팩토리에 scenario_repository 주입
    - `app/game/dependencies.py` 수정: DI 와이어링 업데이트
  - TDD REFACTOR: 정리

  **Must NOT do**:
  - 주사위 로직 추가 금지 (Task 7에서 처리)
  - ScenarioRepositoryInterface 자체 수정 금지 (이미 존재)
  - 기존 테스트 삭제 금지

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 기존 TODO 해결 — 생성자에 파라미터 추가 + 1곳 메서드에서 repo 호출
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 프론트엔드 무관

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Task 7
  - **Blocked By**: None (Wave 1과 독립적이지만, Wave 2 시작은 Wave 1 완료 후)

  **References**:

  **Pattern References**:
  - `app/game/application/use_cases/process_action.py:59-75` — 기존 생성자 패턴 (여기에 scenario_repository 추가)
  - `app/game/application/use_cases/process_action.py:206-214` — 기존 TODO 위치 (scenario_name="", world_setting="" 하드코딩된 부분)
  - `app/game/container.py:123-133` — ProcessActionUseCase 팩토리 (여기에 `scenario_repository=self.scenario_repository()` 추가)
  - `app/game/container.py:113-115` — 이미 존재하는 `scenario_repository()` 메서드 (새로 만들 필요 없음)

  **API/Type References**:
  - `app/game/application/ports/__init__.py:69-80` — ScenarioRepositoryInterface (이미 존재, import만 추가하면 됨)
  - `app/game/domain/entities/scenario.py:ScenarioEntity` — name, world_setting, difficulty 필드
  - `app/game/domain/entities/game_session.py:GameSessionEntity` — scenario_id 필드

  **Test References**:
  - `tests/unit/application/test_process_action.py` — 기존 UseCase 테스트 (mock_repo 패턴, 여기에 scenario_repo mock 추가)

  **Acceptance Criteria**:
  - [ ] `uv run pytest tests/unit/application/test_process_action.py -v` → ALL PASS (기존 + 신규)
  - [ ] ProcessActionUseCase 생성자에 scenario_repository 파라미터 존재
  - [ ] GameMasterPrompt에 scenario.name, scenario.world_setting 전달됨
  - [ ] 기존 테스트 회귀 없음

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Scenario 정보가 LLM 프롬프트에 포함
    Tool: Bash (uv run pytest)
    Preconditions: scenario_repository mock 설정
    Steps:
      1. uv run pytest tests/unit/application/test_process_action.py -k "scenario" -v
      2. Assert: mock_scenario_repo.get_by_id가 session.scenario_id로 호출됨
      3. Assert: GameMasterPrompt 생성 시 scenario.name이 빈 문자열이 아님
    Expected Result: scenario loading tests pass
    Failure Indicators: scenario not loaded or name still empty
    Evidence: .sisyphus/evidence/task-4-scenario-loading.txt

  Scenario: 기존 process_action 테스트 회귀 없음
    Tool: Bash (uv run pytest)
    Preconditions: 수정 완료
    Steps:
      1. uv run pytest tests/unit/application/test_process_action.py -v
      2. Assert: ALL existing tests pass
    Expected Result: 0 failures
    Failure Indicators: any existing test breaks
    Evidence: .sisyphus/evidence/task-4-no-regression.txt
  ```

  **Commit**: YES
  - Message: `fix(game): load scenario in ProcessActionUseCase for difficulty`
  - Files: `app/game/application/use_cases/process_action.py`, `app/game/container.py`, `app/game/dependencies.py`, `tests/unit/application/test_process_action.py`
  - Pre-commit: `uv run pytest tests/unit/application/`

- [ ] 5. LLM 프롬프트 템플릿에 주사위 결과 섹션 추가

  **What to do**:
  - TDD RED: `tests/unit/domain/test_game_master_prompt.py` 작성 (또는 기존에 추가)
    - `GameMasterPrompt`에 `dice_result_section: str = ""` 속성 추가
    - `SYSTEM_PROMPT_TEMPLATE`에 주사위 결과 섹션 추가:
      ```
      ## 주사위 판정 결과
      {dice_result_section}

      ## 응답 규칙 (추가)
      - 주사위 판정 결과가 있는 경우, 결과에 따라 서술해야 합니다.
      - 성공 판정 시: 플레이어의 행동이 성공하는 서술
      - 실패 판정 시: 플레이어의 행동이 실패하는 서술
      - 크리티컬(대성공) 시: 극적으로 성공하는 서술
      - 펌블(대실패) 시: 상황이 악화되는 서술
      - 주사위 판정 결과는 절대적입니다. 판정 결과를 절대 뒤집지 마세요.
      ```
    - `build_dice_result_section(dice_result: DiceResult) -> str` 헬퍼 함수
    - 테스트: dice_result가 있을 때/없을 때 프롬프트 포맷
  - TDD GREEN: `app/llm/prompts/game_master.py` 수정
  - TDD REFACTOR: 정리
  - 주의: LLM 응답 JSON 스키마는 변경하지 않음 (입력 프롬프트만 수정)

  **Must NOT do**:
  - LLM 응답 JSON 스키마(narrative, options, state_changes) 변경 금지
  - 2회 LLM 호출 구조 도입 금지
  - dice_result를 LLM messages에 추가 금지 (system prompt에만 추가)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 프롬프트 템플릿 문자열 수정 + 헬퍼 함수 1개
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 프론트엔드 무관

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6)
  - **Blocks**: Task 7
  - **Blocked By**: Task 1 (DiceResult 타입 참조)

  **References**:

  **Pattern References**:
  - `app/llm/prompts/game_master.py:12-54` — 기존 SYSTEM_PROMPT_TEMPLATE (여기에 주사위 섹션 추가)
  - `app/llm/prompts/game_master.py:130-195` — GameMasterPrompt dataclass (여기에 dice_result_section 필드 추가)
  - `app/llm/prompts/game_master.py:161-185` — _format_game_state() 패턴 (유사한 포맷팅 메서드 참고)

  **API/Type References**:
  - Task 1의 `DiceResult` — display_text 속성 사용하여 섹션 텍스트 생성

  **Acceptance Criteria**:
  - [ ] `uv run pytest tests/unit/domain/test_game_master_prompt.py -v` → ALL PASS
  - [ ] dice_result가 있을 때 system_prompt에 "주사위 판정 결과" 섹션 포함
  - [ ] dice_result가 없을 때 해당 섹션 비어있음
  - [ ] "판정 결과를 절대 뒤집지 마세요" 문구 포함

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 주사위 결과가 있을 때 프롬프트 포맷
    Tool: Bash (uv run pytest)
    Preconditions: DiceResult 값 객체 완성 (Task 1)
    Steps:
      1. uv run pytest tests/unit/domain/test_game_master_prompt.py -k "with_dice" -v
      2. Assert: system_prompt 문자열에 "주사위 판정 결과" 포함
      3. Assert: system_prompt에 dice display_text 포함
      4. Assert: "절대 뒤집지 마세요" 문구 포함
    Expected Result: 1 passed
    Failure Indicators: prompt missing dice section
    Evidence: .sisyphus/evidence/task-5-prompt-with-dice.txt

  Scenario: 주사위 결과가 없을 때 프롬프트 변화 없음
    Tool: Bash (uv run pytest)
    Preconditions: 수정 완료
    Steps:
      1. uv run pytest tests/unit/domain/test_game_master_prompt.py -k "without_dice" -v
      2. Assert: system_prompt에 "주사위 판정 결과" 섹션이 비어있거나 없음
    Expected Result: 1 passed
    Failure Indicators: dice section appears when no dice result
    Evidence: .sisyphus/evidence/task-5-prompt-without-dice.txt
  ```

  **Commit**: YES
  - Message: `feat(llm): add dice result context to game master prompt`
  - Files: `app/llm/prompts/game_master.py`, `tests/unit/domain/test_game_master_prompt.py`
  - Pre-commit: `uv run pytest tests/unit/domain/test_game_master_prompt.py`

- [ ] 6. GameActionResponse에 dice_result 필드 추가

  **What to do**:
  - `app/game/presentation/routes/schemas/response.py`에:
    - `DiceResultResponse` Pydantic 모델 추가:
      - `roll: int`
      - `modifier: int`
      - `total: int`
      - `dc: int`
      - `is_success: bool`
      - `is_critical: bool`
      - `is_fumble: bool`
      - `check_type: str`
      - `damage: Optional[int] = None`
      - `display_text: str`
    - `GameActionResponse`에 `dice_result: Optional[DiceResultResponse] = None` 필드 추가
  - 기존 테스트가 깨지지 않는지 확인 (Optional이므로 기본값 None)
  - `DiceResult` 도메인 VO → `DiceResultResponse` DTO 변환 헬퍼 (선택적, Task 7에서도 가능)

  **Must NOT do**:
  - GameEndingResponse 수정 금지
  - 기존 필드 삭제/변경 금지
  - dice_result를 Required로 만들지 않음 (Optional 필수)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 기존 DTO에 Optional 필드 1개 추가 + 새 DTO 1개 생성
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 프론트엔드 무관

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5)
  - **Blocks**: Tasks 7, 8
  - **Blocked By**: Task 1 (DiceResult 구조 참고)

  **References**:

  **Pattern References**:
  - `app/game/presentation/routes/schemas/response.py:GameActionResponse` — 기존 응답 DTO (여기에 필드 추가)
  - `app/game/presentation/routes/schemas/response.py:GameMessageResponse` — 기존 DTO 구조 패턴

  **API/Type References**:
  - Task 1의 `DiceResult` — 필드 구조 참고 (도메인 VO → 프레젠테이션 DTO 매핑)

  **Acceptance Criteria**:
  - [ ] `uv run pytest --tb=short` → ALL PASS (기존 테스트 회귀 없음)
  - [ ] GameActionResponse에 `dice_result: Optional[DiceResultResponse] = None` 존재
  - [ ] DiceResultResponse에 roll, modifier, total, dc, is_success, is_critical, is_fumble, display_text 필드 존재

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 기존 테스트 회귀 없음
    Tool: Bash (uv run pytest)
    Preconditions: response.py 수정 완료
    Steps:
      1. uv run pytest --tb=short
      2. Assert: ALL existing tests pass (dice_result=None 기본값이므로 영향 없음)
    Expected Result: 0 failures
    Failure Indicators: any test fails due to response schema change
    Evidence: .sisyphus/evidence/task-6-no-regression.txt

  Scenario: DiceResultResponse 직렬화
    Tool: Bash (uv run python -c "...")
    Preconditions: DTO 추가 완료
    Steps:
      1. uv run python -c "from app.game.presentation.routes.schemas.response import DiceResultResponse; r = DiceResultResponse(roll=15, modifier=2, total=17, dc=12, is_success=True, is_critical=False, is_fumble=False, check_type='COMBAT', display_text='test'); print(r.model_dump_json())"
      2. Assert: 유효한 JSON 출력, 모든 필드 포함
    Expected Result: valid JSON with all fields
    Failure Indicators: ValidationError or missing fields
    Evidence: .sisyphus/evidence/task-6-dto-serialization.txt
  ```

  **Commit**: YES
  - Message: `feat(game): add dice_result field to GameActionResponse`
  - Files: `app/game/presentation/routes/schemas/response.py`
  - Pre-commit: `uv run pytest --tb=short`

- [ ] 7. ProcessActionUseCase에 주사위 시스템 통합

  **What to do**:
  - TDD RED: `tests/unit/application/test_process_action_dice.py` 작성
    - 시나리오: 일반 성공 (roll > DC)
    - 시나리오: 일반 실패 (roll < DC)
    - 시나리오: 크리티컬 (nat 20) — 데미지 2배, hp_change override
    - 시나리오: 펌블 (nat 1) — 자해 데미지, hp_change override
    - 시나리오: HP=0 → 즉시 게임 오버 (EndingType.DEFEAT)
    - 시나리오: 서버 dice damage가 LLM hp_change를 override
    - 시나리오: dice_result가 API 응답에 포함
  - TDD GREEN: `app/game/application/use_cases/process_action.py` 수정:
    1. `_handle_normal_turn`에서 LLM 호출 전에:
       - `scenario = await self._scenario_repo.get_by_id(session.scenario_id)` (Task 4에서 준비됨)
       - `character = await self._character_repo.get_by_id(session.character_id)`
       - `dice_result = DiceService.perform_check(character.stats.level, scenario.difficulty)`
    2. `GameMasterPrompt`에 `dice_result_section` 전달 (Task 5에서 준비된 빌더 사용)
    3. LLM 응답 파싱 후:
       - `parsed` 결과의 `state_changes.hp_change`를 주사위 데미지로 override:
         - 성공 시: `hp_change = -dice_result.damage` (적에게 데미지 → 서버는 narrative 목적, 실제 적 HP 없으므로 hp_change 0 유지)
         - 실패 시: `hp_change = 0` (LLM이 정한 hp_change 무시)
         - 크리티컬: `hp_change` LLM이 정한 대로 (보너스 효과는 내러티브에 반영)
         - 펌블: `hp_change = -dice_result.damage` (자해 데미지)
       - 주의: 이 게임은 적에게 별도 HP가 없으므로 데미지는 주로 펌블 자해와 LLM이 서술하는 피해로 처리
       - **핵심 규칙**: 펌블(nat 1)일 때만 서버가 hp_change를 강제 override (자해 데미지). 성공/실패/크리티컬에서는 LLM의 hp_change를 존중하되, dice_result를 전달하여 LLM이 참고하도록 함
    4. HP=0 체크: `GameMasterService.should_end_game_by_death(character.stats)` → True이면 `_handle_ending` 호출
    5. `GameActionResponse`에 `dice_result=DiceResultResponse(...)` 포함
  - TDD REFACTOR: 중복 코드 정리, 메서드 분리

  **Must NOT do**:
  - DiceService 자체 수정 금지 (Task 2에서 완성됨)
  - LLM 응답 JSON 스키마 변경 금지
  - 2회 LLM 호출 도입 금지
  - ProcessActionUseCase의 주사위 외 리팩터링 금지

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 핵심 통합 태스크. 여러 서비스/VO를 조합하고, 기존 코드 수정 범위가 넓으며, hp_change override 로직이 까다로움
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 프론트엔드 무관

  **Parallelization**:
  - **Can Run In Parallel**: NO (Wave 3 단독)
  - **Parallel Group**: Wave 3 (단독)
  - **Blocks**: Tasks 8, 9
  - **Blocked By**: Tasks 1, 2, 3, 4, 5, 6 (모든 선행 태스크)

  **References**:

  **Pattern References**:
  - `app/game/application/use_cases/process_action.py:186-397` — `_handle_normal_turn` 전체 흐름 (이 메서드 내에 주사위 로직 삽입)
  - `app/game/application/use_cases/process_action.py:253-326` — state_changes 처리 패턴 (hp_change override 지점)
  - `app/game/application/use_cases/process_action.py:380-397` — GameActionResponse 생성 패턴 (dice_result 필드 추가 지점)

  **API/Type References**:
  - Task 1: `DiceResult`, `DiceCheckType` — 도메인 VO
  - Task 2: `DiceService.perform_check()` — 주사위 판정 호출
  - Task 3: `GameMasterService.should_end_game_by_death()` — HP=0 체크
  - Task 5: `build_dice_result_section()` — 프롬프트 섹션 빌더
  - Task 6: `DiceResultResponse` — API 응답 DTO

  **Test References**:
  - `tests/unit/application/test_process_action.py` — 기존 UseCase 테스트 패턴 (AsyncMock, mock_repo fixture)

  **Acceptance Criteria**:
  - [ ] `uv run pytest tests/unit/application/test_process_action_dice.py -v` → ALL PASS
  - [ ] `uv run pytest tests/unit/application/test_process_action.py -v` → 기존 테스트 회귀 없음
  - [ ] 주사위 결과가 LLM 프롬프트에 포함
  - [ ] 펌블(nat 1) 시 자해 데미지가 캐릭터 HP에 적용
  - [ ] HP=0 시 게임 오버 (DEFEAT) 처리
  - [ ] API 응답에 dice_result 포함

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 일반 성공 — 주사위 결과가 API 응답에 포함
    Tool: Bash (uv run pytest)
    Preconditions: 모든 선행 Task 완료, mock random = 15
    Steps:
      1. uv run pytest tests/unit/application/test_process_action_dice.py::TestProcessActionDice::test_normal_success -v
      2. Assert: response.dice_result is not None
      3. Assert: response.dice_result.is_success == True
      4. Assert: response.dice_result.roll == 15
    Expected Result: 1 passed
    Failure Indicators: dice_result missing or is_success wrong
    Evidence: .sisyphus/evidence/task-7-normal-success.txt

  Scenario: 펌블 (nat 1) — 자해 데미지 적용
    Tool: Bash (uv run pytest)
    Preconditions: mock random = 1 for d20, mock random for 1d4 damage
    Steps:
      1. uv run pytest tests/unit/application/test_process_action_dice.py::TestProcessActionDice::test_fumble_self_damage -v
      2. Assert: dice_result.is_fumble == True
      3. Assert: character HP decreased by fumble damage
      4. Assert: character_repo.save called with reduced HP
    Expected Result: 1 passed
    Failure Indicators: no self damage applied on fumble
    Evidence: .sisyphus/evidence/task-7-fumble-self-damage.txt

  Scenario: HP=0 → 즉시 게임 오버
    Tool: Bash (uv run pytest)
    Preconditions: character HP=1, fumble damage >= 1
    Steps:
      1. uv run pytest tests/unit/application/test_process_action_dice.py::TestProcessActionDice::test_hp_zero_death -v
      2. Assert: session completed with EndingType.DEFEAT
      3. Assert: response is GameEndingResponse
    Expected Result: 1 passed
    Failure Indicators: game continues after HP=0
    Evidence: .sisyphus/evidence/task-7-hp-zero-death.txt

  Scenario: 전체 테스트 스위트 회귀 없음
    Tool: Bash (uv run pytest)
    Preconditions: 모든 수정 완료
    Steps:
      1. uv run pytest --tb=short
      2. Assert: ALL tests pass (기존 + 신규)
    Expected Result: 0 failures, 0 errors
    Failure Indicators: any test failure
    Evidence: .sisyphus/evidence/task-7-full-regression.txt
  ```

  **Commit**: YES
  - Message: `feat(game): integrate dice system into ProcessActionUseCase`
  - Files: `app/game/application/use_cases/process_action.py`, `tests/unit/application/test_process_action_dice.py`
  - Pre-commit: `uv run pytest tests/unit/application/`

- [ ] 8. 프론트엔드 API 타입 업데이트

  **What to do**:
  - `ai_saga_front/src/types/api.ts`에:
    - `DiceResult` TypeScript 인터페이스 추가:
      ```typescript
      interface DiceResult {
        roll: number;
        modifier: number;
        total: number;
        dc: number;
        is_success: boolean;
        is_critical: boolean;
        is_fumble: boolean;
        check_type: string;
        damage: number | null;
        display_text: string;
      }
      ```
    - 기존 게임 액션 응답 타입에 `dice_result?: DiceResult` 필드 추가
  - `ai_saga_front/src/services/gameService.ts`에서 응답 타입 사용 확인

  **Must NOT do**:
  - 프론트엔드 컴포넌트 수정 금지 (Task 9에서 처리)
  - 기존 타입 삭제/변경 금지

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: TypeScript 인터페이스 1개 추가 + 기존 타입에 optional 필드 1개 추가
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 컴포넌트 아닌 타입 파일만 수정

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 9, 단 Task 9는 Task 8 이후)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 6, 7

  **References**:

  **Pattern References**:
  - `/Users/kitaekang/Documents/dev/ai_saga_front/src/types/api.ts` — 기존 TypeScript 타입 정의 패턴 (인터페이스 구조, 네이밍)

  **API/Type References**:
  - Task 6의 `DiceResultResponse` — 백엔드 DTO 필드와 1:1 매핑

  **Acceptance Criteria**:
  - [ ] `DiceResult` 인터페이스가 `types/api.ts`에 존재
  - [ ] 게임 액션 응답 타입에 `dice_result?: DiceResult` 필드 존재
  - [ ] `npm run build` (또는 `bun run build`) 에러 없음

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 프론트엔드 빌드 성공
    Tool: Bash (npm run build)
    Preconditions: 타입 파일 수정 완료
    Steps:
      1. cd ai_saga_front && npm run build
      2. Assert: exit code 0, no TypeScript errors
    Expected Result: Build successful
    Failure Indicators: TypeScript compilation error
    Evidence: .sisyphus/evidence/task-8-frontend-build.txt

  Scenario: DiceResult 타입이 올바르게 정의됨
    Tool: Bash (grep)
    Preconditions: 타입 파일 수정 완료
    Steps:
      1. grep -n "DiceResult" ai_saga_front/src/types/api.ts
      2. Assert: interface DiceResult 정의 존재, dice_result 필드 존재
    Expected Result: grep finds DiceResult definition
    Failure Indicators: DiceResult not found
    Evidence: .sisyphus/evidence/task-8-type-definition.txt
  ```

  **Commit**: YES (Task 9와 함께)
  - Message: `feat(frontend): add DiceResult type and DiceResultPanel component`
  - Files: `ai_saga_front/src/types/api.ts`
  - Pre-commit: `npm run build` (in ai_saga_front)

- [ ] 9. DiceResultPanel 컴포넌트 + GameSession 통합

  **What to do**:
  - `ai_saga_front/src/components/game/DiceResultPanel.tsx` 생성:
    - Props: `diceResult: DiceResult | null`
    - null이면 렌더링 안 함
    - 표시 형식: 깔끔한 패널/배지
      - 주사위 아이콘 + "1d20+{modifier} = {total} vs DC {dc}"
      - 성공: 초록색 배경 + "성공!"
      - 실패: 빨간색 배경 + "실패..."
      - 크리티컬: 금색 배경 + "대성공!" + 글로우 효과
      - 펌블: 진한 빨간색 배경 + "대실패!" + 경고 아이콘
      - 데미지 표시 (있을 경우): "데미지: {damage}"
    - Tailwind CSS 사용
    - `sanabi-gold` (#FFD700) 크리티컬 색상
  - `ai_saga_front/src/pages/GameSession.tsx`에 DiceResultPanel 통합:
    - AI 응답 메시지 위에 주사위 결과 패널 표시
    - dice_result가 null이면 표시 안 함 (기존 동작 유지)

  **Must NOT do**:
  - 3D/CSS 주사위 애니메이션 추가 금지
  - three.js 등 추가 라이브러리 설치 금지
  - 기존 GameSession 레이아웃 대폭 변경 금지

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI 컴포넌트 생성, Tailwind 스타일링, 조건부 렌더링
  - **Skills**: [`playwright`]
    - `playwright`: 컴포넌트 렌더링 확인용 스크린샷 캡처
  - **Skills Evaluated but Omitted**:
    - `git-master`: 단순 커밋

  **Parallelization**:
  - **Can Run In Parallel**: NO (Task 8 이후)
  - **Parallel Group**: Wave 4 (Task 8 이후)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 8

  **References**:

  **Pattern References**:
  - `/Users/kitaekang/Documents/dev/ai_saga_front/src/components/game/` — 기존 게임 컴포넌트 구조/스타일 패턴
  - `/Users/kitaekang/Documents/dev/ai_saga_front/src/pages/GameSession.tsx` — 게임 세션 페이지 레이아웃 (DiceResultPanel 삽입 지점)

  **API/Type References**:
  - Task 8의 `DiceResult` TypeScript 인터페이스 — 컴포넌트 Props 타입
  - `/Users/kitaekang/Documents/dev/ai_saga_front/src/services/gameService.ts` — API 응답에서 dice_result 접근 패턴

  **External References**:
  - Tailwind CSS: 색상 클래스 (bg-green-500, bg-red-500, text-yellow-400)

  **Acceptance Criteria**:
  - [ ] DiceResultPanel.tsx 파일 존재
  - [ ] GameSession.tsx에서 DiceResultPanel import 및 사용
  - [ ] `npm run build` 에러 없음
  - [ ] dice_result가 null일 때 패널 미표시

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 크리티컬 주사위 결과 패널 렌더링
    Tool: Playwright
    Preconditions: 프론트엔드 dev 서버 실행, 백엔드 API에서 dice_result 포함 응답
    Steps:
      1. Navigate to game session page
      2. Perform an action that triggers dice roll
      3. Wait for AI response with dice_result
      4. Assert: .dice-result-panel element visible
      5. Assert: panel contains "1d20" text
      6. Screenshot capture
    Expected Result: Dice result panel visible with correct formatting
    Failure Indicators: panel not rendered, missing dice info
    Evidence: .sisyphus/evidence/task-9-dice-panel-critical.png

  Scenario: dice_result null일 때 패널 미표시
    Tool: Playwright
    Preconditions: 프론트엔드 dev 서버 실행
    Steps:
      1. Navigate to game session page
      2. Check initial state (no dice result yet)
      3. Assert: .dice-result-panel element NOT present in DOM
    Expected Result: No dice panel when dice_result is null
    Failure Indicators: empty panel visible
    Evidence: .sisyphus/evidence/task-9-dice-panel-null.png

  Scenario: 프론트엔드 빌드 성공
    Tool: Bash (npm run build)
    Preconditions: 모든 프론트엔드 파일 수정 완료
    Steps:
      1. cd ai_saga_front && npm run build
      2. Assert: exit code 0
    Expected Result: Build successful
    Failure Indicators: TypeScript or build error
    Evidence: .sisyphus/evidence/task-9-frontend-build.txt
  ```

  **Commit**: YES (Task 8과 함께)
  - Message: `feat(frontend): add DiceResultPanel component and GameSession integration`
  - Files: `ai_saga_front/src/components/game/DiceResultPanel.tsx`, `ai_saga_front/src/pages/GameSession.tsx`
  - Pre-commit: `npm run build` (in ai_saga_front)

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `uv run black --check app/ tests/`, `uv run isort --check app/ tests/`, `uv run flake8 app/ tests/`, `uv run pytest --tb=short`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill for frontend)
  Start the dev server (`uv run uvicorn app.main:app --reload`). Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (dice result flows from domain → use case → API → frontend). Test edge cases: nat 20, nat 1, HP=0 death, very high level modifier. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Task | Commit Message | Files | Pre-commit |
|------|---------------|-------|------------|
| 1 | `feat(game): add DiceResult and DiceCheckType value objects` | `app/game/domain/value_objects/dice.py`, `app/game/domain/value_objects/__init__.py`, `tests/unit/domain/test_dice_value_objects.py` | `uv run pytest tests/unit/domain/test_dice_value_objects.py` |
| 2 | `feat(game): add DiceService domain service with d20 mechanics` | `app/game/domain/services/dice_service.py`, `app/game/domain/services/__init__.py`, `tests/unit/domain/test_dice_service.py` | `uv run pytest tests/unit/domain/test_dice_service.py` |
| 3 | `feat(game): add HP zero death check to GameMasterService` | `app/game/domain/services/game_master_service.py`, `tests/unit/domain/test_game_master_service.py` | `uv run pytest tests/unit/domain/test_game_master_service.py` |
| 4 | `fix(game): load scenario in ProcessActionUseCase for difficulty` | `app/game/application/use_cases/process_action.py`, `app/game/application/ports/__init__.py`, `tests/unit/application/test_process_action.py` | `uv run pytest tests/unit/application/` |
| 5 | `feat(llm): add dice result context to game master prompt` | `app/llm/prompts/game_master.py`, `tests/unit/domain/test_game_master_prompt.py` | `uv run pytest tests/unit/domain/test_game_master_prompt.py` |
| 6 | `feat(game): add dice_result field to GameActionResponse` | `app/game/presentation/routes/schemas/response.py` | `uv run pytest` |
| 7 | `feat(game): integrate dice system into ProcessActionUseCase` | `app/game/application/use_cases/process_action.py`, `tests/unit/application/test_process_action_dice.py` | `uv run pytest tests/unit/application/` |
| 8+9 | `feat(frontend): add DiceResultPanel component and API types` | Frontend files | `npm run build` (in ai_saga_front) |

---

## Success Criteria

### Verification Commands
```bash
# All tests pass (existing + new)
uv run pytest --tb=short
# Expected: ALL PASSED, 0 failures

# Lint/format check
uv run black --check app/ tests/ && uv run isort --check app/ tests/ && uv run flake8 app/ tests/
# Expected: exit code 0

# Specific dice tests
uv run pytest tests/unit/domain/test_dice_service.py tests/unit/domain/test_dice_value_objects.py -v
# Expected: ALL PASSED

# Integration tests
uv run pytest tests/unit/application/test_process_action_dice.py -v
# Expected: ALL PASSED
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All existing tests still pass (zero regression)
- [ ] All new dice tests pass
- [ ] Lint/format clean
- [ ] Frontend builds without errors
- [ ] dice_result field is Optional (backward compatible)

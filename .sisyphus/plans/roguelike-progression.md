# Plan: Roguelike Meta-Progression System

## Goal
유저에게 게임 레벨과 경험치를 추가하고, 캐릭터 생성 시 유저 레벨을 상속하며, 게임 완료 시 유저 레벨을 올리는 로그라이크 메타 프로그레션 구현.

## Design Decisions
- 레벨업 시점: 게임 완료 시 (승리/패배/중립 결과 기반 XP)
- 캐릭터 레벨: 게임 중 독립적으로 유지 (유저 레벨은 시작 레벨만 결정)
- 레벨 상속 범위: 시작 레벨 + HP (레벨 비례)
- XP 공식: 승리 200+(턴×10), 패배 50+(턴×5), 중립 100+(턴×7). 난이도 보너스 ×1.5
- 레벨업 필요량: level × 300 (예: Lv1→Lv2: 300XP, Lv2→Lv3: 600XP)
- HP 공식: 100 + (level-1) × 10 (기존 level_up 로직과 일치)
- DB: 마이그레이션 없이 DB 초기화 후 재생성
- Cross-domain: Game domain에 `UserProgressionInterface` 포트 → Auth infrastructure에서 구현
- 프론트엔드: 유저 레벨 표시 + 게임 결과 화면 XP UI 포함

## Architecture

### Cross-domain 의존성 해결

```
Game Domain                  Auth Domain
┌──────────────────┐         ┌────────────────────────────┐
│ UserProgression  │         │ UserProgressionRepositoryImpl│
│ Interface (Port) │◄────────│ (구현체, DB + 도메인 로직)  │
└──────────────────┘         └────────────────────────────┘
         ▲
         │ DI Container (GameContainer)에서 주입
```

GameContainer가 초기화 시 `db` 세션을 받아서 Auth 인프라의 구현체를 Game의 포트에 주입함.

---

## Tasks

### PHASE 1: Auth Domain — UserEntity 확장

#### Task 1.1: UserEntity에 game_level, game_experience 필드 추가
- **File**: `app/auth/domain/entities/user.py`
- **RED**: `tests/unit/domain/test_user_entity.py` — `test_gain_game_experience`, `test_game_level_up`, `test_game_experience_for_next_level`
- **Action**:
  - `UserEntity`에 `game_level: int = Field(ge=1, default=1)` 추가
  - `UserEntity`에 `game_experience: int = Field(ge=0, default=0)` 추가
  - `UserEntity`에 `game_current_experience: int = Field(ge=0, default=0)` 추가
  - `game_experience_for_next_level()` 메서드: `return self.game_level * 300`
  - `gain_game_experience(amount: int) -> "UserEntity"` 메서드: CharacterStats.gain_experience 패턴 동일하게
    - XP 누적 후 `while current_exp >= next_level_exp: level_up`
  - `_game_level_up_once() -> "UserEntity"` 내부 메서드
- **GREEN**: 테스트 통과
- **Verify**: `lsp_diagnostics` clean

#### Task 1.2: User ORM 모델 컬럼 추가
- **File**: `app/auth/infrastructure/persistence/models/user_models.py`
- **Action**:
  - `game_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)`
  - `game_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`
  - `game_current_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`
- **No test needed** (ORM model, DB schema change)

#### Task 1.3: UserMapper 업데이트
- **File**: `app/auth/infrastructure/persistence/mappers.py`
- **Action**:
  - `to_entity`: `game_level=orm.game_level`, `game_experience=orm.game_experience`, `game_current_experience=orm.game_current_experience` 추가
  - `to_dict`: 세 필드 추가
- **No separate test needed** (covered by integration tests)

#### Task 1.4: Alembic 마이그레이션 생성
- **Command**: `uv run alembic revision --autogenerate -m "add game level and experience to users"`
- **Verify**: 생성된 파일 확인 — `game_level`, `game_experience`, `game_current_experience` 컬럼이 있는지

---

### PHASE 2: Game Domain — UserProgressionInterface 포트

#### Task 2.1: UserProgressionInterface 정의
- **File**: `app/game/application/ports/__init__.py` (또는 별도 파일 `user_progression.py`)
- **RED**: `tests/unit/application/test_create_character_user_level.py` — 인터페이스 import 검증
- **Action**: Game의 `application/ports/` 에 `UserProgressionInterface(ABC)` 추가
  ```python
  class UserProgressionInterface(ABC):
      @abstractmethod
      async def get_user_game_level(self, user_id: UUID) -> int: ...

      @abstractmethod
      async def award_game_experience(
          self, user_id: UUID, xp: int
      ) -> "UserProgressionResult": ...
  ```
- **UserProgressionResult**: `game_level`, `game_experience`, `leveled_up: bool`, `levels_gained: int` 포함

#### Task 2.2: UserProgressionService 도메인 서비스
- **File**: `app/game/domain/services/user_progression_service.py`
- **RED**: `tests/unit/domain/test_user_progression_service.py`
  - `test_calculate_xp_victory`
  - `test_calculate_xp_defeat`
  - `test_calculate_xp_neutral`
  - `test_calculate_xp_difficulty_bonus`
- **Action**: 순수 XP 계산 로직 (I/O 없음)
  ```python
  class UserProgressionService:
      @staticmethod
      def calculate_game_xp(
          ending_type: EndingType, turn_count: int, difficulty: ScenarioDifficulty
      ) -> int:
          base = {VICTORY: 200, DEFEAT: 50, NEUTRAL: 100}[ending_type]
          per_turn = {VICTORY: 10, DEFEAT: 5, NEUTRAL: 7}[ending_type]
          xp = base + (turn_count * per_turn)
          if difficulty in (ScenarioDifficulty.HARD, ScenarioDifficulty.NIGHTMARE):
              xp = int(xp * 1.5)
          return xp

      @staticmethod
      def calculate_starting_hp(level: int) -> int:
          return 100 + (level - 1) * 10
  ```
- **GREEN**: 테스트 통과
- **Verify**: `lsp_diagnostics` clean

---

### PHASE 3: Auth Infrastructure — UserProgressionInterface 구현

#### Task 3.1: UserProgressionRepositoryImpl 구현
- **File**: `app/auth/infrastructure/repositories/user_progression_repository.py`
- **Action**:
  - `UserProgressionRepositoryImpl(UserProgressionInterface)` 구현
  - `get_user_game_level`: DB에서 user의 `game_level` 조회
  - `award_game_experience`: user 로드 → `gain_game_experience(xp)` → `save` → `UserProgressionResult` 반환
- **Note**: 이 구현체는 Auth infrastructure에 있지만 Game의 Port를 구현함 (의존성 역전)
- **No unit test** (DB 접근 — integration test 대상이지만 환경 제약으로 스킵)

---

### PHASE 4: CreateCharacterUseCase — 유저 레벨 상속

#### Task 4.1: CreateCharacterUseCase 수정
- **File**: `app/game/application/use_cases/create_character.py`
- **RED**: `tests/unit/application/test_create_character_user_level.py`
  - `test_character_inherits_user_level_1` — 유저 Lv1이면 캐릭터 Lv1, HP 100
  - `test_character_inherits_user_level_3` — 유저 Lv3이면 캐릭터 Lv3, HP 120
  - `test_character_inherits_user_level_5` — 유저 Lv5이면 캐릭터 Lv5, HP 140
- **Action**:
  - `CreateCharacterUseCase.__init__`에 `user_progression: UserProgressionInterface` 파라미터 추가
  - `execute()` 내에서 `user_level = await self._user_progression.get_user_game_level(user_id)`
  - `starting_hp = UserProgressionService.calculate_starting_hp(user_level)`
  - `CharacterStats(hp=starting_hp, max_hp=starting_hp, level=user_level)` 로 생성
- **GREEN**: 테스트 통과
- **Verify**: `lsp_diagnostics` clean

---

### PHASE 5: 게임 완료 시 유저 XP 부여

#### Task 5.1: ProcessActionUseCase._handle_ending 수정
- **File**: `app/game/application/use_cases/process_action.py`
- **RED**: `tests/unit/application/test_process_action_user_xp.py`
  - `test_ending_awards_user_xp_victory`
  - `test_ending_awards_user_xp_defeat`
  - `test_ending_awards_user_xp_neutral`
- **Action**:
  - `ProcessActionUseCase.__init__`에 `user_progression: UserProgressionInterface` 추가
  - `_handle_ending()` 내에서 엔딩 타입 결정 후:
    ```python
    xp = UserProgressionService.calculate_game_xp(
        ending_type, session.turn_count, scenario.difficulty
    )
    progression_result = await self._user_progression.award_game_experience(user_id, xp)
    ```
  - `GameEndingResponse`에 `xp_gained`, `new_level`, `leveled_up` 필드 추가

#### Task 5.2: ProcessActionUseCase._handle_death_ending 수정
- **File**: `app/game/application/use_cases/process_action.py`
- **Action**:
  - 사망 엔딩도 DEFEAT XP 부여 (동일 로직)
  - `GameActionResponse`에 `xp_gained`, `leveled_up` 옵셔널 필드 추가 (엔딩 시에만 값 존재)

#### Task 5.3: GenerateEndingUseCase 수정
- **File**: `app/game/application/use_cases/generate_ending.py`
- **Action**:
  - `user_progression: UserProgressionInterface` 추가
  - 엔딩 생성 후 XP 부여 로직 동일하게 적용
  - `user_id`를 `execute()` 파라미터로 받도록 수정 (`GenerateEndingInput`에 이미 있음)
  - `GameEndingResponse`에 `xp_gained`, `new_level`, `leveled_up` 추가

---

### PHASE 6: API Response 업데이트

#### Task 6.1: GameEndingResponse에 XP 필드 추가
- **File**: `app/game/presentation/routes/schemas/response.py`
- **Action**:
  ```python
  class GameEndingResponse(BaseModel):
      ...
      xp_gained: int = 0
      new_game_level: int = 1
      leveled_up: bool = False
      levels_gained: int = 0
  ```

#### Task 6.2: GameActionResponse에 XP 필드 추가 (사망 엔딩용)
- **File**: `app/game/presentation/routes/schemas/response.py`
- **Action**:
  ```python
  class GameActionResponse(BaseModel):
      ...
      xp_gained: Optional[int] = None        # 엔딩(사망)일 때만 값 있음
      leveled_up: Optional[bool] = None
      new_game_level: Optional[int] = None
  ```

#### Task 6.3: Auth UserResponse에 게임 레벨 필드 추가
- **File**: `app/auth/presentation/routes/schemas/response.py`
- **Action**: `UserResponse`, `UserWithSocialAccountsResponse`에
  ```python
  game_level: int = 1
  game_experience: int = 0
  game_current_experience: int = 0
  game_experience_to_next_level: int = 300
  ```

---

### PHASE 7: DI Container 연결

#### Task 7.1: GameContainer에 UserProgression 주입
- **File**: `app/game/container.py`
- **Action**:
  - Auth의 `UserProgressionRepositoryImpl` import
  - `self.user_progression_repository()` 팩토리 메서드 추가
  - `create_character_use_case()`, `process_action_use_case()`, `generate_ending_use_case()`에 `user_progression=self.user_progression_repository()` 주입

---

### PHASE 8: Alembic Migration 적용

#### Task 8.1: DB 재생성
- **Command**:
  ```bash
  uv run alembic downgrade base   # 혹은 DB 직접 DROP/CREATE
  uv run alembic upgrade head
  ```
- **Verify**: `uv run pytest tests/unit/ -v` 전체 통과

---

### PHASE 9: 프론트엔드

#### Task 9.1: API 타입 업데이트
- **File**: `/Users/kitaekang/Documents/dev/ai_saga_front/src/types/api.ts`
- **Action**:
  - `GameEndingResponse`에 `xp_gained`, `new_game_level`, `leveled_up`, `levels_gained` 추가
  - `GameActionResponse`에 옵셔널 XP 필드 추가
  - `UserResponse`에 `game_level`, `game_experience`, `game_current_experience`, `game_experience_to_next_level` 추가

#### Task 9.2: 유저 레벨 표시 컴포넌트
- **Location**: 헤더 또는 프로필 영역에 유저 레벨 배지 추가
- **File**: 기존 레이아웃 컴포넌트 확인 후 결정
- **Content**: `Lv.{game_level}` + XP 프로그레스 바

#### Task 9.3: 게임 결과 화면 XP UI
- **Location**: 게임 엔딩 화면 (`GameSession.tsx` 또는 결과 모달)
- **Content**:
  - 획득 XP 표시: `+{xp_gained} XP`
  - 레벨업 시 애니메이션/강조: `🎉 레벨업! Lv.{old} → Lv.{new_game_level}`
  - 현재 레벨 진행도 표시

---

### PHASE 10: 검증

#### Task 10.1: 전체 단위 테스트 실행
- **Command**: `uv run pytest tests/unit/ -v`
- **기대**: 전체 통과 (기존 269개 + 신규 ~15개)

#### Task 10.2: Lint/Format
- **Command**: `uv run black app/ tests/ && uv run isort app/ tests/ && uv run flake8 app/ tests/`
- **기대**: 에러 없음

---

## File Touch Map

| 파일 | 변경 유형 |
|------|---------|
| `app/auth/domain/entities/user.py` | 수정 — game_level, game_experience 필드 + 메서드 |
| `app/auth/infrastructure/persistence/models/user_models.py` | 수정 — 3개 컬럼 추가 |
| `app/auth/infrastructure/persistence/mappers.py` | 수정 — 필드 매핑 추가 |
| `app/auth/infrastructure/repositories/user_progression_repository.py` | **신규** |
| `app/auth/presentation/routes/schemas/response.py` | 수정 — UserResponse 필드 추가 |
| `app/game/application/ports/__init__.py` | 수정 — UserProgressionInterface 추가 |
| `app/game/domain/services/user_progression_service.py` | **신규** |
| `app/game/domain/services/__init__.py` | 수정 — export 추가 |
| `app/game/application/use_cases/create_character.py` | 수정 — 유저 레벨 상속 |
| `app/game/application/use_cases/process_action.py` | 수정 — 엔딩 시 XP 부여 |
| `app/game/application/use_cases/generate_ending.py` | 수정 — XP 부여 |
| `app/game/presentation/routes/schemas/response.py` | 수정 — Response에 XP 필드 |
| `app/game/container.py` | 수정 — UserProgression DI 연결 |
| `migrations/versions/xxx_add_game_level_to_users.py` | **신규** (autogenerate) |
| `tests/unit/domain/test_user_entity.py` | **신규** |
| `tests/unit/domain/test_user_progression_service.py` | **신규** |
| `tests/unit/application/test_create_character_user_level.py` | **신규** |
| `tests/unit/application/test_process_action_user_xp.py` | **신규** |
| `/ai_saga_front/src/types/api.ts` | 수정 |
| `/ai_saga_front/src/...` | 수정 — 레벨 UI 컴포넌트 |

## Edge Cases to Handle

1. **유저 조회 실패**: `get_user_game_level()` 실패 시 기본값 Lv1 fallback (또는 ServerError)
2. **XP 부여 실패**: 게임 완료 메시지는 이미 저장됐으므로 XP 부여 실패는 로그만 남기고 무시 (게임 데이터 손실 방지)
3. **동시성**: 동일 유저가 여러 게임 동시 완료 — `award_game_experience`는 DB 트랜잭션 내 원자적 처리
4. **사망 엔딩 user_id**: `_handle_death_ending()`은 현재 `user_id` 파라미터가 없음 → 추가 필요

## Acceptance Criteria

- [ ] `UserEntity.gain_game_experience()` XP 누적 및 자동 레벨업 작동
- [ ] 유저 Lv3로 캐릭터 생성 시 → 캐릭터 Lv3, HP 120으로 시작
- [ ] 게임 승리 완료 시 → `GameEndingResponse.xp_gained` > 0, `new_game_level` 반영
- [ ] 게임 패배(사망) 시 → XP 부여 (DEFEAT 공식 적용)
- [ ] `GET /api/v1/auth/self/` → `game_level`, `game_experience` 반환
- [ ] 프론트엔드 게임 결과 화면에 획득 XP 표시
- [ ] 프론트엔드 헤더/프로필에 유저 레벨 표시
- [ ] 전체 단위 테스트 통과
- [ ] lint/format clean

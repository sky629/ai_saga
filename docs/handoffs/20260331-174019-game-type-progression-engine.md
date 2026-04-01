# Common Handoff Template

## 1. Metadata

- Mode: `thread`
- Handoff Type: `phase`
- Title: 시나리오 game_type 도입 및 progression 게임 엔진 분리
- Owner: Codex
- Status: `done`
- Related Branch: `dev`
- Related Worktree:
- Related Files:
  - `app/game/domain/entities/scenario.py`
  - `app/game/infrastructure/persistence/models/game_models.py`
  - `app/game/infrastructure/persistence/mappers.py`
  - `app/game/application/queries/get_scenarios.py`
  - `app/game/presentation/routes/schemas/response.py`
  - `app/game/application/use_cases/start_game.py`
  - `app/game/application/use_cases/process_action.py`
  - `app/dev/routes.py`
  - `migrations/versions/72c1f5a14d56_initial_schema_reset.py`

## 2. Input

- Request summary:
  - 시나리오별 게임 타입을 구분하고 기존 TRPG와 신규 progression 타입을 분기 처리
  - progression은 턴=개월 구조를 사용
  - progression의 현재 상태는 별도 컬럼 대신 `game_state`에 저장
  - 레거시 호환 없이 DB/Alembic 초기화 전제로 구조 정리
- Preconditions:
  - 브랜치 `dev`에서 작업
  - 기존 데이터 마이그레이션/backfill 불필요
- Dependencies:
  - FastAPI game routes
  - scenario/session/message persistence
  - LLM/image generation services
- Required references:
  - `AGENTS.md`
  - `TEAM_OPERATIONS_GUIDE.md`
  - `docs/HANDOFF_TEMPLATE.md`

## 3. Scope

- In scope:
  - `Scenario.game_type` 필수화
  - 시나리오 조회 응답에 `game_type` 노출
  - start/process 흐름을 game_type 기준으로 분기
  - progression 기본 오프닝/턴 처리 추가
- Out of scope:
  - 프론트엔드 렌더링 변경
  - 기존 DB 데이터 호환
  - 운영 마이그레이션/backfill
- Allowed write scope:
  - `app/game/**`
  - `app/dev/routes.py`
  - `migrations/versions/72c1f5a14d56_initial_schema_reset.py`
  - `tests/**`
  - `docs/handoffs/**`
- Forbidden write scope:
  - `app/auth/**`
  - 외부 인프라 설정 파일

## 4. Decisions and Contract

- Confirmed decisions:
  - `turn == month`로 해석
  - progression 상태는 `session.game_state` + `message.parsed_response` 조합으로 관리
  - 레거시 fallback 없이 `scenario.game_type` 필수
- API/schema/contract version:
  - in-progress
- Assumptions:
  - progression 1차 스펙은 LLM 주도 결과 생성 + 서버 스키마 검증

## 5. Work Summary

- What changed:
  - `Scenario.game_type` 필수 필드 및 초기 schema 반영
  - 시나리오 목록 응답에 `game_type` 노출
  - `StartGameUseCase`에 progression 초기 상태/오프닝 분기 추가
  - `ProcessActionUseCase`에 progression 질문/개월 진행/최종 업적 보드 분기 추가
  - progression 상태 관리 서비스 및 전용 LLM 프롬프트 추가
  - dev 시드에 `기연 일지` progression 시나리오 추가
  - 관련 unit/integration 테스트 보강 및 기존 픽스처 정리
- What was inspected:
  - scenario/session/message 모델, start/process use case, illustration/image path
- Remaining work:
  - 없음

## 6. Validation

- Tests run:
  - `uv run pytest tests/unit/application/test_get_scenarios_query.py tests/unit/application/test_progression_game_flow.py tests/unit/application/test_start_game_unit.py tests/unit/application/test_process_action.py tests/unit/application/test_process_action_dice.py tests/unit/application/test_process_action_prompt_and_memory.py tests/unit/application/test_generate_illustration_use_case.py tests/unit/application/test_create_character_user_level.py tests/integration/infrastructure/test_character_repository.py tests/integration/infrastructure/test_game_session_repository.py tests/integration/infrastructure/test_game_message_repository.py tests/integration/infrastructure/test_game_memory_repository.py tests/unit/application/test_dev_seed_scenarios.py`
- Lint/format checks:
  - `uv run black --check app tests`
  - `uv run isort --check app tests`
  - `uv run flake8 app tests`
- Manual verification:
  - 없음

## 7. Risks and Open Questions

- Known risks:
  - progression의 질문/개월 소모 판정은 현재 LLM `consumes_turn` 응답에 의존
  - 최종 업적 보드 이미지는 이미지 모델의 텍스트 렌더링 한계로 인해 실제 텍스트 품질이 들쭉날쭉할 수 있음
- Open questions:
  - 없음
- Blockers:
  - 없음

## 8. Next Handoff

- Next owner: Codex
- Next recommended action:
  - DB reset 후 초기 schema 기준으로 progression 시나리오 실플로우 점검
- Done criteria for receiver:
  - scenario별 게임 엔진 분기가 동작하고 관련 테스트가 통과함

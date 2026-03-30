# Common Handoff Template

## 1. Metadata

- Mode: `sub-agent`
- Handoff Type: `phase`
- Title: 이미지 생성 구조 리셋 및 dead schema 제거
- Owner: Codex
- Status: `done`
- Related Files:
  - `app/game/application/services/illustration_prompt_builder.py`
  - `app/game/application/services/illustration_scene_spec_builder.py`
  - `app/game/application/services/illustration_scenario_profile_resolver.py`
  - `app/game/application/services/illustration_generation_service.py`
  - `app/game/application/use_cases/start_game.py`
  - `app/game/application/use_cases/generate_illustration.py`
  - `app/game/domain/entities/scenario.py`
  - `app/game/infrastructure/persistence/models/game_models.py`
  - `migrations/versions/72c1f5a14d56_initial_schema_reset.py`

## 2. Input

- Request summary:
  - 레거시 호환 없이 이미지 생성 구조를 단순하고 분리된 형태로 재정리
  - 과거 이미지/과거 데이터/backfill 고려 금지
  - 죽은 DB 컬럼/테이블 정리

## 3. Work Summary

- What changed:
  - 일러스트 생성 경로를 `context -> scene spec -> visual profile -> prompt` 구조로 분리
  - `IllustrationPromptBuilder`를 순수 직렬화 전용으로 축소
  - `IllustrationSceneSpecBuilder`, `IllustrationScenarioProfileResolver` 추가
  - `IllustrationGenerationService`가 컨텍스트 조립과 파이프라인 오케스트레이션 담당
  - `StartGameUseCase`, `GenerateIllustrationUseCase`가 loose kwargs 대신 공용 context 경로 사용
  - dead schema인 `scenarios.system_prompt_override` 제거
  - `ScenarioEntity.effective_system_prompt` 제거
- What was intentionally not changed:
  - 외부 API 응답 shape
  - 기존 image_url 재사용 정책
  - 살아 있는 scenario metadata 컬럼 (`thumbnail_url`, `hook`, `recommended_for`, `world_setting`)

## 4. Validation

- Tests run:
  - `uv run pytest tests/unit/application/services/test_illustration_prompt_builder.py tests/unit/application/services/test_illustration_scene_spec_builder.py tests/unit/application/services/test_illustration_scenario_profile_resolver.py tests/unit/application/services/test_illustration_generation_service.py tests/unit/application/test_generate_illustration_use_case.py tests/unit/application/test_start_game_unit.py tests/unit/application/test_get_session.py tests/unit/application/test_game_routes_idempotency.py tests/integration/infrastructure/test_game_session_repository.py`
- Lint/format checks:
  - `uv run black --check ...`
  - `uv run isort --check ...`
  - `uv run flake8 ...`

## 5. Notes

- repo 기준으로 dead DB 항목은 `system_prompt_override`만 확인됨
- migration은 초기 리셋 기준으로 직접 수정했으므로 DB 재생성 전제

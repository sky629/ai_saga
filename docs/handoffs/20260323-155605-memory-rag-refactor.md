# Common Handoff Template

## 1. Metadata

- Mode: `thread`
- Handoff Type: `phase`
- Title: 로그/검색 메모리 분리 기반 RAG 리팩터링
- Owner: Codex
- Status: `done`
- Related Branch: `main`
- Related Worktree:
- Related Files:
  - `app/game/application/use_cases/process_action.py`
  - `app/game/application/services/turn_prompt_composer.py`
  - `app/game/application/services/game_memory_text_builder.py`
  - `app/game/application/services/rag_context_builder.py`
  - `app/game/application/ports/__init__.py`
  - `app/game/domain/entities/game_memory.py`
  - `app/game/domain/value_objects/game_memory_type.py`
  - `app/game/infrastructure/repositories/game_memory_repository.py`
  - `app/game/infrastructure/persistence/models/game_models.py`
  - `migrations/versions/72c1f5a14d56_initial_schema_reset.py`

## 2. Input

- Request summary: 사용자 입력 처리 시 현재 구조와 개선 구조 차이를 실제 코드로 반영
- Preconditions: DB/Alembic 구조 재구성 허용
- Dependencies: 없음
- Required references: 위 관련 파일들

## 3. Scope

- In scope:
  - `game_messages`를 로그 전용으로 축소
  - `game_memory_documents` 기반 검색 메모리 구조 도입
  - 명시적 `TurnPromptComposer` 도입
  - assistant 응답 검색 텍스트를 raw JSON과 분리
- Out of scope:
  - 전체 통합 테스트 재작성
  - 벡터 인덱스 최적화(HNSW/IVFFlat) 적용
- Allowed write scope: `app/`, `tests/`, `migrations/`, `docs/handoffs/`
- Forbidden write scope: 없음

## 4. Decisions and Contract

- Confirmed decisions:
  - 현재 턴 액션은 대화 히스토리에 암묵적으로 섞지 않고, 구조화된 user payload로 전달한다.
  - 검색은 `game_messages`가 아니라 `game_memory_documents` 전용 저장소를 사용한다.
  - assistant 임베딩은 raw JSON 전체가 아니라 narrative/state 기반 검색 텍스트를 사용한다.
  - `build_action_prompt` 및 `GameMasterPrompt.build_action` 경로는 제거한다.
- API/schema/contract version: 현행 리팩터링 버전
- Assumptions:
  - DB는 재구성 가능하며, 기존 vector schema와 호환 유지가 필수는 아님

## 5. Work Summary

- What changed:
  - `GameMemoryEntity`, `GameMemoryType`, `GameMemoryRepository` 추가
  - `TurnPromptComposer`, `GameMemoryTextBuilder` 추가
  - `ProcessActionUseCase`가 raw message 저장과 memory 저장을 분리하도록 변경
  - `RAGContextBuilder`가 actual distance 점수를 활용하도록 변경
  - `GameMasterPrompt`의 dead action prompt 경로 제거
  - 초기 migration에 `game_memory_documents` 추가, `game_messages.embedding` 제거
- What was inspected:
  - 액션 처리 유스케이스
  - 프롬프트 템플릿
  - pgvector 저장/검색 경로
  - 관련 단위 테스트
- Remaining work:
  - 통합 테스트를 `GameMemoryRepository` 기준으로 교체
  - 벡터 인덱스 전략 보강

## 6. Validation

- Tests run:
  - `uv run pytest tests/unit/domain/test_game_master_prompt.py tests/llm/test_prompts.py tests/unit/application/services/test_turn_prompt_composer.py tests/unit/application/services/test_game_memory_text_builder.py tests/unit/application/test_process_action_prompt_and_memory.py tests/unit/application/test_rag_context_builder.py`
- Lint/format checks:
  - `uv run flake8 ...` 대상 파일 통과
  - `uv run isort --check ...` 대상 파일 통과
  - `uv run black --check ...` 대상 파일 통과
- Manual verification:
  - `python -m py_compile`로 주요 변경 파일 컴파일 확인

## 7. Risks and Open Questions

- Known risks:
  - 기존 `GameMessage` vector 통합 테스트는 새 메모리 저장소 기준으로 재작성 필요
  - migration은 초기 리셋 기준으로 수정했으므로 실제 DB 재생성이 전제됨
- Open questions:
  - memory 문서를 한 턴에 1개만 유지할지, fact/state_delta로 더 세분화할지
- Blockers: 없음

## 8. Next Handoff

- Next owner: Codex or user
- Next recommended action:
  - `GameMemoryRepository` 통합 테스트 추가
  - ANN 인덱스 전략 반영
- Done criteria for receiver:
  - 검색이 raw message가 아니라 memory document 기준으로 동작함을 확인

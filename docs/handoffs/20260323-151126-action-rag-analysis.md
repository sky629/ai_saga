# Common Handoff Template

## 1. Metadata

- Mode: `thread`
- Handoff Type: `phase`
- Title: 주사위 액션 판정 / LLM 프롬프트 / RAG 흐름 분석
- Owner: Codex
- Status: `done`
- Related Branch: `main`
- Related Worktree:
- Related Files:
  - `app/game/application/use_cases/process_action.py`
  - `app/game/domain/services/dice_service.py`
  - `app/game/domain/services/game_master_service.py`
  - `app/game/application/services/rag_context_builder.py`
  - `app/game/infrastructure/repositories/game_message_repository.py`
  - `app/game/infrastructure/persistence/models/game_models.py`
  - `app/llm/prompts/game_master.py`
  - `app/llm/providers/gemini.py`
  - `app/llm/providers/gemini_embedding_provider.py`
  - `app/game/application/services/embedding_cache_service.py`
  - `config/settings.py`

## 2. Input

- Request summary: 주사위 액션 판정, LLM 프롬프트 입력, RAG 사용 방식, 벡터 DB 저장 시 청킹 방식, 검색 방식 분석
- Preconditions: 로컬 저장소 코드 기준 분석
- Dependencies: 없음
- Required references: 위 관련 파일들

## 3. Scope

- In scope: 액션 처리 유스케이스와 관련 서비스/저장소 흐름 분석
- Out of scope: 기능 수정, 성능 튜닝, 프롬프트 재설계
- Allowed write scope: `docs/handoffs/`
- Forbidden write scope: `app/`, `tests/`

## 4. Decisions and Contract

- Confirmed decisions:
  - 주사위 판정은 서버 규칙 기반 액션 분류 후 서버에서 결정한다.
  - RAG 저장 단위는 별도 chunk가 아니라 메시지 1건 단위다.
  - 유사도 검색은 같은 세션 내부에서 pgvector cosine distance로 수행한다.
- API/schema/contract version: 현행 코드 기준
- Assumptions: 없음

## 5. Work Summary

- What changed: handoff 문서만 추가
- What was inspected:
  - `ProcessActionUseCase`의 액션 처리 전체 흐름
  - `DiceService`, `GameMasterService`의 판정/보정 규칙
  - `GameMasterPrompt`, Gemini provider의 프롬프트 주입 방식
  - `GameMessageRepositoryImpl`, `GameMessage` 모델의 vector 저장/검색 구조
  - RAG 가중치/필터링 설정과 `RAGContextBuilder`
- Remaining work:
  - 필요 시 프롬프트 개선안 또는 RAG 품질 개선안 별도 제안 가능

## 6. Validation

- Tests run: 없음
- Lint/format checks: 없음
- Manual verification: 코드 경로 추적 및 관련 테스트 파일 확인

## 7. Risks and Open Questions

- Known risks:
  - `build_action_prompt` 템플릿은 존재하지만 현재 정상 턴 처리 경로에서는 사용되지 않는다.
  - state consistency 필터는 location 문자열 일치 여부만 본다.
- Open questions:
  - 자유 입력 액션 분류를 규칙 기반으로 유지할지, 경량 분류기로 대체할지
- Blockers: 없음

## 8. Next Handoff

- Next owner: Codex or user
- Next recommended action: 필요 시 프롬프트/RAG 개선 포인트를 설계 수준에서 추가 분석
- Done criteria for receiver:
  - 요청한 5개 분석 항목을 코드 근거와 함께 설명할 수 있음

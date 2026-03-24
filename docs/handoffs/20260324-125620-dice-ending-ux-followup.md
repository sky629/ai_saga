# Common Handoff Template

## 1. Metadata

- Mode: `thread`
- Handoff Type: `phase`
- Title: 주사위 공개 UX 및 엔딩 플래그 의미 정리 후속 조정
- Owner: Codex
- Status: `done`
- Related Branch: `main`
- Related Worktree:
- Related Files:
  - `app/game/application/use_cases/process_action.py`
  - `app/game/application/services/turn_prompt_composer.py`
  - `app/game/application/services/game_memory_text_builder.py`
  - `app/game/domain/services/game_master_service.py`
  - `app/llm/prompts/game_master.py`
  - `src/pages/GameSession.tsx`
  - `src/components/game/MessageHistory.tsx`
  - `src/components/game/DiceResultPanel.tsx`
  - `src/components/game/GameStatePanel.tsx`
  - `src/types/api.ts`

## 2. Input

- Request summary:
  - 주사위 공개 전/후 메시지 분리 개선
  - 실패 서술을 LLM 중심으로 복원
  - `is_ending` 의미를 실제 엔딩으로 제한
  - 마지막 직전 경고는 프론트에서만 단순 처리
- Preconditions:
  - 백엔드/프론트 모두 `main` 반영 완료
- Dependencies:
  - Gemini 기반 LLM 응답 품질
  - 프론트 local state 기반 주사위 공개 흐름
- Required references:
  - 기존 handoff 2건
  - 관련 파일들

## 3. Scope

- In scope:
  - 주사위 버튼을 누르기 전 결과 스포/자동 공개 방지
  - `before_narrative`와 `narrative` 역할 재정리
  - 마지막 턴과 마지막 직전 턴의 의미 분리
  - Gemini 429 재시도 시간 노출 및 테스트 Redis 분리
- Out of scope:
  - 주사위 상태 영속 복원
  - 엔딩 시스템 전체 재설계
- Allowed write scope:
  - `app/`, `tests/`, `src/`, `docs/handoffs/`
- Forbidden write scope:
  - 없음

## 4. Decisions and Contract

- Confirmed decisions:
  - `GameActionResponse.is_ending`은 실제 엔딩이 아니다. 일반 액션 응답에서는 `false` 유지.
  - 마지막 직전 경고는 프론트에서 `turnCount === maxTurns - 1`로만 판단.
  - 실패 내러티브는 서버가 재작성하지 않고, LLM 서술을 최대한 유지.
  - `before_narrative`는 검색 메모리에 포함하지 않는다.
  - `before_narrative`가 `narrative`와 같거나 포함 관계면 제거한다.
  - 라이브 흐름에서는 주사위 전 임시 메시지를 보여주고, 공개 후 최종 메시지에서 `before_narrative + narrative` 합본으로 보여준다.
- API/schema/contract version:
  - `GameActionResponse.is_ending = false`
  - `GameEndingResponse.is_ending = true`
- Assumptions:
  - 마지막 직전 경고는 UI 힌트일 뿐, 서버 엔딩 판정과 분리해도 괜찮다.

## 5. Work Summary

- What changed:
  - 백엔드
    - `is_ending` 의미를 실제 엔딩 전용으로 정리
    - 실패 내러티브 재작성 제거
    - 프롬프트를 현재 행동 중심으로 단순화
    - `before_narrative` 중복/스포 제거 로직 추가
    - Gemini 429 응답에 `retry_after_seconds` 포함
    - 테스트 Redis DB를 auth 세션 DB와 분리
  - 프론트
    - 주사위 공개 전 자동 결과 노출 방지
    - 주사위 패널 표시 타이밍 조정
    - `before_narrative`/`narrative` 합본 렌더링
    - 마지막 직전 경고 문구/조건 정리
    - 시나리오 시작 429 시 팝업 노출
    - 액션 429 시 N초 뒤 재시도 문구 노출
- What was inspected:
  - `process_action` 엔딩 분기 시점
  - 주사위 공개 전/후 프론트 state 흐름
  - `MessageHistory` parsed_response 렌더 경로
  - Gemini quota error 구조
- Remaining work:
  - 주사위 공개 상태를 새로고침 후 복원하는 영속 복원은 아직 없음
  - 엔딩 프롬프트 자체를 더 “엔딩답게” 만들고 싶다면 별도 작업 필요

## 6. Validation

- Tests run:
  - 백엔드
    - `uv run pytest tests/unit/common/test_exception.py tests/unit/llm/test_gemini_retry_delay.py tests/unit/common/storage/test_redis_storage.py tests/unit/infrastructure/adapters/test_auth_cache_adapter.py`
    - `uv run pytest tests/unit/application/services/test_turn_prompt_composer.py tests/unit/application/services/test_game_memory_text_builder.py tests/unit/application/test_process_action.py tests/unit/application/test_process_action_dice.py tests/unit/domain/test_game_master_service.py tests/unit/domain/test_game_master_prompt.py`
  - 프론트
    - `npm run build`
- Lint/format checks:
  - 백엔드 대상 파일 `flake8` 통과
  - 백엔드 대상 파일 `black --check` 통과
- Manual verification:
  - tmux pane 로그로 Gemini 429 / auth session / 주사위 흐름 이슈 확인
  - 주사위 공개 전/후 메시지 처리 로직 수동 추적

## 7. Risks and Open Questions

- Known risks:
  - 새로고침 시 주사위 공개 상태를 완전 복원하지는 않음
  - LLM이 `before_narrative`와 `narrative`를 충분히 다르게 생성하지 못하면, 서버가 `before_narrative`를 드롭할 수 있음
  - 엔딩 프롬프트는 아직 단순 텍스트 기반이라 “엔딩다운 마무리감”이 약할 수 있음
- Open questions:
  - 마지막 직전 턴을 별도 “final warning turn” UX로 더 명확히 분리할지
  - 엔딩 분기 시 일반 히스토리 대신 전용 엔딩 화면/연출을 둘지
- Blockers:
  - 없음

## 8. Next Handoff

- Next owner: Codex or user
- Next recommended action:
  - 실제 마지막 턴 플레이 테스트로 엔딩 내러티브 품질 점검
  - 필요 시 엔딩 프롬프트 강화
- Done criteria for receiver:
  - 주사위 공개 흐름과 엔딩 플래그 의미를 최신 기준으로 빠르게 이해하고 이어서 수정 가능

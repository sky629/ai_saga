"""ProcessAction prompt/memory behavior tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.game.application.use_cases.process_action import (
    ProcessActionInput,
    ProcessActionUseCase,
)
from app.game.domain.entities import (
    CharacterEntity,
    CharacterStats,
    GameSessionEntity,
)
from app.game.domain.value_objects import ScenarioDifficulty, SessionStatus


@pytest.mark.asyncio
class TestProcessActionPromptAndMemory:
    @pytest.fixture
    def active_session(self):
        now = datetime.now(timezone.utc)
        return GameSessionEntity(
            id=uuid4(),
            user_id=uuid4(),
            character_id=uuid4(),
            scenario_id=uuid4(),
            current_location="감옥 복도",
            game_state={"discoveries": ["쇠창살"]},
            status=SessionStatus.ACTIVE,
            turn_count=1,
            max_turns=10,
            started_at=now,
            last_activity_at=now,
        )

    @pytest.fixture
    def character(self, active_session):
        now = datetime.now(timezone.utc)
        return CharacterEntity(
            id=active_session.character_id,
            user_id=active_session.user_id,
            scenario_id=active_session.scenario_id,
            name="도적",
            description="민첩한 탈옥수",
            stats=CharacterStats(hp=100, max_hp=100, level=3),
            inventory=["철사"],
            is_active=True,
            created_at=now,
        )

    @pytest.fixture
    def scenario(self, active_session):
        now = datetime.now(timezone.utc)
        from app.game.domain.entities import ScenarioEntity

        return ScenarioEntity(
            id=active_session.scenario_id,
            name="감옥 탈출",
            description="탈옥 시도",
            genre="fantasy",
            difficulty=ScenarioDifficulty.NORMAL,
            max_turns=10,
            world_setting="어두운 지하 감옥",
            initial_location="독방",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    def repositories(self, active_session, character, scenario):
        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = active_session

        message_repo = AsyncMock()
        message_repo.get_recent_messages.return_value = []

        memory_repo = AsyncMock()
        memory_repo.get_similar_memories.return_value = []

        character_repo = AsyncMock()
        character_repo.get_by_id.return_value = character

        scenario_repo = AsyncMock()
        scenario_repo.get_by_id.return_value = scenario

        llm_service = AsyncMock()
        llm_response = MagicMock()
        llm_response.content = (
            '{"narrative":"문이 열린다.","options":["달린다"],'
            '"dice_applied":false,"state_changes":{"location":"복도"}}'
        )
        llm_response.usage.total_tokens = 33
        llm_service.generate_response.return_value = llm_response

        cache_service = AsyncMock()
        cache_service.get.return_value = None

        embedding_service = AsyncMock()
        embedding_service.generate_embedding.side_effect = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]

        return {
            "session_repository": session_repo,
            "message_repository": message_repo,
            "memory_repository": memory_repo,
            "character_repository": character_repo,
            "scenario_repository": scenario_repo,
            "llm_service": llm_service,
            "cache_service": cache_service,
            "embedding_service": embedding_service,
        }

    async def test_current_action_is_sent_as_structured_turn_payload(
        self, repositories, active_session
    ):
        use_case = ProcessActionUseCase(**repositories)
        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="문을 따고 탈출한다",
            idempotency_key="prompt-key",
        )

        await use_case.execute(active_session.user_id, input_data)

        llm_call = repositories["llm_service"].generate_response.call_args
        messages = llm_call.kwargs["messages"]
        assert messages[-1]["role"] == "user"
        assert "현재 플레이어 행동" in messages[-1]["content"]
        assert "문을 따고 탈출한다" in messages[-1]["content"]

    async def test_similar_message_search_excludes_current_user_message(
        self, repositories, active_session
    ):
        use_case = ProcessActionUseCase(**repositories)
        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="문을 따고 탈출한다",
            idempotency_key="self-match-key",
        )

        await use_case.execute(active_session.user_id, input_data)

        call = repositories["memory_repository"].get_similar_memories.call_args
        assert len(call.kwargs["exclude_memory_ids"]) == 1

    async def test_ai_embedding_uses_search_text_not_raw_json(
        self, repositories, active_session
    ):
        use_case = ProcessActionUseCase(**repositories)
        input_data = ProcessActionInput(
            session_id=active_session.id,
            action="문을 따고 탈출한다",
            idempotency_key="memory-text-key",
        )

        await use_case.execute(active_session.user_id, input_data)

        calls = repositories[
            "embedding_service"
        ].generate_embedding.await_args_list
        assert calls[0].args[0] == "문을 따고 탈출한다"
        assert "문이 열린다." in calls[1].args[0]
        assert '"narrative"' not in calls[1].args[0]

"""Start Game Use Case.

새 게임 세션을 시작하는 유스케이스.
기존 GameService.start_game()의 비즈니스 로직을 분리.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import (
    CharacterRepositoryInterface,
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    LLMServiceInterface,
    ScenarioRepositoryInterface,
)
from app.game.domain.entities import GameMessageEntity, GameSessionEntity
from app.game.domain.value_objects import MessageRole, SessionStatus
from app.game.presentation.routes.schemas.response import GameSessionResponse
from app.llm.prompts.game_master import GameMasterPrompt
from config.settings import settings


class StartGameInput(BaseModel):
    """Use Case 입력 DTO."""

    model_config = {"frozen": True}

    character_id: UUID
    scenario_id: UUID
    max_turns: Optional[int] = None


class StartGameUseCase:
    """게임 시작 유스케이스.

    Single Responsibility: 새 게임 세션을 생성하고
    초기 내러티브를 생성하는 것만 담당합니다.
    """

    def __init__(
        self,
        session_repository: GameSessionRepositoryInterface,
        character_repository: CharacterRepositoryInterface,
        scenario_repository: ScenarioRepositoryInterface,
        message_repository: GameMessageRepositoryInterface,
        llm_service: LLMServiceInterface,
    ):
        self._session_repo = session_repository
        self._character_repo = character_repository
        self._scenario_repo = scenario_repository
        self._message_repo = message_repository
        self._llm = llm_service

    async def execute(
        self, user_id: UUID, input_data: StartGameInput
    ) -> GameSessionResponse:
        """유스케이스 실행."""
        # 1. Validate character ownership
        character = await self._character_repo.get_by_id(
            input_data.character_id
        )
        if not character or character.user_id != user_id:
            raise ValueError("Character not found or does not belong to user")

        # 2. Validate scenario
        scenario = await self._scenario_repo.get_by_id(input_data.scenario_id)
        if not scenario or not scenario.is_playable:
            raise ValueError("Scenario not found or inactive")

        # 3. Check for existing active session
        existing = await self._session_repo.get_active_by_character(
            character.id
        )
        if existing:
            raise ValueError("Character already has an active session")

        # 4. Determine max_turns
        max_turns = input_data.max_turns or settings.game_max_turns

        # 5. Create session entity
        now = get_utc_datetime()
        session = GameSessionEntity(
            id=get_uuid7(),
            character_id=character.id,
            scenario_id=scenario.id,
            current_location=scenario.initial_location,
            game_state={},
            status=SessionStatus.ACTIVE,
            turn_count=0,
            max_turns=max_turns,
            ending_type=None,
            started_at=now,
            ended_at=None,
            last_activity_at=now,
        )

        # 6. Save session
        session = await self._session_repo.save(session)

        # 7. Generate initial narrative
        await self._generate_initial_narrative(session, character, scenario)

        # 8. Return response
        return GameSessionResponse(
            id=session.id,
            character_id=session.character_id,
            scenario_id=session.scenario_id,
            current_location=session.current_location,
            game_state=session.game_state,
            status=session.status.value,
            turn_count=session.turn_count,
            ending_type=None,
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
        )

    async def _generate_initial_narrative(
        self,
        session: GameSessionEntity,
        character,  # CharacterEntity
        scenario,  # ScenarioEntity
    ) -> None:
        """초기 게임 내러티브 생성."""
        prompt = GameMasterPrompt(
            scenario_name=scenario.name,
            world_setting=scenario.world_setting,
            character_name=character.name,
            character_description=character.description or "",
            current_location=session.current_location,
            recent_events="게임이 시작되었습니다.",
        )

        response = await self._llm.generate_response(
            system_prompt=prompt.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": "게임을 시작합니다. 현재 상황을 묘사해주세요.",
                }
            ],
        )

        # Save initial message
        initial_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            token_count=(
                response.usage.total_tokens if response.usage else None
            ),
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(initial_message)

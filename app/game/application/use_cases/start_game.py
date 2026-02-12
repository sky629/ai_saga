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
    ImageGenerationServiceInterface,
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
        image_service: Optional[ImageGenerationServiceInterface] = None,
    ):
        self._session_repo = session_repository
        self._character_repo = character_repository
        self._scenario_repo = scenario_repository
        self._message_repo = message_repository
        self._llm = llm_service
        self._image_service = image_service

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

        if character.scenario_id != scenario.id:
            raise ValueError("Character does not belong to this scenario")

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
            user_id=user_id,
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
        initial_image_url = await self._generate_initial_narrative(
            session, character, scenario
        )

        # 8. Return response
        return GameSessionResponse(
            id=session.id,
            character_id=session.character_id,
            scenario_id=session.scenario_id,
            current_location=session.current_location,
            game_state=session.game_state,
            status=session.status.value,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            ending_type=None,
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
            image_url=initial_image_url,
        )

    async def _generate_initial_narrative(
        self,
        session: GameSessionEntity,
        character,  # CharacterEntity
        scenario,  # ScenarioEntity
    ) -> Optional[str]:
        """초기 게임 내러티브 및 삽화 생성."""
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
        initial_image_url = None
        # Generate initial illustration
        if self._image_service:
            # 픽셀 아트 스타일 프롬프트 (Pixel Art, Retro Game Style)
            illustration_prompt = (
                f"Pixel art style game illustration: {response.content[:300]}. "
                "Retro 16-bit rpg game aesthetic, detailed pixel art, vibrant colors."
            )
            initial_image_url = await self._image_service.generate_image(
                prompt=illustration_prompt,
                session_id=str(session.id),
                user_id=str(character.id),  # character_id를 user_id 대신 사용
            )

        # Save initial message with image_url
        initial_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            token_count=(
                response.usage.total_tokens if response.usage else None
            ),
            image_url=initial_image_url,
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(initial_message)

        return initial_image_url

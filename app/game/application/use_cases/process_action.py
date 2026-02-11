"""Process Action Use Case.

플레이어 액션을 처리하고 AI 응답을 생성하는 핵심 유스케이스.
기존 GameService.process_action()의 비즈니스 로직을 분리.
"""

import json
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import (
    CacheServiceInterface,
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    ImageGenerationServiceInterface,
    LLMServiceInterface,
)
from app.game.domain.entities import GameMessageEntity, GameSessionEntity
from app.game.domain.services import GameMasterService
from app.game.domain.value_objects import MessageRole
from app.game.presentation.routes.schemas.response import (
    GameActionResponse,
    GameEndingResponse,
    GameMessageResponse,
)
from app.llm.prompts.game_master import GameMasterPrompt


class ProcessActionInput(BaseModel):
    """Use Case 입력 DTO."""

    model_config = {"frozen": True}

    session_id: UUID
    action: str
    idempotency_key: str


class ProcessActionResult(BaseModel):
    """Use Case 결과."""

    response: Union[GameActionResponse, GameEndingResponse]
    is_cached: bool = False


class ProcessActionUseCase:
    """플레이어 액션 처리 유스케이스.

    Single Responsibility: 플레이어 액션을 받아 게임 상태를 업데이트하고
    AI 응답을 생성하는 것만 담당합니다.
    """

    def __init__(
        self,
        session_repository: GameSessionRepositoryInterface,
        message_repository: GameMessageRepositoryInterface,
        llm_service: LLMServiceInterface,
        cache_service: CacheServiceInterface,
        image_service: Optional[ImageGenerationServiceInterface] = None,
    ):
        self._session_repo = session_repository
        self._message_repo = message_repository
        self._llm = llm_service
        self._cache = cache_service
        self._image_service = image_service

    async def execute(
        self, user_id: UUID, input_data: ProcessActionInput
    ) -> ProcessActionResult:
        """유스케이스 실행."""
        # 1. Idempotency Check
        cache_key = f"game:idempotency:{input_data.session_id}:{input_data.idempotency_key}"
        cached_data = await self._cache.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            if data.get("type") == "ending":
                return ProcessActionResult(
                    response=GameEndingResponse.model_validate(data["data"]),
                    is_cached=True,
                )
            else:
                return ProcessActionResult(
                    response=GameActionResponse.model_validate(data["data"]),
                    is_cached=True,
                )

        # 2. Load session entity
        session = await self._session_repo.get_by_id(input_data.session_id)
        if not session:
            raise ValueError("Session not found")

        # 3. Validate ownership and status
        self._validate_session(session, user_id)

        # 4. Advance turn (domain logic)
        session = session.advance_turn()

        # 5. Save user message
        user_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.USER,
            content=input_data.action,
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(user_message)

        # 6. Get recent messages for context
        recent_messages = await self._message_repo.get_recent_messages(
            session.id, limit=20
        )

        # 7. Check if final turn (domain logic)
        if GameMasterService.should_end_game(session):
            response = await self._handle_ending(session, recent_messages)
        else:
            response = await self._handle_normal_turn(
                session, user_id, recent_messages
            )

        # 8. Save session state
        await self._session_repo.save(session)

        # 9. Cache response for idempotency
        cache_key = f"game:idempotency:{input_data.session_id}:{input_data.idempotency_key}"
        await self._cache_response(cache_key, response)

        return ProcessActionResult(response=response)

    def _validate_session(
        self, session: GameSessionEntity, user_id: UUID
    ) -> None:
        """세션 유효성 검증."""
        # Note: user_id 검증은 Character를 통해 해야 하지만,
        # 현재는 세션 상태만 확인 (추후 Character 조회 추가)
        if not session.is_active:
            raise ValueError("Session is not active")

    async def _handle_normal_turn(
        self,
        session: GameSessionEntity,
        user_id: UUID,
        recent_messages: list[GameMessageEntity],
    ) -> GameActionResponse:
        """일반 턴 처리."""
        # Build prompt (도메인 서비스 활용)
        messages_for_llm = [
            {"role": msg.role.value, "content": msg.content}
            for msg in recent_messages
        ]

        recent_events = GameMasterService.summarize_recent_events(
            [msg.content for msg in recent_messages if msg.is_ai_response]
        )

        prompt = GameMasterPrompt(
            scenario_name="",  # TODO: Load from session
            world_setting="",
            character_name="",
            character_description="",
            current_location=session.current_location,
            recent_events=recent_events,
        )

        # Generate LLM response
        llm_response = await self._llm.generate_response(
            system_prompt=prompt.system_prompt,
            messages=messages_for_llm,
        )

        # 3. Validate ownership and status
        self._validate_session(session, user_id)

        # 4. Advance turn (domain logic)
        # ... (skip unchanged lines)

        # Import settings inside method to avoid circular import if necessary,
        # or use self._settings if injected. Here we use global settings for simplicity as usually done in this project.
        from config.settings import settings

        # 설정된 턴 간격마다 삽화 생성
        image_url = None
        interval = settings.image_generation_interval

        # 0 나누기 방지 및 1 이상일 때만 생성
        if interval > 0 and session.turn_count % interval == 0:
            image_url = await self._generate_illustration(
                llm_response.content, session
            )

        # Save AI message with image_url
        ai_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=llm_response.content,
            token_count=(
                llm_response.usage.total_tokens if llm_response.usage else None
            ),
            image_url=image_url,
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(ai_message)

        # Extract options (도메인 서비스 활용)
        options = GameMasterService.extract_action_options(
            llm_response.content
        )

        return GameActionResponse(
            message=GameMessageResponse(
                id=ai_message.id,
                role=ai_message.role.value,
                content=ai_message.content,
                parsed_response=None,
                image_url=image_url,
                created_at=ai_message.created_at,
            ),
            narrative=llm_response.content,
            options=options,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            is_ending=False,
            image_url=image_url,
        )

    async def _handle_ending(
        self,
        session: GameSessionEntity,
        recent_messages: list[GameMessageEntity],
    ) -> GameEndingResponse:
        """게임 엔딩 처리."""
        messages_for_llm = [
            {"role": msg.role.value, "content": msg.content}
            for msg in recent_messages[-10:]
        ]

        ending_prompt = f"""당신은 게임 마스터입니다. 이 게임의 마지막 턴입니다.
현재 위치: {session.current_location}

지시사항:
1. 지금까지의 플레이어 행동을 바탕으로 적절한 엔딩을 생성해주세요.
2. 엔딩 유형을 결정하세요: victory, defeat, 또는 neutral
3. 감동적이고 기억에 남는 엔딩 내러티브를 작성해주세요.

응답 형식:
[엔딩 유형]: victory/defeat/neutral
[엔딩 내러티브]: (상세한 엔딩 스토리)
"""

        llm_response = await self._llm.generate_response(
            system_prompt=ending_prompt,
            messages=messages_for_llm,
        )

        # Parse ending (도메인 서비스 활용)
        ending_type = GameMasterService.parse_ending_type(llm_response.content)
        narrative = GameMasterService.extract_narrative_from_ending(
            llm_response.content
        )

        # Update session to completed
        session = session.complete(ending_type)
        await self._session_repo.save(session)

        # Save ending message
        ending_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=narrative,
            parsed_response={"ending_type": ending_type.value},
            token_count=(
                llm_response.usage.total_tokens if llm_response.usage else None
            ),
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(ending_message)

        return GameEndingResponse(
            session_id=session.id,
            ending_type=ending_type.value,
            narrative=narrative,
            total_turns=session.turn_count,
            character_name="",  # TODO: Load from character
            scenario_name="",  # TODO: Load from scenario
        )

    async def _check_idempotency(
        self, session_id: UUID, idempotency_key: str
    ) -> Optional[Union[GameActionResponse, GameEndingResponse]]:
        """캐시된 응답 확인."""
        cache_key = f"game:idempotency:{session_id}:{idempotency_key}"
        cached_data = await self._cache.get(cache_key)

        if cached_data:
            data = json.loads(cached_data)
            if data.get("type") == "ending":
                return GameEndingResponse.model_validate(data["data"])
            else:
                return GameActionResponse.model_validate(data["data"])
        return None

    async def _cache_response(
        self,
        cache_key: str,
        response: Union[GameActionResponse, GameEndingResponse],
    ) -> None:
        """응답 캐싱."""
        is_ending = isinstance(response, GameEndingResponse)

        cache_data = {
            "type": "ending" if is_ending else "action",
            "data": response.model_dump(mode="json"),
        }
        await self._cache.set(
            cache_key, json.dumps(cache_data), ttl_seconds=600
        )

    async def _generate_illustration(
        self,
        narrative: str,
        session: GameSessionEntity,
    ) -> Optional[str]:
        """LLM 응답 기반 삽화 생성.

        Args:
            narrative: LLM 응답 내용
            session: 게임 세션 (session_id, character_id 사용)

        Returns:
            생성된 이미지 URL, 실패 시 None
        """
        if not self._image_service:
            return None

        # 픽셀 아트 스타일 프롬프트 (Pixel Art, Retro Game Style)
        illustration_prompt = (
            f"Pixel art style game illustration: {narrative[:300]}. "
            "Retro 16-bit rpg game aesthetic, detailed pixel art, vibrant colors."
        )

        return await self._image_service.generate_image(
            prompt=illustration_prompt,
            session_id=str(session.id),
            user_id=str(
                session.character_id
            ),  # character_id를 user_id 대신 사용
        )

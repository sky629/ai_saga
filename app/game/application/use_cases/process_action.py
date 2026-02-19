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
    CharacterRepositoryInterface,
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    ImageGenerationServiceInterface,
    LLMServiceInterface,
)
from app.game.domain.entities import GameMessageEntity, GameSessionEntity
from app.game.domain.services import GameMasterService
from app.game.domain.value_objects import GameState, MessageRole
from app.game.presentation.routes.schemas.response import (
    GameActionResponse,
    GameEndingResponse,
    GameMessageResponse,
)
from app.llm.embedding_service_interface import EmbeddingServiceInterface
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
        character_repository: CharacterRepositoryInterface,
        llm_service: LLMServiceInterface,
        cache_service: CacheServiceInterface,
        embedding_service: EmbeddingServiceInterface,
        image_service: Optional[ImageGenerationServiceInterface] = None,
    ):
        self._session_repo = session_repository
        self._message_repo = message_repository
        self._character_repo = character_repository
        self._llm = llm_service
        self._cache = cache_service
        self._embedding = embedding_service
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

        # 5. Generate embedding for user action
        action_embedding = await self._embedding.generate_embedding(
            input_data.action
        )

        # 6. Save user message with embedding
        user_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.USER,
            content=input_data.action,
            embedding=action_embedding,
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(user_message)

        # 7. Build hybrid context (Sliding Window + RAG)
        # 7.1. Get recent messages (sliding window)
        recent_messages = await self._message_repo.get_recent_messages(
            session.id, limit=10
        )

        # 7.2. Get similar messages (RAG)
        rag_messages = await self._message_repo.get_similar_messages(
            embedding=action_embedding,
            session_id=session.id,
            limit=5,
            distance_threshold=0.3,
        )

        # 7.3. Merge contexts (deduplicate and sort by time)
        from app.game.application.services.rag_context_builder import (
            RAGContextBuilder,
        )

        all_context_messages = RAGContextBuilder.merge_contexts(
            recent_messages, rag_messages
        )

        # 8. Check if final turn (domain logic)
        if GameMasterService.should_end_game(session):
            session, response = await self._handle_ending(
                session, all_context_messages
            )
        else:
            session, response = await self._handle_normal_turn(
                session, user_id, all_context_messages
            )

        # 9. Save session state
        await self._session_repo.save(session)

        # 10. Cache response for idempotency
        cache_key = f"game:idempotency:{input_data.session_id}:{input_data.idempotency_key}"
        await self._cache_response(cache_key, response)

        return ProcessActionResult(response=response)

    def _validate_session(
        self, session: GameSessionEntity, user_id: UUID
    ) -> None:
        """세션 유효성 검증."""
        from app.game.domain.value_objects import SessionStatus

        # Check if session is already completed
        if session.status == SessionStatus.COMPLETED:
            # 상태가 이미 완료라면, 추가 액션 처리 불가
            pass
            # 단, 이전에 완료된 요청에 대한 재요청(idempotency)은 위에서 캐시로 처리됨.
            # 여기까지 왔다는 건 새로운 액션이라는 뜻이므로 에러 처리.
            raise ValueError(
                "Session is already completed. Cannot process further actions."
            )

        # Check if session is in active state
        if not session.is_active:
            raise ValueError("Session is not in active state")

    async def _handle_normal_turn(
        self,
        session: GameSessionEntity,
        user_id: UUID,
        recent_messages: list[GameMessageEntity],
    ) -> tuple[GameSessionEntity, GameActionResponse]:
        """일반 턴 처리."""
        # Build prompt (도메인 서비스 활용)
        messages_for_llm = [
            {"role": msg.role.value, "content": msg.content}
            for msg in recent_messages
        ]

        recent_events = GameMasterService.summarize_recent_events(
            [msg.content for msg in recent_messages if msg.is_ai_response]
        )

        # Parse current game state
        game_state = GameState.from_dict(session.game_state)

        prompt = GameMasterPrompt(
            scenario_name="",  # TODO: Load from session
            world_setting="",
            character_name="",
            character_description="",
            current_location=session.current_location,
            recent_events=recent_events,
            game_state=game_state,
        )

        # Generate LLM response
        llm_response = await self._llm.generate_response(
            system_prompt=prompt.system_prompt,
            messages=messages_for_llm,
        )

        # Try to parse JSON response
        import logging

        logger = logging.getLogger(__name__)

        parsed = GameMasterService.parse_llm_response(llm_response.content)
        logger.info(f"[DEBUG] LLM response parsed: {parsed is not None}")

        if parsed:
            # Extract structured data
            narrative = GameMasterService.extract_narrative_from_parsed(
                parsed, llm_response.content
            )
            options = GameMasterService.extract_options_from_parsed(parsed)
            state_changes = GameMasterService.extract_state_changes(parsed)

            # Update session state
            session = session.update_game_state(state_changes)

            # Update location if changed
            if state_changes.location:
                session = session.update_location(state_changes.location)

            # 🆕 Update Character HP and Inventory
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"[DEBUG] state_changes: hp_change={state_changes.hp_change}, items_gained={state_changes.items_gained}, items_lost={state_changes.items_lost}"
            )

            if (
                state_changes.hp_change != 0
                or state_changes.experience_gained != 0
                or state_changes.items_gained
                or state_changes.items_lost
            ):
                logger.info(
                    f"[DEBUG] Updating character {session.character_id}"
                )
                character = await self._character_repo.get_by_id(
                    session.character_id
                )
                if character:
                    logger.info(
                        f"[DEBUG] Character before update: hp={character.stats.hp}, inventory={character.inventory}"
                    )
                    # Update HP
                    if state_changes.hp_change != 0:
                        if state_changes.hp_change > 0:
                            # Heal
                            character = character.update_stats(
                                character.stats.heal(state_changes.hp_change)
                            )
                        else:
                            # Take damage
                            character = character.update_stats(
                                character.stats.take_damage(
                                    abs(state_changes.hp_change)
                                )
                            )

                    # Update Experience
                    if state_changes.experience_gained > 0:
                        old_level = character.stats.level
                        character = character.update_stats(
                            character.stats.gain_experience(
                                state_changes.experience_gained
                            )
                        )

                        # Log level up
                        if character.stats.level > old_level:
                            logger.info(
                                f"[LEVEL UP] {character.name}: "
                                f"Lv{old_level} → Lv{character.stats.level} "
                                f"(max_hp: {character.stats.max_hp})"
                            )

                    # Update Inventory (items_gained)
                    for item in state_changes.items_gained:
                        if item not in character.inventory:
                            character = character.add_to_inventory(item)

                    # Update Inventory (items_lost)
                    for item in state_changes.items_lost:
                        if item in character.inventory:
                            character = character.remove_from_inventory(item)

                    # Save updated character
                    logger.info(
                        f"[DEBUG] Character after update: hp={character.stats.hp}, inventory={character.inventory}"
                    )
                    try:
                        saved_character = await self._character_repo.save(
                            character
                        )
                        logger.info(
                            f"[DEBUG] Character saved successfully: hp={saved_character.stats.hp}, inventory={saved_character.inventory}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[DEBUG] Character save FAILED: {type(e).__name__}: {e}"
                        )
                        raise
        else:
            # Fallback to text parsing if JSON parsing fails
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Failed to parse JSON from LLM response: {llm_response.content[:200]}"
            )

            narrative = llm_response.content
            options = GameMasterService.extract_action_options(
                llm_response.content
            )

        # Generate illustration based on narrative
        from config.settings import settings

        image_url = None

        # 이미지 생성 (플래그로 on/off 제어)
        if settings.image_generation_enabled:
            interval = settings.image_generation_interval
            # interval=0: 매 턴마다 생성
            # interval>0: N턴마다 생성 (예: 3턴마다)
            should_generate = (interval == 0) or (
                session.turn_count % interval == 0
            )

            if should_generate:
                image_url = await self._generate_illustration(
                    narrative, session
                )

        # Generate embedding for AI response
        ai_embedding = await self._embedding.generate_embedding(
            llm_response.content
        )

        # Save AI message with image_url and embedding
        ai_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=llm_response.content,
            token_count=(
                llm_response.usage.total_tokens if llm_response.usage else None
            ),
            image_url=image_url,
            embedding=ai_embedding,
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(ai_message)

        response = GameActionResponse(
            message=GameMessageResponse(
                id=ai_message.id,
                role=ai_message.role.value,
                content=ai_message.content,
                parsed_response=None,
                image_url=image_url,
                created_at=ai_message.created_at,
            ),
            narrative=narrative,
            options=options,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            is_ending=session.remaining_turns <= 1,
            image_url=image_url,
        )

        return session, response

    async def _handle_ending(
        self,
        session: GameSessionEntity,
        recent_messages: list[GameMessageEntity],
    ) -> tuple[GameSessionEntity, GameEndingResponse]:
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
        # Note: We do NOT save here anymore. The caller (execute) handles saving.

        # Load character name
        character = await self._character_repo.get_by_id(session.character_id)
        character_name = character.name if character else ""

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

        response = GameEndingResponse(
            session_id=session.id,
            ending_type=ending_type.value,
            narrative=narrative,
            total_turns=session.turn_count,
            character_name=character_name,
            scenario_name="",  # TODO: requires scenario_repository
        )

        return session, response

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

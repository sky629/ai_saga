"""Process Action Use Case.

플레이어 액션을 처리하고 AI 응답을 생성하는 핵심 유스케이스.
기존 GameService.process_action()의 비즈니스 로직을 분리.
"""

import copy
import hashlib
import json
import logging
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel

from app.common.exception import Conflict
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import (
    CacheServiceInterface,
    CharacterRepositoryInterface,
    GameMemoryRepositoryInterface,
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    ImageGenerationServiceInterface,
    LLMServiceInterface,
    ScenarioRepositoryInterface,
    UserProgressionInterface,
)
from app.game.application.services.game_memory_text_builder import (
    GameMemoryTextBuilder,
)
from app.game.application.services.rag_context_builder import RAGContextBuilder
from app.game.application.services.turn_prompt_composer import (
    TurnPromptComposer,
)
from app.game.domain.entities import (
    CharacterEntity,
    GameMemoryEntity,
    GameMessageEntity,
    GameSessionEntity,
)
from app.game.domain.services import (
    DiceService,
    GameMasterService,
    UserProgressionService,
)
from app.game.domain.value_objects import (
    ActionType,
    EndingType,
    GameMemoryType,
    GameState,
    MessageRole,
    SessionStatus,
    StateChanges,
)
from app.game.domain.value_objects.dice import DiceCheckType
from app.game.domain.value_objects.scenario_difficulty import (
    ScenarioDifficulty,
)
from app.game.presentation.routes.schemas.response import (
    ActionOptionResponse,
    DiceResultResponse,
    GameActionResponse,
    GameEndingResponse,
    GameMessageResponse,
)
from app.llm.embedding_service_interface import EmbeddingServiceInterface
from app.llm.prompts.game_master import build_dice_result_section
from config.settings import settings

logger = logging.getLogger(__name__)


class _NullGameMemoryRepository:
    """명시적 메모리 저장소가 없을 때 사용하는 no-op 구현."""

    async def create(self, memory: GameMemoryEntity) -> GameMemoryEntity:
        return memory

    async def get_similar_memories(
        self,
        embedding: list[float],
        session_id: UUID,
        limit: int = 5,
        distance_threshold: float = 0.3,
        exclude_memory_ids: Optional[list[UUID]] = None,
    ) -> list[GameMemoryEntity]:
        return []


class ProcessActionInput(BaseModel):
    """Use Case 입력 DTO."""

    model_config = {"frozen": True}

    session_id: UUID
    action: str
    action_type: Optional[str] = None
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
        scenario_repository: ScenarioRepositoryInterface,
        llm_service: LLMServiceInterface,
        cache_service: CacheServiceInterface,
        embedding_service: EmbeddingServiceInterface,
        memory_repository: Optional[GameMemoryRepositoryInterface] = None,
        image_service: Optional[ImageGenerationServiceInterface] = None,
        user_progression: Optional[UserProgressionInterface] = None,
    ):
        self._session_repo = session_repository
        self._message_repo = message_repository
        self._memory_repo = memory_repository or _NullGameMemoryRepository()
        self._character_repo = character_repository
        self._scenario_repo = scenario_repository
        self._llm = llm_service
        self._cache = cache_service
        self._embedding = embedding_service
        self._image_service = image_service
        self._user_progression = user_progression

    async def execute(
        self, user_id: UUID, input_data: ProcessActionInput
    ) -> ProcessActionResult:
        """유스케이스 실행."""
        # 1. Idempotency Check
        payload_hash = self._compute_action_payload_hash(
            input_data.action, input_data.action_type
        )
        cache_key = f"game:idempotency:{input_data.session_id}:{input_data.idempotency_key}"
        cached_data = await self._cache.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            cached_payload_hash = data.get("payload_hash")
            if (
                cached_payload_hash is not None
                and cached_payload_hash != payload_hash
            ):
                raise Conflict(
                    message=(
                        "같은 Idempotency-Key에 다른 요청 본문을 사용할 수 없습니다."
                    )
                )
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
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(user_message)

        user_memory = GameMemoryEntity(
            id=get_uuid7(),
            session_id=session.id,
            source_message_id=user_message.id,
            role=MessageRole.USER,
            memory_type=GameMemoryType.USER_ACTION,
            content=input_data.action,
            embedding=action_embedding,
            created_at=get_utc_datetime(),
        )
        await self._memory_repo.create(user_memory)

        # 7. Build hybrid context (Sliding Window + RAG)
        # 7.1. Get recent messages (sliding window)
        recent_limit = max(1, settings.rag_recent_messages_limit)
        recent_messages = await self._message_repo.get_recent_messages(
            session.id, limit=recent_limit
        )
        history_messages = [
            message
            for message in recent_messages
            if message.id != user_message.id
        ]

        # 7.2. Get similar memories (RAG)
        rag_limit = max(0, settings.rag_similar_messages_limit)
        rag_candidate_limit = max(rag_limit * 3, rag_limit)
        rag_memories = await self._memory_repo.get_similar_memories(
            embedding=action_embedding,
            session_id=session.id,
            limit=rag_candidate_limit,
            distance_threshold=settings.rag_distance_threshold,
            exclude_memory_ids=[user_memory.id],
        )

        # 7.3. Select recalled memories (state consistency + weighted RAG)
        selected_rag_memories = RAGContextBuilder.select_relevant_rag_messages(
            rag_messages=rag_memories,
            current_location=session.current_location,
            max_messages=rag_limit,
            similarity_weight=settings.rag_similarity_weight,
            recency_weight=settings.rag_recency_weight,
        )

        # 8. Check if final turn (domain logic)
        if GameMasterService.should_end_game(session):
            session, response = await self._handle_ending(
                session, recent_messages, user_id
            )
        else:
            session, response = await self._handle_normal_turn(
                session,
                user_id,
                input_data.action,
                input_data.action_type,
                history_messages,
                selected_rag_memories,
            )

        # 9. Save session state
        await self._session_repo.save(session)

        # 10. Commit before idempotency cache write
        await self._session_repo.commit()

        # 11. Cache response for idempotency
        cache_key = f"game:idempotency:{input_data.session_id}:{input_data.idempotency_key}"
        await self._cache_response(
            cache_key, response, payload_hash=payload_hash
        )

        return ProcessActionResult(response=response)

    def _validate_session(
        self, session: GameSessionEntity, user_id: UUID
    ) -> None:
        """세션 유효성 검증."""
        if session.user_id != user_id:
            raise ValueError("Session does not belong to user")

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

        # Check if session has reached max turns
        if session.is_final_turn:
            raise ValueError(
                f"Session has reached maximum turns ({session.max_turns}). "
                "Cannot process further actions."
            )

    async def _handle_normal_turn(
        self,
        session: GameSessionEntity,
        user_id: UUID,
        player_action: str,
        action_type_hint: Optional[str],
        conversation_history: list[GameMessageEntity],
        recalled_memories: list[GameMemoryEntity],
    ) -> tuple[
        GameSessionEntity, Union[GameActionResponse, GameEndingResponse]
    ]:
        """일반 턴 처리."""
        # Parse current game state
        game_state = GameState.from_dict(session.game_state)

        # Load scenario for difficulty context
        scenario = await self._scenario_repo.get_by_id(session.scenario_id)
        if not scenario:
            raise ValueError("Scenario not found")

        character = await self._character_repo.get_by_id(session.character_id)
        if not character:
            raise ValueError(f"Character {session.character_id} not found")

        action_type = self._resolve_action_type(
            player_action, action_type_hint
        )
        should_apply_dice = action_type.requires_dice
        dice_result = None
        dice_result_section = ""

        if should_apply_dice:
            check_type = self._to_dice_check_type(action_type)
            dice_result = DiceService.perform_check(
                level=character.stats.level,
                difficulty=self._coerce_scenario_difficulty(
                    scenario.difficulty
                ),
                check_type=check_type,
            )
            dice_result_section = build_dice_result_section(dice_result)

        prompt = TurnPromptComposer.compose(
            scenario_name=scenario.name,
            world_setting=scenario.world_setting,
            character_name=character.name,
            character_description=character.prompt_profile,
            current_location=session.current_location,
            game_state=game_state,
            inventory=character.inventory,
            player_action=player_action,
            conversation_history=conversation_history,
            recalled_memories=recalled_memories,
            dice_result_section=dice_result_section,
        )

        # Generate LLM response
        llm_response = await self._llm.generate_response(
            system_prompt=prompt.system_prompt,
            messages=prompt.messages,
        )

        # Try to parse JSON response
        parsed = GameMasterService.parse_llm_response(llm_response.content)
        logger.info(f"[DEBUG] LLM response parsed: {parsed is not None}")

        dice_applied = False
        before_narrative = None
        persisted_parsed_response = parsed if parsed else None
        if parsed:
            # Extract structured data
            narrative = GameMasterService.extract_narrative_from_parsed(
                parsed, llm_response.content
            )
            options = self._normalize_action_options(
                GameMasterService.extract_options_from_parsed(parsed)
            )
            dice_applied = should_apply_dice and (
                GameMasterService.extract_dice_applied(parsed)
            )
            state_changes = GameMasterService.extract_state_changes(parsed)
            if dice_applied:
                before_narrative = (
                    GameMasterService.extract_before_narrative_from_parsed(
                        parsed
                    )
                )

            # Filter state_changes if dice check failed
            if (
                dice_applied
                and dice_result is not None
                and not dice_result.is_success
            ):
                state_changes = (
                    GameMasterService.filter_state_changes_on_dice_failure(
                        state_changes
                    )
                )

            resolved_hp_change = state_changes.hp_change
            if (
                dice_result is not None
                and dice_result.is_fumble
                and dice_result.damage
            ):
                resolved_hp_change = -dice_result.damage
            elif should_apply_dice and not dice_applied:
                resolved_hp_change = 0
            if resolved_hp_change != state_changes.hp_change:
                state_changes = state_changes.model_copy(
                    update={"hp_change": resolved_hp_change}
                )

            persisted_parsed_response = self._build_persisted_parsed_response(
                parsed=parsed,
                narrative=narrative,
                state_changes=state_changes,
                dice_applied=dice_applied,
                before_narrative=before_narrative,
            )

            # Update session state
            session = session.update_game_state(state_changes)

            # Update location if changed
            if state_changes.location:
                session = session.update_location(state_changes.location)

            # 🆕 Update Character HP and Inventory
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
                        await self._character_repo.save(character)
                        logger.info(
                            f"[DEBUG] Character saved successfully: hp={character.stats.hp}, inventory={character.inventory}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[DEBUG] Character save FAILED: {type(e).__name__}: {e}"
                        )
                        raise

            character = await self._character_repo.get_by_id(
                session.character_id
            )
            if character and GameMasterService.should_end_game_by_death(
                character
            ):
                session = session.complete(EndingType.DEFEAT)
                await self._session_repo.save(session)
                ending_response = await self._handle_death_ending(
                    session,
                    character,
                    narrative,
                    conversation_history,
                    user_id,
                )
                return session, ending_response
        else:
            # Fallback to text parsing if JSON parsing fails
            logger.warning(
                f"Failed to parse JSON from LLM response: {llm_response.content[:200]}"
            )

            narrative = llm_response.content
            options = self._normalize_action_options(
                GameMasterService.extract_action_options(llm_response.content)
            )

        image_url = None

        # Save AI message with image_url
        ai_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=llm_response.content,
            parsed_response=persisted_parsed_response,
            token_count=(
                llm_response.usage.total_tokens if llm_response.usage else None
            ),
            image_url=image_url,
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(ai_message)

        ai_memory_content = GameMemoryTextBuilder.build_assistant_search_text(
            raw_content=llm_response.content,
            parsed_response=persisted_parsed_response,
        )
        ai_embedding = await self._embedding.generate_embedding(
            ai_memory_content
        )
        ai_memory = GameMemoryEntity(
            id=get_uuid7(),
            session_id=session.id,
            source_message_id=ai_message.id,
            role=MessageRole.ASSISTANT,
            memory_type=GameMemoryType.ASSISTANT_NARRATIVE,
            content=ai_memory_content,
            parsed_response=persisted_parsed_response,
            embedding=ai_embedding,
            created_at=get_utc_datetime(),
        )
        await self._memory_repo.create(ai_memory)

        dice_result_response = None
        if parsed and dice_applied and dice_result is not None:
            dice_result_response = DiceResultResponse(
                roll=dice_result.roll,
                modifier=dice_result.modifier,
                total=dice_result.total,
                dc=dice_result.dc,
                is_success=dice_result.is_success,
                is_critical=dice_result.is_critical,
                is_fumble=dice_result.is_fumble,
                check_type=dice_result.check_type.value,
                damage=dice_result.damage,
                display_text=dice_result.display_text,
            )

        response = GameActionResponse(
            message=GameMessageResponse(
                id=ai_message.id,
                role=ai_message.role.value,
                content=ai_message.content,
                parsed_response=ai_message.parsed_response,
                image_url=image_url,
                created_at=ai_message.created_at,
            ),
            narrative=narrative,
            options=options,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            is_ending=False,
            image_url=image_url,
            dice_result=dice_result_response,
            before_roll_narrative=before_narrative if parsed else None,
        )

        return session, response

    @staticmethod
    def _build_persisted_parsed_response(
        parsed: dict,
        narrative: str,
        state_changes: StateChanges,
        dice_applied: bool,
        before_narrative: Optional[str],
    ) -> dict:
        persisted = copy.deepcopy(parsed)
        persisted["narrative"] = narrative
        persisted["dice_applied"] = dice_applied

        if before_narrative:
            persisted["before_narrative"] = before_narrative
        else:
            persisted.pop("before_narrative", None)

        persisted["state_changes"] = {
            "hp_change": state_changes.hp_change,
            "experience_gained": state_changes.experience_gained,
            "items_gained": state_changes.items_gained,
            "items_lost": state_changes.items_lost,
            "location": state_changes.location,
            "npcs_met": state_changes.npcs_met,
            "discoveries": state_changes.discoveries,
        }

        return persisted

    @staticmethod
    def _coerce_scenario_difficulty(
        difficulty: ScenarioDifficulty | str,
    ) -> ScenarioDifficulty:
        if isinstance(difficulty, ScenarioDifficulty):
            return difficulty
        return ScenarioDifficulty(difficulty)

    async def _handle_ending(
        self,
        session: GameSessionEntity,
        recent_messages: list[GameMessageEntity],
        user_id: Optional[UUID] = None,
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

        ending_type = GameMasterService.parse_ending_type(llm_response.content)
        narrative = GameMasterService.extract_narrative_from_ending(
            llm_response.content
        )

        session = session.complete(ending_type)

        character = await self._character_repo.get_by_id(session.character_id)
        character_name = character.name if character else ""

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

        xp_gained = 0
        progression = None
        if self._user_progression and user_id:
            try:
                scenario = await self._scenario_repo.get_by_id(
                    session.scenario_id
                )
                difficulty = (
                    scenario.difficulty
                    if scenario
                    else ScenarioDifficulty.NORMAL
                )
                xp_gained = UserProgressionService.calculate_game_xp(
                    ending_type, session.turn_count, difficulty
                )
                progression = (
                    await self._user_progression.award_game_experience(
                        user_id, xp_gained
                    )
                )
            except Exception as e:
                logger.error(f"XP 부여 실패 (무시됨): {e}")
                xp_gained = 0
                progression = None

        scenario = await self._scenario_repo.get_by_id(session.scenario_id)

        response = GameEndingResponse(
            session_id=session.id,
            ending_type=ending_type.value,
            narrative=narrative,
            total_turns=session.turn_count,
            character_name=character_name,
            scenario_name=scenario.name if scenario else "",
            xp_gained=xp_gained,
            new_game_level=progression.game_level if progression else 1,
            leveled_up=progression.leveled_up if progression else False,
            levels_gained=progression.levels_gained if progression else 0,
        )

        return session, response

    async def _handle_death_ending(
        self,
        session: GameSessionEntity,
        character: CharacterEntity,
        narrative: str,
        recent_messages: list[GameMessageEntity],
        user_id: Optional[UUID] = None,
    ) -> GameEndingResponse:
        death_narrative = (
            f"{narrative}\n\n"
            f"💀 {character.name}의 HP가 0이 되어 사망했습니다. "
            f"게임 오버."
        )

        ending_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=death_narrative,
            parsed_response={"ending_type": "defeat"},
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(ending_message)

        xp_gained = 0
        progression = None
        if self._user_progression and user_id:
            try:
                scenario = await self._scenario_repo.get_by_id(
                    session.scenario_id
                )
                difficulty = (
                    scenario.difficulty
                    if scenario
                    else ScenarioDifficulty.NORMAL
                )
                xp_gained = UserProgressionService.calculate_game_xp(
                    EndingType.DEFEAT, session.turn_count, difficulty
                )
                progression = (
                    await self._user_progression.award_game_experience(
                        user_id, xp_gained
                    )
                )
            except Exception as e:
                logger.error(f"XP 부여 실패 (무시됨): {e}")
                xp_gained = 0
                progression = None

        scenario = await self._scenario_repo.get_by_id(session.scenario_id)

        return GameEndingResponse(
            session_id=session.id,
            ending_type=EndingType.DEFEAT.value,
            narrative=death_narrative,
            total_turns=session.turn_count,
            character_name=character.name,
            scenario_name=scenario.name if scenario else "",
            xp_gained=xp_gained,
            new_game_level=progression.game_level if progression else 1,
            leveled_up=progression.leveled_up if progression else False,
            levels_gained=progression.levels_gained if progression else 0,
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
        payload_hash: Optional[str] = None,
    ) -> None:
        """응답 캐싱."""
        is_ending = isinstance(response, GameEndingResponse)

        cache_data = {
            "type": "ending" if is_ending else "action",
            "data": response.model_dump(mode="json"),
        }
        if payload_hash is not None:
            cache_data["payload_hash"] = payload_hash
        await self._cache.set(
            cache_key, json.dumps(cache_data), ttl_seconds=600
        )

    @staticmethod
    def _compute_action_payload_hash(
        action: str, action_type: Optional[str] = None
    ) -> str:
        payload = {"action": action}
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

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

    @staticmethod
    def _resolve_action_type(
        action: str, action_type_hint: Optional[str] = None
    ) -> ActionType:
        # TODO: 현재는 서버 규칙 기반 분류를 사용한다.
        # 추후에는 ActionClassifier 인터페이스로 분리하고,
        # 애매한 자유 입력은 경량 로컬 LLM 분류 엔진으로 대체한다.
        # 단, 메인 게임 LLM 호출은 턴당 1회 원칙을 유지하고
        # 최종 requires_dice 결정 권한은 서버가 가진다.
        if action_type_hint:
            logger.info(
                "Received action_type hint '%s'; server inference remains authoritative",
                action_type_hint,
            )

        normalized = action.lower().strip()

        combat_keywords = [
            "attack",
            "fight",
            "strike",
            "hit",
            "battle",
            "swing",
            "slash",
            "stab",
            "lunge",
            "charge",
            "aim",
            "전투",
            "공격",
            "베기",
            "찌르기",
            "사격",
            "휘두르",
            "휘두른",
            "후려치",
            "내리치",
            "겨누",
            "돌진",
            "습격",
        ]
        social_keywords = [
            "persuade",
            "threaten",
            "negotiate",
            "설득",
            "협상",
            "위협",
            "거래",
        ]
        skill_keywords = [
            "hack",
            "unlock",
            "disarm",
            "craft",
            "pick lock",
            "해킹",
            "자물쇠",
            "함정 해제",
            "제작",
            "수리",
        ]
        rest_keywords = [
            "rest",
            "wait",
            "sleep",
            "camp",
            "휴식",
            "쉰",
            "대기",
            "잔다",
        ]
        observation_keywords = [
            "look",
            "observe",
            "inspect",
            "search",
            "살핀",
            "본다",
            "관찰",
            "조사",
        ]
        movement_keywords = [
            "move",
            "walk",
            "go",
            "이동",
            "간다",
            "걷",
        ]
        preparation_keywords = [
            "칼을 뽑",
            "검을 뽑",
            "무기를 뽑",
            "칼을 꺼",
            "검을 꺼",
            "무기를 꺼",
            "칼자루를 잡",
            "검자루를 잡",
            "자세를 잡",
            "전투 준비",
            "ready weapon",
            "draw sword",
            "draw blade",
            "unsheathe",
        ]
        exploration_keywords = [
            "잠입",
            "탈출",
            "도망",
            "숨",
            "엄폐",
            "점프",
            "기어오르",
            "등반",
            "건너",
            "열",
            "연다",
            "밀",
            "sneak",
            "escape",
            "hide",
            "jump",
            "climb",
            "cross",
            "open",
            "push",
        ]

        if any(keyword in normalized for keyword in combat_keywords):
            return ActionType.COMBAT
        if any(keyword in normalized for keyword in social_keywords):
            return ActionType.SOCIAL
        if any(keyword in normalized for keyword in skill_keywords):
            return ActionType.SKILL
        if any(keyword in normalized for keyword in exploration_keywords):
            return ActionType.EXPLORATION
        if any(keyword in normalized for keyword in rest_keywords):
            return ActionType.REST
        if any(keyword in normalized for keyword in preparation_keywords):
            return ActionType.OBSERVATION
        if any(keyword in normalized for keyword in observation_keywords):
            return ActionType.OBSERVATION
        if any(keyword in normalized for keyword in movement_keywords):
            return ActionType.MOVEMENT
        return ActionType.EXPLORATION

    @staticmethod
    def _to_dice_check_type(action_type: ActionType) -> DiceCheckType:
        if action_type == ActionType.COMBAT:
            return DiceCheckType.COMBAT
        if action_type == ActionType.SOCIAL:
            return DiceCheckType.SOCIAL
        if action_type == ActionType.SKILL:
            return DiceCheckType.SKILL
        return DiceCheckType.EXPLORATION

    def _normalize_action_options(
        self, raw_options: list[object]
    ) -> list[ActionOptionResponse]:
        normalized_options = []

        for option in raw_options:
            if isinstance(option, dict):
                label = str(option.get("label", "")).strip()
                inferred_type = self._resolve_action_type(
                    label,
                    (
                        str(option.get("action_type"))
                        if option.get("action_type")
                        else None
                    ),
                )
            else:
                label = str(option).strip()
                inferred_type = self._resolve_action_type(label)

            if not label:
                continue

            normalized_options.append(
                ActionOptionResponse(
                    label=label,
                    action_type=inferred_type.value,
                    requires_dice=inferred_type.requires_dice,
                )
            )

        return normalized_options

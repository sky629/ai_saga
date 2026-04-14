"""Process Action Use Case.

플레이어 액션을 처리하고 AI 응답을 생성하는 핵심 유스케이스.
기존 GameService.process_action()의 비즈니스 로직을 분리.
"""

import copy
import hashlib
import json
import logging
import re
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from app.common.exception import Conflict, ServerError
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
from app.game.application.services.illustration_generation_service import (
    IllustrationGenerationService,
)
from app.game.application.services.progression_state_service import (
    ProgressionStateService,
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
    GameType,
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
from app.llm.prompts.progression_game_master import (
    build_progression_ending_prompt,
    build_progression_title_prompt,
    build_progression_turn_prompt,
)
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

        scenario = await self._scenario_repo.get_by_id(session.scenario_id)
        if not scenario:
            raise ValueError("Scenario not found")

        if scenario.game_type == GameType.PROGRESSION:
            return await self._execute_progression(
                user_id=user_id,
                session=session,
                scenario=scenario,
                input_data=input_data,
                cache_key=cache_key,
                payload_hash=payload_hash,
            )

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
                scenario,
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

    async def _execute_progression(
        self,
        user_id: UUID,
        session: GameSessionEntity,
        scenario,
        input_data: ProcessActionInput,
        cache_key: str,
        payload_hash: str,
    ) -> ProcessActionResult:
        """progression 타입의 액션을 처리한다."""
        character = await self._character_repo.get_by_id(session.character_id)
        if not character:
            raise ValueError(f"Character {session.character_id} not found")

        user_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.USER,
            content=input_data.action,
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(user_message)

        recent_messages = await self._message_repo.get_recent_messages(
            session.id, limit=6
        )
        if not isinstance(recent_messages, list):
            recent_messages = []

        status_panel = ProgressionStateService.build_status_panel(
            session.game_state,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
        )
        system_prompt, messages = build_progression_turn_prompt(
            scenario_name=scenario.name,
            world_setting=scenario.world_setting,
            character_name=character.name,
            character_description=character.prompt_profile,
            current_location=session.current_location,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            status_panel=status_panel,
            player_action=input_data.action,
            conversation_history=[
                {"role": msg.role.value, "content": msg.content}
                for msg in recent_messages[-4:]
                if msg.id != user_message.id
            ],
            will_be_final_turn=(session.turn_count + 1) >= session.max_turns,
        )
        llm_response = None
        parsed: dict[str, Any] = {}
        narrative = ""
        consumes_turn = False
        response_options: list[ActionOptionResponse] = []
        updated_session = session
        updated_status_panel = status_panel
        image_focus = None
        attempt_messages = messages
        for attempt in range(2):
            llm_response = await self._llm.generate_response(
                system_prompt=system_prompt,
                messages=attempt_messages,
            )
            parsed = (
                GameMasterService.parse_llm_response(llm_response.content)
                or {}
            )

            narrative = GameMasterService.extract_narrative_from_parsed(
                parsed,
                fallback=llm_response.content,
            )
            parsed = ProgressionStateService.enrich_llm_response(
                parsed_response=parsed,
                narrative=narrative,
                current_state=session.game_state,
                player_action=input_data.action,
            )

            try:
                consumes_turn = self._require_progression_consumes_turn(
                    parsed.get("consumes_turn"),
                    input_data.action_type,
                )
                self._validate_progression_state_changes(
                    state_changes=parsed.get("state_changes"),
                    consumes_turn=consumes_turn,
                )

                if consumes_turn:
                    new_turn_count = session.turn_count + 1
                    new_state = ProgressionStateService.apply_state_changes(
                        current_state=session.game_state,
                        parsed_response=parsed,
                        turn_count=new_turn_count,
                        max_turns=session.max_turns,
                    )
                    update_payload = {
                        "turn_count": new_turn_count,
                        "game_state": new_state,
                        "last_activity_at": get_utc_datetime(),
                    }
                    next_location = parsed.get("state_changes", {}).get(
                        "location"
                    )
                    if (
                        isinstance(next_location, str)
                        and next_location.strip()
                    ):
                        update_payload["current_location"] = (
                            next_location.strip()
                        )
                    candidate_session = session.model_copy(
                        update=update_payload
                    )
                else:
                    candidate_session = session.model_copy(
                        update={"last_activity_at": get_utc_datetime()}
                    )

                is_final_turn_response = (
                    consumes_turn
                    and candidate_session.turn_count
                    >= candidate_session.max_turns
                )
                response_options = self._require_progression_options(
                    parsed.get("options"),
                    allow_empty=is_final_turn_response,
                )
                candidate_status_panel = (
                    ProgressionStateService.build_status_panel(
                        candidate_session.game_state,
                        turn_count=candidate_session.turn_count,
                        max_turns=candidate_session.max_turns,
                    )
                )
                self._validate_progression_narrative(
                    narrative=narrative,
                    status_panel=candidate_status_panel,
                )
                candidate_image_focus = None
                if consumes_turn and self._image_service:
                    candidate_image_focus = (
                        self._require_progression_image_focus(
                            parsed.get("image_focus")
                        )
                    )
            except ServerError as exc:
                if attempt == 0:
                    logger.warning(
                        "Retrying malformed progression response for session %s: %s",
                        session.id,
                        exc,
                    )
                    attempt_messages = self._build_progression_repair_messages(
                        messages=messages,
                        previous_response=llm_response.content,
                        error_message=str(exc),
                        will_be_final_turn=(
                            (session.turn_count + 1) >= session.max_turns
                        ),
                    )
                    continue
                raise

            updated_session = candidate_session
            updated_status_panel = candidate_status_panel
            image_focus = candidate_image_focus
            break

        if llm_response is None:
            raise ServerError(
                message="Progression response generation failed."
            )

        parsed_for_persistence = copy.deepcopy(parsed)
        parsed_for_persistence["options"] = [
            option.model_dump() for option in response_options
        ]
        persisted_parsed_response = self._build_progression_parsed_response(
            parsed=parsed_for_persistence,
            narrative=narrative,
            consumes_turn=consumes_turn,
            status_panel=updated_status_panel,
        )

        image_url = None
        if consumes_turn and self._image_service:
            prompt_context = IllustrationGenerationService.build_context(
                narrative=image_focus,
                parsed_response=persisted_parsed_response,
                character_name=character.name,
                character_description=character.prompt_profile,
                current_location=updated_session.current_location,
                scenario_genre=scenario.genre,
                scenario_name=scenario.name,
                scenario_world_setting=scenario.world_setting,
                scenario_tags=tuple(scenario.tags),
                scenario_game_type=scenario.game_type,
            )
            image_url = await IllustrationGenerationService.generate(
                image_service=self._image_service,
                context=prompt_context,
                session_id=str(updated_session.id),
                user_id=str(updated_session.user_id),
            )

        ai_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=updated_session.id,
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

        current_hp = int(updated_session.game_state.get("hp", 0))
        if consumes_turn and current_hp <= 0:
            response, updated_session = await self._build_progression_ending(
                session=updated_session,
                character=character,
                scenario=scenario,
                narrative=(
                    f"{narrative}\n\n"
                    f"💀 {character.name}의 체력이 바닥나며 더는 "
                    f"버티지 못하고 쓰러집니다."
                ),
                forced_ending=EndingType.DEFEAT,
                existing_image_url=image_url,
            )
        elif (
            consumes_turn
            and updated_session.turn_count >= updated_session.max_turns
        ):
            response, updated_session = await self._build_progression_ending(
                session=updated_session,
                character=character,
                scenario=scenario,
                narrative=narrative,
                forced_ending=None,
                existing_image_url=image_url,
            )
        else:
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
                options=response_options,
                turn_count=updated_session.turn_count,
                max_turns=updated_session.max_turns,
                is_ending=False,
                image_url=image_url,
                status_panel=updated_status_panel,
            )

        await self._session_repo.save(updated_session)
        await self._session_repo.commit()
        await self._cache_response(
            cache_key, response, payload_hash=payload_hash
        )
        return ProcessActionResult(response=response)

    async def _build_progression_ending(
        self,
        session: GameSessionEntity,
        character: CharacterEntity,
        scenario,
        narrative: str,
        forced_ending: EndingType | None,
        existing_image_url: str | None,
    ) -> tuple[GameEndingResponse, GameSessionEntity]:
        achievement_board = ProgressionStateService.build_achievement_board(
            state=session.game_state,
            character_name=character.name,
            scenario_name=scenario.name,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
        )

        ending_type = (
            forced_ending
            if forced_ending is not None
            else (
                EndingType.VICTORY
                if achievement_board["escaped"]
                else EndingType.DEFEAT
            )
        )
        if forced_ending is not None:
            achievement_board = ProgressionStateService.apply_forced_outcome(
                achievement_board,
                ending_type,
            )

        achievement_board = await self._generate_progression_title(
            scenario=scenario,
            character=character,
            ending_type=ending_type,
            achievement_board=achievement_board,
        )

        completed_session = session.complete(ending_type)
        ending_narrative = await self._generate_progression_ending_narrative(
            scenario=scenario,
            character=character,
            ending_type=ending_type,
            achievement_board=achievement_board,
            base_narrative=narrative,
            cause=(
                "hp_zero"
                if forced_ending == EndingType.DEFEAT
                else "turn_limit"
            ),
        )
        final_image_url = existing_image_url
        if self._image_service:
            final_image_url = await self._image_service.generate_image(
                prompt=ProgressionStateService.build_final_image_prompt(
                    achievement_board=achievement_board,
                    ending_narrative=ending_narrative,
                ),
                session_id=str(completed_session.id),
                user_id=str(completed_session.user_id),
            )
        completed_session = completed_session.model_copy(
            update={
                "game_state": ProgressionStateService.store_final_outcome(
                    state=completed_session.game_state,
                    achievement_board=achievement_board,
                    image_url=final_image_url,
                    ending_narrative=ending_narrative,
                    ending_type=ending_type.value,
                )
            }
        )
        ending_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=completed_session.id,
            role=MessageRole.ASSISTANT,
            content=ending_narrative,
            parsed_response={
                "narrative": ending_narrative,
                "options": [],
                "ending_type": ending_type.value,
                "final_outcome": {
                    "ending_type": ending_type.value,
                    "narrative": ending_narrative,
                    "image_url": final_image_url,
                    "achievement_board": achievement_board,
                },
            },
            image_url=final_image_url,
            created_at=get_utc_datetime(),
        )
        await self._message_repo.create(ending_message)
        return (
            GameEndingResponse(
                session_id=completed_session.id,
                ending_type=ending_type.value,
                narrative=ending_narrative,
                total_turns=completed_session.turn_count,
                character_name=character.name,
                scenario_name=scenario.name,
                final_outcome={
                    "ending_type": ending_type.value,
                    "narrative": ending_narrative,
                    "image_url": final_image_url,
                    "achievement_board": achievement_board,
                },
            ),
            completed_session,
        )

    async def _generate_progression_title(
        self,
        scenario,
        character: CharacterEntity,
        ending_type: EndingType,
        achievement_board: dict[str, Any],
    ) -> dict[str, Any]:
        """최종 업적 보드용 칭호를 생성하고 검증한다."""
        fallback_title = str(achievement_board.get("title", "")).strip()
        try:
            response = await self._llm.generate_response(
                system_prompt=build_progression_title_prompt(
                    scenario_name=scenario.name,
                    world_setting=scenario.world_setting,
                    character_name=character.name,
                    ending_type=ending_type.value,
                    achievement_board=achievement_board,
                ),
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "최종 업적 보드용 칭호와 한 줄 이유를 "
                            "JSON으로 생성해주세요."
                        ),
                    }
                ],
            )
            parsed = GameMasterService.parse_llm_response(response.content)
            if not isinstance(parsed, dict):
                return achievement_board

            title = self._validate_progression_title(
                parsed.get("title"),
                ending_type=ending_type,
            )
            if not title:
                return achievement_board

            title_reason = str(parsed.get("title_reason", "")).strip()
            return ProgressionStateService.apply_generated_title(
                achievement_board=achievement_board,
                title=title,
                title_reason=title_reason,
            )
        except Exception:
            logger.exception(
                "progression final title generation failed: session=%s",
                achievement_board.get("character_name", ""),
            )
            if fallback_title:
                return achievement_board
            return ProgressionStateService.apply_generated_title(
                achievement_board=achievement_board,
                title="무명수련자",
                title_reason="최종 칭호 생성에 실패해 기본 칭호를 사용했습니다.",
            )

    @staticmethod
    def _validate_progression_title(
        raw_title: object,
        ending_type: EndingType,
    ) -> str | None:
        """최종 칭호 형식과 금칙어를 검증한다."""
        if not isinstance(raw_title, str):
            return None
        title = raw_title.strip()
        if not title or len(title) < 2 or len(title) > 12:
            return None

        banned = (
            ("탈출", "생환", "파천", "돌파", "절정")
            if ending_type == EndingType.DEFEAT
            else ("낙명", "사망", "패잔", "추락")
        )
        if any(keyword in title for keyword in banned):
            return None
        return title

    async def _generate_progression_ending_narrative(
        self,
        scenario,
        character: CharacterEntity,
        ending_type: EndingType,
        achievement_board: dict,
        base_narrative: str,
        cause: str,
    ) -> str:
        """최종 판정과 정합된 progression 엔딩 서사를 생성한다."""
        try:
            response = await self._llm.generate_response(
                system_prompt=build_progression_ending_prompt(
                    scenario_name=scenario.name,
                    world_setting=scenario.world_setting,
                    character_name=character.name,
                    ending_type=ending_type.value,
                    achievement_board=achievement_board,
                    cause=cause,
                ),
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "서버가 확정한 판정에 맞는 최종 엔딩만 "
                            "서술해주세요."
                        ),
                    }
                ],
            )
            parsed = GameMasterService.parse_llm_response(response.content)
            if isinstance(parsed, dict):
                return GameMasterService.extract_narrative_from_parsed(
                    parsed,
                    fallback=base_narrative,
                )
            return response.content.strip() or base_narrative
        except Exception:
            return base_narrative

    @staticmethod
    def _build_progression_parsed_response(
        parsed: dict,
        narrative: str,
        consumes_turn: bool,
        status_panel: dict,
    ) -> dict:
        persisted = copy.deepcopy(parsed)
        persisted["narrative"] = narrative
        persisted["consumes_turn"] = consumes_turn
        persisted["status_panel"] = status_panel
        return persisted

    @staticmethod
    def _build_progression_repair_messages(
        messages: list[dict[str, str]],
        previous_response: str,
        error_message: str,
        will_be_final_turn: bool,
    ) -> list[dict[str, str]]:
        """계약 위반 progression 응답에 대해 1회 재생성을 요청한다."""
        repaired_messages = list(messages)
        repaired_messages.append(
            {"role": "assistant", "content": previous_response}
        )
        option_instruction = (
            "이번 응답은 마지막 턴이므로 `options`는 반드시 빈 배열 `[]`로 두세요."
            if will_be_final_turn
            else "이번 응답은 마지막 턴이 아니므로 `options`에 1~5개의 구체적인 행동만 넣으세요."
        )
        repaired_messages.append(
            {
                "role": "user",
                "content": (
                    "방금 JSON 응답은 계약 위반입니다. "
                    f"오류: {error_message} "
                    "같은 행동에 대한 결과를 처음부터 다시 생성하세요. "
                    "narrative에는 선택지 bullet을 넣지 말고, "
                    f"{option_instruction} "
                    "JSON만 출력하세요."
                ),
            }
        )
        return repaired_messages

    @staticmethod
    def _require_progression_consumes_turn(
        raw_consumes_turn: object,
        action_type_hint: Optional[str],
    ) -> bool:
        """진행형 응답의 consumes_turn 계약을 검증한다."""
        normalized_hint = str(action_type_hint or "").strip().lower()
        if normalized_hint == "progression":
            if raw_consumes_turn is not True:
                raise ServerError(
                    message=(
                        "Malformed progression response: "
                        "consumes_turn must be true."
                    )
                )
            return True
        if normalized_hint == "question":
            if raw_consumes_turn is not False:
                raise ServerError(
                    message=(
                        "Malformed progression response: "
                        "consumes_turn must be false for questions."
                    )
                )
            return False
        if not isinstance(raw_consumes_turn, bool):
            raise ServerError(
                message=(
                    "Malformed progression response: "
                    "consumes_turn must be boolean."
                )
            )
        return raw_consumes_turn

    @staticmethod
    def _has_meaningful_progression_state_changes(
        state_changes: dict[str, Any],
    ) -> bool:
        meaningful_numeric_fields = (
            "hp_change",
            "internal_power_delta",
            "external_power_delta",
        )
        meaningful_list_fields = (
            "items_gained",
            "items_lost",
            "npcs_met",
            "discoveries",
            "manuals_gained",
            "manual_mastery_updates",
            "traits_gained",
            "title_candidates",
        )
        for field in meaningful_numeric_fields:
            if state_changes.get(field):
                return True
        for field in meaningful_list_fields:
            value = state_changes.get(field)
            if isinstance(value, list) and value:
                return True
        location = state_changes.get("location")
        return isinstance(location, str) and bool(location.strip())

    @classmethod
    def _validate_progression_state_changes(
        cls,
        state_changes: object,
        consumes_turn: bool,
    ) -> None:
        """질문 응답의 성장 payload를 금지한다."""
        if consumes_turn:
            return
        if not isinstance(state_changes, dict):
            return
        if cls._has_meaningful_progression_state_changes(state_changes):
            raise ServerError(
                message=(
                    "Malformed progression response: "
                    "questions must not include state changes."
                )
            )
        return None

    @classmethod
    def _require_progression_options(
        cls,
        raw_options: object,
        allow_empty: bool = False,
    ) -> list[ActionOptionResponse]:
        """진행형 선택지 계약을 검증한다."""
        if not isinstance(raw_options, list):
            raise ServerError(
                message=(
                    "Malformed progression response: "
                    "options must be a list."
                )
            )
        if allow_empty:
            if raw_options:
                raise ServerError(
                    message=(
                        "Malformed progression response: "
                        "final turn options must be an empty list."
                    )
                )
            return []
        if len(raw_options) < 1 or len(raw_options) > 5:
            raise ServerError(
                message=(
                    "Malformed progression response: "
                    "options must contain 1 to 5 entries."
                )
            )

        normalized: list[ActionOptionResponse] = []
        for option in raw_options:
            if not isinstance(option, dict):
                raise ServerError(
                    message=(
                        "Malformed progression response: "
                        "each option must be an object."
                    )
                )

            label = str(option.get("label", "")).strip()
            if not label or cls._is_invalid_progression_option_label(label):
                raise ServerError(
                    message=(
                        "Malformed progression response: "
                        "option labels must be concrete actions."
                    )
                )

            action_type = str(option.get("action_type", "")).strip()
            if action_type not in {"progression", "question"}:
                raise ServerError(
                    message=(
                        "Malformed progression response: "
                        "action_type must be progression or question."
                    )
                )

            normalized.append(
                ActionOptionResponse(
                    label=label,
                    action_type=action_type,
                    requires_dice=False,
                )
            )

        return normalized

    @staticmethod
    def _is_invalid_progression_option_label(label: str) -> bool:
        normalized = " ".join(label.strip().lower().split())
        if not normalized:
            return True
        generic_labels = {
            "다음 행동",
            "행동 선택",
            "다음 선택",
            "선택지",
            "옵션",
            "next action",
            "choose action",
            "action",
        }
        if normalized in generic_labels:
            return True
        if re.fullmatch(r"옵션\s*\d+", normalized):
            return True
        if re.fullmatch(r"option\s*\d+", normalized):
            return True
        return False

    @classmethod
    def _validate_progression_narrative(
        cls,
        narrative: str,
        status_panel: dict[str, Any],
    ) -> None:
        """선택지 중복과 상태 불일치를 검증한다."""
        for line in narrative.splitlines():
            stripped = line.strip()
            if re.match(r"^(?:\*|-|•|\d+\.)\s+", stripped):
                raise ServerError(
                    message=(
                        "Malformed progression response: "
                        "narrative must not include option bullets."
                    )
                )

        manuals = status_panel.get("manuals")
        if not isinstance(manuals, list):
            return None

        for manual in manuals:
            if not isinstance(manual, dict):
                continue
            name = str(manual.get("name", "")).strip()
            mastery = manual.get("mastery")
            if not name or not isinstance(mastery, int):
                continue

            aliases = [name]
            short_name = name.split(" (", 1)[0].strip()
            if short_name and short_name not in aliases:
                aliases.append(short_name)

            for alias in aliases:
                pattern = re.compile(
                    rf"({re.escape(alias)}[^\n]{{0,80}}?숙련도(?:가)?\s*)"
                    rf"(\d+)(%?)"
                )
                match = pattern.search(narrative)
                if not match:
                    continue
                if int(match.group(2)) != mastery:
                    raise ServerError(
                        message=(
                            "Malformed progression response: "
                            "manual mastery in narrative does not match "
                            "state changes."
                        )
                    )
        return None

    @staticmethod
    def _require_progression_image_focus(raw_image_focus: object) -> str:
        """이미지 프롬프트용 핵심 묘사를 검증한다."""
        if not isinstance(raw_image_focus, str):
            raise ServerError(
                message=(
                    "Malformed progression response: "
                    "image_focus must be provided."
                )
            )
        image_focus = re.sub(r"\s+", " ", raw_image_focus).strip()
        if not image_focus:
            raise ServerError(
                message=(
                    "Malformed progression response: "
                    "image_focus must not be empty."
                )
            )
        return image_focus[:220]

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
        scenario,
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
                options=options,
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
                session, ending_response = await self._handle_death_ending(
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
        options: list[ActionOptionResponse],
        state_changes: StateChanges,
        dice_applied: bool,
        before_narrative: Optional[str],
    ) -> dict:
        persisted = copy.deepcopy(parsed)
        persisted["narrative"] = narrative
        persisted["dice_applied"] = dice_applied
        persisted["options"] = [option.model_dump() for option in options]

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
            final_outcome={
                "ending_type": ending_type.value,
                "narrative": narrative,
                "image_url": None,
                "achievement_board": None,
            },
        )

        return session, response

    async def _handle_death_ending(
        self,
        session: GameSessionEntity,
        character: CharacterEntity,
        narrative: str,
        recent_messages: list[GameMessageEntity],
        user_id: Optional[UUID] = None,
    ) -> tuple[GameSessionEntity, GameEndingResponse]:
        death_narrative = (
            f"{narrative}\n\n"
            f"💀 {character.name}의 HP가 0이 되어 사망했습니다. "
            f"게임 오버."
        )
        death_image_url = None
        if self._image_service:
            scenario = await self._scenario_repo.get_by_id(session.scenario_id)
            raw_prompt_profile = getattr(character, "prompt_profile", "")
            character_prompt_profile = (
                raw_prompt_profile
                if isinstance(raw_prompt_profile, str)
                else ""
            )
            death_image_url = await self._image_service.generate_image(
                prompt=self._build_death_ending_image_prompt(
                    character_name=character.name,
                    character_prompt_profile=character_prompt_profile,
                    current_location=session.current_location,
                    death_narrative=death_narrative,
                    scenario_name=scenario.name if scenario else "",
                ),
                session_id=str(session.id),
                user_id=str(session.user_id),
            )

        ending_message = GameMessageEntity(
            id=get_uuid7(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=death_narrative,
            parsed_response={"ending_type": "defeat"},
            image_url=death_image_url,
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
        session = session.model_copy(
            update={
                "game_state": {
                    **session.game_state,
                    "final_outcome": {
                        "ending_type": EndingType.DEFEAT.value,
                        "narrative": death_narrative,
                        "image_url": death_image_url,
                        "achievement_board": None,
                    },
                }
            }
        )
        return session, GameEndingResponse(
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
            final_outcome={
                "ending_type": EndingType.DEFEAT.value,
                "narrative": death_narrative,
                "image_url": death_image_url,
                "achievement_board": None,
            },
        )

    @staticmethod
    def _build_death_ending_image_prompt(
        character_name: str,
        character_prompt_profile: str,
        current_location: str,
        death_narrative: str,
        scenario_name: str,
    ) -> str:
        scene = re.sub(r"\s+", " ", death_narrative).strip()
        scene = re.sub(r"[\"'`]+", "", scene)
        scene = re.sub(r"\d+", "", scene)
        scene = scene.replace("HP", "").replace("hp", "")
        if len(scene) > 220:
            scene = scene[:220].rsplit(" ", 1)[0]
        location = current_location.strip() or "a hostile cavern"
        world_hint = (
            f"Set the scene in {scenario_name}. " if scenario_name else ""
        )
        profile_hint = (
            ProcessActionUseCase._sanitize_death_ending_profile_hint(
                character_prompt_profile
            )
        )
        return (
            "Create a vertical tragic wuxia ending illustration. "
            "Use a Chinese martial arts animation atmosphere with a refined "
            "Japanese-anime-like protagonist. "
            f"{world_hint}"
            f"Show {character_name} collapsed in {location} after a fatal final struggle. "
            f"{profile_hint}"
            f"Ending moment cue: {scene or 'the final exhausted silence after defeat'}. "
            "Focus on stillness, exhaustion, broken terrain, dim cave light, "
            "and the aftermath of defeat. "
            "No readable text, letters, words, numbers, captions, subtitles, "
            "logos, watermarks, signage, labels, HUDs, stat panels, "
            "achievement boards, trading cards, menus, or UI elements "
            "anywhere in the image."
        )

    @staticmethod
    def _sanitize_death_ending_profile_hint(
        character_prompt_profile: str,
    ) -> str:
        """사망 엔딩 이미지 프롬프트용 캐릭터 프로필을 정리한다."""
        if not character_prompt_profile.strip():
            return ""

        filtered_lines: list[str] = []
        for line in character_prompt_profile.splitlines():
            normalized = line.strip()
            if not normalized:
                continue
            if "성별: 비공개" in normalized:
                continue
            filtered_lines.append(normalized.lstrip("-").strip())

        if not filtered_lines:
            return ""

        return "Character reference: " + " ".join(filtered_lines) + " "

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

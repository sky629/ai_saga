"""Generate Ending Use Case.

게임 엔딩을 생성하는 유스케이스.
ProcessActionUseCase에서 분리된 독립적인 엔딩 처리 로직.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.game.application.ports import (
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    LLMServiceInterface,
)
from app.game.domain.entities import GameMessageEntity, GameSessionEntity
from app.game.domain.services import GameMasterService
from app.game.domain.value_objects import EndingType, MessageRole
from app.game.dto.response import GameEndingResponse


class GenerateEndingInput(BaseModel):
    """Use Case 입력 DTO."""
    model_config = {"frozen": True}
    
    session_id: UUID
    user_id: UUID


class GenerateEndingUseCase:
    """게임 엔딩 생성 유스케이스.
    
    Single Responsibility: 게임 엔딩을 생성하고
    세션을 완료 상태로 변경하는 것만 담당합니다.
    """

    def __init__(
        self,
        session_repository: GameSessionRepositoryInterface,
        message_repository: GameMessageRepositoryInterface,
        llm_service: LLMServiceInterface,
    ):
        self._session_repo = session_repository
        self._message_repo = message_repository
        self._llm = llm_service

    async def execute(self, input_data: GenerateEndingInput) -> GameEndingResponse:
        """유스케이스 실행."""
        # 1. Load session
        session = await self._session_repo.get_by_id(input_data.session_id)
        if not session:
            raise ValueError("Session not found")

        # 2. Validate session is active
        if not session.is_active:
            raise ValueError("Session is not active")

        # 3. Get recent messages for context
        recent_messages = await self._message_repo.get_recent_messages(
            session.id, limit=10
        )

        # 4. Generate ending
        response = await self._generate_ending_narrative(session, recent_messages)

        return response

    async def _generate_ending_narrative(
        self,
        session: GameSessionEntity,
        recent_messages: list[GameMessageEntity],
    ) -> GameEndingResponse:
        """엔딩 내러티브 생성."""
        messages_for_llm = [
            {"role": msg.role.value, "content": msg.content}
            for msg in recent_messages
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
        narrative = GameMasterService.extract_narrative_from_ending(llm_response.content)

        # Update session to completed
        completed_session = session.complete(ending_type)
        await self._session_repo.save(completed_session)

        # Save ending message
        ending_message = GameMessageEntity(
            id=uuid4(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=narrative,
            parsed_response={"ending_type": ending_type.value},
            token_count=llm_response.usage.total_tokens if llm_response.usage else None,
            created_at=datetime.utcnow(),
        )
        await self._message_repo.create(ending_message)

        return GameEndingResponse(
            session_id=session.id,
            ending_type=ending_type.value,
            narrative=narrative,
            total_turns=completed_session.turn_count,
            character_name="",  # TODO: Load from character
            scenario_name="",   # TODO: Load from scenario
        )

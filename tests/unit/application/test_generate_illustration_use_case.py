"""GenerateIllustrationUseCase 단위 테스트."""

from typing import Optional
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import (
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    ImageGenerationServiceInterface,
)
from app.game.application.use_cases.generate_illustration import (
    GenerateIllustrationInput,
    GenerateIllustrationUseCase,
)
from app.game.domain.entities import GameMessageEntity, GameSessionEntity
from app.game.domain.value_objects import MessageRole, SessionStatus


def _make_session(session_id: UUID, user_id: UUID) -> GameSessionEntity:
    return GameSessionEntity(
        id=session_id,
        user_id=user_id,
        character_id=get_uuid7(),
        scenario_id=get_uuid7(),
        current_location="숲 속",
        game_state={},
        status=SessionStatus.ACTIVE,
        turn_count=3,
        max_turns=30,
        ending_type=None,
        started_at=get_utc_datetime(),
        ended_at=None,
        last_activity_at=get_utc_datetime(),
    )


def _make_ai_message(
    message_id: UUID, session_id: UUID, image_url: Optional[str] = None
) -> GameMessageEntity:
    return GameMessageEntity(
        id=message_id,
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content="고블린이 당신을 향해 달려옵니다.",
        parsed_response=None,
        token_count=None,
        image_url=image_url,
        embedding=None,
        created_at=get_utc_datetime(),
    )


class TestGenerateIllustrationUseCase:
    """GenerateIllustrationUseCase 단위 테스트."""

    @pytest.fixture
    def mock_session_repo(self):
        return AsyncMock(spec=GameSessionRepositoryInterface)

    @pytest.fixture
    def mock_message_repo(self):
        return AsyncMock(spec=GameMessageRepositoryInterface)

    @pytest.fixture
    def mock_image_service(self):
        return AsyncMock(spec=ImageGenerationServiceInterface)

    @pytest.fixture
    def use_case(
        self, mock_session_repo, mock_message_repo, mock_image_service
    ):
        return GenerateIllustrationUseCase(
            session_repository=mock_session_repo,
            message_repository=mock_message_repo,
            image_service=mock_image_service,
        )

    @pytest.mark.asyncio
    async def test_generate_illustration_success(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
        mock_image_service,
    ):
        """정상 케이스: 메시지 조회 → 이미지 생성 → 메시지 저장 → URL 반환."""
        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()
        expected_url = "https://r2.example.com/images/test.png"

        session = _make_session(session_id, user_id)
        message = _make_ai_message(message_id, session_id)

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = message
        mock_image_service.generate_image.return_value = expected_url
        mock_message_repo.update_image_url.return_value = message.model_copy(
            update={"image_url": expected_url}
        )

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=message_id,
        )
        result = await use_case.execute(user_id, input_data)

        assert result.image_url == expected_url
        assert result.message_id == message_id
        mock_image_service.generate_image.assert_called_once()
        mock_message_repo.update_image_url.assert_called_once_with(
            message_id, expected_url
        )

    @pytest.mark.asyncio
    async def test_raises_if_session_not_found(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
    ):
        """세션이 없으면 NotFound 예외."""
        from app.common.exception import NotFound

        mock_session_repo.get_by_id.return_value = None

        input_data = GenerateIllustrationInput(
            session_id=get_uuid7(),
            message_id=get_uuid7(),
        )
        with pytest.raises(NotFound):
            await use_case.execute(get_uuid7(), input_data)

    @pytest.mark.asyncio
    async def test_raises_if_session_belongs_to_other_user(
        self,
        use_case,
        mock_session_repo,
    ):
        """다른 유저의 세션이면 Forbidden 예외."""
        from app.common.exception import Forbidden

        session_id = get_uuid7()
        session = _make_session(
            session_id, user_id=get_uuid7()
        )  # 다른 user_id
        mock_session_repo.get_by_id.return_value = session

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=get_uuid7(),
        )
        with pytest.raises(Forbidden):
            await use_case.execute(
                get_uuid7(), input_data
            )  # 다른 user_id로 요청

    @pytest.mark.asyncio
    async def test_raises_if_message_not_found(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
    ):
        """메시지가 없으면 NotFound 예외."""
        from app.common.exception import NotFound

        user_id = get_uuid7()
        session_id = get_uuid7()
        session = _make_session(session_id, user_id)

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = None

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=get_uuid7(),
        )
        with pytest.raises(NotFound):
            await use_case.execute(user_id, input_data)

    @pytest.mark.asyncio
    async def test_raises_if_message_not_ai_response(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
    ):
        """유저 메시지에는 일러스트 생성 불가 → BadRequest 예외."""
        from app.common.exception import BadRequest

        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()

        session = _make_session(session_id, user_id)
        user_message = GameMessageEntity(
            id=message_id,
            session_id=session_id,
            role=MessageRole.USER,  # USER 메시지
            content="앞으로 나아갑니다.",
            parsed_response=None,
            token_count=None,
            image_url=None,
            embedding=None,
            created_at=get_utc_datetime(),
        )

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = user_message

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=message_id,
        )
        with pytest.raises(BadRequest):
            await use_case.execute(user_id, input_data)

    @pytest.mark.asyncio
    async def test_returns_existing_url_if_already_generated(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
        mock_image_service,
    ):
        """이미 image_url이 있으면 이미지 재생성 없이 기존 URL 반환."""
        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()
        existing_url = "https://r2.example.com/images/existing.png"

        session = _make_session(session_id, user_id)
        message = _make_ai_message(
            message_id, session_id, image_url=existing_url
        )

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = message

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=message_id,
        )
        result = await use_case.execute(user_id, input_data)

        assert result.image_url == existing_url
        mock_image_service.generate_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_server_error_if_image_generation_fails(
        self,
        use_case,
        mock_session_repo,
        mock_message_repo,
        mock_image_service,
    ):
        """이미지 생성 실패 시 ServerError 예외."""
        from app.common.exception import ServerError

        user_id = get_uuid7()
        session_id = get_uuid7()
        message_id = get_uuid7()

        session = _make_session(session_id, user_id)
        message = _make_ai_message(message_id, session_id)

        mock_session_repo.get_by_id.return_value = session
        mock_message_repo.get_by_id.return_value = message
        mock_image_service.generate_image.return_value = (
            None  # 실패 시 None 반환
        )

        input_data = GenerateIllustrationInput(
            session_id=session_id,
            message_id=message_id,
        )
        with pytest.raises(ServerError):
            await use_case.execute(user_id, input_data)

"""GameMessageRepository 통합 테스트."""

import pytest
from sqlalchemy import select

from app.auth.infrastructure.persistence.models.user_models import User
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.infrastructure.persistence.models.game_models import (
    GameMessage,
    GameSession,
)
from app.game.infrastructure.repositories.game_message_repository import (
    GameMessageRepositoryImpl,
)


@pytest.mark.asyncio
async def test_update_image_url(db_session):
    """update_image_url 메서드가 실제로 DB에 저장하는지 확인."""
    # Given: User, Session, Message 생성
    user_id = get_uuid7()
    session_id = get_uuid7()
    message_id = get_uuid7()

    user = User(
        id=user_id,
        email="test@example.com",
        name="Test User",
        game_level=1,
        game_experience=0,
    )
    db_session.add(user)
    await db_session.flush()

    session = GameSession(
        id=session_id,
        user_id=user_id,
        character_id=get_uuid7(),
        scenario_id=get_uuid7(),
        current_location="Test Location",
        status="ACTIVE",
        turn_count=0,
        max_turns=30,
        started_at=get_utc_datetime(),
    )
    db_session.add(session)
    await db_session.flush()

    message = GameMessage(
        id=message_id,
        session_id=session_id,
        role="assistant",
        content="Test narrative",
        is_ai_response=True,
        image_url=None,  # 초기값 None
        created_at=get_utc_datetime(),
    )
    db_session.add(message)
    await db_session.flush()

    # When: update_image_url 호출
    repo = GameMessageRepositoryImpl(db_session)
    test_url = "https://example.com/test-image.png"
    await repo.update_image_url(message_id, test_url)
    await db_session.flush()

    # Then: DB에서 직접 조회하여 확인
    result = await db_session.execute(
        select(GameMessage).where(GameMessage.id == message_id)
    )
    updated_message = result.scalar_one()

    assert updated_message.image_url == test_url

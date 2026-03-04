from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain.value_objects import UserLevel
from app.auth.infrastructure.repositories.user_progression_repository import (
    UserProgressionRepositoryImpl,
)


@pytest.mark.asyncio
async def test_award_game_experience_uses_for_update_and_flushes_changes():
    now = datetime.now(UTC)
    user_id = uuid4()
    user_orm = SimpleNamespace(
        id=user_id,
        email="user@example.com",
        name="User",
        profile_image_url=None,
        user_level=UserLevel.NORMAL.value,
        is_active=True,
        email_verified=True,
        created_at=now,
        updated_at=now,
        last_login_at=now,
        game_level=1,
        game_experience=100,
        game_current_experience=100,
    )

    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(
        return_value=SimpleNamespace(scalar_one_or_none=lambda: user_orm)
    )
    db.flush = AsyncMock()

    repo = UserProgressionRepositoryImpl(db)

    result = await repo.award_game_experience(user_id=user_id, xp=120)

    statement = db.execute.await_args.args[0]
    assert "FOR UPDATE" in str(statement).upper()

    assert user_orm.game_level == 1
    assert user_orm.game_experience == 220
    assert user_orm.game_current_experience == 220
    db.flush.assert_awaited_once()

    assert result.game_level == 1
    assert result.game_experience == 220
    assert result.game_current_experience == 220
    assert result.leveled_up is False
    assert result.levels_gained == 0

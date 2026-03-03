"""Integration tests for GameSessionRepository.

Tests verify actual database interactions including constraints.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.auth.infrastructure.persistence.models.user_models import User
from app.common.utils.id_generator import get_uuid7
from app.game.domain.entities.game_session import (
    GameSessionEntity,
    SessionStatus,
)
from app.game.infrastructure.persistence.models.game_models import (
    Character,
    GameSession,
    Scenario,
)
from app.game.infrastructure.repositories.game_session_repository import (
    GameSessionRepositoryImpl,
)


@pytest.mark.asyncio
async def test_save_new_session_includes_user_id(db_session):
    """새 세션 저장 시 user_id가 포함되는지 검증 (regression test for NULL constraint).

    🔴 RED Phase: This test should FAIL initially because user_id is not assigned
    in GameSessionRepository.save() when creating new ORM instances.
    """
    # Given: Create test user, character, and scenario (to satisfy FK constraints)
    user_id = get_uuid7()
    character_id = get_uuid7()
    scenario_id = get_uuid7()
    session_id = get_uuid7()

    # Create User
    user = User(
        id=user_id,
        email=f"test_{user_id}@example.com",
        name="테스트 사용자",
        is_active=True,
    )
    db_session.add(user)

    # Create Character
    character = Character(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="테스트 캐릭터",
        description="테스트용 캐릭터",
        stats={"strength": 10, "intelligence": 10},
    )
    db_session.add(character)

    # Create Scenario
    scenario = Scenario(
        id=scenario_id,
        name="테스트 시나리오",
        description="테스트용 시나리오",
        initial_location="시작 위치",
        world_setting="테스트 세계관",
    )
    db_session.add(scenario)
    await db_session.flush()  # Ensure FK references exist

    # Create game session entity with user_id
    session_entity = GameSessionEntity(
        id=session_id,
        user_id=user_id,  # user_id 설정
        character_id=character_id,
        scenario_id=scenario_id,
        current_location="Test Location - 뒷골목 아지트",
        game_state={},
        status=SessionStatus.ACTIVE,
        turn_count=0,
        max_turns=30,
        ending_type=None,
        started_at=datetime.now(timezone.utc),
        ended_at=None,
        last_activity_at=datetime.now(timezone.utc),
    )

    repo = GameSessionRepositoryImpl(db_session)

    # When: Save the session
    saved_entity = await repo.save(session_entity)
    await db_session.flush()  # Force DB write to trigger constraints

    # Then: Verify user_id is persisted in database
    result = await db_session.execute(
        select(GameSession).where(GameSession.id == session_id)
    )
    orm = result.scalar_one()

    assert orm.user_id == user_id, "user_id should be saved to database"
    assert (
        orm.user_id is not None
    ), "user_id should satisfy NOT NULL constraint"
    assert (
        saved_entity.user_id == user_id
    ), "returned entity should have user_id"


@pytest.mark.asyncio
async def test_save_existing_session_preserves_user_id(db_session):
    """기존 세션 업데이트 시 user_id가 유지되는지 검증."""
    # Given: Create test fixtures
    user_id = get_uuid7()
    character_id = get_uuid7()
    scenario_id = get_uuid7()

    # Create User
    user = User(
        id=user_id,
        email=f"test_{user_id}@example.com",
        name="테스트 사용자",
        is_active=True,
    )
    db_session.add(user)

    # Create Character
    character = Character(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="테스트 캐릭터 2",
        description="테스트용 캐릭터",
        stats={"strength": 10, "intelligence": 10},
    )
    db_session.add(character)

    # Create Scenario
    scenario = Scenario(
        id=scenario_id,
        name="테스트 시나리오 2",
        description="테스트용 시나리오",
        initial_location="시작 위치",
        world_setting="테스트 세계관",
    )
    db_session.add(scenario)
    await db_session.flush()

    # Create and save initial session
    session_entity = GameSessionEntity(
        id=get_uuid7(),
        user_id=user_id,
        character_id=character_id,
        scenario_id=scenario_id,
        current_location="Initial Location",
        game_state={},
        status=SessionStatus.ACTIVE,
        turn_count=0,
        max_turns=30,
        ending_type=None,
        started_at=datetime.now(timezone.utc),
        ended_at=None,
        last_activity_at=datetime.now(timezone.utc),
    )

    repo = GameSessionRepositoryImpl(db_session)
    saved = await repo.save(session_entity)
    await db_session.flush()

    # When: Update the session (e.g., increment turn count)
    updated_entity = GameSessionEntity(
        id=saved.id,
        user_id=saved.user_id,
        character_id=saved.character_id,
        scenario_id=saved.scenario_id,
        current_location="Updated Location",
        game_state={"updated": True},
        status=SessionStatus.ACTIVE,
        turn_count=1,  # Incremented
        max_turns=30,
        ending_type=None,
        started_at=saved.started_at,
        ended_at=None,
        last_activity_at=datetime.now(timezone.utc),
    )

    updated = await repo.save(updated_entity)
    await db_session.flush()

    # Then: Verify user_id is preserved
    result = await db_session.execute(
        select(GameSession).where(GameSession.id == saved.id)
    )
    orm = result.scalar_one()

    assert orm.user_id == user_id, "user_id should be preserved during update"
    assert orm.turn_count == 1, "update should work correctly"
    assert (
        updated.user_id == user_id
    ), "returned entity should preserve user_id"

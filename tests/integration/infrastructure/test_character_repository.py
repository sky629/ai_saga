"""Integration tests for CharacterRepository - Experience System.

Tests verify that experience fields are correctly persisted and retrieved from the database.
"""

from datetime import datetime, timezone

import pytest

from app.auth.infrastructure.persistence.models.user_models import User
from app.common.utils.id_generator import get_uuid7
from app.game.domain.entities.character import (
    CharacterEntity,
    CharacterProfile,
    CharacterStats,
)
from app.game.infrastructure.persistence.models.game_models import Scenario
from app.game.infrastructure.repositories.character_repository import (
    CharacterRepositoryImpl,
)


@pytest.mark.asyncio
async def test_save_character_with_experience(db_session):
    """경험치 필드를 포함한 캐릭터 저장 및 조회 검증.

    🔴 RED Phase: ORM 모델의 기본값에 experience와 current_experience가 없으면 실패.
    """
    # Given: Create test user and scenario
    user_id = get_uuid7()
    scenario_id = get_uuid7()
    character_id = get_uuid7()

    user = User(
        id=user_id,
        email=f"test_{user_id}@example.com",
        name="테스트 사용자",
        is_active=True,
    )
    db_session.add(user)

    scenario = Scenario(
        id=scenario_id,
        name="테스트 시나리오",
        description="테스트용 시나리오",
        initial_location="시작 위치",
        world_setting="테스트 세계관",
        game_type="trpg",
    )
    db_session.add(scenario)
    await db_session.flush()

    # Create character entity with experience
    stats = CharacterStats(
        hp=100,
        max_hp=100,
        level=2,
        experience=150,
        current_experience=50,
    )

    character_entity = CharacterEntity(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="경험치 테스트 캐릭터",
        description="경험치 시스템 테스트용",
        stats=stats,
        inventory=["검", "포션"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    # When: Save character
    repo = CharacterRepositoryImpl(db_session)
    await repo.save(character_entity)
    await db_session.flush()

    # Then: Retrieve and verify experience fields
    retrieved = await repo.get_by_id(character_id)
    assert retrieved is not None
    assert retrieved.stats.level == 2
    assert retrieved.stats.experience == 150
    assert retrieved.stats.current_experience == 50
    assert retrieved.stats.hp == 100
    assert retrieved.stats.max_hp == 100


@pytest.mark.asyncio
async def test_update_character_experience_after_level_up(db_session):
    """레벨업 후 경험치 업데이트 검증."""
    # Given: Create and save character
    user_id = get_uuid7()
    scenario_id = get_uuid7()
    character_id = get_uuid7()

    user = User(
        id=user_id,
        email=f"test_{user_id}@example.com",
        name="테스트 사용자",
        is_active=True,
    )
    db_session.add(user)

    scenario = Scenario(
        id=scenario_id,
        name="테스트 시나리오",
        description="테스트용 시나리오",
        initial_location="시작 위치",
        world_setting="테스트 세계관",
        game_type="trpg",
    )
    db_session.add(scenario)
    await db_session.flush()

    character_entity = CharacterEntity(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="레벨업 테스트",
        description="레벨업 테스트용",
        stats=CharacterStats(
            hp=100,
            max_hp=100,
            level=1,
            experience=90,
            current_experience=90,
        ),
        inventory=[],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    repo = CharacterRepositoryImpl(db_session)
    await repo.save(character_entity)
    await db_session.flush()

    # When: Gain experience and level up
    updated_stats = character_entity.stats.gain_experience(
        50
    )  # 90 + 50 = 140 → Lv2
    updated_character = character_entity.update_stats(updated_stats)

    await repo.save(updated_character)
    await db_session.flush()

    # Then: Verify level up was persisted
    retrieved = await repo.get_by_id(character_id)
    assert retrieved is not None
    assert retrieved.stats.level == 2
    assert retrieved.stats.experience == 140
    assert retrieved.stats.current_experience == 40  # 140 - 100
    assert retrieved.stats.max_hp == 110  # 100 + 10
    assert retrieved.stats.hp == 110  # Full heal on level up


@pytest.mark.asyncio
async def test_save_character_with_profile(db_session):
    """캐릭터 프로필 JSON 저장 및 조회 검증."""
    user_id = get_uuid7()
    scenario_id = get_uuid7()
    character_id = get_uuid7()

    user = User(
        id=user_id,
        email=f"test_{user_id}@example.com",
        name="테스트 사용자",
        is_active=True,
    )
    db_session.add(user)

    scenario = Scenario(
        id=scenario_id,
        name="테스트 시나리오",
        description="테스트용 시나리오",
        initial_location="시작 위치",
        world_setting="테스트 세계관",
        game_type="trpg",
    )
    db_session.add(scenario)
    await db_session.flush()

    character_entity = CharacterEntity(
        id=character_id,
        user_id=user_id,
        scenario_id=scenario_id,
        name="프로필 테스트 캐릭터",
        profile=CharacterProfile(
            age=28,
            gender="여성",
            appearance="왼쪽 눈가에 흉터",
        ),
        stats=CharacterStats(hp=100, max_hp=100, level=1),
        inventory=[],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    repo = CharacterRepositoryImpl(db_session)
    await repo.save(character_entity)
    await db_session.flush()

    retrieved = await repo.get_by_id(character_id)
    assert retrieved is not None
    assert retrieved.profile.age == 28
    assert retrieved.profile.gender == "여성"
    assert retrieved.profile.appearance == "왼쪽 눈가에 흉터"

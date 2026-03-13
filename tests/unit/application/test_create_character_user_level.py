"""CreateCharacterUseCase — 유저 게임 레벨 및 온보딩 프로필 단위 테스트."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import (
    CharacterRepositoryInterface,
    GameSessionRepositoryInterface,
    ScenarioRepositoryInterface,
    UserProgressionInterface,
)
from app.game.application.use_cases.create_character import (
    CreateCharacterInput,
    CreateCharacterUseCase,
)
from app.game.domain.entities import (
    CharacterEntity,
    CharacterProfile,
    CharacterStats,
)
from app.game.domain.entities.scenario import ScenarioEntity
from app.game.domain.value_objects import ScenarioDifficulty


def _make_scenario(scenario_id: UUID) -> ScenarioEntity:
    return ScenarioEntity(
        id=scenario_id,
        name="테스트 시나리오",
        description="테스트용",
        world_setting="판타지 세계",
        initial_location="마을 입구",
        difficulty=ScenarioDifficulty.NORMAL,
        max_turns=10,
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_profile() -> CharacterProfile:
    return CharacterProfile(
        age=28,
        gender="남성",
        appearance="낡은 망토를 걸친 전사",
    )


def _make_saved_character(
    user_id: UUID,
    scenario_id: UUID,
    level: int,
    hp: int,
) -> CharacterEntity:
    return CharacterEntity(
        id=get_uuid7(),
        user_id=user_id,
        scenario_id=scenario_id,
        name="영웅",
        profile=_make_profile(),
        stats=CharacterStats(hp=hp, max_hp=hp, level=level),
        inventory=[],
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def user_id() -> UUID:
    return get_uuid7()


@pytest.fixture
def scenario_id() -> UUID:
    return get_uuid7()


@pytest.fixture
def mock_character_repo():
    return AsyncMock(spec=CharacterRepositoryInterface)


@pytest.fixture
def mock_session_repo():
    return AsyncMock(spec=GameSessionRepositoryInterface)


@pytest.fixture
def mock_scenario_repo():
    return AsyncMock(spec=ScenarioRepositoryInterface)


@pytest.fixture
def mock_user_progression():
    return AsyncMock(spec=UserProgressionInterface)


@pytest.fixture
def use_case(
    mock_character_repo,
    mock_session_repo,
    mock_scenario_repo,
    mock_user_progression,
):
    return CreateCharacterUseCase(
        character_repository=mock_character_repo,
        session_repository=mock_session_repo,
        scenario_repository=mock_scenario_repo,
        user_progression=mock_user_progression,
    )


class TestCreateCharacterUserLevel:

    @pytest.mark.asyncio
    async def test_character_inherits_user_level_1(
        self,
        use_case,
        mock_scenario_repo,
        mock_user_progression,
        mock_character_repo,
        user_id,
        scenario_id,
    ):
        mock_scenario_repo.get_by_id.return_value = _make_scenario(scenario_id)
        mock_user_progression.get_user_game_level.return_value = 1
        saved = _make_saved_character(user_id, scenario_id, level=1, hp=100)
        mock_character_repo.save.return_value = saved

        result = await use_case.execute(
            user_id,
            CreateCharacterInput(
                name="영웅",
                scenario_id=scenario_id,
                profile=_make_profile(),
            ),
        )

        assert result.stats.level == 1
        assert result.stats.hp == 100
        assert result.stats.max_hp == 100

        call_args = mock_character_repo.save.call_args[0][0]
        assert call_args.stats.level == 1
        assert call_args.stats.hp == 100

    @pytest.mark.asyncio
    async def test_character_inherits_user_level_3(
        self,
        use_case,
        mock_scenario_repo,
        mock_user_progression,
        mock_character_repo,
        user_id,
        scenario_id,
    ):
        mock_scenario_repo.get_by_id.return_value = _make_scenario(scenario_id)
        mock_user_progression.get_user_game_level.return_value = 3
        saved = _make_saved_character(user_id, scenario_id, level=3, hp=120)
        mock_character_repo.save.return_value = saved

        result = await use_case.execute(
            user_id,
            CreateCharacterInput(
                name="영웅",
                scenario_id=scenario_id,
                profile=_make_profile(),
            ),
        )

        assert result.stats.level == 3
        assert result.stats.hp == 120

        call_args = mock_character_repo.save.call_args[0][0]
        assert call_args.stats.level == 3
        assert call_args.stats.hp == 120
        assert call_args.stats.max_hp == 120

    @pytest.mark.asyncio
    async def test_character_inherits_user_level_5(
        self,
        use_case,
        mock_scenario_repo,
        mock_user_progression,
        mock_character_repo,
        user_id,
        scenario_id,
    ):
        mock_scenario_repo.get_by_id.return_value = _make_scenario(scenario_id)
        mock_user_progression.get_user_game_level.return_value = 5
        saved = _make_saved_character(user_id, scenario_id, level=5, hp=140)
        mock_character_repo.save.return_value = saved

        result = await use_case.execute(
            user_id,
            CreateCharacterInput(
                name="영웅",
                scenario_id=scenario_id,
                profile=_make_profile(),
            ),
        )

        assert result.stats.level == 5
        assert result.stats.hp == 140

        call_args = mock_character_repo.save.call_args[0][0]
        assert call_args.stats.level == 5
        assert call_args.stats.hp == 140

    @pytest.mark.asyncio
    async def test_user_progression_called_with_correct_user_id(
        self,
        use_case,
        mock_scenario_repo,
        mock_user_progression,
        mock_character_repo,
        user_id,
        scenario_id,
    ):
        mock_scenario_repo.get_by_id.return_value = _make_scenario(scenario_id)
        mock_user_progression.get_user_game_level.return_value = 1
        saved = _make_saved_character(user_id, scenario_id, level=1, hp=100)
        mock_character_repo.save.return_value = saved

        await use_case.execute(
            user_id,
            CreateCharacterInput(
                name="영웅",
                scenario_id=scenario_id,
                profile=_make_profile(),
            ),
        )

        mock_user_progression.get_user_game_level.assert_called_once_with(
            user_id
        )

    @pytest.mark.asyncio
    async def test_character_profile_is_saved_with_optional_goal(
        self,
        use_case,
        mock_scenario_repo,
        mock_user_progression,
        mock_character_repo,
        user_id,
        scenario_id,
    ):
        mock_scenario_repo.get_by_id.return_value = _make_scenario(scenario_id)
        mock_user_progression.get_user_game_level.return_value = 2
        saved = CharacterEntity(
            id=get_uuid7(),
            user_id=user_id,
            scenario_id=scenario_id,
            name="세리아",
            profile=CharacterProfile(
                age=24,
                gender="여성",
                appearance="정제된 귀족풍 복장",
                goal="가문 재건",
            ),
            stats=CharacterStats(hp=110, max_hp=110, level=2),
            inventory=[],
            is_active=True,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        mock_character_repo.save.return_value = saved

        result = await use_case.execute(
            user_id,
            CreateCharacterInput(
                name="세리아",
                scenario_id=scenario_id,
                profile=CharacterProfile(
                    age=24,
                    gender="여성",
                    appearance="정제된 귀족풍 복장",
                    goal="가문 재건",
                ),
            ),
        )

        assert result.profile.age == 24
        assert result.profile.gender == "여성"
        assert result.profile.goal == "가문 재건"

        call_args = mock_character_repo.save.call_args[0][0]
        assert call_args.profile.goal == "가문 재건"
        assert "외형: 정제된 귀족풍 복장." in call_args.prompt_profile

    @pytest.mark.asyncio
    async def test_character_prompt_profile_contains_required_fields_only(
        self,
        use_case,
        mock_scenario_repo,
        mock_user_progression,
        mock_character_repo,
        user_id,
        scenario_id,
    ):
        mock_scenario_repo.get_by_id.return_value = _make_scenario(scenario_id)
        mock_user_progression.get_user_game_level.return_value = 2
        saved = CharacterEntity(
            id=get_uuid7(),
            user_id=user_id,
            scenario_id=scenario_id,
            name="실비아",
            profile=CharacterProfile(
                age=27,
                gender="여성",
                appearance="검은 단발과 오래된 흉터",
            ),
            stats=CharacterStats(hp=110, max_hp=110, level=2),
            inventory=[],
            is_active=True,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        mock_character_repo.save.return_value = saved

        result = await use_case.execute(
            user_id,
            CreateCharacterInput(
                name="실비아",
                scenario_id=scenario_id,
                profile=CharacterProfile(
                    age=27,
                    gender="여성",
                    appearance="검은 단발과 오래된 흉터",
                ),
            ),
        )

        assert result.profile.appearance == "검은 단발과 오래된 흉터"

        call_args = mock_character_repo.save.call_args[0][0]
        assert "이름: 실비아." in call_args.prompt_profile
        assert "나이: 27세." in call_args.prompt_profile
        assert "성별: 여성." in call_args.prompt_profile

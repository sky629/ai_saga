"""GetScenariosQuery 신규 메타데이터 응답 단위 테스트."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import ScenarioRepositoryInterface
from app.game.application.queries.get_scenarios import GetScenariosQuery
from app.game.domain.entities import ScenarioEntity
from app.game.domain.value_objects import (
    GameType,
    ScenarioDifficulty,
    ScenarioGenre,
)


@pytest.mark.asyncio
async def test_get_scenarios_includes_discovery_metadata():
    scenario_repo = AsyncMock(spec=ScenarioRepositoryInterface)
    scenario_repo.get_all.return_value = [
        ScenarioEntity(
            id=get_uuid7(),
            name="네온 시티 추적전",
            description="사이버펑크 도시에서 벌어지는 추적극",
            world_setting="기업 지배 아래의 네온 도시",
            initial_location="슬럼가 입구",
            game_type=GameType.TRPG,
            genre=ScenarioGenre.SCI_FI,
            difficulty=ScenarioDifficulty.HARD,
            max_turns=24,
            is_active=True,
            tags=["사이버펑크", "추적", "도시"],
            thumbnail_url="https://example.com/thumbnail.png",
            hook="첫 단서는 죽은 줄 알았던 동료에게서 온다.",
            recommended_for="추적극과 잠입 플레이를 좋아하는 유저",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
    ]

    query = GetScenariosQuery(scenario_repo)

    result = await query.execute()

    assert result[0].tags == ["사이버펑크", "추적", "도시"]
    assert result[0].game_type == "trpg"
    assert result[0].thumbnail_url == "https://example.com/thumbnail.png"
    assert result[0].hook == "첫 단서는 죽은 줄 알았던 동료에게서 온다."
    assert result[0].recommended_for == "추적극과 잠입 플레이를 좋아하는 유저"

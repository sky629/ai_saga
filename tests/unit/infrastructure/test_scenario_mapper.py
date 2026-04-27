"""ScenarioMapper 단위 테스트."""

from datetime import datetime, timezone

from app.common.utils.id_generator import get_uuid7
from app.game.domain.value_objects import (
    GameType,
    ScenarioDifficulty,
    ScenarioGenre,
)
from app.game.infrastructure.persistence.mappers import ScenarioMapper
from app.game.infrastructure.persistence.models.game_models import Scenario


def test_scenario_mapper_accepts_wuxia_genre():
    """DB의 wuxia 장르 문자열을 도메인 enum으로 변환한다."""
    now = datetime.now(timezone.utc)
    scenario = Scenario(
        id=get_uuid7(),
        name="기연 일지",
        description="무협 성장형 시나리오",
        world_setting="절벽 아래 동굴에서 무공을 수련한다.",
        initial_location="절벽 아래",
        game_type=GameType.PROGRESSION.value,
        genre=ScenarioGenre.WUXIA.value,
        difficulty=ScenarioDifficulty.NORMAL.value,
        max_turns=12,
        tags=["무협", "수련", "기연"],
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    entity = ScenarioMapper.to_entity(scenario)

    assert entity.genre == ScenarioGenre.WUXIA

"""dev 시나리오 시드 품질 회귀 테스트."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.dev.routes import DEFAULT_SCENARIO_THUMBNAIL_URL, seed_scenarios


@pytest.mark.asyncio
async def test_seed_scenarios_creates_detailed_seed_content():
    db = AsyncMock()
    db.add = Mock()
    execute_result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db.execute.return_value = execute_result

    response = await seed_scenarios(db=db)

    assert response.scenarios_created == 3
    assert db.add.call_count == 3

    seeded_scenarios = [call.args[0] for call in db.add.call_args_list]
    for scenario in seeded_scenarios:
        assert len(scenario.description) >= 80
        assert len(scenario.world_setting) >= 300
        assert len(scenario.tags) >= 4
        assert scenario.hook is not None
        assert len(scenario.hook) >= 20
        assert scenario.recommended_for is not None
        assert len(scenario.recommended_for) >= 20
        assert scenario.thumbnail_url == DEFAULT_SCENARIO_THUMBNAIL_URL
        assert "\n" in scenario.world_setting

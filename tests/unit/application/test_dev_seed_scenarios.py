"""dev 라우트 품질 회귀 테스트."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.dev.routes import (
    DEFAULT_SCENARIO_THUMBNAIL_URL,
    DevGenerateImageRequest,
    generate_dev_image,
    seed_scenarios,
)
from config.settings import settings


@pytest.mark.asyncio
async def test_seed_scenarios_creates_detailed_seed_content():
    db = AsyncMock()
    db.add = Mock()
    execute_result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db.execute.return_value = execute_result

    response = await seed_scenarios(db=db)

    assert response.scenarios_created == 4
    assert db.add.call_count == 4

    seeded_scenarios = [call.args[0] for call in db.add.call_args_list]
    for scenario in seeded_scenarios:
        assert len(scenario.description) >= 80
        assert len(scenario.world_setting) >= 300
        assert len(scenario.tags) >= 4
        assert scenario.game_type in {"trpg", "progression"}
        assert scenario.hook is not None
        assert len(scenario.hook) >= 20
        assert scenario.recommended_for is not None
        assert len(scenario.recommended_for) >= 20
        assert scenario.thumbnail_url == DEFAULT_SCENARIO_THUMBNAIL_URL
        assert "\n" in scenario.world_setting

    assert any(
        scenario.game_type == "progression" and scenario.max_turns == 12
        for scenario in seeded_scenarios
    )


@pytest.mark.asyncio
async def test_generate_dev_image_uses_custom_prompt_and_defaults():
    original_env = settings.KANG_ENV
    settings.KANG_ENV = "local"
    try:
        with patch(
            "app.dev.routes.ImageGenerationServiceAdapter"
        ) as adapter_cls:
            adapter = AsyncMock()
            adapter.generate_image.return_value = (
                "https://cdn.example.com/test-image.png"
            )
            adapter_cls.return_value = adapter

            response = await generate_dev_image(
                request=DevGenerateImageRequest(prompt="test prompt")
            )
    finally:
        settings.KANG_ENV = original_env

    assert response.image_url == "https://cdn.example.com/test-image.png"
    assert response.prompt == "test prompt"
    adapter.generate_image.assert_called_once()
    called_kwargs = adapter.generate_image.call_args.kwargs
    assert called_kwargs["prompt"] == "test prompt"
    assert called_kwargs["session_id"]
    assert called_kwargs["user_id"]


@pytest.mark.asyncio
async def test_generate_dev_image_blocks_in_prod():
    original_env = settings.KANG_ENV
    settings.KANG_ENV = "prod"
    try:
        with pytest.raises(Exception) as exc_info:
            await generate_dev_image(
                request=DevGenerateImageRequest(prompt="test prompt")
            )
    finally:
        settings.KANG_ENV = original_env

    assert "disabled in production" in str(exc_info.value)

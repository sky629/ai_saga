"""IllustrationGenerationService 단위 테스트."""

from unittest.mock import AsyncMock

import pytest

from app.game.application.services.illustration_generation_service import (
    IllustrationGenerationService,
)
from app.game.application.services.illustration_prompt_builder import (
    IllustrationPromptBuilder,
    IllustrationPromptContext,
)
from app.game.application.services.illustration_scenario_profile_resolver import (
    IllustrationScenarioProfileResolver,
)
from app.game.application.services.illustration_scene_spec_builder import (
    IllustrationSceneSpecBuilder,
)


class TestIllustrationGenerationService:
    """공용 일러스트 생성 경로를 검증한다."""

    def test_build_scene_narrative_uses_parsed_narrative_when_available(self):
        narrative = IllustrationGenerationService.build_scene_narrative(
            raw_content='{"before_narrative":"대치한다","narrative":"검객이 추격자를 향해 돌진한다."}',
            parsed_response={
                "before_narrative": "대치한다",
                "narrative": "검객이 추격자를 향해 돌진한다.",
            },
        )

        assert narrative == "검객이 추격자를 향해 돌진한다."

    def test_build_context_extracts_state_changes_from_parsed_response(self):
        context = IllustrationGenerationService.build_context(
            narrative="당신은 소리를 따라 몸을 돌린다.",
            parsed_response={
                "narrative": "당신은 소리를 따라 몸을 돌린다.",
                "state_changes": {
                    "location": "서울역 지하 통로",
                    "discoveries": ["깨진 비상 방송 장치"],
                },
            },
            current_location="숲 속",
        )

        assert context.state_changes == {
            "location": "서울역 지하 통로",
            "discoveries": ["깨진 비상 방송 장치"],
        }

    @pytest.mark.asyncio
    async def test_generate_uses_shared_prompt_builder_and_image_service(self):
        image_service = AsyncMock()
        image_service.generate_image.return_value = "https://cdn/image.png"
        context = IllustrationPromptContext(
            scene_narrative="고블린이 성벽 위로 기어오른다.",
            character_name="실비아",
            character_description="- 외형: 검은 단발과 오래된 흉터.",
            current_location="북쪽 성벽",
            scenario_genre="fantasy",
            scenario_name="왕국의 몰락",
            scenario_world_setting="북쪽 왕국의 성벽과 유적이 이어진다.",
            state_changes={"discoveries": ["부서진 성문"]},
        )

        result = await IllustrationGenerationService.generate(
            image_service=image_service,
            context=context,
            session_id="session-1",
            user_id="user-1",
        )

        assert result == "https://cdn/image.png"
        image_service.generate_image.assert_called_once_with(
            prompt=IllustrationPromptBuilder.build(
                context=context,
                scene_spec=IllustrationSceneSpecBuilder.build(context),
                visual_profile=IllustrationScenarioProfileResolver.resolve(
                    context
                ),
            ),
            session_id="session-1",
            user_id="user-1",
        )

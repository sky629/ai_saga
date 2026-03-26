"""IllustrationGenerationService 단위 테스트."""

from unittest.mock import AsyncMock

import pytest

from app.game.application.services.illustration_generation_service import (
    IllustrationGenerationService,
)
from app.game.application.services.illustration_prompt_builder import (
    IllustrationPromptBuilder,
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

    @pytest.mark.asyncio
    async def test_generate_uses_shared_prompt_builder_and_image_service(self):
        image_service = AsyncMock()
        image_service.generate_image.return_value = "https://cdn/image.png"

        result = await IllustrationGenerationService.generate(
            image_service=image_service,
            narrative="고블린이 성벽 위로 기어오른다.",
            session_id="session-1",
            user_id="user-1",
            character_name="실비아",
            character_description="- 외형: 검은 단발과 오래된 흉터.",
            current_location="북쪽 성벽",
            scenario_genre="fantasy",
        )

        assert result == "https://cdn/image.png"
        image_service.generate_image.assert_called_once_with(
            prompt=IllustrationPromptBuilder.build(
                narrative="고블린이 성벽 위로 기어오른다.",
                character_name="실비아",
                character_description="- 외형: 검은 단발과 오래된 흉터.",
                current_location="북쪽 성벽",
                scenario_genre="fantasy",
            ),
            session_id="session-1",
            user_id="user-1",
        )

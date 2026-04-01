"""일러스트 생성 공용 서비스."""

from typing import Optional

from app.game.application.ports import ImageGenerationServiceInterface
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
from app.game.domain.services import GameMasterService


class IllustrationGenerationService:
    """서술 텍스트를 공용 규칙으로 일러스트 생성 호출에 연결한다."""

    @staticmethod
    def build_scene_narrative(
        raw_content: str,
        parsed_response: Optional[dict] = None,
    ) -> str:
        """구조화 응답이 있으면 순수 narrative만 추출한다."""
        if isinstance(parsed_response, dict):
            return GameMasterService.extract_narrative_from_parsed(
                parsed_response,
                fallback=raw_content,
            )
        return raw_content

    @staticmethod
    def build_context(
        narrative: str,
        parsed_response: Optional[dict] = None,
        character_name: str = "",
        character_description: str = "",
        current_location: str = "",
        scenario_game_type: str = "",
        scenario_genre: str = "",
        scenario_name: str = "",
        scenario_world_setting: str = "",
        scenario_tags: tuple[str, ...] = (),
        state_changes: Optional[dict] = None,
    ) -> IllustrationPromptContext:
        """이미지 생성용 컨텍스트를 조립한다."""
        extracted_state_changes = state_changes
        if extracted_state_changes is None and isinstance(
            parsed_response, dict
        ):
            candidate = parsed_response.get("state_changes")
            if isinstance(candidate, dict):
                extracted_state_changes = candidate
        return IllustrationPromptContext(
            scene_narrative=narrative,
            character_name=character_name,
            character_description=character_description,
            current_location=current_location,
            scenario_game_type=(
                getattr(scenario_game_type, "value", scenario_game_type)
            ),
            scenario_genre=getattr(scenario_genre, "value", scenario_genre),
            scenario_name=scenario_name,
            scenario_world_setting=scenario_world_setting,
            scenario_tags=tuple(
                str(tag) for tag in scenario_tags if isinstance(tag, str)
            ),
            state_changes=extracted_state_changes,
        )

    @staticmethod
    async def generate(
        image_service: ImageGenerationServiceInterface,
        context: IllustrationPromptContext,
        session_id: str,
        user_id: str,
    ) -> Optional[str]:
        """일관된 프롬프트로 이미지를 생성한다."""
        scene_spec = IllustrationSceneSpecBuilder.build(context)
        visual_profile = IllustrationScenarioProfileResolver.resolve(context)
        prompt = IllustrationPromptBuilder.build(
            context=context,
            scene_spec=scene_spec,
            visual_profile=visual_profile,
        )
        return await image_service.generate_image(
            prompt=prompt,
            session_id=session_id,
            user_id=user_id,
        )

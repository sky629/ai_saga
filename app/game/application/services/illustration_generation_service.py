"""일러스트 생성 공용 서비스."""

from typing import Optional

from app.game.application.ports import ImageGenerationServiceInterface
from app.game.application.services.illustration_prompt_builder import (
    IllustrationPromptBuilder,
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
    async def generate(
        image_service: ImageGenerationServiceInterface,
        narrative: str,
        session_id: str,
        user_id: str,
        character_name: str = "",
        character_description: str = "",
        current_location: str = "",
        scenario_genre: str = "",
    ) -> Optional[str]:
        """일관된 프롬프트로 이미지를 생성한다."""
        prompt = IllustrationPromptBuilder.build(
            narrative=narrative,
            character_name=character_name,
            character_description=character_description,
            current_location=current_location,
            scenario_genre=scenario_genre,
        )
        return await image_service.generate_image(
            prompt=prompt,
            session_id=session_id,
            user_id=user_id,
        )

"""GenerateIllustrationUseCase — 메시지 내러티브 기반 온디맨드 일러스트 생성."""

import logging
from uuid import UUID

from pydantic import BaseModel

from app.common.exception import BadRequest, Forbidden, NotFound, ServerError
from app.game.application.ports import (
    CacheServiceInterface,
    CharacterRepositoryInterface,
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    ImageGenerationServiceInterface,
    ScenarioRepositoryInterface,
)
from app.game.application.services import IllustrationGenerationService

logger = logging.getLogger(__name__)


class GenerateIllustrationInput(BaseModel):
    """일러스트 생성 유스케이스 입력."""

    model_config = {"frozen": True}

    session_id: UUID
    message_id: UUID


class GenerateIllustrationResult(BaseModel):
    """일러스트 생성 유스케이스 결과."""

    model_config = {"frozen": True}

    message_id: UUID
    image_url: str


class GenerateIllustrationUseCase:
    """플레이어 요청으로 특정 AI 메시지의 픽셀 아트 일러스트를 생성한다.

    이미 image_url이 있는 메시지는 재생성 없이 기존 URL을 반환한다.
    """

    def __init__(
        self,
        session_repository: GameSessionRepositoryInterface,
        message_repository: GameMessageRepositoryInterface,
        character_repository: CharacterRepositoryInterface,
        scenario_repository: ScenarioRepositoryInterface,
        cache_service: CacheServiceInterface,
        image_service: ImageGenerationServiceInterface,
    ):
        self._session_repo = session_repository
        self._message_repo = message_repository
        self._character_repo = character_repository
        self._scenario_repo = scenario_repository
        self._cache_service = cache_service
        self._image_service = image_service

    async def _cleanup_generated_image(
        self, image_url: str, cache_key: str
    ) -> None:
        """업로드된 이미지와 결과 캐시를 정리한다."""
        try:
            await self._image_service.delete_image(image_url)
        except Exception as exc:
            logger.warning(
                "Failed to delete orphan illustration %s: %s",
                image_url,
                exc,
            )

        try:
            await self._cache_service.delete(cache_key)
        except Exception as exc:
            logger.warning(
                "Failed to delete illustration cache %s: %s",
                cache_key,
                exc,
            )

    async def execute(
        self,
        user_id: UUID,
        input_data: GenerateIllustrationInput,
    ) -> GenerateIllustrationResult:
        session = await self._session_repo.get_by_id(input_data.session_id)
        if session is None:
            raise NotFound(message="세션을 찾을 수 없습니다.")

        if session.user_id != user_id:
            raise Forbidden(message="해당 세션에 접근할 권한이 없습니다.")

        message = await self._message_repo.get_by_id(input_data.message_id)
        if message is None:
            raise NotFound(message="메시지를 찾을 수 없습니다.")

        if message.session_id != session.id:
            raise BadRequest(
                message="해당 메시지는 요청한 세션에 속하지 않습니다."
            )

        if not message.is_ai_response:
            raise BadRequest(
                message="AI 응답 메시지에만 일러스트를 생성할 수 있습니다."
            )

        if message.image_url:
            return GenerateIllustrationResult(
                message_id=message.id,
                image_url=message.image_url,
            )

        cache_key = f"game:illustration:result:{message.id}"
        cached_image_url = await self._cache_service.get(cache_key)
        if cached_image_url:
            await self._message_repo.update_image_url(
                message.id, cached_image_url
            )
            return GenerateIllustrationResult(
                message_id=message.id,
                image_url=cached_image_url,
            )

        character = await self._character_repo.get_by_id(session.character_id)
        if character is None:
            raise NotFound(message="캐릭터를 찾을 수 없습니다.")
        scenario = await self._scenario_repo.get_by_id(session.scenario_id)
        if scenario is None:
            raise NotFound(message="시나리오를 찾을 수 없습니다.")

        scene_narrative = IllustrationGenerationService.build_scene_narrative(
            raw_content=message.content,
            parsed_response=message.parsed_response,
        )
        prompt_context = IllustrationGenerationService.build_context(
            narrative=scene_narrative,
            character_name=character.name,
            character_description=character.prompt_profile,
            current_location=session.current_location,
            scenario_genre=scenario.genre,
            scenario_name=scenario.name,
            scenario_world_setting=scenario.world_setting,
            scenario_tags=tuple(scenario.tags),
        )

        image_url = await IllustrationGenerationService.generate(
            image_service=self._image_service,
            context=prompt_context,
            session_id=str(session.id),
            user_id=str(session.user_id),
        )

        if image_url is None:
            raise ServerError(
                message="일러스트 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
            )

        try:
            await self._cache_service.set(
                cache_key,
                image_url,
                ttl_seconds=86400,
            )
        except Exception as exc:
            logger.warning(
                "Failed to cache illustration result for message %s: %s",
                message.id,
                exc,
            )

        try:
            await self._message_repo.update_image_url(message.id, image_url)
        except Exception:
            await self._cleanup_generated_image(image_url, cache_key)
            raise

        return GenerateIllustrationResult(
            message_id=message.id,
            image_url=image_url,
        )

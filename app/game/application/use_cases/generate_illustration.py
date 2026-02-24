"""GenerateIllustrationUseCase — 메시지 내러티브 기반 온디맨드 일러스트 생성."""

from uuid import UUID

from pydantic import BaseModel

from app.common.exception import BadRequest, Forbidden, NotFound, ServerError
from app.game.application.ports import (
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    ImageGenerationServiceInterface,
)
from config.settings import settings


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
        image_service: ImageGenerationServiceInterface,
    ):
        self._session_repo = session_repository
        self._message_repo = message_repository
        self._image_service = image_service

    async def execute(
        self,
        user_id: UUID,
        input_data: GenerateIllustrationInput,
    ) -> GenerateIllustrationResult:
        # 0. 기능 활성화 여부 확인 (설정값 기반)
        if not settings.image_generation_enabled:
            raise BadRequest(
                message="현재 일러스트 생성 기능이 비활성화되어 있습니다."
            )

        session = await self._session_repo.get_by_id(input_data.session_id)
        if session is None:
            raise NotFound(message="세션을 찾을 수 없습니다.")

        if session.user_id != user_id:
            raise Forbidden(message="해당 세션에 접근할 권한이 없습니다.")

        message = await self._message_repo.get_by_id(input_data.message_id)
        if message is None:
            raise NotFound(message="메시지를 찾을 수 없습니다.")

        if not message.is_ai_response:
            raise BadRequest(
                message="AI 응답 메시지에만 일러스트를 생성할 수 있습니다."
            )

        if message.image_url:
            return GenerateIllustrationResult(
                message_id=message.id,
                image_url=message.image_url,
            )

        # Pollinations.ai URL 길이 제한으로 인해 고정 프롬프트만 사용
        # TODO: 유료 Imagen 전환 시 내러티브 기반 프롬프트로 복구 가능
        illustration_prompt = (
            "Pixel art fantasy RPG game scene, 16-bit retro style, "
            "detailed pixel art, vibrant colors, adventure atmosphere"
        )

        image_url = await self._image_service.generate_image(
            prompt=illustration_prompt,
            session_id=str(session.id),
            user_id=str(session.user_id),
        )

        if image_url is None:
            raise ServerError(
                message="일러스트 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
            )

        await self._message_repo.update_image_url(message.id, image_url)

        return GenerateIllustrationResult(
            message_id=message.id,
            image_url=image_url,
        )

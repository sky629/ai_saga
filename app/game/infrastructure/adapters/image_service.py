"""Image Generation Service Adapter.

Imagen 3 API를 사용하여 이미지를 생성하고 Cloudflare R2에 업로드합니다.
"""

import io
import logging
from typing import Optional
from uuid import uuid4

import boto3
from botocore.config import Config
from google import genai
from google.genai import types

from app.game.application.ports import ImageGenerationServiceInterface
from config.settings import settings

logger = logging.getLogger("uvicorn")


class ImageGenerationServiceAdapter(ImageGenerationServiceInterface):
    """이미지 생성 서비스 어댑터.

    Imagen 3 API로 이미지 생성 후 R2에 업로드합니다.
    """

    def __init__(self):
        # Gemini/Imagen 클라이언트
        self._genai_client = genai.Client(api_key=settings.gemini_api_key)
        self._image_model = settings.image_model

        # R2 클라이언트 (S3 호환)
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            config=Config(signature_version="s3v4"),
        )
        self._bucket = settings.r2_bucket_name
        self._public_url = settings.r2_public_url

    async def generate_image(
        self,
        prompt: str,
        session_id: str,
        user_id: str,
    ) -> Optional[str]:
        """이미지 생성 후 R2에 업로드, URL 반환."""
        try:
            # 1. 모델 타입에 따라 API 호출 분기
            if "gemini" in self._image_model.lower():
                # Gemini 멀티모달 생성 (generate_content)
                response = (
                    await self._genai_client.aio.models.generate_content(
                        model=self._image_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"],
                        ),
                    )
                )

                if (
                    not response.candidates
                    or not response.candidates[0].content.parts
                ):
                    logger.warning("Gemini API returned no content")
                    return None

                # 이미지 데이터 추출 (inline_data)
                image_data = None
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image_data = part.inline_data.data
                        break

                if not image_data:
                    logger.warning("Gemini API response has no image data")
                    return None

            else:
                # Imagen 이미지 생성 (generate_images)
                response = await self._genai_client.aio.models.generate_images(
                    model=self._image_model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/png",
                    ),
                )

                if not response.generated_images:
                    logger.warning("Imagen API returned no images")
                    return None

                # 이미지 데이터 추출
                image_data = response.generated_images[0].image.image_bytes

            if not image_data:
                logger.warning("Generated image has no bytes")
                return None

            # 2. R2에 업로드
            file_name = f"{uuid4()}.png"
            object_key = f"{session_id}/{user_id}/{file_name}"

            self._s3_client.upload_fileobj(
                io.BytesIO(image_data),
                self._bucket,
                object_key,
                ExtraArgs={"ContentType": "image/png"},
            )

            # 3. 공개 URL 반환
            if self._public_url:
                return f"{self._public_url}/{object_key}"
            else:
                return (
                    f"{settings.r2_endpoint_url}/{self._bucket}/{object_key}"
                )

        except Exception as e:
            # 이미지 생성 실패 시 게임 진행에 방해되지 않도록 None 반환
            # 재시도 로직 없음 (사용자 요구사항)
            logger.error(f"Image generation failed: {e}")
            return None

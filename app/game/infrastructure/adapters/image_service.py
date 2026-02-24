"""Image Generation Service Adapter.

Imagen 3 API를 사용하여 이미지를 생성하고 Cloudflare R2에 업로드합니다.
"""

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
            # 테스트용
            return await self._generate_dummy_image(prompt)

            # 1. 이미지 데이터 생성
            image_data = await self._generate_google_imagen(prompt)

            # 이미지 데이터 검증
            if not image_data:
                logger.error("Image generation returned no data")
                return None

            # 2. R2에 업로드
            file_name = f"{uuid4()}.png"
            object_key = f"{session_id}/{user_id}/{file_name}"

            self._s3_client.put_object(
                Bucket=self._bucket,
                Key=object_key,
                Body=image_data,
                ContentType="image/png",
                ACL="public-read",
            )

            # 3. 공개 URL 반환
            if self._public_url:
                public_base = self._public_url.rstrip("/")
                return f"{public_base}/{object_key}"
            else:
                # public_url이 없으면 endpoint_url로 대체 시도 (주의: 브라우저 접근 불가할 수 있음)
                logger.warning(
                    f"R2_PUBLIC_URL not set. Falling back to endpoint: {settings.r2_endpoint_url}"
                )
                return (
                    f"{settings.r2_endpoint_url}/{self._bucket}/{object_key}"
                )
        except Exception as e:
            # 이미지 생성 실패 시 게임 진행에 방해되지 않도록 None 반환
            logger.error(f"Image generation failed: {e}")
            return None

    async def _generate_dummy_image(self, prompt: str) -> Optional[str]:
        """dummy 이미지 반환.
        TODO: 유료 결제 계정 등록 후 원래의 Imagen 3 로직으로 복구해야 함.
        """
        return "https://pub-3c25697921ae4f12aac4c4cfdbb57cc4.r2.dev/dummy.png"

    async def _generate_google_imagen(self, prompt: str) -> Optional[bytes]:
        """Google Imagen/Gemini API를 사용한 이미지 생성 (유료 계정용)."""
        try:
            if "gemini" in self._image_model.lower():
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
                    return None
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        return part.inline_data.data
            else:
                response = await self._genai_client.aio.models.generate_images(
                    model=self._image_model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/png",
                    ),
                )
                if response.generated_images:
                    return response.generated_images[0].image.image_bytes
            return None
        except Exception as e:
            logger.error(f"Google Imagen API failed: {e}")
            return None

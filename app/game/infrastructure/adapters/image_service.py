"""Image Generation Service Adapter.

Imagen 3 API를 사용하여 이미지를 생성하고 S3 호환 스토리지에 업로드합니다.
"""

import logging
from typing import Optional
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from google import genai
from google.genai import types

from app.common.utils.id_generator import get_uuid7
from app.game.application.ports import ImageGenerationServiceInterface
from app.game.application.services.illustration_layout_constraints import (
    GLOBAL_IMAGE_LAYOUT_PROMPT,
    GLOBAL_IMAGE_STYLE_PROMPT,
)
from config.settings import settings

logger = logging.getLogger("uvicorn")
DEFAULT_IMAGE_ASPECT_RATIO = "3:4"


class ImageGenerationServiceAdapter(ImageGenerationServiceInterface):
    """이미지 생성 서비스 어댑터.

    Imagen 3 API로 이미지 생성 후 S3 호환 스토리지에 업로드합니다.
    """

    def __init__(self):
        # Gemini/Imagen 클라이언트
        self._genai_client = genai.Client(api_key=settings.gemini_api_key)
        self._image_model = settings.image_model

        client_kwargs = {
            "service_name": "s3",
            "config": Config(signature_version="s3v4"),
        }
        if settings.object_storage_endpoint_url:
            client_kwargs["endpoint_url"] = (
                settings.object_storage_endpoint_url
            )
        if settings.object_storage_access_key_id:
            client_kwargs["aws_access_key_id"] = (
                settings.object_storage_access_key_id
            )
        if settings.object_storage_secret_access_key:
            client_kwargs["aws_secret_access_key"] = (
                settings.object_storage_secret_access_key
            )
        if settings.object_storage_region:
            client_kwargs["region_name"] = settings.object_storage_region

        self._s3_client = boto3.client(**client_kwargs)
        self._bucket = settings.object_storage_bucket_name
        self._public_url = settings.object_storage_public_url

    async def generate_image(
        self,
        prompt: str,
        session_id: str,
        user_id: str,
    ) -> Optional[str]:
        """이미지 생성 후 R2에 업로드, URL 반환."""
        try:
            if not settings.image_generation_enabled:
                return await self._generate_dummy_image(prompt)

            # 1. 이미지 데이터 생성
            image_data = await self._generate_google_imagen(
                self._apply_global_style(prompt)
            )

            # 이미지 데이터 검증
            if not image_data:
                logger.error("Image generation returned no data")
                return None

            # 2. Object storage에 업로드
            file_name = f"{get_uuid7()}.png"
            object_key = f"{user_id}/{session_id}/{file_name}"

            put_object_kwargs = {
                "Bucket": self._bucket,
                "Key": object_key,
                "Body": image_data,
                "ContentType": "image/png",
            }
            if settings.object_storage_public_read_acl:
                put_object_kwargs["ACL"] = "public-read"

            self._s3_client.put_object(**put_object_kwargs)

            # 3. 공개 URL 반환
            if self._public_url:
                public_base = self._public_url.rstrip("/")
                return f"{public_base}/{object_key}"

            fallback_url = self._build_fallback_object_url(object_key)
            if fallback_url:
                logger.warning(
                    "OBJECT_STORAGE_PUBLIC_URL not set. Falling back to derived object url."
                )
                return fallback_url
            logger.warning("공개 이미지 URL을 계산할 수 없습니다.")
            return None
        except Exception as e:
            # 이미지 생성 실패 시 게임 진행에 방해되지 않도록 None 반환
            logger.error(f"Image generation failed: {e}")
            return None

    @staticmethod
    def _apply_global_style(prompt: str) -> str:
        """모든 이미지 생성 프롬프트에 공통 스타일 힌트를 추가한다."""
        normalized_prompt = prompt.lower()
        prefix_parts: list[str] = []

        if GLOBAL_IMAGE_STYLE_PROMPT.lower() not in normalized_prompt:
            prefix_parts.append(GLOBAL_IMAGE_STYLE_PROMPT)

        if GLOBAL_IMAGE_LAYOUT_PROMPT.lower() not in normalized_prompt:
            prefix_parts.append(GLOBAL_IMAGE_LAYOUT_PROMPT)

        if not prefix_parts:
            return prompt

        return f"{', '.join(prefix_parts)}, {prompt}"

    async def delete_image(self, image_url: str) -> None:
        """업로드된 이미지를 삭제한다."""
        object_key = self._extract_object_key(image_url)
        if object_key is None:
            logger.warning(
                "Skipping image deletion for unmanaged url: %s", image_url
            )
            return

        self._s3_client.delete_object(
            Bucket=self._bucket,
            Key=object_key,
        )

    async def _generate_dummy_image(self, prompt: str) -> Optional[str]:
        """dummy 이미지 반환.
        TODO: 유료 결제 계정 등록 후 원래의 Imagen 3 로직으로 복구해야 함.
        """
        del prompt
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
                            image_config=types.ImageConfig(
                                aspect_ratio=DEFAULT_IMAGE_ASPECT_RATIO,
                            ),
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
                        aspect_ratio=DEFAULT_IMAGE_ASPECT_RATIO,
                        output_mime_type="image/png",
                    ),
                )
                if response.generated_images:
                    return response.generated_images[0].image.image_bytes
            return None
        except Exception as e:
            logger.error(f"Google Imagen API failed: {e}")
            return None

    def _extract_object_key(self, image_url: str) -> Optional[str]:
        """공개 URL에서 object key를 역으로 추출한다."""
        public_base = self._public_url.rstrip("/")
        if public_base and image_url.startswith(f"{public_base}/"):
            return image_url.removeprefix(f"{public_base}/")

        endpoint_base = settings.object_storage_endpoint_url.rstrip("/")
        endpoint_prefix = f"{endpoint_base}/{self._bucket}/"
        if endpoint_base and image_url.startswith(endpoint_prefix):
            return image_url.removeprefix(endpoint_prefix)

        parsed = urlparse(image_url)
        if not parsed.scheme or not parsed.netloc:
            return None
        s3_virtual_host = self._build_s3_virtual_host()
        if s3_virtual_host and parsed.netloc == s3_virtual_host:
            return parsed.path.lstrip("/") or None
        return None

    def _build_fallback_object_url(self, object_key: str) -> Optional[str]:
        endpoint_base = settings.object_storage_endpoint_url.rstrip("/")
        if endpoint_base:
            return f"{endpoint_base}/{self._bucket}/{object_key}"

        s3_virtual_host = self._build_s3_virtual_host()
        if s3_virtual_host:
            return f"https://{s3_virtual_host}/{object_key}"

        return None

    def _build_s3_virtual_host(self) -> Optional[str]:
        region = settings.object_storage_region.strip()
        if not region:
            return None
        return f"{self._bucket}.s3.{region}.amazonaws.com"

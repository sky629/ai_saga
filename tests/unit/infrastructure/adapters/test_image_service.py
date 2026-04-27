"""ImageGenerationServiceAdapter 단위 테스트."""

from unittest.mock import AsyncMock, patch

import pytest

from app.game.infrastructure.adapters.image_service import (
    DEFAULT_IMAGE_ASPECT_RATIO,
    GLOBAL_IMAGE_LAYOUT_PROMPT,
    GLOBAL_IMAGE_STYLE_PROMPT,
    ImageGenerationServiceAdapter,
)
from config.settings import settings


@pytest.mark.asyncio
async def test_returns_dummy_image_when_generation_disabled(monkeypatch):
    """IMAGE_GENERATION_ENABLED가 false면 더미 이미지를 반환한다."""
    monkeypatch.setattr(settings, "image_generation_enabled", False)

    with (
        patch(
            "app.game.infrastructure.adapters.image_service.boto3.client"
        ) as mock_boto_client,
        patch("app.game.infrastructure.adapters.image_service.genai.Client"),
    ):
        adapter = ImageGenerationServiceAdapter()
        adapter._generate_google_imagen = AsyncMock(return_value=b"real-image")

        image_url = await adapter.generate_image(
            prompt="pixel art hero",
            session_id="session-1",
            user_id="user-1",
        )

    assert image_url == (
        "https://pub-3c25697921ae4f12aac4c4cfdbb57cc4.r2.dev/dummy.png"
    )
    adapter._generate_google_imagen.assert_not_called()
    mock_boto_client.return_value.put_object.assert_not_called()


@pytest.mark.asyncio
async def test_generates_real_image_when_generation_enabled_in_local(
    monkeypatch,
):
    """로컬 환경이어도 활성화되면 실제 이미지 생성 경로를 사용한다."""
    monkeypatch.setattr(settings, "KANG_ENV", "local")
    monkeypatch.setattr(settings, "image_generation_enabled", True)
    monkeypatch.setattr(
        settings,
        "object_storage_public_url",
        "https://cdn.example.com",
    )

    with (
        patch(
            "app.game.infrastructure.adapters.image_service.boto3.client"
        ) as mock_boto_client,
        patch("app.game.infrastructure.adapters.image_service.genai.Client"),
    ):
        adapter = ImageGenerationServiceAdapter()
        adapter._generate_google_imagen = AsyncMock(return_value=b"png-bytes")

        image_url = await adapter.generate_image(
            prompt="pixel art hero",
            session_id="session-1",
            user_id="user-1",
        )

    assert image_url is not None
    assert image_url.startswith("https://cdn.example.com/user-1/session-1/")
    adapter._generate_google_imagen.assert_called_once_with(
        f"{GLOBAL_IMAGE_STYLE_PROMPT}, {GLOBAL_IMAGE_LAYOUT_PROMPT}, pixel art hero"
    )
    mock_boto_client.return_value.put_object.assert_called_once()
    put_kwargs = mock_boto_client.return_value.put_object.call_args.kwargs
    assert "ACL" not in put_kwargs


@pytest.mark.asyncio
async def test_generate_images_uses_portrait_aspect_ratio(
    monkeypatch,
):
    monkeypatch.setattr(
        settings, "image_model", "imagen-4.0-fast-generate-001"
    )

    class _GeneratedImage:
        class _ImagePayload:
            image_bytes = b"png-bytes"

        image = _ImagePayload()

    class _GenerateImagesResponse:
        generated_images = [_GeneratedImage()]

    with (
        patch(
            "app.game.infrastructure.adapters.image_service.boto3.client"
        ) as mock_boto_client,
        patch("app.game.infrastructure.adapters.image_service.genai.Client"),
    ):
        adapter = ImageGenerationServiceAdapter()
        adapter._genai_client.aio.models.generate_images = AsyncMock(
            return_value=_GenerateImagesResponse()
        )

        image_url = await adapter.generate_image(
            prompt="farm scene",
            session_id="session-1",
            user_id="user-1",
        )

    assert image_url is not None
    generate_kwargs = (
        adapter._genai_client.aio.models.generate_images.call_args.kwargs
    )
    config = generate_kwargs["config"]
    assert config.aspect_ratio == DEFAULT_IMAGE_ASPECT_RATIO
    mock_boto_client.return_value.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_generate_content_uses_portrait_aspect_ratio(monkeypatch):
    monkeypatch.setattr(
        settings, "image_model", "gemini-3.1-flash-image-preview"
    )

    class _InlineData:
        data = b"png-bytes"

    class _Part:
        inline_data = _InlineData()

    class _Content:
        parts = [_Part()]

    class _Candidate:
        content = _Content()

    class _GenerateContentResponse:
        candidates = [_Candidate()]

    with (
        patch(
            "app.game.infrastructure.adapters.image_service.boto3.client"
        ) as mock_boto_client,
        patch("app.game.infrastructure.adapters.image_service.genai.Client"),
    ):
        adapter = ImageGenerationServiceAdapter()
        adapter._genai_client.aio.models.generate_content = AsyncMock(
            return_value=_GenerateContentResponse()
        )

        image_url = await adapter.generate_image(
            prompt="wuxia cave scene",
            session_id="session-1",
            user_id="user-1",
        )

    assert image_url is not None
    generate_kwargs = (
        adapter._genai_client.aio.models.generate_content.call_args.kwargs
    )
    config = generate_kwargs["config"]
    assert config.image_config.aspect_ratio == DEFAULT_IMAGE_ASPECT_RATIO
    mock_boto_client.return_value.put_object.assert_called_once()


def test_apply_global_style_adds_global_constraints_once():
    """전역 스타일/레이아웃 힌트는 한 번만 붙어야 한다."""
    prompt = ImageGenerationServiceAdapter._apply_global_style("hero portrait")
    assert prompt == (
        f"{GLOBAL_IMAGE_STYLE_PROMPT}, "
        f"{GLOBAL_IMAGE_LAYOUT_PROMPT}, hero portrait"
    )

    duplicated = ImageGenerationServiceAdapter._apply_global_style(
        f"{GLOBAL_IMAGE_STYLE_PROMPT}, "
        f"{GLOBAL_IMAGE_LAYOUT_PROMPT}, hero portrait"
    )
    assert duplicated == (
        f"{GLOBAL_IMAGE_STYLE_PROMPT}, "
        f"{GLOBAL_IMAGE_LAYOUT_PROMPT}, hero portrait"
    )


def test_apply_global_style_adds_layout_when_only_partial_constraint_exists():
    """일부 금지어가 있어도 전체 단일 컷 제약을 생략하면 안 된다."""
    prompt = ImageGenerationServiceAdapter._apply_global_style(
        "no speech bubbles, hero portrait"
    )

    assert GLOBAL_IMAGE_LAYOUT_PROMPT in prompt
    assert "no split-screen" in prompt
    assert "no sequential panels" in prompt


def test_uses_generic_object_storage_settings_for_boto_client(monkeypatch):
    """범용 object storage 설정으로 boto3 client를 구성해야 한다."""
    monkeypatch.setattr(
        settings,
        "object_storage_endpoint_url",
        "https://s3.ap-northeast-2.amazonaws.com",
    )
    monkeypatch.setattr(
        settings,
        "object_storage_access_key_id",
        "access-key",
    )
    monkeypatch.setattr(
        settings,
        "object_storage_secret_access_key",
        "secret-key",
    )
    monkeypatch.setattr(
        settings,
        "object_storage_region",
        "ap-northeast-2",
    )

    with (
        patch(
            "app.game.infrastructure.adapters.image_service.boto3.client"
        ) as mock_boto_client,
        patch("app.game.infrastructure.adapters.image_service.genai.Client"),
    ):
        ImageGenerationServiceAdapter()

    mock_boto_client.assert_called_once()
    client_kwargs = mock_boto_client.call_args.kwargs
    assert (
        client_kwargs["endpoint_url"]
        == "https://s3.ap-northeast-2.amazonaws.com"
    )
    assert client_kwargs["aws_access_key_id"] == "access-key"
    assert client_kwargs["aws_secret_access_key"] == "secret-key"
    assert client_kwargs["region_name"] == "ap-northeast-2"


@pytest.mark.asyncio
async def test_delete_image_removes_object_by_public_url(monkeypatch):
    monkeypatch.setattr(
        settings,
        "object_storage_public_url",
        "https://cdn.example.com",
    )

    with (
        patch(
            "app.game.infrastructure.adapters.image_service.boto3.client"
        ) as mock_boto_client,
        patch("app.game.infrastructure.adapters.image_service.genai.Client"),
    ):
        adapter = ImageGenerationServiceAdapter()

        await adapter.delete_image(
            "https://cdn.example.com/user-1/session-1/file.png"
        )

    mock_boto_client.return_value.delete_object.assert_called_once_with(
        Bucket=settings.object_storage_bucket_name,
        Key="user-1/session-1/file.png",
    )

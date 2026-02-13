"""Unit tests for EmbeddingCacheService.

TDD: Test-First Approach
테스트 케이스:
1. ✅ cache_hit_returns_cached_embedding - 캐시 히트 시 API 호출 안 함
2. ✅ cache_miss_generates_and_caches - 캐시 미스 시 생성 및 저장
3. ✅ same_text_returns_same_embedding - 동일 텍스트는 동일 hash
4. ✅ different_text_different_hash - 다른 텍스트는 다른 hash
5. ✅ cache_failure_falls_back_to_generation - 캐시 실패 시 정상 동작
6. ✅ empty_text_raises_value_error - 빈 텍스트 검증
7. ✅ cache_ttl_is_24_hours - TTL 설정 확인
"""

import json
from unittest.mock import AsyncMock

import pytest

from app.game.application.ports import CacheServiceInterface
from app.game.application.services.embedding_cache_service import (
    EmbeddingCacheService,
)
from app.llm.embedding_service_interface import EmbeddingServiceInterface


@pytest.fixture
def mock_embedding_service() -> AsyncMock:
    """Mock Embedding Service."""
    service = AsyncMock(spec=EmbeddingServiceInterface)
    # Default: 768차원 벡터 반환
    service.generate_embedding.return_value = [0.1] * 768
    return service


@pytest.fixture
def mock_cache_service() -> AsyncMock:
    """Mock Cache Service."""
    service = AsyncMock(spec=CacheServiceInterface)
    service.get.return_value = None  # Default: cache miss
    service.set.return_value = None
    return service


@pytest.fixture
def cache_service(
    mock_embedding_service: AsyncMock, mock_cache_service: AsyncMock
) -> EmbeddingCacheService:
    """EmbeddingCacheService instance with mocked dependencies."""
    return EmbeddingCacheService(
        embedding_service=mock_embedding_service,
        cache_service=mock_cache_service,
    )


class TestEmbeddingCacheService:
    """EmbeddingCacheService 단위 테스트."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_embedding(
        self,
        cache_service: EmbeddingCacheService,
        mock_cache_service: AsyncMock,
        mock_embedding_service: AsyncMock,
    ):
        """캐시 히트 시 저장된 embedding 반환, API 호출 안 함."""
        # Arrange
        text = "동쪽으로 이동"
        cached_embedding = [0.5] * 768
        mock_cache_service.get.return_value = json.dumps(cached_embedding)

        # Act
        result = await cache_service.generate_embedding(text)

        # Assert
        assert result == cached_embedding
        mock_cache_service.get.assert_called_once()
        mock_embedding_service.generate_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_generates_and_caches(
        self,
        cache_service: EmbeddingCacheService,
        mock_cache_service: AsyncMock,
        mock_embedding_service: AsyncMock,
    ):
        """캐시 미스 시 embedding 생성하고 캐시에 저장."""
        # Arrange
        text = "검으로 공격"
        generated_embedding = [0.3] * 768
        mock_cache_service.get.return_value = None  # Cache miss
        mock_embedding_service.generate_embedding.return_value = (
            generated_embedding
        )

        # Act
        result = await cache_service.generate_embedding(text)

        # Assert
        assert result == generated_embedding
        mock_cache_service.get.assert_called_once()
        mock_embedding_service.generate_embedding.assert_called_once_with(text)
        mock_cache_service.set.assert_called_once()

        # Verify cache key and TTL
        call_args = mock_cache_service.set.call_args
        cache_key = call_args[0][0]
        ttl = call_args[1]["ttl_seconds"]
        assert cache_key.startswith("embedding:hash:")
        assert ttl == 86400  # 24 hours

    @pytest.mark.asyncio
    async def test_same_text_returns_same_embedding(
        self,
        cache_service: EmbeddingCacheService,
        mock_cache_service: AsyncMock,
        mock_embedding_service: AsyncMock,
    ):
        """동일한 텍스트는 동일한 hash를 생성하여 캐시 재사용."""
        # Arrange
        text = "동쪽으로 이동"
        embedding = [0.2] * 768
        mock_embedding_service.generate_embedding.return_value = embedding

        # Act
        result1 = await cache_service.generate_embedding(text)
        # 두 번째 호출 - 캐시된 값 반환하도록 설정
        mock_cache_service.get.return_value = json.dumps(embedding)
        result2 = await cache_service.generate_embedding(text)

        # Assert
        assert result1 == result2
        # 첫 호출은 API 호출, 두 번째는 캐시에서 가져옴
        assert mock_embedding_service.generate_embedding.call_count == 1

    @pytest.mark.asyncio
    async def test_different_text_different_hash(
        self,
        cache_service: EmbeddingCacheService,
        mock_cache_service: AsyncMock,
        mock_embedding_service: AsyncMock,
    ):
        """다른 텍스트는 다른 hash를 생성하여 각각 캐싱."""
        # Arrange
        text1 = "동쪽으로 이동"
        text2 = "서쪽으로 이동"

        # Act
        await cache_service.generate_embedding(text1)
        await cache_service.generate_embedding(text2)

        # Assert
        assert mock_cache_service.set.call_count == 2
        call1_key = mock_cache_service.set.call_args_list[0][0][0]
        call2_key = mock_cache_service.set.call_args_list[1][0][0]
        assert call1_key != call2_key  # 다른 hash

    @pytest.mark.asyncio
    async def test_cache_failure_falls_back_to_generation(
        self,
        cache_service: EmbeddingCacheService,
        mock_cache_service: AsyncMock,
        mock_embedding_service: AsyncMock,
    ):
        """캐시 조회 실패 시에도 embedding 정상 생성."""
        # Arrange
        text = "마법 사용"
        embedding = [0.7] * 768
        mock_cache_service.get.side_effect = Exception(
            "Redis connection failed"
        )
        mock_embedding_service.generate_embedding.return_value = embedding

        # Act
        result = await cache_service.generate_embedding(text)

        # Assert
        assert result == embedding
        mock_embedding_service.generate_embedding.assert_called_once_with(text)

    @pytest.mark.asyncio
    async def test_empty_text_raises_value_error(
        self, cache_service: EmbeddingCacheService
    ):
        """빈 텍스트는 ValueError 발생."""
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot generate embedding"):
            await cache_service.generate_embedding("")

        with pytest.raises(ValueError, match="Cannot generate embedding"):
            await cache_service.generate_embedding("   ")  # whitespace only

    @pytest.mark.asyncio
    async def test_cache_ttl_is_24_hours(
        self,
        cache_service: EmbeddingCacheService,
        mock_cache_service: AsyncMock,
        mock_embedding_service: AsyncMock,
    ):
        """캐시 TTL이 24시간(86400초)인지 확인."""
        # Arrange
        text = "아이템 획득"
        mock_embedding_service.generate_embedding.return_value = [0.6] * 768

        # Act
        await cache_service.generate_embedding(text)

        # Assert
        mock_cache_service.set.assert_called_once()
        call_args = mock_cache_service.set.call_args
        ttl = call_args[1]["ttl_seconds"]
        assert ttl == 86400  # 24 hours

    @pytest.mark.asyncio
    async def test_cache_store_failure_does_not_break_flow(
        self,
        cache_service: EmbeddingCacheService,
        mock_cache_service: AsyncMock,
        mock_embedding_service: AsyncMock,
    ):
        """캐시 저장 실패 시에도 embedding은 정상 반환."""
        # Arrange
        text = "전투 시작"
        embedding = [0.9] * 768
        mock_cache_service.set.side_effect = Exception("Redis write failed")
        mock_embedding_service.generate_embedding.return_value = embedding

        # Act
        result = await cache_service.generate_embedding(text)

        # Assert
        assert result == embedding
        mock_embedding_service.generate_embedding.assert_called_once()

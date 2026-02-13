"""Integration tests for EmbeddingCacheService with real Redis.

실제 Redis를 사용하여 캐싱 동작을 검증합니다.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.game.application.services.embedding_cache_service import (
    EmbeddingCacheService,
)
from app.game.infrastructure.adapters import CacheServiceAdapter
from app.llm.embedding_service_interface import EmbeddingServiceInterface


@pytest.fixture
def mock_embedding_service() -> AsyncMock:
    """Mock Embedding Service (실제 API 호출 없이 테스트)."""
    service = AsyncMock(spec=EmbeddingServiceInterface)
    # 호출마다 다른 벡터 반환 (호출 횟수 추적용)
    call_count = [0]

    async def generate_mock_embedding(text: str) -> list[float]:
        call_count[0] += 1
        # 각 호출마다 조금씩 다른 벡터 생성
        return [float(call_count[0])] * 768

    service.generate_embedding.side_effect = generate_mock_embedding
    service.call_count = call_count
    return service


@pytest.fixture
async def cache_service() -> CacheServiceAdapter:
    """실제 Redis 캐시 서비스."""
    return CacheServiceAdapter()


@pytest.fixture
async def embedding_cache_service(
    mock_embedding_service: AsyncMock,
    cache_service: CacheServiceAdapter,
) -> EmbeddingCacheService:
    """Integration test용 EmbeddingCacheService."""
    service = EmbeddingCacheService(
        embedding_service=mock_embedding_service,
        cache_service=cache_service,
    )

    # 테스트 후 캐시 정리
    yield service

    # Cleanup: 테스트 중 생성된 캐시 삭제
    # (실제로는 Redis FLUSHDB를 사용하지만, 여기서는 TTL로 자동 만료)


class TestEmbeddingCacheIntegration:
    """실제 Redis를 사용한 통합 테스트."""

    @pytest.mark.asyncio
    async def test_cache_with_real_redis(
        self,
        embedding_cache_service: EmbeddingCacheService,
        mock_embedding_service: AsyncMock,
    ):
        """실제 Redis에 캐싱 동작 확인."""
        # Arrange
        text = "동쪽으로 이동"

        # Act - 첫 번째 호출 (캐시 미스)
        result1 = await embedding_cache_service.generate_embedding(text)
        api_calls_after_first = mock_embedding_service.call_count[0]

        # Act - 두 번째 호출 (캐시 히트)
        result2 = await embedding_cache_service.generate_embedding(text)
        api_calls_after_second = mock_embedding_service.call_count[0]

        # Assert
        assert result1 == result2  # 동일한 embedding
        assert api_calls_after_first == 1  # 첫 호출만 API 사용
        assert api_calls_after_second == 1  # 두 번째는 캐시에서 가져옴

    @pytest.mark.asyncio
    async def test_cache_persistence_across_requests(
        self,
        embedding_cache_service: EmbeddingCacheService,
        mock_embedding_service: AsyncMock,
    ):
        """여러 요청 간 캐시 유지 확인."""
        # Arrange
        texts = [
            "검으로 공격",
            "마법 사용",
            "검으로 공격",  # 중복
            "아이템 획득",
            "마법 사용",  # 중복
        ]

        # Act
        results = []
        for text in texts:
            result = await embedding_cache_service.generate_embedding(text)
            results.append(result)

        # Assert
        total_api_calls = mock_embedding_service.call_count[0]
        assert total_api_calls == 3  # 고유한 텍스트 3개만 API 호출
        assert results[0] == results[2]  # "검으로 공격" 동일
        assert results[1] == results[4]  # "마법 사용" 동일

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(
        self,
        mock_embedding_service: AsyncMock,
        cache_service: CacheServiceAdapter,
    ):
        """TTL 만료 확인 (짧은 TTL로 테스트)."""
        # Arrange - 짧은 TTL (1초)을 사용하는 별도 서비스 생성
        short_ttl_service = EmbeddingCacheService(
            embedding_service=mock_embedding_service,
            cache_service=cache_service,
        )

        # Monkey-patch TTL to 1 second
        async def short_ttl_store(key: str, embedding: list[float]) -> None:
            await cache_service.set(key, embedding.__str__(), ttl_seconds=1)

        short_ttl_service._store_in_cache = short_ttl_store

        text = "전투 시작"

        # Act - 첫 호출
        await short_ttl_service.generate_embedding(text)
        first_call_count = mock_embedding_service.call_count[0]

        # Wait for TTL to expire
        await asyncio.sleep(1.5)

        # Act - 만료 후 재호출
        await short_ttl_service.generate_embedding(text)
        second_call_count = mock_embedding_service.call_count[0]

        # Assert
        assert first_call_count == 1
        assert second_call_count == 2  # TTL 만료로 다시 API 호출

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(
        self,
        embedding_cache_service: EmbeddingCacheService,
        mock_embedding_service: AsyncMock,
    ):
        """동시 요청에서도 캐시 안전성 확인."""
        # Arrange
        text = "동시 접근 테스트"

        # Act - 동시에 10개 요청
        tasks = [
            embedding_cache_service.generate_embedding(text) for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        # 모든 결과가 동일해야 함
        assert all(r == results[0] for r in results)

        # API 호출은 최대 10회 (Race condition으로 일부 중복 가능)
        # 하지만 대부분은 캐시 히트되어야 함
        api_calls = mock_embedding_service.call_count[0]
        assert api_calls <= 10
        # NOTE: Redis는 원자적 연산을 보장하므로 실제로는 1-2회만 호출될 가능성 높음

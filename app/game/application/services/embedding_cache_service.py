"""Embedding Cache Service with Content Hash strategy.

동일한 텍스트는 캐싱해서 재사용하여 API 비용 절감.
Content Hash 기반으로 중복 API 호출을 방지합니다.

Expected Cost Savings:
- 목표: 30-50% API 호출 절감
- 중복률: 반복 액션("동쪽으로 이동", "검으로 공격") 기준
"""

import hashlib
import json
import logging
from typing import Optional

from app.game.application.ports import CacheServiceInterface
from app.llm.embedding_service_interface import EmbeddingServiceInterface

logger = logging.getLogger(__name__)


class EmbeddingCacheService:
    """Content Hash 기반 Embedding 캐싱 서비스.

    동일한 텍스트에 대해서는 embedding을 캐싱하여 재사용.
    캐시 미스 시에만 실제 embedding 생성.

    Features:
    - SHA-256 해시 기반 캐싱 (충돌 가능성 거의 없음)
    - 24시간 TTL (embedding은 변하지 않으므로 장기 보관)
    - Fallback 보장 (캐시 실패 시 정상 동작)
    """

    def __init__(
        self,
        embedding_service: EmbeddingServiceInterface,
        cache_service: CacheServiceInterface,
    ):
        self._embedding = embedding_service
        self._cache = cache_service

    async def generate_embedding(self, text: str) -> list[float]:
        """텍스트의 embedding 생성 (캐싱 포함).

        Args:
            text: Embedding을 생성할 텍스트

        Returns:
            768차원 embedding 벡터

        Raises:
            ValueError: 빈 텍스트
            Exception: Gemini API 호출 실패 (캐시 실패는 무시)
        """
        # 1. Validate input
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        # 2. Compute content hash
        text_hash = self._compute_hash(text)
        cache_key = f"embedding:hash:{text_hash}"

        # 3. Try cache
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            logger.info(f"[Embedding Cache] HIT - Hash: {text_hash[:8]}...")
            return cached

        # 4. Cache miss - generate new embedding
        logger.info(f"[Embedding Cache] MISS - Hash: {text_hash[:8]}...")
        embedding = await self._embedding.generate_embedding(text)

        # 5. Store in cache (fire and forget)
        await self._store_in_cache(cache_key, embedding)

        return embedding

    @staticmethod
    def _compute_hash(text: str) -> str:
        """텍스트의 SHA-256 hash 계산.

        Args:
            text: 해싱할 텍스트

        Returns:
            64자 16진수 해시값
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def _get_from_cache(self, key: str) -> Optional[list[float]]:
        """캐시에서 embedding 조회.

        Args:
            key: 캐시 키

        Returns:
            저장된 embedding 벡터, 없으면 None
        """
        try:
            cached_data = await self._cache.get(key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            # 캐시 실패는 무시 (정상 동작 보장)
            logger.warning(f"Cache get failed: {e}")
        return None

    async def _store_in_cache(self, key: str, embedding: list[float]) -> None:
        """캐시에 embedding 저장.

        Args:
            key: 캐시 키
            embedding: 저장할 embedding 벡터
        """
        try:
            await self._cache.set(
                key,
                json.dumps(embedding),
                ttl_seconds=86400,  # 24시간
            )
        except Exception as e:
            # 캐시 저장 실패는 무시 (정상 동작 보장)
            logger.warning(f"Cache set failed: {e}")

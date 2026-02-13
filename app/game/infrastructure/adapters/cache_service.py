"""Cache Service Adapter.

Redis를 Port 인터페이스에 맞춰 래핑합니다.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from app.common.storage.redis import pools
from app.game.application.ports import CacheServiceInterface

logger = logging.getLogger(__name__)


class CacheServiceAdapter(CacheServiceInterface):
    """캐시 서비스 어댑터.

    Redis를 Port 인터페이스에 맞춰 래핑합니다.
    멱등성 키 저장 등에 사용됩니다.
    """

    async def get(self, key: str) -> Optional[str]:
        """캐시 조회."""
        redis = await pools.get_connection()
        return await redis.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int = 600) -> None:
        """캐시 저장."""
        redis = await pools.get_connection()
        await redis.set(key, value, ex=ttl_seconds)

    @asynccontextmanager
    async def lock(self, key: str, ttl_ms: int = 1000):
        """분산 락 with auto-extension (heartbeat).

        Lock이 만료되기 전에 자동으로 TTL을 갱신하여
        긴 작업도 안전하게 보호합니다.

        Args:
            key: Lock key
            ttl_ms: Initial lock TTL in milliseconds

        Yields:
            None (lock context)
        """
        redis = await pools.get_connection()
        lock_key = f"lock:{key}"
        timeout_seconds = ttl_ms / 1000.0

        # Lock 획득
        lock_obj = redis.lock(
            lock_key, timeout=timeout_seconds, blocking_timeout=5.0
        )
        await lock_obj.acquire()

        logger.debug(f"[Lock] Acquired: {lock_key} (TTL: {timeout_seconds}s)")

        # Background task: Lock TTL 자동 갱신
        # 갱신 주기: TTL의 1/3 (예: 20초 TTL → 6.67초마다 갱신)
        extend_interval = timeout_seconds / 3.0
        extend_amount = timeout_seconds  # 갱신 시 추가할 시간

        extend_task = asyncio.create_task(
            self._extend_lock_periodically(
                lock_obj, extend_interval, extend_amount, lock_key
            )
        )

        try:
            yield
        finally:
            # Background task 종료
            extend_task.cancel()
            try:
                await extend_task
            except asyncio.CancelledError:
                logger.debug(f"[Lock] Extend task cancelled: {lock_key}")

            # Lock 해제
            try:
                await lock_obj.release()
                logger.debug(f"[Lock] Released: {lock_key}")
            except Exception as e:
                # Lock이 이미 만료되었거나 다른 이유로 해제 실패
                # 에러를 로깅하지만 예외는 발생시키지 않음
                logger.warning(f"[Lock] Failed to release: {lock_key} - {e}")

    async def _extend_lock_periodically(
        self, lock: Any, interval: float, extend_amount: float, lock_key: str
    ) -> None:
        """주기적으로 lock TTL 연장 (heartbeat).

        Args:
            lock: Redis lock object
            interval: 갱신 주기 (초)
            extend_amount: 갱신 시 추가할 시간 (초)
            lock_key: Lock key (로깅용)
        """
        extend_count = 0
        while True:
            await asyncio.sleep(interval)
            try:
                # Lock TTL 연장
                await lock.extend(extend_amount)
                extend_count += 1
                logger.debug(
                    f"[Lock] Extended: {lock_key} "
                    f"(+{extend_amount}s, count: {extend_count})"
                )
            except Exception as e:
                # Lock이 이미 해제되었거나 소유권이 없음
                logger.warning(f"[Lock] Failed to extend: {lock_key} - {e}")
                break  # 갱신 실패 시 loop 종료

    async def delete(self, key: str) -> None:
        """캐시 삭제."""
        redis = await pools.get_connection()
        await redis.delete(key)

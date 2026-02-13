"""Unit tests for CacheService lock extension.

Redis Lock 갱신(auto-extension) 기능을 검증합니다.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.game.infrastructure.adapters.cache_service import CacheServiceAdapter


class TestCacheServiceLockExtension:
    """Lock 갱신 기능 단위 테스트."""

    @pytest.mark.asyncio
    async def test_lock_is_extended_during_long_operation(self):
        """긴 작업 중 lock이 주기적으로 갱신됨.

        시나리오:
        - 9초 TTL lock 획득
        - 10초 작업 실행
        - 갱신 주기: 9초 / 3 = 3초
        - 10초 동안 약 3회 갱신 (3초, 6초, 9초)
        """
        # Arrange
        cache_service = CacheServiceAdapter()
        lock_mock = MagicMock()
        lock_mock.acquire = AsyncMock()
        lock_mock.extend = AsyncMock()  # 갱신 메서드
        lock_mock.release = AsyncMock()
        lock_mock.__aenter__ = AsyncMock(return_value=lock_mock)
        lock_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.common.storage.redis.pools.get_connection"
        ) as mock_conn:
            redis_mock = AsyncMock()
            redis_mock.lock = MagicMock(return_value=lock_mock)
            mock_conn.return_value = redis_mock

            # Act - 10초 작업 (3초마다 갱신되어야 함)
            async with cache_service.lock("test-key", ttl_ms=9000):  # 9초 TTL
                await asyncio.sleep(10)  # 10초 작업

            # Assert
            # 갱신 주기 = 9초 / 3 = 3초
            # 10초 동안 약 3회 갱신 (3초, 6초, 9초)
            assert (
                lock_mock.extend.call_count >= 3
            ), f"Expected at least 3 extend calls, got {lock_mock.extend.call_count}"
            lock_mock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_lock_released_even_if_extension_fails(self):
        """Lock 갱신 실패 시에도 정상 해제됨.

        시나리오:
        - Lock 획득 성공
        - 갱신 시도 시 예외 발생 (lock 만료 등)
        - 작업 완료 후 lock 해제는 정상 수행
        """
        # Arrange
        cache_service = CacheServiceAdapter()
        lock_mock = MagicMock()
        lock_mock.acquire = AsyncMock()
        lock_mock.extend = AsyncMock(side_effect=Exception("Extension failed"))
        lock_mock.release = AsyncMock()
        lock_mock.__aenter__ = AsyncMock(return_value=lock_mock)
        lock_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.common.storage.redis.pools.get_connection"
        ) as mock_conn:
            redis_mock = AsyncMock()
            redis_mock.lock = MagicMock(return_value=lock_mock)
            mock_conn.return_value = redis_mock

            # Act
            async with cache_service.lock("test-key", ttl_ms=6000):
                await asyncio.sleep(2)  # 짧은 작업

            # Assert
            lock_mock.release.assert_called_once()  # 해제됨

    @pytest.mark.asyncio
    async def test_lock_context_manager_cancellation_cleanup(self):
        """Lock context manager가 취소되어도 cleanup됨.

        시나리오:
        - Lock 획득 후 긴 작업 시작
        - 작업 중 asyncio task 취소
        - Lock은 정상 해제되어야 함
        """
        # Arrange
        cache_service = CacheServiceAdapter()
        lock_mock = MagicMock()
        lock_mock.acquire = AsyncMock()
        lock_mock.extend = AsyncMock()
        lock_mock.release = AsyncMock()
        lock_mock.__aenter__ = AsyncMock(return_value=lock_mock)
        lock_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.common.storage.redis.pools.get_connection"
        ) as mock_conn:
            redis_mock = AsyncMock()
            redis_mock.lock = MagicMock(return_value=lock_mock)
            mock_conn.return_value = redis_mock

            # Act - Lock context 강제 종료
            async def cancel_during_lock():
                async with cache_service.lock("test-key", ttl_ms=9000):
                    await asyncio.sleep(100)  # 긴 작업 (취소될 예정)

            task = asyncio.create_task(cancel_during_lock())
            await asyncio.sleep(0.5)  # Lock 획득 대기
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # Assert
            await asyncio.sleep(0.1)  # Cleanup 대기
            lock_mock.release.assert_called()  # 취소되어도 해제됨

    @pytest.mark.asyncio
    async def test_lock_extension_stops_when_context_exits(self):
        """Lock context 종료 시 갱신 background task도 종료됨.

        시나리오:
        - Lock 획득 후 짧은 작업 (3초)
        - Context 종료
        - Background task가 정리되어야 함 (더 이상 갱신 안 함)
        """
        # Arrange
        cache_service = CacheServiceAdapter()
        lock_mock = MagicMock()
        lock_mock.acquire = AsyncMock()
        lock_mock.extend = AsyncMock()
        lock_mock.release = AsyncMock()
        lock_mock.__aenter__ = AsyncMock(return_value=lock_mock)
        lock_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.common.storage.redis.pools.get_connection"
        ) as mock_conn:
            redis_mock = AsyncMock()
            redis_mock.lock = MagicMock(return_value=lock_mock)
            mock_conn.return_value = redis_mock

            # Act
            async with cache_service.lock("test-key", ttl_ms=9000):  # 9초 TTL
                await asyncio.sleep(3)  # 3초 작업

            # 갱신 호출 횟수 기록
            extend_count_during_lock = lock_mock.extend.call_count

            # Context 종료 후 추가 대기
            await asyncio.sleep(5)  # 5초 추가 대기

            # Assert
            # Context 종료 후에는 갱신이 더 이상 호출되지 않아야 함
            assert lock_mock.extend.call_count == extend_count_during_lock, (
                f"Extension should stop after context exit. "
                f"During lock: {extend_count_during_lock}, "
                f"After exit: {lock_mock.extend.call_count}"
            )

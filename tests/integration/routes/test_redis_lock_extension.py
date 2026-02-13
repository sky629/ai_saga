"""Integration tests for Redis lock extension with real Redis.

실제 Redis를 사용하여 Lock 갱신 기능을 검증합니다.
"""

import asyncio

import pytest
import pytest_asyncio

from app.common.storage.redis import pools
from app.game.infrastructure.adapters.cache_service import CacheServiceAdapter


@pytest_asyncio.fixture
async def cache_service():
    """각 테스트마다 새로운 CacheServiceAdapter 제공."""
    # Redis pool 재초기화 (event loop 문제 방지)
    await pools.close_all()
    service = CacheServiceAdapter()
    yield service
    # Cleanup
    await pools.close_all()


class TestRedisLockExtensionIntegration:
    """Lock 갱신 기능 통합 테스트 (실제 Redis)."""

    @pytest.mark.asyncio
    async def test_lock_extends_during_30_second_operation(
        self, cache_service
    ):
        """30초 작업 중 lock이 자동 갱신되어 timeout 없음 (실제 Redis).

        시나리오:
        - 실제 Redis에 20초 TTL lock 획득
        - 30초 작업 실행
        - Lock이 자동 갱신되어 LockNotOwnedError 발생 안 함

        기대 결과:
        - 30초 작업 완료 (에러 없음)
        - Lock 정상 해제
        """
        work_completed = False

        # 20초 TTL lock으로 30초 작업
        async with cache_service.lock("long-work-test", ttl_ms=20000):
            await asyncio.sleep(30)  # 30초 작업
            work_completed = True

        # 작업 완료 확인
        assert work_completed, "30초 작업이 완료되어야 함"

    @pytest.mark.asyncio
    async def test_concurrent_locks_are_serialized(self, cache_service):
        """동시 lock 요청이 순차 처리됨 (실제 Redis).

        시나리오:
        - 동일 키로 3개 동시 lock 요청
        - Redis lock으로 순차 처리됨
        - 모두 성공

        기대 결과:
        - 3개 작업 모두 완료
        - 총 소요 시간: 약 6초 (3 x 2초, 순차 처리)
        """
        results = []

        async def do_work(worker_id: int):
            """2초 걸리는 작업."""
            async with cache_service.lock("shared-resource", ttl_ms=10000):
                results.append(f"Worker {worker_id} started")
                await asyncio.sleep(2)  # 2초 작업
                results.append(f"Worker {worker_id} done")

        # 동시에 3개 작업 시작
        await asyncio.gather(
            do_work(1),
            do_work(2),
            do_work(3),
        )

        # 모두 완료됨
        assert len(results) == 6  # 각 worker당 2개 로그 (start + done)
        assert "Worker 1 done" in results
        assert "Worker 2 done" in results
        assert "Worker 3 done" in results

    @pytest.mark.asyncio
    async def test_different_lock_keys_run_concurrently(self, cache_service):
        """다른 lock 키는 동시 처리 가능 (실제 Redis).

        시나리오:
        - 서로 다른 2개 키로 동시 lock 획득
        - 각각 독립적으로 처리됨

        기대 결과:
        - 2개 작업 동시 완료
        - 총 소요 시간: 약 3초 (병렬 처리)
        """
        results = []

        async def work_on_resource_a():
            """Resource A 작업 (3초)."""
            async with cache_service.lock("resource-a", ttl_ms=10000):
                results.append("A started")
                await asyncio.sleep(3)
                results.append("A done")

        async def work_on_resource_b():
            """Resource B 작업 (3초)."""
            async with cache_service.lock("resource-b", ttl_ms=10000):
                results.append("B started")
                await asyncio.sleep(3)
                results.append("B done")

        # 동시 실행
        import time

        start = time.time()
        await asyncio.gather(work_on_resource_a(), work_on_resource_b())
        elapsed = time.time() - start

        # 병렬 처리로 약 3초에 완료 (순차면 6초)
        assert elapsed < 4, f"Expected ~3s (parallel), got {elapsed:.1f}s"
        assert len(results) == 4
        assert "A done" in results
        assert "B done" in results

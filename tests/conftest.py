"""Test configuration and fixtures.

Note: App-related fixtures (app, client, async_client) require environment
variables to be set. Unit tests for isolated modules like LLM can run without them.
"""

import os

import pytest

# 테스트 시 로컬 의존성 주소를 우선 사용한다.
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["TEST_POSTGRES_HOST"] = "localhost"
os.environ["REDIS_URL"] = "redis://localhost:6379"


@pytest.fixture
def app():
    """Create FastAPI application for testing.

    Requires environment variables to be set.
    Skip this fixture for unit tests that don't need the full app.
    """
    # Lazy import to avoid loading settings at module level
    from app.common.logging import CONSOLE_LOGGING_CONFIG
    from app.main import create_app

    return create_app(CONSOLE_LOGGING_CONFIG)


@pytest.fixture
def client(app):
    """Create test client."""
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create async test client."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture(autouse=True)
async def reset_connection_pools():
    """테스트 간 Redis/Postgres 커넥션 풀 공유를 방지한다."""
    import redis.asyncio as redis

    redis_client = redis.from_url("redis://localhost:6379", db=1)
    await redis_client.flushdb()
    await redis_client.aclose()

    yield

    from app.common.storage.postgres import postgres_storage
    from app.common.storage import redis as redis_storage
    from app.common.storage.redis import pools

    try:
        await pools.close_all()
    except RuntimeError:
        redis_storage._POOLS = {}

    try:
        await postgres_storage.close_all_pools()
    except RuntimeError:
        pass

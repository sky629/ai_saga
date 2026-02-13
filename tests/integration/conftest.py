"""Integration test configuration and fixtures."""

import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth.infrastructure.persistence.models.user_models import (  # noqa: F401
    SocialAccount,
    User,
)
from app.common.storage.postgres import Base

# Import all ORM models so they're registered with Base.metadata
from app.game.infrastructure.persistence.models.game_models import (  # noqa: F401
    Character,
    GameMessage,
    GameSession,
    Scenario,
)
from config.settings import settings


# === Redis 설정 (로컬 테스트용) ===
@pytest.fixture(scope="session", autouse=True)
def setup_test_redis():
    """테스트 환경에서 Redis를 localhost로 설정."""
    # Docker Compose 'redis' 서비스명을 localhost로 변경
    original_redis_url = os.environ.get("REDIS_URL")
    os.environ["REDIS_URL"] = "redis://localhost:6379"

    yield

    # 원래 값 복원
    if original_redis_url:
        os.environ["REDIS_URL"] = original_redis_url
    else:
        del os.environ["REDIS_URL"]


@pytest_asyncio.fixture
async def db_session():
    """Create a new database session for each test with auto-cleanup."""
    # Use test database URL (not production database!)
    database_url = settings.test_postgres_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

    # Create engine
    engine = create_async_engine(
        database_url,
        echo=False,  # Disable SQL logging in tests
    )

    # Enable pgvector extension and create tables
    async with engine.begin() as conn:
        # Enable pgvector extension first
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Provide session
    async with session_factory() as session:
        yield session
        # Transaction will be rolled back automatically

    # Cleanup
    await engine.dispose()


@pytest.fixture
def gemini_api_key():
    """Provide Gemini API key for integration tests."""
    return settings.gemini_api_key

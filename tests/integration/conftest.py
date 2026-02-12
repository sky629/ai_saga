"""Integration test configuration and fixtures."""

import pytest_asyncio
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

    # Create tables
    async with engine.begin() as conn:
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

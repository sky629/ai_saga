"""PostgreSQL database connection management using asyncpg and SQLAlchemy."""

import functools
from contextlib import asynccontextmanager
from typing import Any, Dict

import asyncpg
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.common.exception import ServerError
from app.common.logging import logger
from app.common.utils.singleton import Singleton
from config.settings import settings

# SQLAlchemy Base
Base = declarative_base()
metadata = MetaData()


def handle_postgres_error(func):
    """Decorator to handle PostgreSQL errors."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncpg.PostgresError as exc:
            logger.exception("PostgreSQL operation failed")
            raise ServerError from exc
        except Exception as exc:
            logger.exception("Unknown database error occurred")
            raise ServerError from exc

    return wrapper


class PostgresStorage(metaclass=Singleton):
    """Domain-aware PostgreSQL storage manager with read/write separation."""

    def __init__(self):
        self._domain_pools = (
            {}
        )  # domain -> {read_engine, write_engine, read_session_factory, write_session_factory}

    def _get_domain_database_urls(self, domain: str) -> tuple[str, str]:
        """Get read and write database URLs for a specific domain."""
        domain_upper = domain.upper()

        # Try domain-specific URLs first
        read_url_attr = f"{domain_upper}_POSTGRES_READ_URL"
        write_url_attr = f"{domain_upper}_POSTGRES_WRITE_URL"

        read_url = getattr(settings, read_url_attr.lower(), "")
        write_url = getattr(settings, write_url_attr.lower(), "")

        # Final fallback to global URLs
        if not read_url:
            read_url = settings.postgres_read_url or settings.postgres_url
        if not write_url:
            write_url = settings.postgres_write_url or settings.postgres_url

        return read_url, write_url

    def _get_database_url(self, url: str) -> str:
        """Convert PostgreSQL URL to asyncpg format."""
        return url.replace("postgresql://", "postgresql+asyncpg://")

    def _get_or_create_domain_pool(self, domain: str) -> Dict[str, Any]:
        """Get or create connection pools for a specific domain."""
        if domain not in self._domain_pools:
            read_url, write_url = self._get_domain_database_urls(domain)

            # Create read engine
            read_database_url = self._get_database_url(read_url)
            read_engine = create_async_engine(
                read_database_url,
                echo=not settings.is_prod(),
                pool_size=8,  # Optimized for read operations
                max_overflow=15,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            # Create write engine
            write_database_url = self._get_database_url(write_url)
            write_engine = create_async_engine(
                write_database_url,
                echo=not settings.is_prod(),
                pool_size=10,  # Optimized for write operations
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            # Create session factories
            read_session_factory = async_sessionmaker(
                bind=read_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            write_session_factory = async_sessionmaker(
                bind=write_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            self._domain_pools[domain] = {
                "read_engine": read_engine,
                "write_engine": write_engine,
                "read_session_factory": read_session_factory,
                "write_session_factory": write_session_factory,
            }

            logger.info(
                f"Created domain pool for '{domain}': read='{read_url}', write='{write_url}'"
            )

        return self._domain_pools[domain]

    @asynccontextmanager
    async def get_domain_read_session(self, domain: str = "default"):
        """Get read-only database session for a specific domain."""
        pool = self._get_or_create_domain_pool(domain)
        async with pool["read_session_factory"]() as session:
            try:
                yield session
                # No commit needed for read operations
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def get_domain_write_session(self, domain: str = "default"):
        """Get write database session for a specific domain."""
        pool = self._get_or_create_domain_pool(domain)
        async with pool["write_session_factory"]() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close_domain_pool(self, domain: str):
        """Close all connections for a specific domain."""
        if domain in self._domain_pools:
            pool = self._domain_pools[domain]
            await pool["read_engine"].dispose()
            await pool["write_engine"].dispose()
            del self._domain_pools[domain]
            logger.info(f"Closed domain pool for '{domain}'")

    async def close_all_pools(self):
        """Close all domain connection pools."""
        for domain in list(self._domain_pools.keys()):
            await self.close_domain_pool(domain)
        logger.info("All domain pools closed")

    # FastAPI Dependency Methods
    async def read_db(self):
        """FastAPI dependency for read-only database session.
        
        Usage: Depends(postgres_storage.read_db)
        """
        async with self.get_domain_read_session() as session:
            yield session

    async def write_db(self):
        """FastAPI dependency for write database session.
        
        Usage: Depends(postgres_storage.write_db)
        """
        async with self.get_domain_write_session() as session:
            yield session


# Global instance
postgres_storage = PostgresStorage()

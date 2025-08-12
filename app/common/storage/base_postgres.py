"""Base repository with read/write database separation."""

from typing import Any, Dict, List, Optional, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.orm import DeclarativeBase

from app.common.logging import logger
from app.common.storage.postgres import postgres_storage
from app.common.utils.datetime import get_utc_datetime

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository:
    """Base repository class with read/write routing."""

    model_class = None
    domain = "default"
    logger.debug(f"Repository initialized for model {model_class} in domain '{domain}'")

    # Read operations - use read database
    @classmethod
    async def get_by_id(cls, entity_id: str) -> Optional[T]:
        """Get entity by ID using read database."""
        async with postgres_storage.get_domain_read_session(
            domain=cls.domain
        ) as session:
            result = await session.execute(
                select(cls.model_class).where(cls.model_class.id == entity_id)
            )
            return result.scalar_one_or_none()

    @classmethod
    async def get_by_field(cls, field_name: str, field_value: Any) -> Optional[T]:
        """Get entity by specific field using read database."""
        async with postgres_storage.get_domain_read_session(
            domain=cls.domain
        ) as session:
            field = getattr(cls.model_class, field_name)
            result = await session.execute(
                select(cls.model_class).where(field == field_value)
            )
            return result.scalar_one_or_none()

    @classmethod
    async def list_all(
        cls,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[T]:
        """List entities with pagination using read database."""
        async with postgres_storage.get_domain_read_session(
            domain=cls.domain
        ) as session:
            stmt = select(cls.model_class).offset(offset).limit(limit)

            if filters:
                for field_name, field_value in filters.items():
                    if hasattr(cls.model_class, field_name):
                        field = getattr(cls.model_class, field_name)
                        stmt = stmt.where(field == field_value)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    @classmethod
    async def count(cls, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities using read database."""
        from sqlalchemy import func

        async with postgres_storage.get_domain_read_session(
            domain=cls.domain
        ) as session:
            stmt = select(func.count(cls.model_class.id))

            if filters:
                for field_name, field_value in filters.items():
                    if hasattr(cls.model_class, field_name):
                        field = getattr(cls.model_class, field_name)
                        stmt = stmt.where(field == field_value)

            result = await session.execute(stmt)
            return result.scalar()

    @classmethod
    async def exists(cls, entity_id: Any) -> bool:
        """Check if entity exists using read database."""
        from sqlalchemy import func

        async with postgres_storage.get_domain_read_session(
            domain=cls.domain
        ) as session:
            stmt = select(func.count(cls.model_class.id)).where(
                cls.model_class.id == entity_id
            )
            result = await session.execute(stmt)
            return result.scalar() > 0

    # Write operations - use write database
    @classmethod
    async def create(cls, entity) -> T:
        """Create new entity using write database."""
        async with postgres_storage.get_domain_write_session(
            domain=cls.domain
        ) as session:
            session.add(entity)
            await session.flush()
            await session.refresh(entity)
            return entity

    @classmethod
    async def update_by_id(cls, entity_id: str, **kwargs) -> Optional[T]:
        """Update entity by ID using write database."""

        async with postgres_storage.get_domain_write_session(
            domain=cls.domain
        ) as session:
            # Add updated_at if the model has it
            if hasattr(cls.model_class, "updated_at"):
                kwargs["updated_at"] = get_utc_datetime()

            stmt = (
                update(cls.model_class)
                .where(cls.model_class.id == entity_id)
                .values(**kwargs)
                .returning(cls.model_class)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @classmethod
    async def delete_by_id(cls, entity_id: str) -> bool:
        """Delete entity by ID using write database."""
        async with postgres_storage.get_domain_write_session(
            domain=cls.domain
        ) as session:
            stmt = delete(cls.model_class).where(cls.model_class.id == entity_id)
            result = await session.execute(stmt)
            return result.rowcount > 0

    @classmethod
    async def delete_by_field(cls, field_name: str, field_value: Any) -> bool:
        """Delete entity by ID using write database."""
        async with postgres_storage.get_domain_write_session(
            domain=cls.domain
        ) as session:
            field = getattr(cls.model_class, field_name)
            stmt = delete(cls.model_class).where(field == field_value)
            result = await session.execute(stmt)
            return result.rowcount > 0

    @classmethod
    async def bulk_create(cls, entities_data: List[Dict[str, Any]]) -> List[T]:
        """Bulk create entities using write database."""
        async with postgres_storage.get_domain_write_session(
            domain=cls.domain
        ) as session:
            entities = [cls.model_class(**data) for data in entities_data]
            session.add_all(entities)
            await session.flush()
            for entity in entities:
                await session.refresh(entity)
            return entities

    @classmethod
    async def bulk_update(
        cls, filters: Dict[str, Any], update_data: Dict[str, Any]
    ) -> int:
        """Bulk update entities using write database."""
        async with postgres_storage.get_domain_write_session(
            domain=cls.domain
        ) as session:
            # Add updated_at if the model has it
            if hasattr(cls.model_class, "updated_at"):
                update_data["updated_at"] = get_utc_datetime()

            stmt = update(cls.model_class).values(**update_data)

            for field_name, field_value in filters.items():
                if hasattr(cls.model_class, field_name):
                    field = getattr(cls.model_class, field_name)
                    stmt = stmt.where(field == field_value)

            result = await session.execute(stmt)
            return result.rowcount

    # Manual session access for complex operations
    @classmethod
    async def with_read_session(cls, func):
        """Execute function with domain-specific read session."""
        async with postgres_storage.get_domain_read_session(
            domain=cls.domain
        ) as session:
            return await func(session)

    @classmethod
    async def with_write_session(cls, func):
        """Execute function with domain-specific write session."""
        async with postgres_storage.get_domain_write_session(
            domain=cls.domain
        ) as session:
            return await func(session)

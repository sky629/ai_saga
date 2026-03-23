"""GameMemoryRepository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.application.ports import GameMemoryRepositoryInterface
from app.game.domain.entities import GameMemoryEntity
from app.game.infrastructure.persistence.mappers import (
    GameMemoryDocumentMapper,
)
from app.game.infrastructure.persistence.models import GameMemoryDocument


class GameMemoryRepositoryImpl(GameMemoryRepositoryInterface):
    """검색 메모리 저장소 구현."""

    def __init__(self, session: AsyncSession):
        self._db = session

    async def create(self, memory: GameMemoryEntity) -> GameMemoryEntity:
        orm = GameMemoryDocument(
            id=memory.id,
            session_id=memory.session_id,
            source_message_id=memory.source_message_id,
            role=memory.role.value,
            memory_type=memory.memory_type.value,
            content=memory.content,
            parsed_response=memory.parsed_response,
            embedding=memory.embedding,
            created_at=memory.created_at,
        )
        self._db.add(orm)
        await self._db.flush()
        await self._db.refresh(orm)
        return GameMemoryDocumentMapper.to_entity(orm)

    async def get_similar_memories(
        self,
        embedding: list[float],
        session_id: UUID,
        limit: int = 5,
        distance_threshold: float = 0.3,
        exclude_memory_ids: list[UUID] | None = None,
    ) -> list[GameMemoryEntity]:
        distance_expr = GameMemoryDocument.embedding.cosine_distance(
            embedding
        ).label("similarity_distance")
        query = (
            select(GameMemoryDocument, distance_expr)
            .where(GameMemoryDocument.session_id == session_id)
            .where(
                GameMemoryDocument.embedding.cosine_distance(embedding)
                < distance_threshold
            )
        )
        if exclude_memory_ids:
            query = query.where(~GameMemoryDocument.id.in_(exclude_memory_ids))

        query = query.order_by(distance_expr).limit(limit)
        result = await self._db.execute(query)
        rows = result.all()

        memories: list[GameMemoryEntity] = []
        for orm, distance in rows:
            entity = GameMemoryDocumentMapper.to_entity(orm)
            memories.append(
                entity.model_copy(
                    update={"similarity_distance": float(distance)}
                )
            )
        return memories

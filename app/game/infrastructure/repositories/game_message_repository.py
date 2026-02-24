"""GameMessage Repository Implementation."""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.application.ports import GameMessageRepositoryInterface
from app.game.domain.entities import GameMessageEntity
from app.game.infrastructure.persistence.mappers import GameMessageMapper
from app.game.infrastructure.persistence.models import GameMessage


class GameMessageRepositoryImpl(GameMessageRepositoryInterface):
    """게임 메시지 저장소 구현."""

    def __init__(self, session: AsyncSession):
        self._db = session

    async def create(self, message: GameMessageEntity) -> GameMessageEntity:
        """메시지 생성."""
        orm = GameMessage(
            id=message.id,
            session_id=message.session_id,
            role=message.role.value,
            content=message.content,
            parsed_response=message.parsed_response,
            token_count=message.token_count,
            image_url=message.image_url,
            embedding=message.embedding,
            created_at=message.created_at,
        )
        self._db.add(orm)
        await self._db.flush()
        await self._db.refresh(orm)

        return GameMessageMapper.to_entity(orm)

    async def get_recent_messages(
        self, session_id: UUID, limit: int = 20
    ) -> list[GameMessageEntity]:
        """최근 메시지 조회."""
        result = await self._db.execute(
            select(GameMessage)
            .where(GameMessage.session_id == session_id)
            .order_by(desc(GameMessage.created_at))
            .limit(limit)
        )
        orms = result.scalars().all()

        # 역순으로 정렬하여 시간순 반환
        return [
            GameMessageMapper.to_entity(orm) for orm in reversed(list(orms))
        ]

    async def get_similar_messages(
        self,
        embedding: list[float],
        session_id: UUID,
        limit: int = 5,
        distance_threshold: float = 0.3,
    ) -> list[GameMessageEntity]:
        """벡터 유사도 기반 메시지 검색.

        pgvector의 cosine distance 연산자(<=>)를 사용하여 유사한 메시지를 검색합니다.

        Args:
            embedding: 검색 기준 벡터 (768차원)
            session_id: 세션 ID (같은 세션 내에서만 검색)
            limit: 최대 반환 개수
            distance_threshold: 유사도 임계값 (코사인 거리, 낮을수록 유사)

        Returns:
            유사도 높은 순으로 정렬된 메시지 목록
        """
        result = await self._db.execute(
            select(GameMessage)
            .where(GameMessage.session_id == session_id)
            .where(GameMessage.embedding.isnot(None))
            .where(
                GameMessage.embedding.cosine_distance(embedding)
                < distance_threshold
            )
            .order_by(GameMessage.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        orms = result.scalars().all()

        return [GameMessageMapper.to_entity(orm) for orm in orms]

    async def get_by_id(self, message_id: UUID) -> GameMessageEntity | None:
        result = await self._db.execute(
            select(GameMessage).where(GameMessage.id == message_id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return GameMessageMapper.to_entity(orm)

    async def update_image_url(
        self, message_id: UUID, image_url: str
    ) -> GameMessageEntity:
        result = await self._db.execute(
            select(GameMessage).where(GameMessage.id == message_id)
        )
        orm = result.scalar_one()
        orm.image_url = image_url
        await self._db.flush()
        await self._db.refresh(orm)
        return GameMessageMapper.to_entity(orm)

"""GameMessage Repository Implementation."""

from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.application.ports import GameMessageRepositoryInterface
from app.game.domain.entities import GameMessageEntity
from app.game.infrastructure.persistence.mappers import GameMessageMapper
from app.game.infrastructure.persistence.models.game_models import GameMessage


class GameMessageRepositoryImpl(GameMessageRepositoryInterface):
    """GameMessage 저장소 구현체."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, message: GameMessageEntity) -> GameMessageEntity:
        """메시지 생성."""
        orm = GameMessage(
            id=message.id if message.id else uuid4(),
            session_id=message.session_id,
            role=message.role.value,
            content=message.content,
            parsed_response=message.parsed_response,
            token_count=message.token_count,
            created_at=message.created_at,
        )
        self._db.add(orm)
        await self._db.commit()
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
        return [GameMessageMapper.to_entity(orm) for orm in reversed(list(orms))]

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

    async def get_messages(
        self,
        session_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GameMessageEntity]:
        """세션 메시지 조회."""
        result = await self._db.execute(
            select(GameMessage)
            .where(GameMessage.session_id == session_id)
            .order_by(GameMessage.created_at)
            .offset(offset)
            .limit(limit)
        )
        orms = result.scalars().all()
        return [GameMessageMapper.to_entity(orm) for orm in orms]

    async def get_messages_with_cursor(
        self,
        session_id: UUID,
        limit: int = 50,
        cursor: UUID | None = None,
    ) -> tuple[list[GameMessageEntity], UUID | None, bool]:
        """Cursor 기반 세션 메시지 조회."""
        query = (
            select(GameMessage)
            .where(GameMessage.session_id == session_id)
            .order_by(GameMessage.created_at.desc(), GameMessage.id.desc())
        )

        if cursor:
            cursor_result = await self._db.execute(
                select(GameMessage).where(GameMessage.id == cursor)
            )
            cursor_obj = cursor_result.scalar_one_or_none()
            if cursor_obj:
                query = query.where(
                    (GameMessage.created_at < cursor_obj.created_at)
                    | (
                        (GameMessage.created_at == cursor_obj.created_at)
                        & (GameMessage.id < cursor)
                    )
                )

        query = query.limit(limit + 1)
        result = await self._db.execute(query)
        orms = result.scalars().all()

        has_more = len(orms) > limit
        if has_more:
            orms = orms[:limit]
        next_cursor = orms[-1].id if orms and has_more else None

        return (
            [GameMessageMapper.to_entity(orm) for orm in orms],
            next_cursor,
            has_more,
        )

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

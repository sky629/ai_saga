"""GameSession Repository Implementation."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.game.application.ports import GameSessionRepositoryInterface
from app.game.domain.entities import GameSessionEntity
from app.game.infrastructure.persistence.mappers import GameSessionMapper
from app.game.infrastructure.persistence.models.game_models import GameSession


class GameSessionRepositoryImpl(GameSessionRepositoryInterface):
    """GameSession 저장소 구현체.

    SQLAlchemy를 사용하여 실제 DB와 통신합니다.
    도메인 엔티티와 ORM 모델 간 변환에 Mapper를 사용합니다.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, session_id: UUID) -> Optional[GameSessionEntity]:
        """ID로 세션 조회."""
        result = await self._db.execute(
            select(GameSession)
            .options(
                selectinload(GameSession.character),
                selectinload(GameSession.scenario),
            )
            .where(GameSession.id == session_id)
        )
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return GameSessionMapper.to_entity(orm)

    async def get_active_by_character(
        self, character_id: UUID
    ) -> Optional[GameSessionEntity]:
        """캐릭터의 활성 세션 조회."""
        result = await self._db.execute(
            select(GameSession).where(
                GameSession.character_id == character_id,
                GameSession.status == "active",
            )
        )
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return GameSessionMapper.to_entity(orm)

    async def save(self, session: GameSessionEntity) -> GameSessionEntity:
        """세션 저장 (생성 또는 업데이트)."""
        # Check if exists
        result = await self._db.execute(
            select(GameSession).where(GameSession.id == session.id)
        )
        orm = result.scalar_one_or_none()

        if orm is None:
            # Create new
            orm = GameSession(
                id=session.id,
                character_id=session.character_id,
                scenario_id=session.scenario_id,
                current_location=session.current_location,
                game_state=session.game_state,
                status=session.status.value,
                turn_count=session.turn_count,
                max_turns=session.max_turns,
                ending_type=(
                    session.ending_type.value if session.ending_type else None
                ),
                started_at=session.started_at,
                ended_at=session.ended_at,
                last_activity_at=session.last_activity_at,
            )
            self._db.add(orm)
        else:
            # Update existing
            updates = GameSessionMapper.to_dict(session)
            for key, value in updates.items():
                setattr(orm, key, value)

        await self._db.flush()
        await self._db.refresh(orm)

        return GameSessionMapper.to_entity(orm)

    async def delete(self, session_id: UUID) -> None:
        """세션 삭제."""
        from sqlalchemy import delete as sql_delete

        from app.game.infrastructure.persistence.models.game_models import (
            GameMessage,
            GameSession,
        )

        # Delete related messages first
        await self._db.execute(
            sql_delete(GameMessage).where(GameMessage.session_id == session_id)
        )
        # Delete session
        await self._db.execute(
            sql_delete(GameSession).where(GameSession.id == session_id)
        )
        await self._db.flush()

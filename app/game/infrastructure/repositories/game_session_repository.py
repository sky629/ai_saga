"""GameSession Repository Implementation."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.game.application.ports import (
    GameSessionRepositoryInterface,
    UserSessionReadModel,
)
from app.game.domain.entities import GameSessionEntity
from app.game.infrastructure.persistence.mappers import (
    CharacterMapper,
    GameSessionMapper,
)
from app.game.infrastructure.persistence.models.game_models import (
    Character,
    GameMessage,
    GameSession,
)

logger = logging.getLogger(__name__)


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

    async def list_by_user(
        self,
        user_id: UUID,
        status_filter: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[UUID] = None,
    ) -> list[UserSessionReadModel]:
        """사용자 세션 목록 조회."""
        char_result = await self._db.execute(
            select(Character.id).where(Character.user_id == user_id)
        )
        character_ids = [row[0] for row in char_result.fetchall()]
        if not character_ids:
            return []

        query = (
            select(GameSession)
            .options(
                selectinload(GameSession.character),
                selectinload(GameSession.scenario),
            )
            .where(GameSession.character_id.in_(character_ids))
            .order_by(
                GameSession.last_activity_at.desc(),
                GameSession.id.desc(),
            )
        )

        if cursor:
            cursor_session = await self._db.execute(
                select(GameSession).where(GameSession.id == cursor)
            )
            cursor_obj = cursor_session.scalar_one_or_none()
            if cursor_obj:
                query = query.where(
                    (
                        GameSession.last_activity_at
                        < cursor_obj.last_activity_at
                    )
                    | (
                        (
                            GameSession.last_activity_at
                            == cursor_obj.last_activity_at
                        )
                        & (GameSession.id < cursor)
                    )
                )

        if status_filter:
            query = query.where(GameSession.status == status_filter)

        query = query.limit(limit + 1)
        result = await self._db.execute(query)
        sessions = result.scalars().all()

        return [
            self._to_user_session_read_model(session) for session in sessions
        ]

    async def save(self, session: GameSessionEntity) -> GameSessionEntity:
        """세션 저장 (생성 또는 업데이트)."""
        # Check if exists
        result = await self._db.execute(
            select(GameSession).where(GameSession.id == session.id)
        )
        orm = result.scalar_one_or_none()

        if orm is None:
            logger.info(f"[DEBUG] Creating new session: {session.id}")
            # Create new
            orm = GameSession(
                id=session.id,
                user_id=session.user_id,
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
            logger.info(
                f"[DEBUG] Updating existing session: {session.id} (Turn {session.turn_count}/{session.max_turns})"
            )
            logger.info(
                f"[DEBUG] ORM before update: turn_count={orm.turn_count}, current_location={orm.current_location}, game_state keys={list(orm.game_state.keys()) if orm.game_state else []}"
            )
            updates = GameSessionMapper.to_dict(session)
            logger.info(
                f"[DEBUG] Updates to apply: turn_count={updates.get('turn_count')}, current_location={updates.get('current_location')}, game_state keys={list(updates.get('game_state', {}).keys())}"
            )
            for key, value in updates.items():
                setattr(orm, key, value)
            logger.info(
                f"[DEBUG] ORM after update: turn_count={orm.turn_count}, current_location={orm.current_location}, game_state keys={list(orm.game_state.keys()) if orm.game_state else []}"
            )

        await self._db.flush()
        await self._db.refresh(orm)

        return GameSessionMapper.to_entity(orm)

    async def delete(self, session_id: UUID) -> None:
        """세션 삭제."""
        # Delete related messages first
        await self._db.execute(
            sql_delete(GameMessage).where(GameMessage.session_id == session_id)
        )
        # Delete session
        await self._db.execute(
            sql_delete(GameSession).where(GameSession.id == session_id)
        )
        await self._db.flush()

    async def commit(self) -> None:
        """세션 관련 작업 트랜잭션 커밋."""
        await self._db.commit()

    @staticmethod
    def _to_user_session_read_model(
        session: GameSession,
    ) -> UserSessionReadModel:
        return UserSessionReadModel(
            id=session.id,
            character_name=session.character.name,
            scenario_name=session.scenario.name,
            status=session.status,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
            ending_type=session.ending_type,
            character=CharacterMapper.to_entity(session.character),
        )

"""ORM ↔ Domain Entity Mappers.

ORM 모델과 도메인 엔티티 간 변환을 담당합니다.
인프라 레이어에서만 사용되며, 도메인 레이어는 ORM에 대해 알지 못합니다.
"""

from app.game.domain.entities import (
    CharacterEntity,
    GameMessageEntity,
    GameSessionEntity,
    ScenarioEntity,
)
from app.game.domain.entities.character import CharacterStats
from app.game.domain.value_objects import (
    EndingType,
    MessageRole,
    SessionStatus,
)
from app.game.infrastructure.persistence.models.game_models import (
    Character,
    GameMessage,
    GameSession,
    Scenario,
)


class GameSessionMapper:
    """GameSession ORM ↔ GameSessionEntity 매퍼."""

    @staticmethod
    def to_entity(orm: GameSession) -> GameSessionEntity:
        """ORM 모델을 도메인 엔티티로 변환."""
        ending_type = None
        if orm.ending_type:
            ending_type = EndingType(orm.ending_type)

        return GameSessionEntity(
            id=orm.id,
            user_id=orm.user_id,
            character_id=orm.character_id,
            scenario_id=orm.scenario_id,
            current_location=orm.current_location,
            game_state=orm.game_state or {},
            status=SessionStatus(orm.status),
            turn_count=orm.turn_count,
            max_turns=orm.max_turns,
            ending_type=ending_type,
            started_at=orm.started_at,
            ended_at=orm.ended_at,
            last_activity_at=orm.last_activity_at,
        )

    @staticmethod
    def to_dict(entity: GameSessionEntity) -> dict:
        """도메인 엔티티의 변경사항을 ORM 업데이트 딕셔너리로 변환."""
        return {
            "current_location": entity.current_location,
            "game_state": entity.game_state,
            "status": entity.status.value,
            "turn_count": entity.turn_count,
            "max_turns": entity.max_turns,
            "ending_type": (
                entity.ending_type.value if entity.ending_type else None
            ),
            "ended_at": entity.ended_at,
            "last_activity_at": entity.last_activity_at,
        }


class CharacterMapper:
    """Character ORM ↔ CharacterEntity 매퍼."""

    @staticmethod
    def to_entity(orm: Character) -> CharacterEntity:
        """ORM 모델을 도메인 엔티티로 변환."""
        stats_dict = orm.stats or {"hp": 100, "max_hp": 100, "level": 1}
        stats = CharacterStats(**stats_dict)

        return CharacterEntity(
            id=orm.id,
            user_id=orm.user_id,
            scenario_id=orm.scenario_id,
            name=orm.name,
            description=orm.description,
            stats=stats,
            inventory=orm.inventory or [],
            is_active=orm.is_active,
            created_at=orm.created_at,
        )

    @staticmethod
    def to_dict(entity: CharacterEntity) -> dict:
        """도메인 엔티티의 변경사항을 ORM 업데이트 딕셔너리로 변환."""
        return {
            "name": entity.name,
            "description": entity.description,
            "stats": entity.stats.model_dump(),
            "inventory": entity.inventory,
            "is_active": entity.is_active,
        }


class ScenarioMapper:
    """Scenario ORM ↔ ScenarioEntity 매퍼."""

    @staticmethod
    def to_entity(orm: Scenario) -> ScenarioEntity:
        """ORM 모델을 도메인 엔티티로 변환."""
        from app.game.domain.value_objects import (
            ScenarioDifficulty,
            ScenarioGenre,
        )

        return ScenarioEntity(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            world_setting=orm.world_setting,
            initial_location=orm.initial_location,
            genre=ScenarioGenre(orm.genre),
            difficulty=ScenarioDifficulty(orm.difficulty),
            system_prompt_override=orm.system_prompt_override,
            max_turns=orm.max_turns,
            is_active=orm.is_active,
            created_at=orm.created_at,
        )


class GameMessageMapper:
    """GameMessage ORM ↔ GameMessageEntity 매퍼."""

    @staticmethod
    def to_entity(orm: GameMessage) -> GameMessageEntity:
        """ORM 모델을 도메인 엔티티로 변환."""
        return GameMessageEntity(
            id=orm.id,
            session_id=orm.session_id,
            role=MessageRole(orm.role),
            content=orm.content,
            parsed_response=orm.parsed_response,
            token_count=orm.token_count,
            image_url=orm.image_url,
            embedding=orm.embedding,
            created_at=orm.created_at,
        )

    @staticmethod
    def to_dict(entity: GameMessageEntity) -> dict:
        """도메인 엔티티를 ORM 생성용 딕셔너리로 변환."""
        return {
            "session_id": entity.session_id,
            "role": entity.role.value,
            "content": entity.content,
            "parsed_response": entity.parsed_response,
            "token_count": entity.token_count,
        }

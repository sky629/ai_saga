"""Game State Value Objects.

GameState represents the current state of the game world.
StateChanges represents incremental updates to apply to GameState.
"""

from typing import Optional

from pydantic import BaseModel, Field


class GameState(BaseModel):
    """게임 상태를 나타내는 불변 값 객체.

    게임 진행 중 수집한 아이템, 방문한 장소, 만난 NPC, 발견한 것들을 추적합니다.
    불변 객체로 상태 변경 시 새 인스턴스를 생성합니다.
    """

    model_config = {"frozen": True}

    items: list[str] = Field(
        default_factory=list, description="보유 아이템 목록"
    )
    visited_locations: list[str] = Field(
        default_factory=list, description="방문한 장소 목록"
    )
    met_npcs: list[str] = Field(
        default_factory=list, description="만난 NPC 목록"
    )
    discoveries: list[str] = Field(
        default_factory=list, description="발견한 것들 (비밀, 단서 등)"
    )

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        """딕셔너리에서 GameState 생성.

        Args:
            data: 게임 상태 딕셔너리

        Returns:
            GameState 인스턴스
        """
        return cls(
            items=data.get("items", []),
            visited_locations=data.get("visited_locations", []),
            met_npcs=data.get("met_npcs", []),
            discoveries=data.get("discoveries", []),
        )

    def to_dict(self) -> dict:
        """GameState를 딕셔너리로 변환.

        Returns:
            게임 상태 딕셔너리
        """
        return {
            "items": self.items,
            "visited_locations": self.visited_locations,
            "met_npcs": self.met_npcs,
            "discoveries": self.discoveries,
        }


class StateChanges(BaseModel):
    """게임 상태 변경 사항을 나타내는 불변 값 객체.

    LLM이 생성한 state_changes를 파싱하여 GameState에 적용할 변경사항을 표현합니다.
    """

    model_config = {"frozen": True}

    hp_change: int = Field(default=0, description="HP 변화량")
    items_gained: list[str] = Field(
        default_factory=list, description="획득한 아이템"
    )
    items_lost: list[str] = Field(
        default_factory=list, description="잃은 아이템"
    )
    location: Optional[str] = Field(
        default=None, description="새로운 위치 (변경 시)"
    )
    npcs_met: list[str] = Field(
        default_factory=list, description="새로 만난 NPC"
    )
    discoveries: list[str] = Field(
        default_factory=list, description="새로 발견한 것들"
    )

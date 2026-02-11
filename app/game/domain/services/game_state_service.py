"""Game State Domain Service.

게임 상태 변경사항을 적용하는 순수 도메인 로직입니다.
"""

from app.game.domain.value_objects import GameState, StateChanges


class GameStateService:
    """게임 상태 변경 사항을 적용하는 도메인 서비스.

    여러 엔티티에 걸친 게임 상태 관리 로직을 처리합니다.
    외부 인프라에 의존하지 않는 순수 비즈니스 로직만 포함합니다.
    """

    @staticmethod
    def apply_state_changes(
        current_state_dict: dict, changes: StateChanges
    ) -> dict:
        """현재 게임 상태에 변경사항을 적용.

        Args:
            current_state_dict: 현재 게임 상태 딕셔너리
            changes: 적용할 변경사항

        Returns:
            변경사항이 적용된 새로운 게임 상태 딕셔너리
        """
        # 현재 상태를 GameState 객체로 변환
        current = GameState.from_dict(current_state_dict)

        # 아이템 변경 적용
        new_items = list(current.items)
        for item in changes.items_gained:
            if item not in new_items:
                new_items.append(item)
        for item in changes.items_lost:
            if item in new_items:
                new_items.remove(item)

        # 위치 변경 적용
        new_locations = list(current.visited_locations)
        if changes.location and changes.location not in new_locations:
            new_locations.append(changes.location)

        # NPC 변경 적용
        new_npcs = list(current.met_npcs)
        for npc in changes.npcs_met:
            if npc not in new_npcs:
                new_npcs.append(npc)

        # 발견 사항 적용
        new_discoveries = list(current.discoveries)
        for discovery in changes.discoveries:
            if discovery not in new_discoveries:
                new_discoveries.append(discovery)

        # 새로운 GameState 생성
        new_state = GameState(
            items=new_items,
            visited_locations=new_locations,
            met_npcs=new_npcs,
            discoveries=new_discoveries,
        )

        return new_state.to_dict()

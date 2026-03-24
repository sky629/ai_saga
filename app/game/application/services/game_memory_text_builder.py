"""검색용 게임 메모리 텍스트 빌더."""

from app.game.domain.entities import GameMessageEntity


class GameMemoryTextBuilder:
    """원문과 별도로 검색 최적화 텍스트를 생성한다."""

    @staticmethod
    def build_message_memory_text(message: GameMessageEntity) -> str:
        """메시지를 검색용 텍스트로 정규화한다."""
        if message.is_ai_response:
            return GameMemoryTextBuilder.build_assistant_search_text(
                raw_content=message.content,
                parsed_response=message.parsed_response,
            )
        return message.content.strip()

    @staticmethod
    def build_assistant_search_text(
        raw_content: str,
        parsed_response: dict | None,
    ) -> str:
        """assistant 응답을 검색용 텍스트로 변환한다."""
        if not isinstance(parsed_response, dict):
            return raw_content.strip()

        sections: list[str] = []

        narrative = parsed_response.get("narrative")
        if isinstance(narrative, str) and narrative.strip():
            sections.append(narrative.strip())

        state_changes = parsed_response.get("state_changes")
        if isinstance(state_changes, dict):
            state_lines = GameMemoryTextBuilder._build_state_lines(
                state_changes
            )
            sections.extend(state_lines)

        if sections:
            return "\n".join(sections)
        return raw_content.strip()

    @staticmethod
    def _build_state_lines(state_changes: dict) -> list[str]:
        """state_changes를 사람이 읽을 수 있는 검색 텍스트로 변환한다."""
        lines: list[str] = []

        location = state_changes.get("location")
        if isinstance(location, str) and location.strip():
            lines.append(f"위치 변화: {location.strip()}")

        items_gained = state_changes.get("items_gained")
        if isinstance(items_gained, list) and items_gained:
            lines.append(
                "획득 아이템: "
                + ", ".join(str(item).strip() for item in items_gained)
            )

        items_lost = state_changes.get("items_lost")
        if isinstance(items_lost, list) and items_lost:
            lines.append(
                "소모/분실 아이템: "
                + ", ".join(str(item).strip() for item in items_lost)
            )

        discoveries = state_changes.get("discoveries")
        if isinstance(discoveries, list) and discoveries:
            lines.append(
                "발견: " + ", ".join(str(item).strip() for item in discoveries)
            )

        npcs_met = state_changes.get("npcs_met")
        if isinstance(npcs_met, list) and npcs_met:
            lines.append(
                "만난 NPC: "
                + ", ".join(str(item).strip() for item in npcs_met)
            )

        hp_change = state_changes.get("hp_change")
        if isinstance(hp_change, int) and hp_change != 0:
            lines.append(f"HP 변화: {hp_change}")

        experience_gained = state_changes.get("experience_gained")
        if isinstance(experience_gained, int) and experience_gained != 0:
            lines.append(f"경험치 변화: {experience_gained}")

        return lines

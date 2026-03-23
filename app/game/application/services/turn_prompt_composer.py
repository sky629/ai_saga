"""현재 턴 프롬프트 조립 서비스."""

from dataclasses import dataclass

from app.game.application.services.game_memory_text_builder import (
    GameMemoryTextBuilder,
)
from app.game.domain.entities import GameMessageEntity
from app.game.domain.value_objects import ActionType, GameState
from app.llm.prompts.game_master import GameMasterPrompt


@dataclass(frozen=True)
class TurnPrompt:
    """LLM 호출에 사용할 프롬프트 묶음."""

    system_prompt: str
    messages: list[dict[str, str]]


class TurnPromptComposer:
    """시스템 프롬프트와 현재 턴 payload를 일관되게 조립한다."""

    @staticmethod
    def compose(
        scenario_name: str,
        world_setting: str,
        character_name: str,
        character_description: str,
        current_location: str,
        game_state: GameState,
        inventory: list[str],
        player_action: str,
        action_type: ActionType,
        conversation_history: list[GameMessageEntity],
        recalled_memories: list[GameMessageEntity],
        recent_events_summary: str,
        dice_result_section: str = "",
    ) -> TurnPrompt:
        """현재 턴의 명시적 LLM 입력을 생성한다."""
        base_prompt = GameMasterPrompt(
            scenario_name=scenario_name,
            world_setting=world_setting,
            character_name=character_name,
            character_description=character_description,
            current_location=current_location,
            inventory=inventory,
            game_state=game_state,
            dice_result_section=dice_result_section,
        )
        messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in conversation_history
        ]
        messages.append(
            {
                "role": "user",
                "content": TurnPromptComposer._build_turn_payload(
                    player_action=player_action,
                    action_type=action_type,
                    recent_events_summary=recent_events_summary,
                    recalled_memories=recalled_memories,
                    dice_result_section=dice_result_section,
                ),
            }
        )
        return TurnPrompt(
            system_prompt=base_prompt.system_prompt,
            messages=messages,
        )

    @staticmethod
    def _build_turn_payload(
        player_action: str,
        action_type: ActionType,
        recent_events_summary: str,
        recalled_memories: list[GameMessageEntity],
        dice_result_section: str,
    ) -> str:
        """현재 턴 payload를 user message 형식으로 만든다."""
        sections = [
            "## 현재 플레이어 행동",
            player_action,
            "",
            "## 서버 판정",
            f"- action_type: {action_type.value}",
            (
                f"- requires_dice: {'true' if action_type.requires_dice else 'false'}"
            ),
        ]

        if dice_result_section:
            sections.extend(
                [
                    "",
                    "## 서버 주사위 판정 결과",
                    dice_result_section,
                ]
            )

        if recent_events_summary and recent_events_summary != "없음":
            sections.extend(
                [
                    "",
                    "## 최근 주요 사건",
                    recent_events_summary,
                ]
            )

        if recalled_memories:
            memory_lines = [
                f"- {GameMemoryTextBuilder.build_message_memory_text(message)}"
                for message in recalled_memories
            ]
            sections.extend(
                [
                    "",
                    "## 회수된 관련 기억",
                    "\n".join(memory_lines),
                ]
            )

        sections.extend(
            [
                "",
                "위 정보를 바탕으로 JSON 형식의 게임 마스터 응답을 생성하세요.",
            ]
        )

        return "\n".join(sections).strip()

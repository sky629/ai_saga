"""현재 턴 프롬프트 조립 서비스."""

from dataclasses import dataclass

from app.game.application.services.game_memory_text_builder import (
    GameMemoryTextBuilder,
)
from app.game.domain.entities import GameMessageEntity
from app.game.domain.value_objects import GameState
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
        conversation_history: list[GameMessageEntity],
        recalled_memories: list[GameMessageEntity],
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
                    recalled_memories=recalled_memories,
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
        recalled_memories: list[GameMessageEntity],
    ) -> str:
        """현재 턴 payload를 user message 형식으로 만든다."""
        sections = [
            "## 현재 플레이어 행동",
            player_action,
        ]

        if recalled_memories:
            memory_lines = [
                f"- {GameMemoryTextBuilder.build_message_memory_text(message)}"
                for message in recalled_memories
            ]
            sections.extend(
                [
                    "",
                    "## 참고 기억",
                    "\n".join(memory_lines),
                ]
            )

        sections.extend(
            [
                "",
                "현재 행동을 중심으로 JSON 형식의 게임 마스터 응답을 생성하세요.",
            ]
        )

        return "\n".join(sections).strip()

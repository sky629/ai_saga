"""Game Master prompt templates for AI MUD game.

Contains system prompts and action prompts for the LLM game master.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.game.domain.value_objects import GameState

SYSTEM_PROMPT_TEMPLATE = """당신은 텍스트 기반 MUD 게임의 게임 마스터(Game Master)입니다.

## 시나리오
- 시나리오 이름: {scenario_name}
- 세계관: {world_setting}

## 캐릭터 정보
- 이름: {character_name}
- 설명: {character_description}

## 현재 게임 상태
- 위치: {current_location}
{game_state_section}

## 당신의 역할
1. 플레이어의 행동에 대해 생생하고 몰입감 있는 서술을 제공합니다.
2. 세계관에 맞는 일관된 반응을 생성합니다.
3. 플레이어의 선택에 따른 결과를 공정하게 판정합니다.
4. 때로는 예상치 못한 이벤트를 발생시켜 게임을 흥미롭게 만듭니다.

## 응답 규칙
- 응답은 한국어로 작성합니다.
- 2인칭 시점("당신은...")으로 서술합니다.
- 플레이어에게 2-3개의 선택지를 제안합니다.
- 응답은 다음 JSON 형식을 따릅니다:

```json
{{
  "narrative": "상황 서술 텍스트",
  "options": ["선택지1", "선택지2", "선택지3"],
  "state_changes": {{
    "hp_change": 0,
    "items_gained": [],
    "items_lost": [],
    "location": "현재 위치 (변경 시에만)",
    "npcs_met": [],
    "discoveries": []
  }}
}}
```

**중요**: state_changes는 변경사항만 포함합니다. 예를 들어 location은 새로운 장소로 이동할 때만 명시하고, 같은 장소에 머무를 때는 생략합니다.
"""

ACTION_PROMPT_TEMPLATE = """## 현재 상황
- 캐릭터: {character_name}
- 위치: {current_location}
{inventory_section}

## 플레이어 행동
{player_action}

위 행동에 대한 게임 마스터 응답을 생성해주세요.
"""


def build_system_prompt(
    scenario_name: str,
    world_setting: str,
    character_name: str,
    character_description: str,
    current_location: str = "",
    game_state_section: str = "",
) -> str:
    """Build the system prompt for the game master.

    Args:
        scenario_name: Name of the current scenario.
        world_setting: Description of the world setting.
        character_name: Name of the character.
        character_description: Description of the character.
        current_location: Current location in the game.
        game_state_section: Formatted game state information.

    Returns:
        Formatted system prompt string.
    """
    return SYSTEM_PROMPT_TEMPLATE.format(
        scenario_name=scenario_name,
        world_setting=world_setting,
        character_name=character_name,
        character_description=character_description,
        current_location=current_location,
        game_state_section=game_state_section,
    )


def build_action_prompt(
    player_action: str,
    character_name: str,
    current_location: str,
    inventory: Optional[list[str]] = None,
) -> str:
    """Build the action prompt for player actions.

    Args:
        player_action: The action the player wants to take.
        character_name: Name of the player's character.
        current_location: Current location in the game world.
        inventory: Optional list of items the character has.

    Returns:
        Formatted action prompt string.
    """
    inventory_section = ""
    if inventory:
        inventory_str = ", ".join(inventory)
        inventory_section = f"- 인벤토리: {inventory_str}"

    return ACTION_PROMPT_TEMPLATE.format(
        character_name=character_name,
        current_location=current_location,
        inventory_section=inventory_section,
        player_action=player_action,
    )


@dataclass
class GameMasterPrompt:
    """Data class for game master prompt configuration.

    Automatically generates system prompt from scenario settings.
    """

    scenario_name: str
    world_setting: str
    character_name: str
    current_location: str
    character_description: str = ""
    recent_events: str = ""
    inventory: list[str] = field(default_factory=list)
    game_state: Optional["GameState"] = None

    @property
    def system_prompt(self) -> str:
        """Generate system prompt from scenario settings."""
        game_state_section = (
            self._format_game_state() if self.game_state else ""
        )

        return build_system_prompt(
            scenario_name=self.scenario_name,
            world_setting=self.world_setting,
            character_name=self.character_name,
            character_description=self.character_description,
            current_location=self.current_location,
            game_state_section=game_state_section,
        )

    def _format_game_state(self) -> str:
        """Format game state for inclusion in prompt.

        Returns:
            Formatted game state string with inventory, visited locations, NPCs, and discoveries.
        """
        if not self.game_state:
            return "- (아직 수집한 정보 없음)"

        lines = []

        if self.game_state.items:
            lines.append(f"- 인벤토리: {', '.join(self.game_state.items)}")
        if self.game_state.visited_locations:
            # Show only last 5 locations to keep prompt manageable
            recent_locations = self.game_state.visited_locations[-5:]
            lines.append(f"- 방문한 장소: {', '.join(recent_locations)}")
        if self.game_state.met_npcs:
            lines.append(f"- 만난 NPC: {', '.join(self.game_state.met_npcs)}")
        if self.game_state.discoveries:
            lines.append(
                f"- 발견한 것: {', '.join(self.game_state.discoveries)}"
            )

        return "\n".join(lines) if lines else "- (아직 수집한 정보 없음)"

    def build_action(self, player_action: str) -> str:
        """Build action prompt for a specific player action."""
        return build_action_prompt(
            player_action=player_action,
            character_name=self.character_name,
            current_location=self.current_location,
            inventory=self.inventory,
        )

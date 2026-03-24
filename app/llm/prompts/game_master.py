"""Game Master prompt templates for AI MUD game.

Contains system prompts and action prompts for the LLM game master.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.game.domain.value_objects import DiceResult, GameState

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
{dice_result_block}

## 당신의 역할
1. 플레이어의 행동에 대해 생생하고 몰입감 있는 서술을 제공합니다.
2. 세계관에 맞는 일관된 반응을 생성합니다.
3. 플레이어의 선택에 따른 결과를 공정하게 판정합니다.
4. 때로는 예상치 못한 이벤트를 발생시켜 게임을 흥미롭게 만듭니다.

## 응답 규칙
- 응답은 한국어로 작성합니다.
- 2인칭 시점("당신은...")으로 서술합니다.
- 플레이어에게 2-3개의 선택지를 제안합니다.
- 주사위 판정 결과가 있는 경우, 결과에 따라 서술해야 합니다.
  - 성공 판정 시: 플레이어의 행동이 성공하는 서술
  - 실패 판정 시: 플레이어의 행동이 실패하거나 일부만 통하는 서술
  - 크리티컬(대성공) 시: 극적으로 성공하는 서술
  - 펌블(대실패) 시: 상황이 악화되는 서술
- **주사위 판정 결과는 절대적입니다. 이미 나온 결과를 절대 뒤집지 마세요.**
- **현재 인벤토리나 게임 상태에 없는 무기, 도구, 아이템을 플레이어가 이미 가지고 있는 것처럼 임의로 서술하지 마세요.**
- **인벤토리에 없는 장비가 필요하면 맨손, 주변 환경, 즉흥적인 행동으로 묘사하세요.**
- **실패 판정이어도 서술은 풍부하고 구체적으로 유지하세요. 단, 성공이 확정된 것처럼 묘사하지 마세요.**
- **실패 판정에서는 긴장 고조, 부분적 손상, 불완전한 반응, 새로운 단서 노출 같은 결과는 가능하지만, 성공 보상이나 확정적 돌파는 묘사하지 마세요.**
- dice_applied는 이 행동에 주사위 판정이 적용되는지 나타냅니다.
  - 전투, 위험한 행동, 기술 사용, 잠입, 탈출 등 불확실한 행동 → dice_applied: true
  - 단순 이동, 대화, 관찰, 휴식 등 일상적 행동 → dice_applied: false
  - dice_applied가 true인 경우, 반드시 위 주사위 판정 결과에 따라 서술하세요.
  응답은 다음 JSON 형식을 따릅니다:

```json
{{
  "before_narrative": "주사위를 굴리기 전의 준비 상황 묘사 (dice_applied가 true일 때만)",
  "narrative": "주사위 결과를 반영한 최종 상황 서술 텍스트",
  "options": [
    {{
      "label": "선택지1",
      "action_type": "movement"
    }},
    {{
      "label": "선택지2",
      "action_type": "social"
    }}
  ],
  "dice_applied": false,
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
### before_narrative와 narrative 작성 규칙:
- **dice_applied가 true인 경우**:
  - `before_narrative`: 주사위를 굴리기 직전의 긴장감 있는 상황 묘사. 아직 결과가 드러나면 안 됩니다.
  - `narrative`: 주사위 판정 결과를 반영한 행동의 결과 서술.
  - `before_narrative`와 `narrative`는 같은 문장을 반복하지 마세요.
  - `before_narrative`에는 충돌 직전, 망설임, 자세, 숨 고르기, 주변 반응 등 결과 이전의 정보만 넣으세요.
  - `narrative`에는 결과가 드러난 뒤 변화, 손상, 성공/실패의 여파만 넣으세요.
- **dice_applied가 false인 경우**:
  - `before_narrative`: 생략 (포함하지 마세요)
  - `narrative`: 일반적인 상황 서술을 작성합니다.
- `options[].action_type`은 반드시 다음 중 하나를 사용합니다:
  - `combat`, `social`, `skill`, `movement`, `observation`, `rest`, `exploration`
**중요**: state_changes는 변경사항만 포함합니다. 예를 들어 location은 새로운 장소로 이동할 때만 명시하고, 같은 장소에 머무를 때는 생략합니다.
"""


def build_dice_result_section(dice_result: "DiceResult") -> str:
    """Format dice result for inclusion in prompt.

    Args:
        dice_result: The dice result to format.

    Returns:
        Formatted dice result string for the prompt.
    """
    return dice_result.display_text


def build_system_prompt(
    scenario_name: str,
    world_setting: str,
    character_name: str,
    character_description: str,
    current_location: str = "",
    game_state_section: str = "",
    dice_result_section: str = "",
) -> str:
    """Build the system prompt for the game master.

    Args:
        scenario_name: Name of the current scenario.
        world_setting: Description of the world setting.
        character_name: Name of the character.
        character_description: Description of the character.
        current_location: Current location in the game.
        game_state_section: Formatted game state information.
        dice_result_section: Formatted dice result information.

    Returns:
        Formatted system prompt string.
    """
    dice_result_block = ""
    if dice_result_section:
        dice_result_block = (
            "\n## 주사위 판정 결과\n" f"{dice_result_section}\n"
        )

    return SYSTEM_PROMPT_TEMPLATE.format(
        scenario_name=scenario_name,
        world_setting=world_setting,
        character_name=character_name,
        character_description=character_description,
        current_location=current_location,
        game_state_section=game_state_section,
        dice_result_block=dice_result_block,
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
    inventory: list[str] = field(default_factory=list)
    game_state: Optional["GameState"] = None
    dice_result_section: str = ""

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
            dice_result_section=self.dice_result_section,
        )

    def _format_game_state(self) -> str:
        """Format game state for inclusion in prompt.

        Returns:
            Formatted game state string with inventory, visited locations, NPCs, and discoveries.
        """
        if not self.game_state:
            return "- (아직 수집한 정보 없음)"

        lines = []

        inventory_items = self.game_state.items
        if self.inventory:
            inventory_items = list(
                dict.fromkeys([*self.inventory, *inventory_items])
            )

        if inventory_items:
            lines.append(f"- 인벤토리: {', '.join(inventory_items)}")
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

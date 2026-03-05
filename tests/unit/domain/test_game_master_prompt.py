"""Unit tests for Game Master prompt templates."""

from app.game.domain.value_objects import DiceCheckType, DiceResult
from app.llm.prompts.game_master import (
    GameMasterPrompt,
    build_dice_result_section,
    build_system_prompt,
)


class TestBuildDiceResultSection:
    """Tests for build_dice_result_section helper function."""

    def test_build_dice_result_section_success(self):
        """Test dice result section for successful roll."""
        result = DiceResult(
            roll=15,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.COMBAT,
        )
        section = build_dice_result_section(result)
        assert "🎲" in section
        assert "성공!" in section
        assert "1d20+2" in section

    def test_build_dice_result_section_failure(self):
        """Test dice result section for failed roll."""
        result = DiceResult(
            roll=5,
            modifier=2,
            dc=12,
            check_type=DiceCheckType.SKILL,
        )
        section = build_dice_result_section(result)
        assert "🎲" in section
        assert "실패..." in section

    def test_build_dice_result_section_critical(self):
        """Test dice result section for critical success."""
        result = DiceResult(
            roll=20,
            modifier=0,
            dc=10,
            check_type=DiceCheckType.COMBAT,
        )
        section = build_dice_result_section(result)
        assert "대성공!" in section

    def test_build_dice_result_section_fumble(self):
        """Test dice result section for fumble."""
        result = DiceResult(
            roll=1,
            modifier=5,
            dc=10,
            check_type=DiceCheckType.SOCIAL,
        )
        section = build_dice_result_section(result)
        assert "대실패!" in section

    def test_build_dice_result_section_returns_display_text(self):
        """Test that build_dice_result_section returns display_text."""
        result = DiceResult(
            roll=12,
            modifier=1,
            dc=11,
            check_type=DiceCheckType.EXPLORATION,
        )
        section = build_dice_result_section(result)
        assert section == result.display_text


class TestBuildSystemPrompt:
    """Tests for build_system_prompt function."""

    def test_build_system_prompt_basic(self):
        """Test system prompt generation with basic parameters."""
        prompt = build_system_prompt(
            scenario_name="던전 탐험",
            world_setting="판타지 세계",
            character_name="용사",
            character_description="용감한 전사",
        )
        assert "던전 탐험" in prompt
        assert "판타지 세계" in prompt
        assert "용사" in prompt
        assert "용감한 전사" in prompt

    def test_build_system_prompt_with_game_state(self):
        """Test system prompt includes game state section."""
        prompt = build_system_prompt(
            scenario_name="던전",
            world_setting="세계",
            character_name="캐릭터",
            character_description="설명",
            game_state_section="- 인벤토리: 검, 방패",
        )
        assert "- 인벤토리: 검, 방패" in prompt

    def test_build_system_prompt_with_dice_result(self):
        """Test system prompt includes dice result section."""
        dice_result = DiceResult(
            roll=18,
            modifier=2,
            dc=15,
            check_type=DiceCheckType.COMBAT,
        )
        dice_section = build_dice_result_section(dice_result)
        prompt = build_system_prompt(
            scenario_name="전투",
            world_setting="세계",
            character_name="전사",
            character_description="강한",
            dice_result_section=dice_section,
        )
        assert "## 주사위 판정 결과" in prompt
        assert "🎲" in prompt
        assert "성공!" in prompt
        assert "이미 나온 결과를 절대 뒤집지 마세요" in prompt

    def test_build_system_prompt_includes_dice_rules(self):
        """Test system prompt includes dice judgment rules."""
        prompt = build_system_prompt(
            scenario_name="테스트",
            world_setting="테스트",
            character_name="테스트",
            character_description="테스트",
        )
        assert "주사위 판정 결과가 있는 경우" in prompt
        assert "성공 판정 시" in prompt
        assert "실패 판정 시" in prompt
        assert "크리티컬(대성공)" in prompt
        assert "펌블(대실패)" in prompt
        assert "이미 나온 결과를 절대 뒤집지 마세요" in prompt

    def test_build_system_prompt_empty_dice_section(self):
        """Test system prompt with empty dice result section."""
        prompt = build_system_prompt(
            scenario_name="테스트",
            world_setting="테스트",
            character_name="테스트",
            character_description="테스트",
            dice_result_section="",
        )
        assert "## 주사위 판정 결과" not in prompt

    def test_system_prompt_keeps_original_json_schema(self):
        """Test system prompt JSON format keeps original schema fields."""
        prompt = build_system_prompt(
            scenario_name="test",
            world_setting="test",
            character_name="test",
            character_description="test",
        )
        assert '"narrative"' in prompt
        assert '"options"' in prompt
        assert '"state_changes"' in prompt
        assert "before_narrative" not in prompt
        assert "dice_applied" not in prompt


class TestGameMasterPrompt:
    """Tests for GameMasterPrompt dataclass."""

    def test_action_prompt_contains_dice_result(self):
        """Test action prompt includes dice result section when provided."""
        from app.llm.prompts.game_master import build_action_prompt

        result = build_action_prompt(
            player_action="건물 밖으로 나간다",
            character_name="용사",
            current_location="건물 안",
            dice_result_section="🎲 1d20+2 = 8 vs DC 12 → 실패...",
        )
        assert "🎲 1d20+2 = 8 vs DC 12 → 실패..." in result

    def test_action_prompt_without_dice_result(self):
        """Test action prompt handles missing dice result gracefully."""
        from app.llm.prompts.game_master import build_action_prompt

        result = build_action_prompt(
            player_action="대화한다",
            character_name="용사",
            current_location="마을",
        )
        assert "용사" in result
        assert "대화한다" in result

    def test_game_master_prompt_creation(self):
        """Test GameMasterPrompt can be created with basic fields."""
        prompt = GameMasterPrompt(
            scenario_name="던전",
            world_setting="판타지",
            character_name="용사",
            current_location="입구",
        )
        assert prompt.scenario_name == "던전"
        assert prompt.world_setting == "판타지"
        assert prompt.character_name == "용사"
        assert prompt.current_location == "입구"

    def test_game_master_prompt_default_dice_result_section(self):
        """Test dice_result_section defaults to empty string."""
        prompt = GameMasterPrompt(
            scenario_name="던전",
            world_setting="판타지",
            character_name="용사",
            current_location="입구",
        )
        assert prompt.dice_result_section == ""

    def test_game_master_prompt_with_dice_result_section(self):
        """Test GameMasterPrompt can be created with dice result."""
        dice_result = DiceResult(
            roll=16,
            modifier=1,
            dc=14,
            check_type=DiceCheckType.COMBAT,
        )
        dice_section = build_dice_result_section(dice_result)
        prompt = GameMasterPrompt(
            scenario_name="전투",
            world_setting="판타지",
            character_name="전사",
            current_location="전장",
            dice_result_section=dice_section,
        )
        assert prompt.dice_result_section == dice_section
        assert "성공!" in prompt.dice_result_section

    def test_game_master_prompt_system_prompt_includes_dice(self):
        """Test system_prompt property includes dice result section."""
        dice_result = DiceResult(
            roll=19,
            modifier=2,
            dc=15,
            check_type=DiceCheckType.SKILL,
        )
        dice_section = build_dice_result_section(dice_result)
        prompt = GameMasterPrompt(
            scenario_name="도둑질",
            world_setting="도시",
            character_name="도둑",
            current_location="금고실",
            dice_result_section=dice_section,
        )
        system_prompt = prompt.system_prompt
        assert "🎲" in system_prompt
        assert "성공!" in system_prompt

    def test_game_master_prompt_system_prompt_empty_dice(self):
        """Test system_prompt with empty dice result section."""
        prompt = GameMasterPrompt(
            scenario_name="탐험",
            world_setting="숲",
            character_name="탐험가",
            current_location="숲길",
        )
        system_prompt = prompt.system_prompt
        assert "## 주사위 판정 결과" not in system_prompt
        assert "탐험" in system_prompt

    def test_game_master_prompt_build_action(self):
        """Test build_action method generates action prompt."""
        prompt = GameMasterPrompt(
            scenario_name="던전",
            world_setting="판타지",
            character_name="용사",
            current_location="방",
            inventory=["검", "방패"],
        )
        action_prompt = prompt.build_action("북쪽으로 이동한다")
        assert "용사" in action_prompt
        assert "방" in action_prompt
        assert "검" in action_prompt
        assert "방패" in action_prompt
        assert "북쪽으로 이동한다" in action_prompt

    def test_game_master_prompt_with_all_fields(self):
        """Test GameMasterPrompt with all fields populated."""
        dice_result = DiceResult(
            roll=17,
            modifier=3,
            dc=16,
            check_type=DiceCheckType.COMBAT,
        )
        dice_section = build_dice_result_section(dice_result)
        prompt = GameMasterPrompt(
            scenario_name="최종 보스",
            world_setting="마왕의 성",
            character_name="영웅",
            current_location="왕좌의 방",
            character_description="전설의 영웅",
            recent_events="보스와 만남",
            inventory=["전설의 검", "불사의 갑옷"],
            dice_result_section=dice_section,
        )
        system_prompt = prompt.system_prompt
        assert "최종 보스" in system_prompt
        assert "마왕의 성" in system_prompt
        assert "영웅" in system_prompt
        assert "전설의 영웅" in system_prompt
        assert "왕좌의 방" in system_prompt
        assert "성공!" in system_prompt

    def test_game_master_prompt_multiple_dice_results(self):
        """Test GameMasterPrompt can be updated with different dice results."""
        prompt = GameMasterPrompt(
            scenario_name="전투",
            world_setting="전장",
            character_name="전사",
            current_location="전투지",
        )

        # First dice result
        result1 = DiceResult(
            roll=20,
            modifier=2,
            dc=15,
            check_type=DiceCheckType.COMBAT,
        )
        prompt.dice_result_section = build_dice_result_section(result1)
        assert "대성공!" in prompt.system_prompt

        # Second dice result
        result2 = DiceResult(
            roll=1,
            modifier=2,
            dc=15,
            check_type=DiceCheckType.COMBAT,
        )
        prompt.dice_result_section = build_dice_result_section(result2)
        assert "대실패!" in prompt.system_prompt

    def test_game_master_prompt_dice_result_section_in_prompt(self):
        """Test dice result section appears in correct location in prompt."""
        dice_result = DiceResult(
            roll=14,
            modifier=1,
            dc=12,
            check_type=DiceCheckType.SKILL,
        )
        dice_section = build_dice_result_section(dice_result)
        prompt = GameMasterPrompt(
            scenario_name="스킬 체크",
            world_setting="세계",
            character_name="캐릭터",
            current_location="위치",
            dice_result_section=dice_section,
        )
        system_prompt = prompt.system_prompt
        # Verify dice section appears before response rules
        dice_index = system_prompt.find("## 주사위 판정 결과")
        rules_index = system_prompt.find("## 응답 규칙")
        assert dice_index < rules_index
        assert dice_index != -1

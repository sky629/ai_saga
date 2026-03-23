"""Tests for Game Master Prompt Templates - TDD RED Phase."""

from app.game.domain.value_objects import GameState
from app.llm.prompts.game_master import GameMasterPrompt, build_system_prompt


class TestGameMasterPrompt:
    """TDD tests for game master prompt templates."""

    def test_build_system_prompt_contains_role(self):
        """System prompt should define the game master role."""
        prompt = build_system_prompt(
            scenario_name="던전 탐험",
            world_setting="중세 판타지 세계",
            character_name="테스트 영웅",
            character_description="용감한 전사",
        )

        assert "게임 마스터" in prompt or "Game Master" in prompt
        assert "던전 탐험" in prompt
        assert "중세 판타지 세계" in prompt

    def test_build_system_prompt_includes_rules(self):
        """System prompt should include game rules."""
        prompt = build_system_prompt(
            scenario_name="마법사의 탑",
            world_setting="마법이 존재하는 세계",
            character_name="테스트 영웅",
            character_description="용감한 전사",
        )

        # Should include response format rules
        assert "JSON" in prompt or "응답" in prompt

    def test_game_master_prompt_dataclass(self):
        """GameMasterPrompt should be a proper dataclass."""
        prompt_data = GameMasterPrompt(
            scenario_name="드래곤 슬레이어",
            world_setting="용이 지배하는 세계",
            character_name="드래곤 헌터",
            current_location="용의 둥지 입구",
        )

        assert prompt_data.scenario_name == "드래곤 슬레이어"
        assert prompt_data.system_prompt is not None
        assert len(prompt_data.system_prompt) > 100

    def test_prompt_handles_korean_properly(self):
        """Prompts should handle Korean text correctly."""
        prompt = build_system_prompt(
            scenario_name="한글 시나리오 테스트",
            world_setting="한글로 된 세계관 설정입니다.",
            character_name="테스트 영웅",
            character_description="용감한 전사",
        )

        # Should not have encoding issues
        assert "한글" in prompt
        assert len(prompt) > 0

    def test_game_master_prompt_with_game_state(self):
        """GameMasterPrompt should include game state in system prompt."""
        game_state = GameState(
            items=["sword", "torch"],
            visited_locations=["start", "forest"],
            met_npcs=["wizard"],
            discoveries=["secret_door"],
        )

        prompt_data = GameMasterPrompt(
            scenario_name="던전 탐험",
            world_setting="중세 판타지",
            character_name="영웅",
            current_location="forest",
            game_state=game_state,
        )

        system_prompt = prompt_data.system_prompt

        assert "sword" in system_prompt
        assert "torch" in system_prompt
        assert "wizard" in system_prompt
        assert "secret_door" in system_prompt

    def test_game_master_prompt_without_game_state(self):
        """GameMasterPrompt should work without game state."""
        prompt_data = GameMasterPrompt(
            scenario_name="던전 탐험",
            world_setting="중세 판타지",
            character_name="영웅",
            current_location="start",
        )

        system_prompt = prompt_data.system_prompt

        assert "던전 탐험" in system_prompt
        assert len(system_prompt) > 100

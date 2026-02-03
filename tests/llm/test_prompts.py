"""Tests for Game Master Prompt Templates - TDD RED Phase."""

import pytest

from app.llm.prompts.game_master import (
    GameMasterPrompt,
    build_system_prompt,
    build_action_prompt,
)


class TestGameMasterPrompt:
    """TDD tests for game master prompt templates."""

    def test_build_system_prompt_contains_role(self):
        """System prompt should define the game master role."""
        prompt = build_system_prompt(
            scenario_name="던전 탐험",
            world_setting="중세 판타지 세계",
        )
        
        assert "게임 마스터" in prompt or "Game Master" in prompt
        assert "던전 탐험" in prompt
        assert "중세 판타지 세계" in prompt

    def test_build_system_prompt_includes_rules(self):
        """System prompt should include game rules."""
        prompt = build_system_prompt(
            scenario_name="마법사의 탑",
            world_setting="마법이 존재하는 세계",
        )
        
        # Should include response format rules
        assert "JSON" in prompt or "응답" in prompt

    def test_build_action_prompt_with_player_action(self):
        """Action prompt should format player's action."""
        prompt = build_action_prompt(
            player_action="북쪽으로 이동한다",
            character_name="용사 김철수",
            current_location="마을 광장",
        )
        
        assert "북쪽으로 이동" in prompt
        assert "용사 김철수" in prompt or "김철수" in prompt

    def test_build_action_prompt_with_inventory(self):
        """Action prompt should include character state."""
        prompt = build_action_prompt(
            player_action="검을 휘두른다",
            character_name="전사",
            current_location="동굴",
            inventory=["철검", "가죽 갑옷", "치료 물약"],
        )
        
        assert "철검" in prompt
        assert "동굴" in prompt

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
        )
        
        # Should not have encoding issues
        assert "한글" in prompt
        assert len(prompt) > 0

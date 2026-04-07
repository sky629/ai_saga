"""Progression 게임 프롬프트 단위 테스트."""

from app.llm.prompts.progression_game_master import (
    build_progression_turn_prompt,
)


def test_progression_turn_prompt_requires_unique_manual_names():
    system_prompt, _ = build_progression_turn_prompt(
        scenario_name="기연 일지",
        world_setting="절벽 아래 신비한 동굴에서 수련한다.",
        character_name="연우",
        character_description="가벼운 체구의 젊은 무인",
        current_location="청색광이 감도는 거대 동굴",
        turn_count=3,
        max_turns=12,
        status_panel={
            "remaining_turns": 9,
            "hp": 100,
            "max_hp": 100,
            "internal_power": 10,
            "external_power": 12,
            "manuals": [],
            "escape_status": "아직 멀다",
        },
        player_action="한 달 동안 광맥 주변을 탐색한다",
        conversation_history=[],
        will_be_final_turn=False,
    )

    assert "고유한 무협식 이름" in system_prompt
    assert "내공 심법" in system_prompt
    assert "고적 기초 내공심법" in system_prompt
    assert "청광심법" in system_prompt
    assert "현무금강체" in system_prompt
    assert "낙영보" in system_prompt


def test_progression_turn_prompt_requires_manual_name_consistency():
    system_prompt, _ = build_progression_turn_prompt(
        scenario_name="기연 일지",
        world_setting="절벽 아래 신비한 동굴에서 수련한다.",
        character_name="연우",
        character_description="가벼운 체구의 젊은 무인",
        current_location="청색광이 감도는 거대 동굴",
        turn_count=3,
        max_turns=12,
        status_panel={
            "remaining_turns": 9,
            "hp": 100,
            "max_hp": 100,
            "internal_power": 10,
            "external_power": 12,
            "manuals": [],
            "escape_status": "아직 멀다",
        },
        player_action="한 달 동안 광맥 주변을 탐색한다",
        conversation_history=[],
        will_be_final_turn=False,
    )

    assert "narrative에 등장한 같은 이름" in system_prompt
    assert (
        "`state_changes.manuals_gained`에도 그대로 넣으세요" in system_prompt
    )

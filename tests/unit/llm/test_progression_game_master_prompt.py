"""Progression 게임 프롬프트 단위 테스트."""

from app.llm.prompts.progression_game_master import (
    build_progression_ending_prompt,
    build_progression_opening_prompt,
    build_progression_title_prompt,
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
        scenario_genre="wuxia",
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
        scenario_genre="wuxia",
    )

    assert "narrative에 등장한 같은 이름" in system_prompt
    assert (
        "`state_changes.manuals_gained`에도 그대로 넣으세요" in system_prompt
    )


def test_progression_turn_prompt_uses_genre_specific_wuxia_rules_only_for_wuxia():
    system_prompt, _ = build_progression_turn_prompt(
        scenario_name="생존 기록",
        world_setting="감염체가 배회하는 폐허 도시에서 버틴다.",
        character_name="하윤",
        character_description="응급 구조 교육을 받은 생존자",
        current_location="폐허 병원",
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
        player_action="한 달 동안 의약품을 찾는다",
        conversation_history=[],
        will_be_final_turn=False,
        scenario_genre="survival",
    )

    assert "무협 성장형" not in system_prompt
    assert "고유한 무협식 이름" not in system_prompt
    assert "중국 무협 애니메이션" not in system_prompt
    assert "폭포수 아래 명상" not in system_prompt
    assert "시나리오 장르와 세계관 분위기" in system_prompt


def test_progression_opening_prompt_uses_genre_specific_atmosphere():
    prompt = build_progression_opening_prompt(
        scenario_name="생존 기록",
        world_setting="폐허 도시",
        character_name="하윤",
        character_description="생존자",
        current_location="폐허 병원",
        max_turns=12,
        scenario_genre="survival",
    )

    assert "무협 성장형" not in prompt
    assert "무협, 기연, 수련" not in prompt
    assert "동굴 벽면" not in prompt
    assert "청색 광맥" not in prompt
    assert "시나리오 장르와 세계관 분위기" in prompt


def test_progression_ending_and_title_prompts_use_genre_specific_role():
    achievement_board = {
        "title": "생존자",
        "total_score": 50,
        "internal_power": 10,
        "external_power": 12,
        "manuals": [],
    }

    ending_prompt = build_progression_ending_prompt(
        scenario_name="생존 기록",
        world_setting="폐허 도시",
        character_name="하윤",
        ending_type="victory",
        achievement_board=achievement_board,
        cause="escaped",
        scenario_genre="survival",
    )
    title_prompt = build_progression_title_prompt(
        scenario_name="생존 기록",
        world_setting="폐허 도시",
        character_name="하윤",
        ending_type="victory",
        achievement_board=achievement_board,
        scenario_genre="survival",
    )

    assert "무협 성장형" not in ending_prompt
    assert "무협 성장형" not in title_prompt
    assert "성장형 텍스트 게임" in ending_prompt
    assert "성장형 텍스트 게임" in title_prompt

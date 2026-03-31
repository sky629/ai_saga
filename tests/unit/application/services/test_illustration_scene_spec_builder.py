"""IllustrationSceneSpecBuilder 단위 테스트."""

from app.game.application.services.illustration_prompt_builder import (
    IllustrationPromptContext,
)
from app.game.application.services.illustration_scene_spec_builder import (
    IllustrationSceneSpecBuilder,
)


class TestIllustrationSceneSpecBuilder:
    """장면 추출 규칙을 검증한다."""

    def test_build_extracts_counter_scene_with_exact_cast_and_props(self):
        context = IllustrationPromptContext(
            scene_narrative=(
                "당신은 길드 카운터로 다가가 묵묵히 잔을 닦고 있는 "
                "뚱뚱한 주점 주인 앞에 섭니다. 낡은 나무 카운터는 "
                "세월의 흔적으로 반질반질하며, 그 위로 흐릿한 촛불이 "
                "어른거립니다. 그는 기름때 낀 앞치마를 매만지며 "
                "거친 목소리로 중얼거립니다."
            ),
            character_name="호호",
            current_location="하늘빛 마을 - 모험가 길드 앞",
        )

        spec = IllustrationSceneSpecBuilder.build(context)

        assert spec.location == "guild counter interior"
        assert spec.visible_character_count == 2
        assert spec.other_visible_figures == (
            "one tavern keeper behind the guild counter",
        )
        assert "worn wooden counter" in spec.required_props
        assert "flickering candlelight" in spec.required_props
        assert "greasy apron" in spec.required_props

    def test_build_uses_current_location_when_narrative_is_generic(self):
        context = IllustrationPromptContext(
            scene_narrative="당신은 숨을 고르며 주변을 살핀다.",
            character_name="민준",
            current_location="서울 외곽 - 폐건물 2층",
        )

        spec = IllustrationSceneSpecBuilder.build(context)

        assert spec.location == "서울 외곽 - 폐건물 2층"
        assert spec.visible_character_count == 1

    def test_build_prioritizes_state_changes_over_narrative(self):
        context = IllustrationPromptContext(
            scene_narrative="당신은 숲 속에서 숨을 고르며 주변을 살핀다.",
            character_name="민준",
            current_location="숲 속",
            state_changes={
                "location": "서울역 지하 통로",
                "npcs_met": ["하윤"],
                "discoveries": ["깨진 비상 방송 장치"],
                "items_gained": ["신호탄 권총"],
                "items_lost": ["빈 생수병"],
            },
        )

        spec = IllustrationSceneSpecBuilder.build(context)

        assert spec.location == "서울역 지하 통로"
        assert "named NPC present: 하윤" in spec.other_visible_figures
        assert "discovered clue: 깨진 비상 방송 장치" in spec.required_props
        assert "newly acquired item: 신호탄 권총" in spec.required_props
        assert "recently lost item: 빈 생수병" in spec.required_props
        assert "Confirmed location: 서울역 지하 통로" in spec.state_fact_lines
        assert spec.visible_character_count == 2

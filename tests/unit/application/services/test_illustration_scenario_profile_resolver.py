"""IllustrationScenarioProfileResolver 단위 테스트."""

from app.game.application.services.illustration_prompt_builder import (
    IllustrationPromptContext,
)
from app.game.application.services.illustration_scenario_profile_resolver import (
    IllustrationScenarioProfileResolver,
)


class TestIllustrationScenarioProfileResolver:
    """시나리오 비주얼 프로필 해석 규칙을 검증한다."""

    def test_resolve_defaults_to_fantasy_profile_without_genre(self):
        context = IllustrationPromptContext(
            scene_narrative="고블린이 성벽 위로 기어오른다.",
        )

        profile = IllustrationScenarioProfileResolver.resolve(context)

        assert "cinematic Korean fantasy illustration" in profile.opening_line
        assert (
            profile.world_guidance
            == "Keep the world grounded in medieval fantasy."
        )

    def test_resolve_zombie_apocalypse_profile_from_survival_context(self):
        context = IllustrationPromptContext(
            scene_narrative=(
                "서울 외곽의 폐건물 2층에서 당신은 창밖의 신음 소리를 "
                "확인한다."
            ),
            current_location="서울 외곽 - 폐건물 2층",
            scenario_name="좀비 아포칼립스",
            scenario_genre="survival",
            scenario_world_setting=(
                "폐허가 된 서울에서 생존자와 좀비가 뒤엉킨다. "
                "감염체는 소리와 움직임, 피 냄새에 민감하다."
            ),
            scenario_tags=("좀비", "아포칼립스", "서울"),
        )

        profile = IllustrationScenarioProfileResolver.resolve(context)

        assert (
            "gritty cinematic post-apocalyptic survival illustration"
            in profile.opening_line
        )
        assert any(
            "zombie apocalypse in ruined modern Seoul" in line
            for line in profile.anchor_lines
        )
        assert any("Joseon-era" in line for line in profile.negative_guidance)

    def test_resolve_accepts_scifi_alias(self):
        context = IllustrationPromptContext(
            scene_narrative="우주 정거장 외벽에서 경비 드론이 추격한다.",
            scenario_genre="sci-fi",
        )

        profile = IllustrationScenarioProfileResolver.resolve(context)

        assert profile.world_guidance == "Keep the world grounded in sci-fi."

    def test_resolve_trpg_does_not_apply_wuxia_anchor_from_keywords(self):
        context = IllustrationPromptContext(
            scene_narrative="수련받은 마법사가 고대 비급을 조사한다.",
            scenario_game_type="trpg",
            scenario_name="용사의 여정",
            scenario_genre="fantasy",
            scenario_world_setting="검과 마법이 공존하는 왕국 모험.",
            scenario_tags=("판타지", "모험", "수련"),
        )

        profile = IllustrationScenarioProfileResolver.resolve(context)

        assert any(
            "TRPG adventure scene" in line for line in profile.game_type_lines
        )
        assert not any(
            "wuxia" in line.lower() for line in profile.anchor_lines
        )
        assert not any(
            "Chinese martial arts" in line for line in profile.anchor_lines
        )

    def test_resolve_progression_survival_does_not_apply_wuxia_detail(self):
        context = IllustrationPromptContext(
            scene_narrative="폐허 도시에서 한 달 동안 식량과 약품을 모은다.",
            scenario_game_type="progression",
            scenario_name="생존 기록",
            scenario_genre="survival",
            scenario_world_setting="감염체가 배회하는 폐허 도시.",
            scenario_tags=("생존", "아포칼립스", "성장"),
        )

        profile = IllustrationScenarioProfileResolver.resolve(context)

        assert any(
            "progression growth scene" in line
            for line in profile.game_type_lines
        )
        assert not any(
            "wuxia" in line.lower() for line in profile.game_type_lines
        )
        assert not any(
            "wuxia" in line.lower() for line in profile.anchor_lines
        )

    def test_resolve_wuxia_genre_applies_wuxia_visual_detail(self):
        context = IllustrationPromptContext(
            scene_narrative="청색 광맥 앞에서 심법 수련을 시작한다.",
            scenario_game_type="progression",
            scenario_name="기연 일지",
            scenario_genre="wuxia",
            scenario_world_setting="절벽 아래 동굴에서 무공을 수련한다.",
            scenario_tags=("무협", "수련", "기연"),
        )

        profile = IllustrationScenarioProfileResolver.resolve(context)

        assert any(
            "progression growth scene" in line
            for line in profile.game_type_lines
        )
        assert not any(
            "wuxia" in line.lower() for line in profile.game_type_lines
        )
        assert any("wuxia" in line.lower() for line in profile.anchor_lines)

    def test_resolve_missing_game_type_uses_generic_game_detail(self):
        context = IllustrationPromptContext(
            scene_narrative="모험가가 수련장에서 검을 점검한다.",
            scenario_genre="fantasy",
        )

        profile = IllustrationScenarioProfileResolver.resolve(context)

        assert any(
            "scenario-specific game scene" in line
            for line in profile.game_type_lines
        )
        assert not any(
            "TRPG adventure scene" in line for line in profile.game_type_lines
        )

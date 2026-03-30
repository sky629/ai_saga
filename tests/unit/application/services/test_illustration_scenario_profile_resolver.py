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

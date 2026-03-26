"""IllustrationPromptBuilder 단위 테스트."""

from app.game.application.services.illustration_prompt_builder import (
    IllustrationPromptBuilder,
)


class TestIllustrationPromptBuilder:
    """일러스트 프롬프트 구성 규칙을 검증한다."""

    def test_build_includes_scene_direction_and_negative_constraints(self):
        prompt = IllustrationPromptBuilder.build(
            "고블린이 횃불을 들고 폐허 속에서 영웅에게 달려든다."
        )

        assert "Scene:" in prompt
        assert "고블린이 횃불을 들고 폐허 속에서 영웅에게 달려든다." in prompt
        assert "mood, tension, and immediate situation" in prompt
        assert "Retro 16-bit pixel art" in prompt
        assert (
            "No text, no speech bubbles, no captions, no UI, no HUD" in prompt
        )
        assert "no white margins" in prompt
        assert "framed card-like compositions" in prompt

    def test_build_normalizes_whitespace_and_uses_fallback_scene(self):
        prompt = IllustrationPromptBuilder.build(" \n\t ")

        assert "mysterious fantasy RPG adventure scene" in prompt
        assert "  " not in prompt

    def test_build_requests_story_readability(self):
        prompt = IllustrationPromptBuilder.build(
            "기사단장이 부서진 성문 앞에서 피 묻은 검을 들고 후퇴를 막는다."
        )

        assert "understand this turn's mood" in prompt
        assert (
            "Scene: 기사단장이 부서진 성문 앞에서 피 묻은 검을 들고 후퇴를 막는다."
            in prompt
        )

    def test_build_requires_background_when_implied(self):
        prompt = IllustrationPromptBuilder.build(
            "낡은 여관 앞 좁은 골목에서 검객이 추격자를 노려본다."
        )

        assert "If buildings, streets, interiors, ruins" in prompt
        assert "give the environment meaningful visual weight" in prompt
        assert "Avoid empty ground" in prompt

    def test_build_includes_character_details_and_location_when_provided(self):
        prompt = IllustrationPromptBuilder.build(
            narrative="도적이 좁은 복도 끝에서 횃불을 든 경비병과 마주친다.",
            character_name="실비아",
            character_description=(
                "- 이름: 실비아.\n"
                "- 외형: 검은 단발과 오래된 흉터.\n"
                "- 목표: 실종된 형을 찾는 것."
            ),
            current_location="하수도 감옥 복도",
        )

        assert "The protagonist is 실비아" in prompt
        assert "외형: 검은 단발과 오래된 흉터." in prompt
        assert "The scene takes place at 하수도 감옥 복도." in prompt

    def test_build_requires_clear_role_separation_between_figures(self):
        prompt = IllustrationPromptBuilder.build(
            narrative="젊은 검사가 거대한 기사와 마주 선다.",
            character_name="아론",
        )

        assert "The protagonist is 아론" in prompt
        assert (
            "strong separation between the protagonist and other figures"
            in prompt
        )
        assert "duplicate-looking people" in prompt
        assert "Do not add a crowd" in prompt

    def test_build_includes_lightweight_genre_anchor_when_provided(self):
        prompt = IllustrationPromptBuilder.build(
            narrative="우주 정거장 외벽에서 경비 드론이 추격한다.",
            scenario_genre="sci-fi",
        )

        assert "grounded in a sci-fi setting" in prompt
        assert "avoid unrelated genre elements" in prompt

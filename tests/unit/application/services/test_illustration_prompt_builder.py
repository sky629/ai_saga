"""IllustrationPromptBuilder 단위 테스트."""

from app.game.application.services.illustration_prompt_builder import (
    IllustrationPromptBuilder,
    IllustrationPromptContext,
    IllustrationSceneSpec,
    IllustrationVisualProfile,
)


class TestIllustrationPromptBuilder:
    """일러스트 프롬프트 직렬화 규칙을 검증한다."""

    def test_build_serializes_scene_profile_and_output_constraints(self):
        context = IllustrationPromptContext(
            scene_narrative="고블린이 횃불을 들고 폐허 속에서 영웅에게 달려든다.",
            character_name="실비아",
            character_description="- 외형: 검은 단발과 오래된 흉터.",
            current_location="북쪽 성벽",
            scenario_name="왕국의 몰락",
        )
        scene_spec = IllustrationSceneSpec(
            location="북쪽 성벽",
            visible_character_count=2,
            other_visible_figures=("one goblin attacker",),
            required_props=("lit torch",),
            state_fact_lines=("Confirmed location: 북쪽 성벽",),
            key_visual_beat=context.scene_narrative,
            mood_and_lighting="restrained danger",
        )
        visual_profile = IllustrationVisualProfile(
            opening_line=(
                "Create a cinematic Korean fantasy illustration for a "
                "single story moment."
            ),
            world_guidance="Keep the world grounded in medieval fantasy.",
            anchor_lines=("Scenario context: 왕국의 몰락.",),
            negative_guidance=(
                "Do not introduce modern firearms or ruined city highways.",
            ),
        )

        prompt = IllustrationPromptBuilder.build(
            context=context,
            scene_spec=scene_spec,
            visual_profile=visual_profile,
        )

        assert "cinematic Korean fantasy illustration" in prompt
        assert "Single-panel illustration only." in prompt
        assert "Depict this exact story moment:" in prompt
        assert "No readable text" in prompt
        assert "This must look like a clean illustration" in prompt
        assert "Set the scene at 북쪽 성벽." in prompt
        assert "The main focus is 실비아." in prompt
        assert "Only these additional visible figures appear:" in prompt
        assert "Important visual details: lit torch." in prompt
        assert "These scene facts must stay true:" in prompt
        assert "Scenario context: 왕국의 몰락." in prompt

    def test_build_omits_optional_sections_when_input_is_empty(self):
        context = IllustrationPromptContext(
            scene_narrative="안개가 골목을 덮는다."
        )
        scene_spec = IllustrationSceneSpec(
            location="",
            visible_character_count=1,
            other_visible_figures=(),
            required_props=(),
            state_fact_lines=(),
            key_visual_beat="안개가 골목을 덮는다.",
            mood_and_lighting="restrained story tension",
        )
        visual_profile = IllustrationVisualProfile(
            opening_line=(
                "Create a cinematic Korean fantasy illustration for a "
                "single story moment."
            ),
            world_guidance="Keep the world grounded in medieval fantasy.",
        )

        prompt = IllustrationPromptBuilder.build(
            context=context,
            scene_spec=scene_spec,
            visual_profile=visual_profile,
        )

        assert (
            "Depict this exact story moment: 안개가 골목을 덮는다." in prompt
        )
        assert "Set the scene at" not in prompt
        assert "The main focus is" not in prompt
        assert "Only these additional visible figures appear:" not in prompt
        assert "Important visual details:" not in prompt

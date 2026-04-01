"""일러스트 프롬프트 직렬화 도구."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IllustrationPromptContext:
    """일러스트 생성 입력 컨텍스트."""

    scene_narrative: str
    character_name: str = ""
    character_description: str = ""
    current_location: str = ""
    scenario_name: str = ""
    scenario_game_type: str = ""
    scenario_genre: str = ""
    scenario_world_setting: str = ""
    scenario_tags: tuple[str, ...] = ()
    state_changes: dict | None = None


@dataclass(frozen=True)
class IllustrationSceneSpec:
    """장면 구조화 결과."""

    location: str
    visible_character_count: int
    other_visible_figures: tuple[str, ...]
    required_props: tuple[str, ...]
    state_fact_lines: tuple[str, ...]
    key_visual_beat: str
    mood_and_lighting: str


@dataclass(frozen=True)
class IllustrationVisualProfile:
    """장르/시나리오 기반 비주얼 방향."""

    opening_line: str
    world_guidance: str
    anchor_lines: tuple[str, ...] = ()
    negative_guidance: tuple[str, ...] = ()


class IllustrationPromptBuilder:
    """일러스트 생성 모델에 전달할 최종 프롬프트를 직렬화한다."""

    @staticmethod
    def _normalize_text(value: object, max_length: int) -> str:
        """프롬프트 입력 텍스트를 안전하게 정규화한다."""
        if not isinstance(value, str):
            return ""
        return " ".join(value.split())[:max_length]

    @staticmethod
    def _ensure_terminal_punctuation(value: str) -> str:
        """문장 끝 문장부호를 한 번만 유지한다."""
        if not value:
            return value
        if value.endswith((".", "!", "?")):
            return value
        return f"{value}."

    @classmethod
    def build(
        cls,
        context: IllustrationPromptContext,
        scene_spec: IllustrationSceneSpec,
        visual_profile: IllustrationVisualProfile,
    ) -> str:
        """구조화된 정보를 짧은 장면 지시형 프롬프트로 변환한다."""
        narrative = cls._normalize_text(context.scene_narrative, 500)
        if not narrative:
            narrative = cls._normalize_text(scene_spec.key_visual_beat, 500)
        if not narrative:
            narrative = "mysterious scene"

        normalized_character_name = cls._normalize_text(
            context.character_name, 100
        )
        normalized_character_description = cls._normalize_text(
            context.character_description, 240
        )

        parts = [
            visual_profile.opening_line,
            "Single-panel illustration only.",
            (
                "Depict this exact story moment: "
                + cls._ensure_terminal_punctuation(narrative)
            ),
        ]

        if scene_spec.location:
            parts.append(
                "Set the scene at "
                + cls._ensure_terminal_punctuation(scene_spec.location)
            )

        if normalized_character_name:
            parts.append(f"The main focus is {normalized_character_name}.")

        parts.append(
            f"Show exactly {scene_spec.visible_character_count} visible figures."
        )

        if scene_spec.other_visible_figures:
            parts.append(
                "Only these additional visible figures appear: "
                + ", ".join(scene_spec.other_visible_figures)
                + "."
            )

        if scene_spec.required_props:
            parts.append(
                "Important visual details: "
                + ", ".join(scene_spec.required_props)
                + "."
            )

        if scene_spec.state_fact_lines:
            parts.append(
                "These scene facts must stay true: "
                + " ".join(
                    cls._ensure_terminal_punctuation(line)
                    for line in scene_spec.state_fact_lines
                )
            )

        if normalized_character_description:
            parts.append(
                "Keep the protagonist visually consistent with: "
                + cls._ensure_terminal_punctuation(
                    normalized_character_description
                )
            )

        if visual_profile.world_guidance:
            parts.append(visual_profile.world_guidance)

        parts.extend(visual_profile.anchor_lines)
        parts.extend(visual_profile.negative_guidance)

        parts.extend(
            [
                (
                    "No readable text, letters, words, numbers, captions, "
                    "dialogue balloons, sound effects, subtitles, signage, "
                    "labels, logos, or watermarks anywhere in the image."
                ),
                (
                    "Do not render documents, white text boxes, book pages, "
                    "forms, posters, menus, HUDs, chat windows, or comic panels."
                ),
                (
                    "This must look like a clean illustration, not a "
                    "text-heavy graphic, screenshot, or UI mockup."
                ),
            ]
        )

        return " ".join(parts)

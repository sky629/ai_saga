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
    scenario_genre: str = ""
    scenario_world_setting: str = ""
    scenario_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class IllustrationSceneSpec:
    """장면 구조화 결과."""

    location: str
    visible_character_count: int
    other_visible_figures: tuple[str, ...]
    required_props: tuple[str, ...]
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
        """구조화된 정보를 최종 프롬프트 문자열로 변환한다."""
        normalized_character_name = cls._normalize_text(
            context.character_name, 100
        )
        normalized_character_description = cls._normalize_text(
            context.character_description, 500
        )

        parts = [
            visual_profile.opening_line,
            (
                "Use crisp inked linework, restrained cel shading, "
                "dramatic cinematic composition, and readable silhouettes."
            ),
            "Format: single cinematic full-bleed illustration.",
            (
                "The image must contain zero readable writing, letters, "
                "numbers, symbols, dialogue balloons, sound effects, caption "
                "boxes, signage text, labels, or interface elements."
            ),
        ]

        if scene_spec.location:
            parts.append(
                "Location: "
                + cls._ensure_terminal_punctuation(scene_spec.location)
            )

        parts.append(
            f"Visible characters: exactly {scene_spec.visible_character_count}."
        )

        if normalized_character_name:
            parts.append(
                f"Primary subject: {normalized_character_name}, clearly identifiable at first glance."
            )

        if scene_spec.other_visible_figures:
            parts.append(
                "Other visible figures: "
                + ", ".join(scene_spec.other_visible_figures)
                + "."
            )

        if scene_spec.required_props:
            parts.append(
                "Required props: " + ", ".join(scene_spec.required_props) + "."
            )

        parts.append(
            "Key visual beat: "
            + cls._ensure_terminal_punctuation(scene_spec.key_visual_beat)
        )
        parts.append(
            "Mood and lighting: "
            + cls._ensure_terminal_punctuation(scene_spec.mood_and_lighting)
        )

        if normalized_character_description:
            parts.append(
                "Keep these protagonist details consistent: "
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
                "Show only the explicitly described figures.",
                "Do not add extra guards, crowds, or background bystanders.",
                (
                    "Meaningful background detail is required when "
                    "architecture, streets, interiors, or ruins are implied."
                ),
                (
                    "Avoid battle-line formations, idle posing, "
                    "duplicate-looking people, framed card layouts, and "
                    "character-select compositions."
                ),
                (
                    "Avoid cute or soft anime styling, pastel colors, "
                    "comedic expressions, glossy poster-like rendering, and "
                    "overly bright fantasy cheerfulness."
                ),
            ]
        )

        return " ".join(parts)

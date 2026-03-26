"""일러스트 생성용 구조화 프롬프트 빌더."""


class IllustrationPromptBuilder:
    """일러스트 생성 모델에 전달할 장면 프롬프트를 조립한다."""

    _FALLBACK_SCENE = "mysterious fantasy RPG adventure scene"

    @staticmethod
    def _normalize_text(value: object, max_length: int) -> str:
        """프롬프트 입력 텍스트를 안전하게 정규화한다."""
        if not isinstance(value, str):
            return ""
        return " ".join(value.split())[:max_length]

    @classmethod
    def build(
        cls,
        narrative: str,
        character_name: str = "",
        character_description: str = "",
        current_location: str = "",
        scenario_genre: str = "",
    ) -> str:
        """장면 설명형 프롬프트를 생성한다."""
        scene_brief = (
            cls._normalize_text(narrative, 400) or cls._FALLBACK_SCENE
        )
        normalized_character_name = cls._normalize_text(character_name, 100)
        normalized_character_description = cls._normalize_text(
            character_description, 500
        )
        normalized_location = cls._normalize_text(current_location, 200)
        normalized_genre = cls._normalize_text(scenario_genre, 80)

        parts = [
            (
                "Retro 16-bit pixel art narrative scene illustration. "
                "Show one full-frame story moment only."
            ),
            (
                "The viewer should understand this turn's mood, tension, and "
                "immediate situation at a glance."
            ),
            (
                "No text, no speech bubbles, no captions, no UI, no HUD, no "
                "menu, no logo, no watermark, no title area, no metadata block, "
                "no poster layout, no inventory screen, no dialogue box, no "
                "status window, no floating labels, and no white margins."
            ),
            f"Scene: {scene_brief}.",
        ]

        if normalized_character_name:
            parts.append(
                f"The protagonist is {normalized_character_name} and must be clearly identifiable at first glance."
            )

        if normalized_character_description:
            parts.append(
                f"Keep these protagonist details consistent: {normalized_character_description}."
            )

        if normalized_location:
            parts.append(f"The scene takes place at {normalized_location}.")

        if normalized_genre:
            parts.append(
                f"Keep the visual language grounded in a {normalized_genre} setting and avoid unrelated genre elements."
            )

        parts.extend(
            [
                (
                    "Use cinematic framing, dynamic lighting, readable silhouettes, "
                    "clear action, and strong separation between the protagonist "
                    "and other figures."
                ),
                (
                    "Only include people, creatures, or opponents that are explicitly "
                    "described or strongly implied by the scene. Do not add a crowd, "
                    "party members, bystanders, or duplicate characters unless the "
                    "scene clearly requires them."
                ),
                (
                    "If buildings, streets, interiors, ruins, furniture, weather, "
                    "or environmental props are implied, show them clearly and "
                    "give the environment meaningful visual weight."
                ),
                (
                    "Avoid empty ground, idle standing poses, duplicate-looking "
                    "people, game battle screen layouts, character-select layouts, "
                    "and framed card-like compositions."
                ),
            ]
        )

        return " ".join(parts)

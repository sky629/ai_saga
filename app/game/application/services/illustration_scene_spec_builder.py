"""일러스트 장면 구조화 빌더."""

from app.game.application.services.illustration_prompt_builder import (
    IllustrationPromptContext,
    IllustrationSceneSpec,
)


class IllustrationSceneSpecBuilder:
    """내러티브를 장면 스펙으로 변환한다."""

    _FALLBACK_SCENE = "mysterious fantasy adventure scene"
    _FIGURE_HINTS = (
        ("주점 주인", "one tavern keeper behind the guild counter"),
        ("여관 주인", "one innkeeper"),
        ("경비병", "one guard"),
        ("고블린", "one goblin attacker"),
        ("도적", "one bandit"),
        ("기사", "one armored knight"),
        ("검객", "one swordsman"),
        ("상인", "one merchant"),
        ("늑대", "one wolf"),
    )
    _PROP_HINTS = (
        ("카운터", "worn wooden counter"),
        ("촛불", "flickering candlelight"),
        ("앞치마", "greasy apron"),
        ("잔", "cleaning glass"),
        ("횃불", "lit torch"),
        ("간판", "weathered wooden signboard"),
        ("골목", "narrow alley walls"),
        ("복도", "tight corridor walls"),
        ("성문", "broken stone gate"),
    )
    _LOCATION_HINTS = (
        (("카운터", "길드"), "guild counter interior"),
        (("카운터",), "counter interior"),
        (("골목",), "narrow alley"),
        (("복도",), "narrow corridor"),
        (("성문",), "broken fortress gate"),
        (("여관",), "inn frontage"),
    )

    @staticmethod
    def _normalize_text(value: object, max_length: int) -> str:
        """프롬프트 입력 텍스트를 안전하게 정규화한다."""
        if not isinstance(value, str):
            return ""
        return " ".join(value.split())[:max_length]

    @classmethod
    def _dedupe(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """순서를 유지하며 중복 제거."""
        deduped: list[str] = []
        for value in values:
            if value and value not in deduped:
                deduped.append(value)
        return tuple(deduped)

    @classmethod
    def _extract_other_visible_figures(cls, narrative: str) -> tuple[str, ...]:
        matches = tuple(
            label for token, label in cls._FIGURE_HINTS if token in narrative
        )
        return cls._dedupe(matches)

    @classmethod
    def _extract_required_props(cls, narrative: str) -> tuple[str, ...]:
        matches = tuple(
            label for token, label in cls._PROP_HINTS if token in narrative
        )
        return cls._dedupe(matches)

    @classmethod
    def _infer_location(cls, narrative: str, current_location: str) -> str:
        normalized_current = cls._normalize_text(current_location, 200)
        if normalized_current and "카운터" not in narrative:
            return normalized_current
        for tokens, inferred in cls._LOCATION_HINTS:
            if all(token in narrative for token in tokens):
                return inferred
        return normalized_current

    @classmethod
    def _infer_mood_and_lighting(cls, narrative: str) -> str:
        fragments: list[str] = []
        if "촛불" in narrative or "흐릿" in narrative:
            fragments.append("dim candlelit tension")
        if "햇살" in narrative or "한낮" in narrative:
            fragments.append("daylight with uneasy calm")
        if any(
            token in narrative
            for token in (
                "복수",
                "예리",
                "거친",
                "위태",
                "달려든다",
                "마주친다",
            )
        ):
            fragments.append("restrained danger")
        if "묵묵히" in narrative or "잠시" in narrative:
            fragments.append("held stillness before action")
        if not fragments:
            fragments.append("restrained story tension")
        return ", ".join(cls._dedupe(tuple(fragments)))

    @classmethod
    def build(
        cls, context: IllustrationPromptContext
    ) -> IllustrationSceneSpec:
        """컨텍스트에서 장면 스펙을 추출한다."""
        key_visual_beat = (
            cls._normalize_text(context.scene_narrative, 320)
            or cls._FALLBACK_SCENE
        )
        location = cls._infer_location(
            key_visual_beat,
            cls._normalize_text(context.current_location, 200),
        )
        other_visible_figures = cls._extract_other_visible_figures(
            key_visual_beat
        )
        required_props = cls._extract_required_props(key_visual_beat)

        has_protagonist = (
            bool(cls._normalize_text(context.character_name, 100))
            or "당신" in key_visual_beat
        )
        visible_character_count = len(other_visible_figures)
        if has_protagonist:
            visible_character_count += 1
        if visible_character_count == 0:
            visible_character_count = 1

        return IllustrationSceneSpec(
            location=location,
            visible_character_count=visible_character_count,
            other_visible_figures=other_visible_figures,
            required_props=required_props,
            key_visual_beat=key_visual_beat,
            mood_and_lighting=cls._infer_mood_and_lighting(key_visual_beat),
        )

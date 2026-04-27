"""시나리오 기반 일러스트 비주얼 프로필 해석기."""

from app.game.application.services.illustration_prompt_builder import (
    IllustrationPromptContext,
    IllustrationVisualProfile,
)


class IllustrationScenarioProfileResolver:
    """시나리오/장르 정보를 비주얼 프로필로 변환한다."""

    _GENRE_PROFILES = {
        "fantasy": IllustrationVisualProfile(
            opening_line=(
                "Create a cinematic Korean fantasy illustration for a "
                "single story moment."
            ),
            world_guidance="Keep the world grounded in medieval fantasy.",
        ),
        "sci_fi": IllustrationVisualProfile(
            opening_line=(
                "Create a cinematic science-fiction illustration for a "
                "single story moment."
            ),
            world_guidance="Keep the world grounded in sci-fi.",
            negative_guidance=(
                "Do not introduce medieval fantasy, Joseon-era, or feudal motifs.",
            ),
        ),
        "cyberpunk": IllustrationVisualProfile(
            opening_line=(
                "Create a gritty cinematic cyberpunk illustration for a "
                "single story moment."
            ),
            world_guidance=(
                "Keep the world grounded in cyberpunk, with near-future "
                "technology, dense urban decay, surveillance, and neon-lit "
                "tension."
            ),
            negative_guidance=(
                "Do not introduce medieval fantasy, Joseon-era, or pastoral historical motifs.",
            ),
        ),
        "horror": IllustrationVisualProfile(
            opening_line=(
                "Create a bleak cinematic horror illustration for a single "
                "story moment."
            ),
            world_guidance=(
                "Keep the world grounded in oppressive horror and credible "
                "physical dread."
            ),
            negative_guidance=(
                "Do not introduce heroic fantasy pageantry, palace drama, or ornate historical court imagery.",
            ),
        ),
        "survival": IllustrationVisualProfile(
            opening_line=(
                "Create a gritty cinematic post-apocalyptic survival "
                "illustration for a single story moment."
            ),
            world_guidance=(
                "Keep the world grounded in harsh survival drama."
            ),
            negative_guidance=(
                "Do not introduce medieval fantasy, Joseon-era, hanbok, palace architecture, or swords-and-sorcery motifs.",
            ),
        ),
        "mystery": IllustrationVisualProfile(
            opening_line=(
                "Create a cinematic mystery thriller illustration for a "
                "single story moment."
            ),
            world_guidance=(
                "Keep the world grounded in investigative tension and "
                "suspense."
            ),
        ),
        "historical": IllustrationVisualProfile(
            opening_line=(
                "Create a cinematic historical illustration for a single "
                "story moment."
            ),
            world_guidance=(
                "Keep the world grounded in historical realism and period "
                "appropriate material culture."
            ),
        ),
        "wuxia": IllustrationVisualProfile(
            opening_line=(
                "Create a cinematic wuxia illustration for a single story "
                "moment."
            ),
            world_guidance=(
                "Keep the world grounded in wuxia drama, martial discipline, "
                "cultivation, and atmospheric period fantasy."
            ),
        ),
        "post_apocalyptic": IllustrationVisualProfile(
            opening_line=(
                "Create a gritty cinematic post-apocalyptic survival "
                "illustration for a single story moment."
            ),
            world_guidance=(
                "Keep the world grounded in post-apocalyptic survival "
                "realism, with scarcity, ruin, and practical danger."
            ),
            negative_guidance=(
                "Do not introduce medieval fantasy, Joseon-era, hanbok, palace architecture, or swords-and-sorcery motifs.",
            ),
        ),
    }

    @staticmethod
    def _normalize_text(value: object, max_length: int) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(value.split())[:max_length]

    @classmethod
    def _canonicalize_genre(cls, genre: str) -> str:
        return genre.lower().replace("-", "_").replace(" ", "_")

    @classmethod
    def _canonicalize_game_type(cls, game_type: str) -> str:
        return game_type.lower().replace("-", "_").replace(" ", "_")

    @classmethod
    def _build_game_type_lines(
        cls, context: IllustrationPromptContext
    ) -> tuple[str, ...]:
        game_type = cls._canonicalize_game_type(
            cls._normalize_text(context.scenario_game_type, 80)
        )
        if game_type == "progression":
            return (
                "Game type detail: progression growth scene focused on accumulated training, visible effort, and concrete state change.",
            )
        if game_type == "trpg":
            return (
                "Game type detail: TRPG adventure scene focused on the current role-playing moment, genre fidelity, and environmental storytelling.",
            )
        return (
            "Game type detail: scenario-specific game scene focused on the current story moment and genre fidelity.",
        )

    @classmethod
    def _get_genre_profile(cls, genre: str) -> IllustrationVisualProfile:
        if not genre:
            return cls._GENRE_PROFILES["fantasy"]
        canonical = cls._canonicalize_genre(genre)
        if canonical in cls._GENRE_PROFILES:
            return cls._GENRE_PROFILES[canonical]
        return IllustrationVisualProfile(
            opening_line=(
                "Create a cinematic genre illustration for a single story "
                "moment."
            ),
            world_guidance=(
                f"Keep the world grounded in {genre}, and avoid unrelated "
                "visual motifs."
            ),
        )

    @classmethod
    def _build_anchor_lines(
        cls, context: IllustrationPromptContext
    ) -> tuple[str, ...]:
        genre = cls._canonicalize_genre(
            cls._normalize_text(context.scenario_genre, 80)
        )
        combined = " ".join(
            filter(
                None,
                (
                    context.scenario_name,
                    context.scenario_game_type,
                    context.scenario_world_setting,
                    context.scenario_genre,
                    context.scene_narrative,
                    context.current_location,
                    " ".join(context.scenario_tags),
                ),
            )
        ).lower()
        anchors: list[str] = []

        if any(
            token in combined
            for token in (
                "좀비",
                "zombie",
                "apocalypse",
                "아포칼립스",
                "감염",
                "infected",
            )
        ):
            return (
                "Scenario anchor: zombie apocalypse in ruined modern Seoul, with infected undead, abandoned buildings, scavenged modern gear, and constant survival tension.",
            )

        if "cyberpunk" in combined or "네오 서울" in combined:
            return (
                "Scenario anchor: dystopian near-future Seoul with cyberware, neon signage, dense infrastructure, surveillance, and corporate decay.",
            )

        if genre == "wuxia" and any(
            token in combined
            for token in (
                "무협",
                "강호",
                "심법",
                "내공",
                "외공",
                "비급",
                "수련",
                "기연",
            )
        ):
            return (
                "Scenario anchor: mystical Chinese wuxia cave training ground, martial aura trails, spiritual minerals, flowing robes, and disciplined anime-style hero framing.",
                "Visual style: Chinese wuxia animation atmosphere with a refined Japanese anime-inspired protagonist design.",
            )

        if context.scenario_name:
            anchors.append(
                "Scenario context: "
                + cls._normalize_text(context.scenario_name, 120)
                + "."
            )
        if context.scenario_world_setting:
            anchors.append(
                "World context: "
                + cls._normalize_text(context.scenario_world_setting, 260)
                + "."
            )
        return tuple(anchors)

    @classmethod
    def _merge_negative_guidance(
        cls,
        context: IllustrationPromptContext,
        profile: IllustrationVisualProfile,
    ) -> tuple[str, ...]:
        combined = " ".join(
            filter(
                None,
                (
                    context.scenario_name,
                    context.scenario_game_type,
                    context.scenario_world_setting,
                    context.scene_narrative,
                    context.current_location,
                    " ".join(context.scenario_tags),
                ),
            )
        ).lower()
        guidance = list(profile.negative_guidance)

        if any(
            token in combined
            for token in (
                "좀비",
                "zombie",
                "apocalypse",
                "아포칼립스",
                "감염",
                "infected",
            )
        ):
            guidance.append(
                "Do not introduce medieval fantasy, Joseon-era court imagery, hanbok, palaces, magical glyphs, or swords-and-sorcery styling."
            )

        deduped: list[str] = []
        for line in guidance:
            if line not in deduped:
                deduped.append(line)
        return tuple(deduped)

    @classmethod
    def resolve(
        cls, context: IllustrationPromptContext
    ) -> IllustrationVisualProfile:
        """컨텍스트를 비주얼 프로필로 해석한다."""
        genre = cls._normalize_text(context.scenario_genre, 80)
        base_profile = cls._get_genre_profile(genre)
        return IllustrationVisualProfile(
            opening_line=base_profile.opening_line,
            world_guidance=base_profile.world_guidance,
            game_type_lines=cls._build_game_type_lines(context),
            anchor_lines=cls._build_anchor_lines(context),
            negative_guidance=cls._merge_negative_guidance(
                context, base_profile
            ),
        )

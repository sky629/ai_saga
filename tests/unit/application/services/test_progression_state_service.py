"""ProgressionStateService 단위 테스트."""

from app.game.application.services.progression_state_service import (
    ProgressionStateService,
)


class TestProgressionStateService:
    """엔딩 장면 프롬프트 규칙을 검증한다."""

    def test_build_final_image_prompt_excludes_textual_board_elements(self):
        achievement_board = {
            "character_name": "연우",
            "title": "청광동천객",
            "internal_power": 93,
            "external_power": 35,
            "ending_type": "victory",
            "manuals": [
                {
                    "name": "청광진기 (靑光眞氣)",
                    "category": "internal",
                    "mastery": 95,
                },
                {
                    "name": "용권신장 (龍拳神掌)",
                    "category": "external",
                    "mastery": 75,
                },
            ],
        }

        prompt = ProgressionStateService.build_final_image_prompt(
            achievement_board=achievement_board,
            ending_narrative=(
                "연우는 마침내 동굴의 끝에서 바깥 공기를 마주하며 "
                "지친 몸으로 숨을 고른다."
            ),
        )

        lowered = prompt.lower()
        assert "청광동천객" not in prompt
        assert "청광진기" not in prompt
        assert "용권신장" not in prompt
        assert "93" not in prompt
        assert "35" not in prompt
        assert "achievement-board" not in lowered
        assert "trophy-card composition" not in lowered
        assert "trading cards" in lowered
        assert "no readable text" in lowered
        assert "cinematic composition" in lowered

    def test_build_final_image_prompt_changes_tone_by_ending_type(self):
        victory_prompt = ProgressionStateService.build_final_image_prompt(
            achievement_board={
                "character_name": "연우",
                "title": "동굴생환자",
                "ending_type": "victory",
                "manuals": [],
            },
            ending_narrative="연우는 동굴 밖 바람을 처음으로 들이마신다.",
        )
        defeat_prompt = ProgressionStateService.build_final_image_prompt(
            achievement_board={
                "character_name": "연우",
                "title": "벽중수련객",
                "ending_type": "defeat",
                "manuals": [],
            },
            ending_narrative="연우는 끝내 벽 아래에 주저앉아 마지막 기운을 흩뿌린다.",
        )

        assert "victory, cave exit, release, dawn light" in victory_prompt
        assert "defeat, tragic stillness, exhaustion" in defeat_prompt

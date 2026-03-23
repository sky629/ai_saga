"""Game memory text builder unit tests."""

from datetime import datetime, timezone

from app.common.utils.id_generator import get_uuid7
from app.game.application.services.game_memory_text_builder import (
    GameMemoryTextBuilder,
)
from app.game.domain.entities import GameMemoryEntity
from app.game.domain.value_objects import GameMemoryType, MessageRole


class TestGameMemoryTextBuilder:
    """검색용 텍스트 생성 규칙을 검증한다."""

    def test_build_assistant_search_text_uses_narrative_not_raw_json(self):
        parsed = {
            "before_narrative": "당신은 숨을 죽이고 자물쇠에 철사를 집어넣습니다.",
            "narrative": "철사가 자물쇠의 걸쇠를 밀어내며 문이 열립니다.",
            "state_changes": {
                "location": "감옥 바깥 복도",
                "items_gained": ["경비 열쇠"],
                "discoveries": ["감시탑으로 가는 계단"],
            },
        }

        search_text = GameMemoryTextBuilder.build_assistant_search_text(
            raw_content='{"narrative":"raw json"}',
            parsed_response=parsed,
        )

        assert "철사가 자물쇠의 걸쇠를 밀어내며 문이 열립니다." in search_text
        assert "감옥 바깥 복도" in search_text
        assert "경비 열쇠" in search_text
        assert '"narrative"' not in search_text

    def test_build_message_memory_text_supports_game_memory_entity(self):
        now = datetime.now(timezone.utc)
        memory = GameMemoryEntity(
            id=get_uuid7(),
            session_id=get_uuid7(),
            role=MessageRole.ASSISTANT,
            memory_type=GameMemoryType.ASSISTANT_NARRATIVE,
            content='{"narrative":"raw json"}',
            parsed_response={
                "narrative": "경비의 눈을 피해 복도로 빠져나옵니다.",
                "state_changes": {"location": "복도"},
            },
            embedding=[0.1, 0.2, 0.3],
            created_at=now,
        )

        search_text = GameMemoryTextBuilder.build_message_memory_text(memory)

        assert "경비의 눈을 피해 복도로 빠져나옵니다." in search_text
        assert "복도" in search_text
        assert '"narrative"' not in search_text

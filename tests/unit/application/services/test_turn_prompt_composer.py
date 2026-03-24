"""Turn prompt composer unit tests."""

from datetime import datetime, timezone

from app.common.utils.id_generator import get_uuid7
from app.game.application.services.turn_prompt_composer import (
    TurnPromptComposer,
)
from app.game.domain.entities import GameMessageEntity
from app.game.domain.value_objects import GameState, MessageRole


class TestTurnPromptComposer:
    """명시적 현재 턴 프롬프트 조립을 검증한다."""

    def test_compose_includes_structured_current_turn_payload(self):
        now = datetime.now(timezone.utc)
        session_id = get_uuid7()
        history = [
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.USER,
                content="지난 턴 행동",
                created_at=now,
            )
        ]
        recalled = [
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content='{"narrative":"문이 잠겨 있다.","state_changes":{"location":"감옥 복도"}}',
                parsed_response={
                    "narrative": "문이 잠겨 있다.",
                    "state_changes": {"location": "감옥 복도"},
                },
                created_at=now,
            )
        ]

        composed = TurnPromptComposer.compose(
            scenario_name="감옥 탈출",
            world_setting="어두운 지하 감옥",
            character_name="도적",
            character_description="민첩한 탈옥수",
            current_location="감옥 복도",
            game_state=GameState(
                discoveries=["녹슨 열쇠 구멍"],
                visited_locations=["독방", "감옥 복도"],
            ),
            inventory=["철사"],
            player_action="문을 따고 탈출한다",
            conversation_history=history,
            recalled_memories=recalled,
        )

        assert "감옥 탈출" in composed.system_prompt
        assert composed.messages[-1]["role"] == "user"
        assert "현재 플레이어 행동" in composed.messages[-1]["content"]
        assert "문을 따고 탈출한다" in composed.messages[-1]["content"]
        assert "서버 판정" not in composed.messages[-1]["content"]
        assert "문이 잠겨 있다." in composed.messages[-1]["content"]
        assert "녹슨 열쇠 구멍" in composed.system_prompt

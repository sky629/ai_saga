"""E2E tests for development-only routes."""

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.auth.infrastructure.persistence.models.user_models import User
from app.common.storage.postgres import postgres_storage
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.infrastructure.adapters.image_service import (
    ImageGenerationServiceAdapter,
)
from app.game.infrastructure.persistence.models import (
    Character,
    GameMessage,
    GameSession,
    Scenario,
)


@pytest.mark.asyncio
async def test_regenerate_ending_image_updates_session_and_message(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """엔딩 이미지 재생성 시 세션과 엔딩 메시지를 함께 갱신한다."""
    user_id = get_uuid7()
    scenario_id = get_uuid7()
    character_id = get_uuid7()
    session_id = get_uuid7()
    ending_message_id = get_uuid7()
    old_image_url = "https://example.com/old-ending.png"
    new_image_url = "https://example.com/new-ending.png"
    ending_narrative = "주인공은 끝내 동굴을 돌파하고 새벽빛 아래로 나아간다."
    deleted_urls: list[str] = []
    email = f"{user_id}@test.dev"

    async def fake_generate_image(self, prompt, session_id, user_id):
        del self, session_id, user_id
        assert "No readable text" in prompt
        assert "주인공은 끝내 동굴을 돌파" in prompt
        return new_image_url

    async def fake_delete_image(self, image_url):
        del self
        deleted_urls.append(image_url)

    monkeypatch.setattr(
        ImageGenerationServiceAdapter,
        "generate_image",
        fake_generate_image,
    )
    monkeypatch.setattr(
        ImageGenerationServiceAdapter,
        "delete_image",
        fake_delete_image,
    )

    async with postgres_storage.get_domain_write_session() as db:
        db.add(
            User(
                id=user_id,
                email=email,
                name="Ending Dev",
                email_verified=True,
                is_active=True,
                user_level=100,
            )
        )
        db.add(
            Scenario(
                id=scenario_id,
                name="기연 일지",
                description="엔딩 이미지 재생성 테스트",
                world_setting="절벽 아래 동굴",
                initial_location="절벽 아래 - 수련 동굴",
                game_type="progression",
                genre="historical",
                difficulty="normal",
                max_turns=12,
                is_active=True,
            )
        )
        db.add(
            Character(
                id=character_id,
                user_id=user_id,
                scenario_id=scenario_id,
                name="연우",
                profile={"description": "무협 수련자"},
                stats={
                    "hp": 78,
                    "max_hp": 100,
                    "level": 1,
                    "experience": 0,
                    "current_experience": 0,
                },
                inventory=[],
                is_active=True,
            )
        )
        db.add(
            GameSession(
                id=session_id,
                user_id=user_id,
                character_id=character_id,
                scenario_id=scenario_id,
                current_location="절벽 아래 - 수련 동굴",
                game_state={
                    "final_outcome": {
                        "ending_type": "victory",
                        "narrative": ending_narrative,
                        "image_url": old_image_url,
                        "achievement_board": {
                            "character_name": "연우",
                            "scenario_name": "기연 일지",
                            "title": "절벽 돌파자",
                            "escaped": True,
                            "total_score": 92,
                            "hp": 78,
                            "max_hp": 100,
                            "internal_power": 61,
                            "external_power": 31,
                            "manuals": [],
                            "remaining_turns": 0,
                            "summary": "절벽을 돌파해 탈출했다.",
                            "traits": ["집요함"],
                            "title_candidates": [],
                            "title_reason": "끝까지 버텨 탈출했다.",
                            "ending_type": "victory",
                        },
                    }
                },
                status="completed",
                turn_count=12,
                max_turns=12,
                ending_type="victory",
                started_at=get_utc_datetime(),
                ended_at=get_utc_datetime(),
                last_activity_at=get_utc_datetime(),
            )
        )
        db.add(
            GameMessage(
                id=ending_message_id,
                session_id=session_id,
                role="assistant",
                content=ending_narrative,
                parsed_response={
                    "narrative": ending_narrative,
                    "options": [],
                    "ending_type": "victory",
                    "final_outcome": {
                        "ending_type": "victory",
                        "narrative": ending_narrative,
                        "image_url": old_image_url,
                        "achievement_board": {
                            "character_name": "연우",
                            "scenario_name": "기연 일지",
                            "title": "절벽 돌파자",
                            "escaped": True,
                            "total_score": 92,
                            "hp": 78,
                            "max_hp": 100,
                            "internal_power": 61,
                            "external_power": 31,
                            "manuals": [],
                            "remaining_turns": 0,
                            "summary": "절벽을 돌파해 탈출했다.",
                            "traits": ["집요함"],
                            "title_candidates": [],
                            "title_reason": "끝까지 버텨 탈출했다.",
                            "ending_type": "victory",
                        },
                    },
                },
                token_count=None,
                created_at=get_utc_datetime(),
                image_url=old_image_url,
            )
        )

    response = await async_client.post(
        f"/api/v1/dev/sessions/{session_id}/regenerate-ending-image/"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == str(session_id)
    assert data["old_image_url"] == old_image_url
    assert data["image_url"] == new_image_url
    assert deleted_urls == [old_image_url]

    async with postgres_storage.get_domain_read_session() as db:
        session_result = await db.execute(
            select(GameSession).where(
                GameSession.id == UUID(data["session_id"])
            )
        )
        saved_session = session_result.scalar_one()
        assert (
            saved_session.game_state["final_outcome"]["image_url"]
            == new_image_url
        )

        message_result = await db.execute(
            select(GameMessage).where(GameMessage.id == ending_message_id)
        )
        saved_message = message_result.scalar_one()
        assert saved_message.image_url == new_image_url
        assert (
            saved_message.parsed_response["final_outcome"]["image_url"]
            == new_image_url
        )

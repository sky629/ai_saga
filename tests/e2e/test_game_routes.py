"""E2E tests for game routes.

Tests the full HTTP request/response cycle for game API endpoints.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestGetSessionEndpoint:
    """Test GET /api/v1/game/sessions/{session_id}/ endpoint."""

    @pytest.fixture
    async def auth_headers(self, async_client: AsyncClient):
        """Get auth headers for dev user."""
        response = await async_client.post("/api/v1/dev/token/")
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def seeded_scenarios(self, async_client: AsyncClient, auth_headers):
        """Ensure scenarios are seeded and return them."""
        # Seed scenarios
        await async_client.post(
            "/api/v1/dev/seed-scenarios/", headers=auth_headers
        )

        # Get scenarios
        response = await async_client.get(
            "/api/v1/game/scenarios/", headers=auth_headers
        )
        assert response.status_code == 200
        scenarios = response.json()
        assert len(scenarios) > 0
        return scenarios

    @pytest.fixture
    async def test_session(
        self, async_client: AsyncClient, auth_headers, seeded_scenarios
    ):
        """Create a test game session."""
        scenario_id = seeded_scenarios[0]["id"]

        # Create character
        char_response = await async_client.post(
            "/api/v1/game/characters/",
            json={
                "name": "Test Hero",
                "description": "A test character",
                "scenario_id": scenario_id,
            },
            headers=auth_headers,
        )
        assert char_response.status_code == 201
        character_id = char_response.json()["id"]

        # Start game session
        session_response = await async_client.post(
            "/api/v1/game/sessions/",
            json={
                "character_id": character_id,
                "scenario_id": scenario_id,
            },
            headers=auth_headers,
        )
        assert session_response.status_code == 201
        return session_response.json()

    @pytest.fixture
    async def other_user_session(
        self, async_client: AsyncClient, seeded_scenarios
    ):
        """Create a game session for a different user.

        This fixture creates its own auth token for a different user.
        """
        # Get token for "other" user (we'll use dev token twice but conceptually different)
        # In real test, this would be a different user
        # For now, we skip this fixture as we can't easily create multiple users
        # without more complex setup
        pytest.skip("Multiple user setup not available in test environment")

    async def test_get_session_success(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """존재하는 세션 조회 성공."""
        session_id = test_session["id"]

        response = await async_client.get(
            f"/api/v1/game/sessions/{session_id}/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure (GameSessionResponse)
        assert data["id"] == session_id
        assert "game_state" in data
        assert "current_location" in data
        assert "status" in data
        assert "turn_count" in data
        assert "character_id" in data
        assert "scenario_id" in data
        assert "started_at" in data
        assert "last_activity_at" in data

        # Verify game_state is a dict
        assert isinstance(data["game_state"], dict)

    async def test_get_session_not_found(
        self, async_client: AsyncClient, auth_headers
    ):
        """존재하지 않는 세션 조회 → 404."""
        fake_id = str(uuid4())

        response = await async_client.get(
            f"/api/v1/game/sessions/{fake_id}/",
            headers=auth_headers,
        )

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "not found" in detail.lower()

    async def test_get_session_invalid_uuid(
        self, async_client: AsyncClient, auth_headers
    ):
        """잘못된 UUID 형식 → 422 Validation Error."""
        invalid_uuid = "not-a-valid-uuid"

        response = await async_client.get(
            f"/api/v1/game/sessions/{invalid_uuid}/",
            headers=auth_headers,
        )

        # FastAPI will return 422 for invalid UUID path parameter
        assert response.status_code == 422

    async def test_get_session_unauthorized(
        self, async_client: AsyncClient, test_session
    ):
        """인증 없이 조회 → 401."""
        session_id = test_session["id"]

        response = await async_client.get(
            f"/api/v1/game/sessions/{session_id}/",
            # No headers = no authentication
        )

        assert response.status_code == 401

    async def test_get_session_invalid_token(
        self, async_client: AsyncClient, test_session
    ):
        """잘못된 토큰으로 조회 → 401."""
        session_id = test_session["id"]

        response = await async_client.get(
            f"/api/v1/game/sessions/{session_id}/",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    # Note: test_get_session_forbidden (다른 사용자의 세션) is skipped
    # because we don't have easy multi-user setup in test environment.
    # The authorization logic is tested via the query unit test instead.


@pytest.mark.asyncio
class TestSubmitActionOnCompletedSession:
    """Test POST /api/v1/game/sessions/{session_id}/actions/ on completed sessions."""

    @pytest.fixture
    async def auth_headers(self, async_client: AsyncClient):
        """Get auth headers for dev user."""
        response = await async_client.post("/api/v1/dev/token/")
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def seeded_scenarios(self, async_client: AsyncClient, auth_headers):
        """Ensure scenarios are seeded and return them."""
        await async_client.post(
            "/api/v1/dev/seed-scenarios/", headers=auth_headers
        )
        response = await async_client.get(
            "/api/v1/game/scenarios/", headers=auth_headers
        )
        assert response.status_code == 200
        scenarios = response.json()
        assert len(scenarios) > 0
        return scenarios

    @pytest.fixture
    async def completed_session(
        self, async_client: AsyncClient, auth_headers, seeded_scenarios
    ):
        """Create a completed game session (max_turns=1, submit 1 action)."""
        scenario_id = seeded_scenarios[0]["id"]

        # Create character
        char_response = await async_client.post(
            "/api/v1/game/characters/",
            json={
                "name": "Test Hero",
                "description": "A test character",
                "scenario_id": scenario_id,
            },
            headers=auth_headers,
        )
        assert char_response.status_code == 201
        character_id = char_response.json()["id"]

        # Start game session with max_turns=1
        session_response = await async_client.post(
            "/api/v1/game/sessions/",
            json={
                "character_id": character_id,
                "scenario_id": scenario_id,
                "max_turns": 1,  # 1턴으로 설정하여 첫 액션에서 종료
            },
            headers={**auth_headers, "Idempotency-Key": str(uuid4())},
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        # Submit first action to complete the game
        action_response = await async_client.post(
            f"/api/v1/game/sessions/{session_id}/actions/",
            json={"action": "북쪽으로 이동"},
            headers={**auth_headers, "Idempotency-Key": str(uuid4())},
        )
        assert action_response.status_code == 200

        # Verify session is completed
        session_check = await async_client.get(
            f"/api/v1/game/sessions/{session_id}/",
            headers=auth_headers,
        )
        assert session_check.status_code == 200
        session_data = session_check.json()
        assert session_data["status"] == "completed"
        assert session_data["turn_count"] >= session_data["max_turns"]

        return session_id

    async def test_submit_action_on_completed_session_returns_409(
        self, async_client: AsyncClient, auth_headers, completed_session
    ):
        """완료된 세션에 액션 제출 시 409 Conflict 반환."""
        session_id = completed_session

        response = await async_client.post(
            f"/api/v1/game/sessions/{session_id}/actions/",
            json={"action": "남쪽으로 이동"},
            headers={**auth_headers, "Idempotency-Key": str(uuid4())},
        )

        # Expected: 409 Conflict
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "completed" in detail.lower()
        assert (
            "cannot process" in detail.lower() or "already" in detail.lower()
        )

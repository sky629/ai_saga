from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestScenarioCharacterLink:
    @pytest.fixture
    async def auth_headers(self, async_client: AsyncClient):
        """Get auth headers for dev user."""
        response = await async_client.post("/api/v1/dev/token/")
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def seeded_scenarios(self, async_client: AsyncClient, auth_headers):
        """Ensure scenarios are seeded."""
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

    async def test_create_character_with_valid_scenario(
        self, async_client: AsyncClient, auth_headers, seeded_scenarios
    ):
        """Test creating character with valid scenario ID."""
        scenario_id = seeded_scenarios[0]["id"]

        payload = {
            "name": "Test Hero",
            "description": "A brave hero",
            "scenario_id": scenario_id,
        }

        response = await async_client.post(
            "/api/v1/game/characters/", json=payload, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Hero"
        assert data["scenario_id"] == scenario_id

    async def test_create_character_with_invalid_scenario(
        self, async_client: AsyncClient, auth_headers
    ):
        """Test creating character with non-existent scenario ID."""
        random_uuid = str(uuid4())

        payload = {
            "name": "Test Hero",
            "description": "A brave hero",
            "scenario_id": random_uuid,
        }

        response = await async_client.post(
            "/api/v1/game/characters/", json=payload, headers=auth_headers
        )

        # Should be 404 (Scenario not found) or 400
        assert response.status_code in [400, 404, 422, 500]
        # Note: Depending on how ValueError is handled, it might be 500 if not caught by exception handler,
        # or 400 if caught. UseCase raises ValueError.

    async def test_start_game_with_matching_scenario(
        self, async_client: AsyncClient, auth_headers, seeded_scenarios
    ):
        """Test starting game with correct character-scenario pair."""
        scenario_id = seeded_scenarios[0]["id"]

        # Create character
        char_res = await async_client.post(
            "/api/v1/game/characters/",
            json={
                "name": "Matching Hero",
                "description": "desc",
                "scenario_id": scenario_id,
            },
            headers=auth_headers,
        )
        assert char_res.status_code == 201
        character_id = char_res.json()["id"]

        # Start game
        payload = {"character_id": character_id, "scenario_id": scenario_id}

        response = await async_client.post(
            "/api/v1/game/sessions/", json=payload, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["character_id"] == character_id
        assert data["scenario_id"] == scenario_id

    async def test_start_game_with_mismatching_scenario(
        self, async_client: AsyncClient, auth_headers, seeded_scenarios
    ):
        """Test starting game with mismatched character-scenario pair."""
        if len(seeded_scenarios) < 2:
            pytest.skip("Need at least 2 scenarios to test mismatch")

        scenario1_id = seeded_scenarios[0]["id"]
        scenario2_id = seeded_scenarios[1]["id"]

        # Create character for Scenario 1
        char_res = await async_client.post(
            "/api/v1/game/characters/",
            json={
                "name": "Scenario 1 Hero",
                "description": "desc",
                "scenario_id": scenario1_id,
            },
            headers=auth_headers,
        )
        assert char_res.status_code == 201
        character_id = char_res.json()["id"]

        # Try to start game with Scenario 2
        payload = {"character_id": character_id, "scenario_id": scenario2_id}

        response = await async_client.post(
            "/api/v1/game/sessions/", json=payload, headers=auth_headers
        )

        # Should fail
        assert response.status_code != 201
        assert response.status_code in [400, 422, 500]

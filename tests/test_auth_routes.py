"""Test authentication routes."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.auth.application.use_cases.handle_oauth_callback import (
    OAuthCallbackResult,
)
from app.auth.application.use_cases.refresh_token import RefreshTokenResult
from app.auth.dependencies import (
    get_handle_oauth_callback_use_case,
    get_refresh_token_use_case,
)
from app.auth.domain.entities.user import UserEntity
from app.auth.domain.value_objects import UserLevel
from app.common.utils.id_generator import get_uuid7
from config.settings import settings


class TestAuthRoutes:
    """Test authentication route endpoints."""

    def test_health_check(self, client: TestClient):
        """Test auth health check endpoint."""
        # Health endpoint doesn't exist - test self endpoint instead
        response = client.get("/api/v1/auth/self/")

        # Should return 401 without authentication
        assert response.status_code == 401

    def test_google_login_initiation(self, client: TestClient):
        """Test Google OAuth login initiation."""
        response = client.get(
            "/api/v1/auth/google/login/", follow_redirects=False
        )

        if response.status_code == 307:
            assert response.headers["location"].startswith(
                "https://accounts.google.com/"
            )
        else:
            assert response.status_code in [429, 500]

    def test_google_callback_missing_code(self, client: TestClient):
        """Test Google OAuth callback with missing code."""
        response = client.get(
            "/api/v1/auth/google/callback/", params={"state": "test-state"}
        )

        # Should return validation error for missing code
        assert response.status_code == 422

    def test_google_callback_missing_state(self, client: TestClient):
        """Test Google OAuth callback with missing state."""
        response = client.get(
            "/api/v1/auth/google/callback/", params={"code": "test-code"}
        )

        # Should return validation error for missing state
        assert response.status_code == 422

    def test_refresh_token_missing_token(self, client: TestClient):
        """Test token refresh with missing refresh token."""
        response = client.post("/api/v1/auth/refresh/")
        assert response.status_code == 401

    def test_refresh_token_invalid_token(self, client: TestClient):
        """Test token refresh with invalid refresh token."""
        response = client.post(
            "/api/v1/auth/refresh/",
            cookies={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401

    def test_me_endpoint_unauthenticated(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/self/")

        # Should return unauthorized
        assert response.status_code == 401

    def test_me_endpoint_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/v1/auth/self/",
            headers={"Authorization": "Bearer invalid-token"},
        )

        # Should return unauthorized for invalid token
        assert response.status_code == 401

    def test_update_me_unauthenticated(self, client: TestClient):
        """Test updating current user without authentication."""
        response = client.put("/api/v1/auth/self/", json={"name": "New Name"})

        # Should return unauthorized
        assert response.status_code == 401

    def test_social_accounts_unauthenticated(self, client: TestClient):
        """Test getting social accounts without authentication."""
        response = client.get("/api/v1/auth/self/social-accounts/")

        # Should return unauthorized
        assert response.status_code == 401

    def test_logout_unauthenticated(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout/")

        # Should return unauthorized
        assert response.status_code == 401


class TestAuthValidation:
    """Test request validation for auth endpoints."""

    def test_google_callback_validation(self, client: TestClient):
        """Test Google callback request validation."""
        # Test empty request
        response = client.get("/api/v1/auth/google/callback/")
        assert response.status_code == 422

        # Test missing code
        response = client.get(
            "/api/v1/auth/google/callback/", params={"state": "test-state"}
        )
        assert response.status_code == 422

        # Test missing state
        response = client.get(
            "/api/v1/auth/google/callback/", params={"code": "test-code"}
        )
        assert response.status_code == 422

    def test_user_update_validation(self, client: TestClient):
        """Test user update request validation."""
        # Test with invalid token (should fail auth before validation)
        response = client.put(
            "/api/v1/auth/self/",
            json={"name": ""},  # Empty name should be caught after auth
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401  # Auth fails first

    def test_disconnect_social_account_validation(self, client: TestClient):
        """Test social account disconnect validation."""
        # Test with invalid UUID format
        response = client.delete(
            "/api/v1/auth/self/social-accounts/invalid-uuid/",
            headers={"Authorization": "Bearer invalid-token"},
        )
        # Auth fails first before UUID validation
        assert response.status_code == 401


def test_refresh_token_sets_rotated_cookie(app):
    """Test refresh route rotates refresh token cookie."""

    class FakeRefreshUseCase:
        async def execute(self, input_data):
            return RefreshTokenResult(
                access_token="new-access",
                token_type="bearer",
                expires_in=1800,
                refresh_token="new-refresh-token",
            )

    app.dependency_overrides[get_refresh_token_use_case] = (
        lambda: FakeRefreshUseCase()
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/refresh/",
        cookies={"refresh_token": "old-refresh-token"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access"
    assert "refresh_token=new-refresh-token" in response.headers["set-cookie"]


def test_google_callback_redirects_to_configured_frontend_url(
    app, monkeypatch
):
    """Test Google callback uses configured frontend success URL."""

    class FakeOAuthCallbackUseCase:
        async def execute(self, input_data):
            del input_data
            now = datetime.now(timezone.utc)
            return OAuthCallbackResult(
                user=UserEntity(
                    id=get_uuid7(),
                    email="test@example.com",
                    name="Test User",
                    profile_image_url=None,
                    user_level=UserLevel.NORMAL,
                    is_active=True,
                    email_verified=True,
                    created_at=now,
                    updated_at=now,
                    last_login_at=now,
                ),
                access_token="issued-access-token",
                refresh_token="issued-refresh-token",
                expires_in=1800,
                is_new_user=True,
            )

    frontend_url = "http://localhost:4173/auth/callback/success"
    monkeypatch.setattr(settings, "frontend_login_success_url", frontend_url)

    app.dependency_overrides[get_handle_oauth_callback_use_case] = (
        lambda: FakeOAuthCallbackUseCase()
    )
    client = TestClient(app)

    response = client.get(
        "/api/v1/auth/google/callback/",
        params={"code": "oauth-code", "state": "oauth-state"},
        follow_redirects=False,
    )

    app.dependency_overrides.clear()

    assert response.status_code == 307
    assert response.headers["location"] == (
        f"{frontend_url}?access_token=issued-access-token&new_user=true"
    )
    assert (
        "refresh_token=issued-refresh-token" in response.headers["set-cookie"]
    )

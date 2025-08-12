"""Test authentication routes."""

from fastapi.testclient import TestClient


class TestAuthRoutes:
    """Test authentication route endpoints."""

    def test_health_check(self, client: TestClient):
        """Test auth health check endpoint."""
        response = client.get("/api/auth/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "auth"

    def test_google_login_initiation(self, client: TestClient):
        """Test Google OAuth login initiation."""
        response = client.get("/api/auth/google/login")

        # Should return auth URL and state
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "state" in data
        assert "accounts.google.com" in data["auth_url"]

    def test_google_callback_missing_code(self, client: TestClient):
        """Test Google OAuth callback with missing code."""
        response = client.post(
            "/api/auth/google/callback", json={"state": "test-state"}
        )

        # Should return validation error for missing code
        assert response.status_code == 422

    def test_google_callback_missing_state(self, client: TestClient):
        """Test Google OAuth callback with missing state."""
        response = client.post("/api/auth/google/callback", json={"code": "test-code"})

        # Should return validation error for missing state
        assert response.status_code == 422

    def test_refresh_token_missing_token(self, client: TestClient):
        """Test token refresh with missing refresh token."""
        response = client.post("/api/auth/refresh", json={})

        # Should return validation error for missing refresh_token
        assert response.status_code == 422

    def test_refresh_token_invalid_token(self, client: TestClient):
        """Test token refresh with invalid refresh token."""
        response = client.post(
            "/api/auth/refresh", json={"refresh_token": "invalid-token"}
        )

        # Should return unauthorized for invalid token
        assert response.status_code == 401

    def test_me_endpoint_unauthenticated(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/api/auth/me")

        # Should return unauthorized
        assert response.status_code == 401

    def test_me_endpoint_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid-token"}
        )

        # Should return unauthorized for invalid token
        assert response.status_code == 401

    def test_update_me_unauthenticated(self, client: TestClient):
        """Test updating current user without authentication."""
        response = client.put("/api/auth/me", json={"name": "New Name"})

        # Should return unauthorized
        assert response.status_code == 401

    def test_social_accounts_unauthenticated(self, client: TestClient):
        """Test getting social accounts without authentication."""
        response = client.get("/api/auth/me/social-accounts")

        # Should return unauthorized
        assert response.status_code == 401

    def test_logout_unauthenticated(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/auth/logout")

        # Should return unauthorized
        assert response.status_code == 401


class TestAuthValidation:
    """Test request validation for auth endpoints."""

    def test_google_callback_validation(self, client: TestClient):
        """Test Google callback request validation."""
        # Test empty request
        response = client.post("/api/auth/google/callback", json={})
        assert response.status_code == 422

        # Test missing code
        response = client.post(
            "/api/auth/google/callback", json={"state": "test-state"}
        )
        assert response.status_code == 422

        # Test missing state
        response = client.post("/api/auth/google/callback", json={"code": "test-code"})
        assert response.status_code == 422

    def test_user_update_validation(self, client: TestClient):
        """Test user update request validation."""
        # Test with invalid token (should fail auth before validation)
        response = client.put(
            "/api/auth/me",
            json={"name": ""},  # Empty name should be caught after auth
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401  # Auth fails first

    def test_disconnect_social_account_validation(self, client: TestClient):
        """Test social account disconnect validation."""
        # Test with invalid UUID format
        response = client.delete(
            "/api/auth/me/social-accounts/invalid-uuid",
            headers={"Authorization": "Bearer invalid-token"},
        )
        # Auth fails first before UUID validation
        assert response.status_code == 401

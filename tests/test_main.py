"""Test main application."""

from fastapi.testclient import TestClient


class TestMainApplication:
    """Test main application endpoints."""

    def test_ping_endpoint(self, client: TestClient):
        """Test ping endpoint."""
        response = client.get("/api/ping/")

        assert response.status_code == 200
        data = response.json()
        assert data["ping"] == "pong!"

    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/api/ping/")

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_docs_endpoint_dev(self, client: TestClient):
        """Test API documentation endpoint in development."""
        response = client.get("/api/docs/")

        # Should return HTML content for API docs
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_openapi_schema(self, client: TestClient):
        """Test OpenAPI schema endpoint."""
        response = client.get("/api/docs/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Kang Server Swagger"

    def test_nonexistent_endpoint(self, client: TestClient):
        """Test accessing non-existent endpoint."""
        response = client.get("/api/nonexistent/")

        assert response.status_code == 404


class TestMiddleware:
    """Test middleware functionality."""

    def test_access_log_middleware(self, client: TestClient):
        """Test that access log middleware is working."""
        # This test mainly ensures the middleware doesn't break requests
        response = client.get("/api/ping/")

        assert response.status_code == 200
        # Access logs should be generated (check logs if needed)

    def test_exception_handling(self, client: TestClient):
        """Test global exception handling."""
        # Test with malformed JSON
        response = client.post(
            "/api/auth/google/callback",
            data="invalid-json",
            headers={"Content-Type": "application/json"},
        )

        # Should return proper error response
        assert response.status_code == 422  # Validation error

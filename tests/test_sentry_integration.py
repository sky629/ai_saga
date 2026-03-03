"""Sentry integration tests."""

from app.main import (
    _resolve_sentry_enable_logs,
    _sentry_before_send,
    _should_enable_sentry,
)


class TestSentryIntegration:
    """Test Sentry helper behavior."""

    def test_should_enable_sentry(self):
        """Enable when DSN exists and environment is allowed."""
        assert _should_enable_sentry(
            dsn="https://example@sentry.io/1",
            environment="prod",
            enabled_environments="prod,stage",
        )

        assert not _should_enable_sentry(
            dsn="",
            environment="prod",
            enabled_environments="prod,stage",
        )

        assert not _should_enable_sentry(
            dsn="https://example@sentry.io/1",
            environment="local",
            enabled_environments="prod,stage",
        )

    def test_before_send_masks_sensitive_data(self):
        """Mask sensitive values before event is sent."""
        event = {
            "request": {
                "headers": {
                    "authorization": "Bearer secret-token",
                    "x-api-key": "my-api-key",
                    "x-request-id": "safe-value",
                },
                "data": {
                    "password": "p@ssw0rd",
                    "nested": {
                        "refresh_token": "refresh-token",
                    },
                },
            },
            "user": {
                "id": "user-1",
                "email": "user@example.com",
            },
            "extra": {
                "jwt": "some-jwt-token",
            },
        }

        masked = _sentry_before_send(event, {})

        assert masked is not None
        assert masked["request"]["headers"]["authorization"] == "[Filtered]"
        assert masked["request"]["headers"]["x-api-key"] == "[Filtered]"
        assert masked["request"]["headers"]["x-request-id"] == "safe-value"
        assert masked["request"]["data"]["password"] == "[Filtered]"
        assert (
            masked["request"]["data"]["nested"]["refresh_token"]
            == "[Filtered]"
        )
        assert masked["extra"]["jwt"] == "[Filtered]"
        assert masked["user"]["email"] == "[Filtered]"

    def test_resolve_sentry_enable_logs_by_environment(self):
        """Enable logs in local/beta by default, disable in prod."""
        assert _resolve_sentry_enable_logs("local", None) is True
        assert _resolve_sentry_enable_logs("beta", None) is True
        assert _resolve_sentry_enable_logs("prod", None) is False

        assert _resolve_sentry_enable_logs("prod", True) is True
        assert _resolve_sentry_enable_logs("local", False) is False

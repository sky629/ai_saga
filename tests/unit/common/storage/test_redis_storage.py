"""Redis storage configuration unit tests."""

from app.common.storage.redis import _RedisStorage


class TestRedisStorageConnectionInfo:
    """Redis alias별 connection info 선택을 검증한다."""

    def test_get_connection_info_uses_alias_specific_db_env(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
        monkeypatch.setenv("REDIS_DEFAULT_DB", "15")
        monkeypatch.setenv("REDIS_AUTH_DB", "14")

        storage = _RedisStorage()

        default_info = storage.get_connection_info("default")
        auth_info = storage.get_connection_info("auth")

        assert default_info.db == 15
        assert auth_info.db == 14

    def test_get_connection_info_defaults_to_db_1_without_alias_env(
        self, monkeypatch
    ):
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
        monkeypatch.delenv("REDIS_DEFAULT_DB", raising=False)

        storage = _RedisStorage()

        info = storage.get_connection_info("default")

        assert info.db == 1

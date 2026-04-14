"""Postgres storage configuration unit tests."""

from unittest.mock import patch

from app.common.storage.postgres import PostgresStorage
from app.common.utils.singleton import Singleton


class TestPostgresStorageLogging:
    """SQLAlchemy 엔진 생성 시 쿼리 echo 비활성화를 검증한다."""

    def test_domain_pools_disable_sqlalchemy_echo(self):
        Singleton._instances.pop(PostgresStorage, None)

        with patch(
            "app.common.storage.postgres.create_async_engine"
        ) as mock_create_engine:
            storage = PostgresStorage()
            storage._get_or_create_domain_pool("default")

        assert mock_create_engine.call_count == 2
        for call in mock_create_engine.call_args_list:
            assert call.kwargs["echo"] is False

        Singleton._instances.pop(PostgresStorage, None)

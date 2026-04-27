"""로깅 설정 단위 테스트."""

import logging

from app.common.logging import (
    get_console_logging_config,
    get_uvicorn_logging_config,
)


class TestLoggingConfig:
    """환경별 로깅 설정 검증."""

    def test_console_logging_config_keeps_info_in_local(self):
        """로컬에서는 앱 로그가 INFO 레벨을 유지해야 한다."""
        config = get_console_logging_config(is_prod=False)

        assert config["loggers"][""]["level"] == logging.INFO
        assert config["loggers"]["app"]["level"] == logging.INFO

    def test_console_logging_config_reduces_noise_in_prod(self):
        """프로덕션에서는 앱/루트 로그를 WARNING으로 낮춰야 한다."""
        config = get_console_logging_config(is_prod=True)

        assert config["loggers"][""]["level"] == logging.WARNING
        assert config["loggers"]["app"]["level"] == logging.WARNING
        assert config["loggers"]["uvicorn.access"]["handlers"] == ["ignore"]

    def test_uvicorn_logging_config_reduces_access_logs_in_prod(self):
        """프로덕션에서는 uvicorn access 로그를 비활성화해야 한다."""
        config = get_uvicorn_logging_config(is_prod=True)

        assert config["loggers"]["uvicorn"]["level"] == logging.WARNING
        assert config["loggers"]["uvicorn.error"]["level"] == logging.WARNING
        assert config["loggers"]["uvicorn.access"]["handlers"] == ["ignore"]
        assert config["loggers"]["uvicorn.access"]["level"] == logging.WARNING

    def test_console_logging_config_keeps_llm_prompt_logger_in_prod(self):
        """프로덕션에서도 프롬프트 로거는 INFO로 유지해야 한다."""
        config = get_console_logging_config(is_prod=True)

        assert config["loggers"]["app.llm.prompt"]["level"] == logging.INFO
        assert config["loggers"]["app.llm.prompt"]["handlers"] == ["default"]

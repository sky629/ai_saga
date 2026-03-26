"""애플리케이션 로깅 설정."""

import logging
import sys


def _build_console_logging_config(
    root_level: int,
    app_level: int,
) -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "": {"level": root_level, "handlers": ["default"]},
            "app": {
                "level": app_level,
                "handlers": ["default"],
                "propagate": False,
            },
            "app.access": {
                "level": logging.INFO,
                "handlers": ["ignore"],
                "propagate": False,
            },
            "app.error": {
                "level": logging.WARNING,
                "handlers": ["error"],
                "propagate": False,
            },
            "uvicorn": {
                "level": app_level,
                "handlers": ["default"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": app_level,
                "handlers": ["default"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": logging.WARNING,
                "handlers": ["ignore"],
                "propagate": False,
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout,
            },
            "error": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stderr,
            },
            "ignore": {
                "class": "logging.NullHandler",
            },
        },
        "formatters": {
            "default": {
                "format": "[%(asctime)s] [%(levelname)s] [%(name)s] [%(process)d] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S %z",
                "class": "logging.Formatter",
            },
        },
    }


def _build_uvicorn_logging_config(
    default_level: int,
    access_level: int,
    access_handler: str,
) -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": default_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": default_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": [access_handler],
                "level": access_level,
                "propagate": False,
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "ignore": {
                "class": "logging.NullHandler",
            },
        },
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "[%(asctime)s] [%(levelname)s] [%(name)s] [%(process)d] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S %z",
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '[%(asctime)s] [%(levelname)s] [%(name)s] [%(process)d] %(client_addr)s - "%(request_line)s" %(status_code)s',  # noqa: E501
                "datefmt": "%Y-%m-%d %H:%M:%S %z",
            },
        },
    }


# Log config for local development
CONSOLE_LOGGING_CONFIG: dict = _build_console_logging_config(
    root_level=logging.INFO,
    app_level=logging.INFO,
)

PROD_CONSOLE_LOGGING_CONFIG: dict = _build_console_logging_config(
    root_level=logging.WARNING,
    app_level=logging.WARNING,
)

# Log config for local development
UVICORN_LOGGING_CONFIG: dict = _build_uvicorn_logging_config(
    default_level=logging.INFO,
    access_level=logging.INFO,
    access_handler="access",
)

PROD_UVICORN_LOGGING_CONFIG: dict = _build_uvicorn_logging_config(
    default_level=logging.WARNING,
    access_level=logging.WARNING,
    access_handler="ignore",
)


def get_console_logging_config(is_prod: bool) -> dict:
    """환경에 맞는 애플리케이션 로깅 설정 반환."""
    if is_prod:
        return _build_console_logging_config(
            root_level=logging.WARNING,
            app_level=logging.WARNING,
        )
    return _build_console_logging_config(
        root_level=logging.INFO,
        app_level=logging.INFO,
    )


def get_uvicorn_logging_config(is_prod: bool) -> dict:
    """환경에 맞는 uvicorn 로깅 설정 반환."""
    if is_prod:
        return _build_uvicorn_logging_config(
            default_level=logging.WARNING,
            access_level=logging.WARNING,
            access_handler="ignore",
        )
    return _build_uvicorn_logging_config(
        default_level=logging.INFO,
        access_level=logging.INFO,
        access_handler="access",
    )


logger = logging.getLogger("app")
access_logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.error")

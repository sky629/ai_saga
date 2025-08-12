import logging
import sys

# Log config for local development
CONSOLE_LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "": {"level": logging.INFO, "handlers": ["default"]},
        "app": {
            "level": logging.INFO,
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

# Log config for local development
UVICORN_LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "uvicorn": {
            "handlers": ["default"],
            "level": logging.INFO,
            "propagate": False,
        },
        "uvicorn.error": {"level": logging.INFO},
        "uvicorn.access": {
            "handlers": ["access"],
            "level": logging.INFO,
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

logger = logging.getLogger("app")
access_logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.error")

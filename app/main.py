import copy
from logging import config as logging_config
from typing import Any, Dict, Optional

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.auth.presentation.routes.auth import auth_public_router_v1
from app.common.exception import APIException
from app.common.logging import (
    CONSOLE_LOGGING_CONFIG,
    UVICORN_LOGGING_CONFIG,
    logger,
)
from app.common.middleware.access_log import access_log_middleware
from app.common.middleware.exception_handler import (
    api_exception_handler,
    general_exception_handler,
    http_exception_handler,
    starlette_http_exception_handler,
)
from app.common.middleware.rate_limiting import (
    get_rate_limit_handler,
    get_rate_limit_middleware,
    limiter,
)
from app.common.storage.postgres import postgres_storage
from app.common.storage.redis import pools
from app.dev.routes import dev_router
from app.game.presentation.routes.game_routes import game_router_v1
from config.settings import settings

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
except ImportError:  # pragma: no cover - optional dependency guard
    sentry_sdk = None
    FastApiIntegration = None
    StarletteIntegration = None

router = APIRouter()
SENTRY_FILTERED_VALUE = "[Filtered]"
SENSITIVE_FIELD_KEYWORDS = {
    "authorization",
    "cookie",
    "set-cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "jwt",
    "session",
}
_SENTRY_INITIALIZED = False


@router.get("/api/ping/")
async def pong():
    return {"ping": "pong!"}


def _should_enable_sentry(
    dsn: str, environment: str, enabled_environments: str
) -> bool:
    if not settings.sentry_enabled or not dsn.strip():
        return False

    enabled_envs = {
        env.strip().lower()
        for env in enabled_environments.split(",")
        if env.strip()
    }
    return environment.strip().lower() in enabled_envs


def _resolve_sentry_enable_logs(
    environment: str, configured_value: Optional[bool]
) -> bool:
    if configured_value is not None:
        return configured_value

    return environment.strip().lower() in {"local", "beta"}


def _is_sensitive_key(key: str) -> bool:
    normalized_key = key.replace("-", "_").lower()
    return any(
        sensitive in normalized_key for sensitive in SENSITIVE_FIELD_KEYWORDS
    )


def _mask_sensitive_data(payload: Any) -> Any:
    if isinstance(payload, dict):
        masked_payload: Dict[Any, Any] = {}
        for key, value in payload.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                masked_payload[key] = SENTRY_FILTERED_VALUE
                continue
            masked_payload[key] = _mask_sensitive_data(value)
        return masked_payload

    if isinstance(payload, list):
        return [_mask_sensitive_data(item) for item in payload]

    return payload


def _sentry_before_send(
    event: Dict[str, Any], hint: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    del hint
    masked_event = copy.deepcopy(event)

    request_data = masked_event.get("request")
    if isinstance(request_data, dict):
        request_data["headers"] = _mask_sensitive_data(
            request_data.get("headers", {})
        )
        request_data["data"] = _mask_sensitive_data(
            request_data.get("data", {})
        )

    masked_event["extra"] = _mask_sensitive_data(masked_event.get("extra", {}))

    user_data = masked_event.get("user")
    if isinstance(user_data, dict):
        if "email" in user_data:
            user_data["email"] = SENTRY_FILTERED_VALUE
        if "ip_address" in user_data:
            user_data["ip_address"] = SENTRY_FILTERED_VALUE

    return masked_event


def _initialize_sentry() -> bool:
    global _SENTRY_INITIALIZED

    if _SENTRY_INITIALIZED:
        return True

    if sentry_sdk is None:
        logger.warning("sentry-sdk is not installed. Skipping Sentry setup.")
        return False

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.KANG_ENV.lower(),
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
        ],
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profile_session_sample_rate=(
            settings.sentry_profile_session_sample_rate
        ),
        profile_lifecycle=settings.sentry_profile_lifecycle,
        enable_logs=_resolve_sentry_enable_logs(
            settings.KANG_ENV, settings.sentry_enable_logs
        ),
        before_send=_sentry_before_send,
        send_default_pii=settings.sentry_send_default_pii,
    )
    _SENTRY_INITIALIZED = True
    logger.info("Sentry initialized.")
    return True


def _set_sentry_request_context(request) -> None:
    if sentry_sdk is None:
        return

    user_id = request.headers.get("x-user-id")
    session_id = request.headers.get("x-session-id")
    if user_id:
        sentry_sdk.set_user({"id": user_id})
        sentry_sdk.set_tag("user_id", user_id)
    if session_id:
        sentry_sdk.set_tag("session_id", session_id)


def get_custom_openapi(f_app: FastAPI):
    if f_app.openapi_schema:
        return f_app.openapi_schema

    openapi_schema = get_openapi(
        title="Kang Server Swagger",
        version=__version__,
        routes=f_app.routes,
    )

    # security_scheme = {
    #     "BearerAuth": {
    #         "type": "http",
    #         "scheme": "bearer",
    #         "bearerFormat": "JWT",
    #     }
    # }
    # print(openapi_schema)
    # openapi_schema["components"]["securitySchemes"] = security_scheme
    app.openapi_schema = openapi_schema

    return openapi_schema


def create_app(logging_configuration: dict):
    logging_config.dictConfig(logging_configuration)

    tags_metadata = [
        {"name": "auth", "description": "auth endpoints"},
        {"name": "rag", "description": "rag endpoints"},
    ]

    app_args = {
        "middleware": (access_log_middleware,),
        "version": __version__,
    }
    if not settings.is_prod():
        app_args.update(
            {
                "docs_url": "/api/docs/",
                "openapi_url": "/api/docs/openapi.json",
                "openapi_tags": tags_metadata,
                "redoc_url": "/api/docs/redoc/",
            }
        )
    _app = FastAPI(**app_args)

    sentry_enabled = _should_enable_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.KANG_ENV,
        enabled_environments=settings.sentry_enabled_environments,
    )
    if sentry_enabled and _initialize_sentry():

        @_app.middleware("http")
        async def sentry_context_middleware(request, call_next):
            with sentry_sdk.push_scope():
                _set_sentry_request_context(request)
                return await call_next(request)

    # Add CORS middleware
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware
    _app.add_middleware(get_rate_limit_middleware())
    _app.state.limiter = limiter

    # Add exception handlers
    _app.add_exception_handler(APIException, api_exception_handler)
    _app.add_exception_handler(HTTPException, http_exception_handler)
    _app.add_exception_handler(
        StarletteHTTPException, starlette_http_exception_handler
    )
    _app.add_exception_handler(Exception, general_exception_handler)

    # Add rate limit exceeded handler
    _app.add_exception_handler(RateLimitExceeded, get_rate_limit_handler())

    _app.include_router(router)
    _app.include_router(auth_public_router_v1)
    _app.include_router(game_router_v1)

    # Dev routes (disabled in production)
    if not settings.is_prod():
        _app.include_router(dev_router)

    # Startup and shutdown events
    @_app.on_event("startup")
    async def startup_event():
        """Application startup events."""
        logger.info("Application starting up...")

    @_app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown events."""
        logger.info("Application shutting down...")

        # Close database connections
        await postgres_storage.close_all_pools()
        await pools.close_all()

        logger.info("Application shutdown complete")

    if not settings.is_prod():
        _app.openapi = lambda: get_custom_openapi(_app)

    _app.router.redirect_slashes = False
    return _app


app = create_app(CONSOLE_LOGGING_CONFIG)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_config=UVICORN_LOGGING_CONFIG,
        use_colors=True,
        reload=False,
    )

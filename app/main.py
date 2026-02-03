from logging import config as logging_config

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.auth.presentation.routes.auth import auth_public_router_v1
from app.dev.routes import dev_router
from app.game.presentation.routes.game_routes import game_router_v1
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
from config.settings import settings

router = APIRouter()


@router.get("/api/ping/")
async def pong():
    return {"ping": "pong!"}


def get_custom_openapi(f_app: FastAPI):
    from fastapi.openapi.utils import get_openapi

    from app import __version__ as app_version

    if f_app.openapi_schema:
        return f_app.openapi_schema

    openapi_schema = get_openapi(
        title="Kang Server Swagger",
        version=app_version,
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
    _app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
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

"""Rate limiting middleware using SlowAPI."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from config.settings import settings


def get_limiter_key(request):
    """Get rate limiting key from request."""
    # Use IP address for anonymous requests
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_limiter_key,
    default_limits=["60/minute"] if not settings.is_prod() else ["1/minute"],
    storage_uri=settings.redis_url,
    in_memory_fallback_enabled=True,
)

# Rate limit configurations for different endpoints
RATE_LIMITS = {
    "auth": "10/minute",  # Authentication endpoints
    "oauth": "5/minute",  # OAuth callback endpoints
    "general": "30/minute",  # General API endpoints
    "user_update": "5/minute",  # User profile updates
}


def get_rate_limit_middleware():
    """Get rate limiting middleware for FastAPI app."""
    return SlowAPIMiddleware


def get_rate_limit_handler():
    """Get rate limit exceeded handler."""
    return _rate_limit_exceeded_handler

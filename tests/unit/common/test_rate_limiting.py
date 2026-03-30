"""Rate limiting configuration tests."""

import app.main  # noqa: F401
from app.common.middleware.rate_limiting import (
    get_default_rate_limits,
    limiter,
)


def test_default_rate_limits_are_prod_safe():
    """기본 제한이 prod에서 정상 요청을 막지 않을 수준이어야 한다."""
    assert get_default_rate_limits() == ["60/minute"]


def test_ping_endpoint_is_exempt_from_rate_limiting():
    """헬스체크 ping 엔드포인트는 rate limit 대상이 아니어야 한다."""
    assert "app.main.pong" in limiter._exempt_routes

import time

from starlette.middleware import Middleware
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response

from app.common.logging import access_logger


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    요청/응답 및 처리 시간을 기록하는 함수 기반 미들웨어
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()

        log_extra = {
            "url": request.url.include_query_params(),
            "method": request.method,
            "user_agent": request.headers.get("User-Agent"),
            "path": request.url.path,
            "path_template": request.scope.get("path_template"),
            "client": request.client.host,
        }

        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            process_time = (time.time() - start_time) * 1000  # ms 단위
            status_code = response.status_code if response else 500

            # 최종 응답 상태와 처리 시간을 로그에 추가
            log_extra["status_code"] = status_code
            log_extra["process_time_ms"] = round(process_time, 2)

            # HTTP 버전과 함께 최종 로그 메시지 포맷팅
            log_message = "%s %s HTTP/%s %d" % (
                request.method,
                request.url.include_query_params(),
                request.scope["http_version"],
                status_code,
            )

            access_logger.info(log_message, extra=log_extra)


access_log_middleware = Middleware(AccessLogMiddleware)

from typing import Any, Dict, Optional

from starlette import status
from starlette.responses import JSONResponse, Response


class APIException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "An unknown error"
    headers: Dict = {}
    extra: Dict[str, Any] = {}

    def __init__(
        self,
        *,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        headers: Optional[dict] = None,
        extra: Optional[dict] = None,
    ):
        if message is not None:
            self.message = message

        if status_code is not None:
            self.status_code = status_code

        if headers is not None:
            self.headers = headers

        if extra is not None:
            self.extra = extra

        super().__init__(message, self.status_code)

    def __str__(self):
        return str(self.message)

    def __repr__(self):
        return self.__str__()

    def construct_response(self) -> Response:
        content = {
            "message": self.message,
        }
        if self.extra:
            content.update(self.extra)

        return JSONResponse(
            content=content,
            status_code=self.status_code,
            headers=self.headers,
        )


class Unauthorized(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Unauthorized"


class Forbidden(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Forbidden"


class NotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found"


class BadRequest(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Bad request"


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    message = "Conflict"


class ServerError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Internal server error."


class TooManyRequests(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Sorry, too many requests. Please try again later."

    def __init__(
        self,
        message: Optional[str] = None,
        retry_after_seconds: Optional[int] = None,
    ):
        headers = {}
        extra = {}
        if retry_after_seconds is not None:
            headers["Retry-After"] = str(retry_after_seconds)
            extra["retry_after_seconds"] = retry_after_seconds

        super().__init__(
            message=message,
            status_code=self.status_code,
            headers=headers or None,
            extra=extra or None,
        )

"""Common exception unit tests."""

from app.common.exception import TooManyRequests


class TestTooManyRequests:
    """429 예외 응답 payload를 검증한다."""

    def test_construct_response_includes_retry_after_seconds(self):
        exc = TooManyRequests(
            message="Gemini API Quota Exceeded. Please try again later.",
            retry_after_seconds=54,
        )

        response = exc.construct_response()

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "54"
        assert b'"retry_after_seconds":54' in response.body

"""Gemini retry delay parsing unit tests."""

from app.llm.providers.gemini import _extract_retry_after_seconds


class TestGeminiRetryDelay:
    """Gemini rate limit 에러의 retry delay 파싱을 검증한다."""

    def test_extract_retry_after_seconds_from_retry_sentence(self):
        error = Exception("Please retry in 23.640115089s.")

        retry_after = _extract_retry_after_seconds(error)

        assert retry_after == 24

    def test_extract_retry_after_seconds_from_retry_delay_field(self):
        error = Exception("{'retryDelay': '53s'}")

        retry_after = _extract_retry_after_seconds(error)

        assert retry_after == 53

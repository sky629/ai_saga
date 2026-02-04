"""Tests for Gemini Provider - TDD tests.

Tests for GeminiProvider using google.genai SDK.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.dto.llm_response import LLMResponse
from app.llm.providers.base import LLMProvider
from app.llm.providers.gemini import GeminiProvider


class TestGeminiProvider:
    """TDD tests for GeminiProvider."""

    @pytest.fixture
    def mock_genai(self):
        """Mock google.genai module."""
        with patch("app.llm.providers.gemini.genai") as mock:
            # Mock the Client and its async generate_content method
            mock_response = MagicMock()
            mock_response.text = "AI generated response"
            mock_response.usage_metadata = MagicMock(
                prompt_token_count=100,
                candidates_token_count=50,
                total_token_count=150,
            )
            mock_response.candidates = [MagicMock(finish_reason="STOP")]

            mock_client = MagicMock()
            mock_client.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )
            mock.Client.return_value = mock_client
            yield mock

    @pytest.fixture
    def provider(self, mock_genai):
        """Create GeminiProvider instance with mocked genai."""
        return GeminiProvider(api_key="test-api-key")

    async def test_gemini_provider_inherits_base(self, provider):
        """GeminiProvider should inherit from LLMProvider base class."""
        assert isinstance(provider, LLMProvider)

    async def test_generate_response_returns_llm_response(
        self, provider, mock_genai
    ):
        """generate_response should return LLMResponse dataclass."""
        response = await provider.generate_response(
            system_prompt="You are a game master.",
            messages=[{"role": "user", "content": "Look around"}],
        )

        assert isinstance(response, LLMResponse)
        assert response.content == "AI generated response"
        assert response.model == "gemini-2.0-flash"
        assert response.usage is not None
        assert response.usage.total_tokens == 150

    async def test_generate_response_with_temperature(
        self, provider, mock_genai
    ):
        """generate_response should accept temperature parameter."""
        await provider.generate_response(
            system_prompt="You are a game master.",
            messages=[{"role": "user", "content": "Attack the dragon"}],
            temperature=0.9,
        )

        # Verify API was called
        mock_client = mock_genai.Client.return_value
        mock_client.aio.models.generate_content.assert_called()

    async def test_generate_response_handles_empty_messages(self, provider):
        """Should handle empty messages gracefully."""
        with pytest.raises(ValueError, match="messages cannot be empty"):
            await provider.generate_response(
                system_prompt="You are a game master.",
                messages=[],
            )

    async def test_generate_response_retries_on_api_error(
        self, provider, mock_genai
    ):
        """Should retry on transient API errors using tenacity."""
        mock_client = mock_genai.Client.return_value

        mock_success_response = MagicMock()
        mock_success_response.text = "Success after retry"
        mock_success_response.usage_metadata = MagicMock(
            prompt_token_count=100,
            candidates_token_count=50,
            total_token_count=150,
        )
        mock_success_response.candidates = [MagicMock(finish_reason="STOP")]

        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[
                Exception("API rate limit"),
                mock_success_response,
            ]
        )

        response = await provider.generate_response(
            system_prompt="Test",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert response.content == "Success after retry"
        assert mock_client.aio.models.generate_content.call_count == 2

    async def test_provider_uses_correct_model_name(self, mock_genai):
        """Should use the correct Gemini model name."""
        provider = GeminiProvider(
            api_key="test-key", model_name="gemini-2.0-flash"
        )

        await provider.generate_response(
            system_prompt="Test",
            messages=[{"role": "user", "content": "Hello"}],
        )

        # Verify Client was instantiated
        mock_genai.Client.assert_called_with(api_key="test-key")

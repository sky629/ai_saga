"""Gemini 임베딩 provider 단위 테스트."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.providers.gemini_embedding_provider import GeminiEmbeddingProvider


class TestGeminiEmbeddingProvider:
    """GeminiEmbeddingProvider 로그/기본 동작 테스트."""

    @pytest.fixture
    def mock_genai(self):
        with patch(
            "app.llm.providers.gemini_embedding_provider.genai"
        ) as mock:
            mock_embedding = MagicMock()
            mock_embedding.values = [0.1] * 768
            mock_response = MagicMock()
            mock_response.embeddings = [mock_embedding]

            mock_client = MagicMock()
            mock_client.aio.models.embed_content = AsyncMock(
                return_value=mock_response
            )
            mock.Client.return_value = mock_client
            yield mock

    @pytest.fixture
    def provider(self, mock_genai):
        return GeminiEmbeddingProvider(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_generate_embedding_logs_payload_before_api_call(
        self, provider
    ):
        with patch(
            "app.llm.providers.gemini_embedding_provider.prompt_logger"
        ) as mock_logger:
            embedding = await provider.generate_embedding(
                "test embedding text"
            )

        assert len(embedding) == 768
        mock_logger.info.assert_called_once()
        _, payload_json = mock_logger.info.call_args.args
        payload = json.loads(payload_json)
        assert payload["event"] == "embedding_prompt"
        assert payload["provider"] == "gemini"
        assert payload["model"] == "gemini-embedding-001"
        assert payload["output_dimensionality"] == 768
        assert payload["text"] == "test embedding text"

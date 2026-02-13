"""Integration tests for Gemini Embedding Provider.

TDD Red Phase: Testing real Gemini API calls for embedding generation.
"""

import pytest

from app.llm.providers.gemini_embedding_provider import GeminiEmbeddingProvider


@pytest.mark.asyncio
class TestGeminiEmbeddingProvider:
    """Integration tests for Gemini embedding generation."""

    async def test_generate_embedding_success(self, gemini_api_key):
        """Valid text should generate 768-dimensional embedding."""
        provider = GeminiEmbeddingProvider(api_key=gemini_api_key)

        text = "The brave warrior explores the ancient dungeon."
        embedding = await provider.generate_embedding(text)

        # Should return 768-dimensional vector (Gemini text-embedding-004)
        assert isinstance(embedding, list)
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)

        # Vector values should be in reasonable range (typically -1 to 1)
        assert all(-2.0 <= x <= 2.0 for x in embedding)

    async def test_generate_embedding_different_texts_different_vectors(
        self, gemini_api_key
    ):
        """Different texts should generate different embeddings."""
        provider = GeminiEmbeddingProvider(api_key=gemini_api_key)

        text1 = "The warrior fights the dragon."
        text2 = "The chef cooks a delicious meal."

        embedding1 = await provider.generate_embedding(text1)
        embedding2 = await provider.generate_embedding(text2)

        # Embeddings should be different
        assert embedding1 != embedding2

        # But both should be valid 768-dimensional vectors
        assert len(embedding1) == 768
        assert len(embedding2) == 768

    async def test_generate_embedding_similar_texts_similar_vectors(
        self, gemini_api_key
    ):
        """Similar texts should have similar embeddings (high cosine similarity)."""
        from app.game.domain.services.vector_similarity_service import (
            VectorSimilarityService,
        )

        provider = GeminiEmbeddingProvider(api_key=gemini_api_key)

        text1 = "The brave knight slays the fierce dragon."
        text2 = "The courageous warrior defeats the mighty dragon."

        embedding1 = await provider.generate_embedding(text1)
        embedding2 = await provider.generate_embedding(text2)

        # Calculate similarity
        similarity = VectorSimilarityService.cosine_similarity(
            embedding1, embedding2
        )

        # Similar texts should have high similarity (> 0.7)
        assert similarity > 0.7

    async def test_generate_embedding_empty_text_raises_error(
        self, gemini_api_key
    ):
        """Empty text should raise ValueError."""
        provider = GeminiEmbeddingProvider(api_key=gemini_api_key)

        with pytest.raises(ValueError, match="empty"):
            await provider.generate_embedding("")

    async def test_generate_embedding_whitespace_only_raises_error(
        self, gemini_api_key
    ):
        """Whitespace-only text should raise ValueError."""
        provider = GeminiEmbeddingProvider(api_key=gemini_api_key)

        with pytest.raises(ValueError, match="empty"):
            await provider.generate_embedding("   \n\t  ")

    async def test_generate_embedding_long_text(self, gemini_api_key):
        """Long text (multiple paragraphs) should work."""
        provider = GeminiEmbeddingProvider(api_key=gemini_api_key)

        # Simulate a long game narrative
        text = """
        You enter the dark forest. The trees are ancient and twisted.
        Strange sounds echo through the mist. You see a faint light
        in the distance, flickering like a candle. As you approach,
        you notice footprints in the mud leading deeper into the woods.
        The air grows colder with each step.
        """

        embedding = await provider.generate_embedding(text)

        # Should still generate valid embedding
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)

    async def test_generate_embedding_special_characters(self, gemini_api_key):
        """Text with special characters should work."""
        provider = GeminiEmbeddingProvider(api_key=gemini_api_key)

        text = "You found a sword: ⚔️! HP +10, ATK +5. 🎉"
        embedding = await provider.generate_embedding(text)

        # Should generate valid embedding
        assert len(embedding) == 768

    async def test_generate_embedding_korean_text(self, gemini_api_key):
        """Korean text should generate valid embedding."""
        provider = GeminiEmbeddingProvider(api_key=gemini_api_key)

        text = "용감한 전사가 고대 던전을 탐험합니다."
        embedding = await provider.generate_embedding(text)

        # Should generate valid embedding
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)

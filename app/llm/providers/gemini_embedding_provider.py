"""Gemini Embedding Provider implementation.

Uses Google's genai SDK to generate text embeddings for RAG.
"""

import logging

from google import genai
from google.genai.errors import ClientError
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.common.exception import TooManyRequests
from app.llm.embedding_service_interface import EmbeddingServiceInterface

logger = logging.getLogger("uvicorn")


class GeminiEmbeddingProvider(EmbeddingServiceInterface):
    """Gemini embedding provider using Google genai SDK.

    Uses text-embedding-004 model (768 dimensions).
    Includes automatic retry logic for transient API errors.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-embedding-001",
        output_dimensionality: int = 768,
    ):
        """Initialize Gemini embedding provider.

        Args:
            api_key: Google AI API key
            model_name: Embedding model to use (default: gemini-embedding-001)
            output_dimensionality: Output vector dimension (default: 768)
                gemini-embedding-001 supports 3072 (default) but can be truncated
                to smaller dimensions (e.g., 768) via Matryoshka Representation Learning
        """
        self._client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.output_dimensionality = output_dimensionality

        masked_key = api_key[:5] + "*" * 5 if api_key else "None"
        logger.info(
            f"GeminiEmbeddingProvider initialized with model: {model_name}, "
            f"API Key: {masked_key}"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_not_exception_type((ValueError, TypeError)),
        reraise=True,
    )
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate vector embedding for the given text.

        Args:
            text: Text to embed (should not be empty)

        Returns:
            Vector embedding (768 dimensions for text-embedding-004)

        Raises:
            ValueError: If text is empty or invalid
            TooManyRequests: If API rate limit exceeded
            Exception: If API call fails after retries
        """
        # Validate input
        if not text or not text.strip():
            raise ValueError("Text cannot be empty or whitespace-only")

        try:
            # Call Gemini Embedding API with output dimensionality
            response = await self._client.aio.models.embed_content(
                model=self.model_name,
                contents=text,
                config={"output_dimensionality": self.output_dimensionality},
            )

            # Extract embedding vector
            if not response.embeddings:
                raise ValueError("No embedding returned from API")

            embedding = response.embeddings[0].values

            # Validate embedding dimensions
            if len(embedding) != self.output_dimensionality:
                raise ValueError(
                    f"Expected {self.output_dimensionality} dimensions, "
                    f"got {len(embedding)}"
                )

            return embedding

        except ClientError as e:
            # Handle rate limiting
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning(f"Gemini API rate limit hit: {e}")
                raise TooManyRequests("Gemini API rate limit exceeded") from e

            # Re-raise other client errors
            logger.error(f"Gemini API error: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error in generate_embedding: {e}")
            raise

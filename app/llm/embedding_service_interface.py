"""Embedding Service Interface.

Port (interface) for text embedding generation.
This follows the Dependency Inversion Principle - the application layer
depends on this interface, not on concrete implementations.
"""

from abc import ABC, abstractmethod


class EmbeddingServiceInterface(ABC):
    """Interface for text embedding generation services."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate vector embedding for the given text.

        Args:
            text: Text to embed (should not be empty)

        Returns:
            Vector embedding (768 dimensions for Gemini text-embedding-004)

        Raises:
            ValueError: If text is empty or invalid
            Exception: If API call fails after retries
        """
        pass

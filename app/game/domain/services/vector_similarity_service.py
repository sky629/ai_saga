"""Vector Similarity Service.

Domain service for calculating vector similarity and distance.
Used for RAG (Retrieval-Augmented Generation) context retrieval.
"""

import math


class VectorSimilarityService:
    """Service for vector similarity calculations."""

    @staticmethod
    def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Cosine similarity is the cosine of the angle between two vectors.
        Returns a value between -1.0 (opposite) and 1.0 (identical).
        0.0 means orthogonal (no correlation).

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (range: -1.0 to 1.0)

        Raises:
            ValueError: If vectors have different dimensions or zero magnitude
        """
        if len(vec1) != len(vec2):
            raise ValueError(
                f"Vectors must have the same dimension. "
                f"Got {len(vec1)} and {len(vec2)}"
            )

        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        # Check for zero magnitude
        if magnitude1 == 0.0 or magnitude2 == 0.0:
            raise ValueError(
                "Cannot calculate cosine similarity for vectors with zero magnitude"
            )

        # Calculate cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)

        return similarity

    @staticmethod
    def cosine_distance(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine distance between two vectors.

        Cosine distance = 1 - cosine_similarity
        This matches pgvector's `<=>` operator behavior.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine distance (range: 0.0 to 2.0)
            - 0.0: Identical vectors
            - 1.0: Orthogonal vectors
            - 2.0: Opposite vectors

        Raises:
            ValueError: If vectors have different dimensions or zero magnitude
        """
        similarity = VectorSimilarityService.cosine_similarity(vec1, vec2)
        distance = 1.0 - similarity

        return distance

    @staticmethod
    def is_similar(
        vec1: list[float], vec2: list[float], distance_threshold: float = 0.3
    ) -> bool:
        """Check if two vectors are similar based on distance threshold.

        Args:
            vec1: First vector
            vec2: Second vector
            distance_threshold: Maximum distance to consider similar (default: 0.3)

        Returns:
            True if cosine distance < threshold, False otherwise

        Raises:
            ValueError: If vectors have different dimensions or zero magnitude
        """
        distance = VectorSimilarityService.cosine_distance(vec1, vec2)
        return distance < distance_threshold

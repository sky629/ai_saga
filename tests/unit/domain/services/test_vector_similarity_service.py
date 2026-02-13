"""Unit tests for Vector Similarity Service.

TDD Red Phase: Testing vector similarity calculations.
"""

import pytest

from app.game.domain.services.vector_similarity_service import (
    VectorSimilarityService,
)


class TestVectorSimilarityService:
    """Test vector similarity calculations."""

    def test_cosine_similarity_identical_vectors(self):
        """동일한 벡터는 유사도 1.0을 반환해야 함."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        similarity = VectorSimilarityService.cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_cosine_similarity_orthogonal_vectors(self):
        """직교하는 벡터는 유사도 0.0을 반환해야 함."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        similarity = VectorSimilarityService.cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_cosine_similarity_opposite_vectors(self):
        """반대 방향 벡터는 유사도 -1.0을 반환해야 함."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]

        similarity = VectorSimilarityService.cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(-1.0, abs=1e-6)

    def test_cosine_similarity_arbitrary_vectors(self):
        """임의의 벡터 간 코사인 유사도 계산."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [4.0, 5.0, 6.0]

        similarity = VectorSimilarityService.cosine_similarity(vec1, vec2)

        # Manual calculation: (1*4 + 2*5 + 3*6) / (sqrt(14) * sqrt(77))
        # = 32 / (3.742 * 8.775) = 32 / 32.839 ≈ 0.9746
        assert similarity == pytest.approx(0.9746, abs=1e-3)

    def test_cosine_similarity_high_dimensional_vectors(self):
        """고차원 벡터(768차원)에 대한 유사도 계산."""
        vec1 = [0.1] * 768
        vec2 = [0.1] * 768

        similarity = VectorSimilarityService.cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_cosine_similarity_zero_magnitude_raises_error(self):
        """영벡터(magnitude 0)는 에러를 발생시켜야 함."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        with pytest.raises(ValueError, match="zero magnitude"):
            VectorSimilarityService.cosine_similarity(vec1, vec2)

    def test_cosine_similarity_mismatched_dimensions_raises_error(self):
        """차원이 다른 벡터는 에러를 발생시켜야 함."""
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        with pytest.raises(ValueError, match="same dimension"):
            VectorSimilarityService.cosine_similarity(vec1, vec2)

    def test_cosine_distance_identical_vectors(self):
        """동일한 벡터는 거리 0.0을 반환해야 함."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        distance = VectorSimilarityService.cosine_distance(vec1, vec2)

        assert distance == pytest.approx(0.0, abs=1e-6)

    def test_cosine_distance_orthogonal_vectors(self):
        """직교하는 벡터는 거리 1.0을 반환해야 함."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        distance = VectorSimilarityService.cosine_distance(vec1, vec2)

        assert distance == pytest.approx(1.0, abs=1e-6)

    def test_cosine_distance_opposite_vectors(self):
        """반대 방향 벡터는 거리 2.0을 반환해야 함."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]

        distance = VectorSimilarityService.cosine_distance(vec1, vec2)

        assert distance == pytest.approx(2.0, abs=1e-6)

    def test_is_similar_within_threshold(self):
        """임계값 이내의 거리는 유사하다고 판정해야 함."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.1, 2.1, 3.1]  # 매우 유사한 벡터

        is_similar = VectorSimilarityService.is_similar(
            vec1, vec2, distance_threshold=0.3
        )

        assert is_similar is True

    def test_is_similar_outside_threshold(self):
        """임계값을 초과하는 거리는 유사하지 않다고 판정해야 함."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]  # 직교 벡터 (거리 1.0)

        is_similar = VectorSimilarityService.is_similar(
            vec1, vec2, distance_threshold=0.3
        )

        assert is_similar is False

    def test_is_similar_exactly_at_threshold(self):
        """임계값과 정확히 같은 거리는 유사하지 않다고 판정해야 함 (미만 조건)."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        # 거리가 정확히 0.3이 되도록 조정된 벡터 생성
        # cosine_distance = 1 - cosine_similarity
        # 0.3 = 1 - similarity -> similarity = 0.7
        # 하지만 테스트의 의도는 경계값 테스트이므로 명확하게 작성

        # 실제로는 threshold와 같으면 is_similar는 False여야 함 (< 조건)
        # 이 테스트는 로직 명확성을 위해 유지
        is_similar = VectorSimilarityService.is_similar(
            vec1, vec2, distance_threshold=0.0
        )

        assert is_similar is False  # distance == 0.0이지만 < 조건이므로 False

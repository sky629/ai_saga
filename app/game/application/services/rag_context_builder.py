"""RAG Context Builder Service.

Application service for merging sliding window and RAG contexts.
Handles deduplication and chronological sorting.
"""

from typing import TypeAlias

from app.game.domain.entities.game_memory import GameMemoryEntity
from app.game.domain.entities.game_message import GameMessageEntity

RAGContextEntity: TypeAlias = GameMessageEntity | GameMemoryEntity


class RAGContextBuilder:
    """Service for building hybrid RAG contexts."""

    @staticmethod
    def select_relevant_rag_messages(
        rag_messages: list[RAGContextEntity],
        current_location: str,
        max_messages: int = 2,
        similarity_weight: float = 0.7,
        recency_weight: float = 0.3,
    ) -> list[RAGContextEntity]:
        """상태 일관성과 최신성 가중치를 반영해 RAG 후보를 선택."""
        if max_messages <= 0 or not rag_messages:
            return []

        filtered_messages = [
            message
            for message in rag_messages
            if RAGContextBuilder._is_state_consistent(
                message, current_location
            )
        ]
        if not filtered_messages:
            return []

        if similarity_weight < 0:
            similarity_weight = 0.0
        if recency_weight < 0:
            recency_weight = 0.0
        if similarity_weight == 0 and recency_weight == 0:
            similarity_weight = 1.0

        recency_sorted = sorted(
            filtered_messages,
            key=lambda message: message.created_at,
            reverse=True,
        )
        recency_rank_map = {
            message.id: index for index, message in enumerate(recency_sorted)
        }

        def rank_score(message: RAGContextEntity) -> float:
            recency_rank = recency_rank_map[message.id]
            similarity_score = (
                1 - message.similarity_distance
                if message.similarity_distance is not None
                else 0.0
            )
            recency_score = 1 / (recency_rank + 1)
            return (
                similarity_weight * similarity_score
                + recency_weight * recency_score
            )

        ranked_messages = sorted(
            filtered_messages,
            key=lambda message: (
                rank_score(message),
                message.created_at.timestamp(),
            ),
            reverse=True,
        )
        return ranked_messages[:max_messages]

    @staticmethod
    def merge_contexts(
        recent_messages: list[GameMessageEntity],
        rag_messages: list[RAGContextEntity],
    ) -> list[GameMessageEntity]:
        """Merge sliding window and RAG contexts with deduplication.

        Args:
            recent_messages: Recent messages from sliding window
            rag_messages: Similar messages from RAG search

        Returns:
            Merged and deduplicated messages sorted by created_at (oldest first)
        """
        # Combine all messages
        all_messages = recent_messages + rag_messages

        # Deduplicate by ID (preserve first occurrence)
        seen_ids = set()
        unique_messages = []

        for message in all_messages:
            if message.id not in seen_ids:
                seen_ids.add(message.id)
                unique_messages.append(message)

        # Sort by created_at (oldest first for LLM context)
        sorted_messages = sorted(
            unique_messages, key=lambda msg: msg.created_at
        )

        return sorted_messages

    @staticmethod
    def _is_state_consistent(
        message: RAGContextEntity, current_location: str
    ) -> bool:
        message_location = RAGContextBuilder._extract_location(message)
        if not message_location:
            return True

        normalized_current = RAGContextBuilder._normalize_text(
            current_location
        )
        normalized_message = RAGContextBuilder._normalize_text(
            message_location
        )
        if not normalized_current or not normalized_message:
            return True

        return normalized_current == normalized_message

    @staticmethod
    def _extract_location(message: RAGContextEntity) -> str | None:
        parsed = message.parsed_response
        if not isinstance(parsed, dict):
            return None

        state_changes = parsed.get("state_changes")
        if not isinstance(state_changes, dict):
            return None

        location = state_changes.get("location")
        if not isinstance(location, str):
            return None
        return location

    @staticmethod
    def _normalize_text(text: str) -> str:
        return text.strip().lower()

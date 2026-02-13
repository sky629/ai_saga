"""RAG Context Builder Service.

Application service for merging sliding window and RAG contexts.
Handles deduplication and chronological sorting.
"""

from app.game.domain.entities.game_message import GameMessageEntity


class RAGContextBuilder:
    """Service for building hybrid RAG contexts."""

    @staticmethod
    def merge_contexts(
        recent_messages: list[GameMessageEntity],
        rag_messages: list[GameMessageEntity],
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

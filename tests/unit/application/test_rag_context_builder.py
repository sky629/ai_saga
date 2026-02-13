"""Unit tests for RAG Context Builder.

TDD Red Phase: Testing hybrid context merging logic.
"""

from datetime import datetime, timedelta, timezone

from app.common.utils.id_generator import get_uuid7
from app.game.application.services.rag_context_builder import RAGContextBuilder
from app.game.domain.entities.game_message import GameMessageEntity
from app.game.domain.value_objects.message_role import MessageRole


class TestRAGContextBuilder:
    """Test RAG context merging and deduplication."""

    def test_merge_contexts_no_overlap(self):
        """중복이 없는 경우 모든 메시지가 포함되어야 함."""
        session_id = get_uuid7()
        now = datetime.now(timezone.utc)

        # Recent messages (most recent first)
        recent = [
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.USER,
                content="Recent 1",
                created_at=now - timedelta(minutes=1),
            ),
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content="Recent 2",
                created_at=now - timedelta(minutes=2),
            ),
        ]

        # RAG messages (older, similar messages)
        rag = [
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.USER,
                content="RAG 1",
                created_at=now - timedelta(hours=1),
            ),
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content="RAG 2",
                created_at=now - timedelta(hours=2),
            ),
        ]

        merged = RAGContextBuilder.merge_contexts(recent, rag)

        # Should have all 4 messages
        assert len(merged) == 4

        # Should be sorted by created_at (oldest first)
        assert merged[0].content == "RAG 2"
        assert merged[1].content == "RAG 1"
        assert merged[2].content == "Recent 2"
        assert merged[3].content == "Recent 1"

    def test_merge_contexts_with_duplicates(self):
        """중복 메시지는 제거되어야 함 (ID 기준)."""
        session_id = get_uuid7()
        now = datetime.now(timezone.utc)

        duplicate_id = get_uuid7()

        recent = [
            GameMessageEntity(
                id=duplicate_id,
                session_id=session_id,
                role=MessageRole.USER,
                content="Duplicate message",
                created_at=now - timedelta(minutes=1),
            ),
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content="Unique recent",
                created_at=now - timedelta(minutes=2),
            ),
        ]

        rag = [
            GameMessageEntity(
                id=duplicate_id,  # Same ID as recent[0]
                session_id=session_id,
                role=MessageRole.USER,
                content="Duplicate message",
                created_at=now - timedelta(minutes=1),
            ),
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content="Unique RAG",
                created_at=now - timedelta(hours=1),
            ),
        ]

        merged = RAGContextBuilder.merge_contexts(recent, rag)

        # Should have 3 unique messages (1 duplicate removed)
        assert len(merged) == 3

        # Check unique contents
        contents = [msg.content for msg in merged]
        assert "Duplicate message" in contents
        assert "Unique recent" in contents
        assert "Unique RAG" in contents

        # Duplicate should appear only once
        assert contents.count("Duplicate message") == 1

    def test_merge_contexts_empty_recent(self):
        """Recent가 비어있어도 RAG 메시지는 반환되어야 함."""
        session_id = get_uuid7()
        now = datetime.now(timezone.utc)

        recent = []

        rag = [
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.USER,
                content="RAG only",
                created_at=now - timedelta(hours=1),
            ),
        ]

        merged = RAGContextBuilder.merge_contexts(recent, rag)

        assert len(merged) == 1
        assert merged[0].content == "RAG only"

    def test_merge_contexts_empty_rag(self):
        """RAG가 비어있어도 Recent 메시지는 반환되어야 함."""
        session_id = get_uuid7()
        now = datetime.now(timezone.utc)

        recent = [
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.USER,
                content="Recent only",
                created_at=now - timedelta(minutes=1),
            ),
        ]

        rag = []

        merged = RAGContextBuilder.merge_contexts(recent, rag)

        assert len(merged) == 1
        assert merged[0].content == "Recent only"

    def test_merge_contexts_both_empty(self):
        """둘 다 비어있으면 빈 리스트 반환."""
        recent = []
        rag = []

        merged = RAGContextBuilder.merge_contexts(recent, rag)

        assert len(merged) == 0
        assert merged == []

    def test_merge_contexts_preserves_chronological_order(self):
        """시간순 정렬이 올바르게 유지되어야 함."""
        session_id = get_uuid7()
        now = datetime.now(timezone.utc)

        recent = [
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.USER,
                content="T5",
                created_at=now - timedelta(minutes=5),
            ),
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content="T3",
                created_at=now - timedelta(minutes=3),
            ),
        ]

        rag = [
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.USER,
                content="T10",
                created_at=now - timedelta(minutes=10),
            ),
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content="T7",
                created_at=now - timedelta(minutes=7),
            ),
        ]

        merged = RAGContextBuilder.merge_contexts(recent, rag)

        # Should be sorted: T10, T7, T5, T3 (oldest to newest)
        assert merged[0].content == "T10"
        assert merged[1].content == "T7"
        assert merged[2].content == "T5"
        assert merged[3].content == "T3"

    def test_merge_contexts_handles_same_timestamp(self):
        """동일한 타임스탬프를 가진 메시지도 처리 가능해야 함."""
        session_id = get_uuid7()
        now = datetime.now(timezone.utc)

        recent = [
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.USER,
                content="Same time 1",
                created_at=now,
            ),
            GameMessageEntity(
                id=get_uuid7(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content="Same time 2",
                created_at=now,
            ),
        ]

        rag = []

        merged = RAGContextBuilder.merge_contexts(recent, rag)

        # Should have both messages despite same timestamp
        assert len(merged) == 2

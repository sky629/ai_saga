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

    def test_select_relevant_rag_messages_filters_state_conflict(self):
        """현재 location과 충돌하는 과거 메시지는 제외해야 함."""
        session_id = get_uuid7()
        now = datetime.now(timezone.utc)

        same_location = GameMessageEntity(
            id=get_uuid7(),
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="동일 장소 단서",
            parsed_response={
                "state_changes": {"location": "네오 서울 - 뒷골목 아지트"}
            },
            created_at=now - timedelta(minutes=10),
        )
        conflict_location = GameMessageEntity(
            id=get_uuid7(),
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="충돌 장소 단서",
            parsed_response={
                "state_changes": {"location": "네오 서울 - 기업 연구소"}
            },
            created_at=now - timedelta(minutes=2),
        )
        no_location_metadata = GameMessageEntity(
            id=get_uuid7(),
            session_id=session_id,
            role=MessageRole.USER,
            content="위치 메타 없음",
            parsed_response={"state_changes": {}},
            created_at=now - timedelta(minutes=1),
        )

        selected = RAGContextBuilder.select_relevant_rag_messages(
            rag_messages=[
                same_location,
                conflict_location,
                no_location_metadata,
            ],
            current_location="네오 서울 - 뒷골목 아지트",
            max_messages=3,
        )

        contents = [message.content for message in selected]
        assert "동일 장소 단서" in contents
        assert "위치 메타 없음" in contents
        assert "충돌 장소 단서" not in contents

    def test_select_relevant_rag_messages_applies_recency_weight(self):
        """가중치 설정에 따라 최신 메시지가 우선될 수 있어야 함."""
        session_id = get_uuid7()
        now = datetime.now(timezone.utc)

        older_but_high_similarity_rank = GameMessageEntity(
            id=get_uuid7(),
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="유사도 높지만 오래된 메시지",
            parsed_response={"state_changes": {"location": "아지트"}},
            created_at=now - timedelta(days=2),
        )
        newer_but_low_similarity_rank = GameMessageEntity(
            id=get_uuid7(),
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="유사도 낮지만 최신 메시지",
            parsed_response={"state_changes": {"location": "아지트"}},
            created_at=now - timedelta(minutes=5),
        )

        selected = RAGContextBuilder.select_relevant_rag_messages(
            rag_messages=[
                older_but_high_similarity_rank,
                newer_but_low_similarity_rank,
            ],
            current_location="아지트",
            max_messages=1,
            similarity_weight=0.1,
            recency_weight=0.9,
        )

        assert len(selected) == 1
        assert selected[0].content == "유사도 낮지만 최신 메시지"

    def test_select_relevant_rag_messages_uses_distance_score(self):
        """입력 순서가 아니라 실제 distance 점수를 우선 반영해야 함."""
        session_id = get_uuid7()
        now = datetime.now(timezone.utc)

        lower_similarity = GameMessageEntity(
            id=get_uuid7(),
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="입력 순서는 앞이지만 distance가 나쁜 메시지",
            parsed_response={"state_changes": {"location": "아지트"}},
            similarity_distance=0.29,
            created_at=now - timedelta(minutes=1),
        )
        higher_similarity = GameMessageEntity(
            id=get_uuid7(),
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="입력 순서는 뒤지만 distance가 좋은 메시지",
            parsed_response={"state_changes": {"location": "아지트"}},
            similarity_distance=0.05,
            created_at=now - timedelta(days=1),
        )

        selected = RAGContextBuilder.select_relevant_rag_messages(
            rag_messages=[lower_similarity, higher_similarity],
            current_location="아지트",
            max_messages=1,
            similarity_weight=0.9,
            recency_weight=0.1,
        )

        assert len(selected) == 1
        assert (
            selected[0].content == "입력 순서는 뒤지만 distance가 좋은 메시지"
        )

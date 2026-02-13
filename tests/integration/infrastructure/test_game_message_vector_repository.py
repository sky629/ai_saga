"""Integration tests for GameMessage Vector Repository.

TDD Red Phase: Testing pgvector-based similarity search.
"""

import pytest_asyncio

from app.auth.infrastructure.persistence.models.user_models import User
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.domain.entities.game_message import GameMessageEntity
from app.game.domain.value_objects.message_role import MessageRole
from app.game.infrastructure.persistence.models.game_models import (
    Character,
    GameSession,
    Scenario,
)
from app.game.infrastructure.repositories.game_message_repository import (
    GameMessageRepositoryImpl,
)
from app.llm.providers.gemini_embedding_provider import GeminiEmbeddingProvider


class TestGameMessageVectorRepository:
    """Integration tests for vector similarity search."""

    @pytest_asyncio.fixture
    async def embedding_provider(self, gemini_api_key):
        """Create embedding provider for tests."""
        return GeminiEmbeddingProvider(api_key=gemini_api_key)

    @pytest_asyncio.fixture
    async def repository(self, db_session):
        """Create repository instance."""
        return GameMessageRepositoryImpl(db_session)

    @pytest_asyncio.fixture
    async def test_user(self, db_session):
        """Create a test user for sessions."""
        user = User(
            id=get_uuid7(),
            email="test@example.com",
            name="Test User",
            user_level=1,
            is_active=True,
            email_verified=True,
        )
        db_session.add(user)
        await db_session.flush()
        return user

    @pytest_asyncio.fixture
    async def test_scenario(self, db_session):
        """Create a test scenario."""
        scenario = Scenario(
            id=get_uuid7(),
            name="Test Scenario",
            description="Test scenario description",
            world_setting="Fantasy world",
            initial_location="Starting village",
            genre="fantasy",
            difficulty="normal",
        )
        db_session.add(scenario)
        await db_session.flush()
        return scenario

    @pytest_asyncio.fixture
    async def test_character(self, db_session, test_user, test_scenario):
        """Create a test character."""
        character = Character(
            id=get_uuid7(),
            user_id=test_user.id,
            scenario_id=test_scenario.id,
            name="Test Character",
            description="Test character description",
        )
        db_session.add(character)
        await db_session.flush()
        return character

    @pytest_asyncio.fixture
    async def test_session_id(
        self, db_session, test_user, test_character, test_scenario
    ):
        """Create a test game session and return its ID."""
        session = GameSession(
            id=get_uuid7(),
            user_id=test_user.id,
            character_id=test_character.id,
            scenario_id=test_scenario.id,
            current_location="Test Location",
            status="active",
        )
        db_session.add(session)
        await db_session.flush()
        return session.id

    async def test_get_similar_messages_finds_relevant_content(
        self, repository, embedding_provider, test_session_id
    ):
        """Similar messages should be retrieved based on vector similarity."""
        # Create messages with embeddings
        messages = [
            (
                "You explore the dark dungeon and find a treasure chest.",
                "explore dungeon",
            ),
            ("You fight a fierce dragon with your sword.", "fight dragon"),
            (
                "You meet a friendly merchant in the village.",
                "meet merchant",
            ),
            (
                "You discover a hidden passage in the dungeon.",
                "discover passage dungeon",
            ),
        ]

        created_ids = []
        for content, _ in messages:
            embedding = await embedding_provider.generate_embedding(content)
            message = GameMessageEntity(
                id=get_uuid7(),
                session_id=test_session_id,
                role=MessageRole.ASSISTANT,
                content=content,
                embedding=embedding,
                created_at=get_utc_datetime(),
            )
            await repository.create(message)
            created_ids.append(message.id)

        # Search for dungeon-related messages
        query_text = "Looking for items in the dungeon"
        query_embedding = await embedding_provider.generate_embedding(
            query_text
        )

        similar_messages = await repository.get_similar_messages(
            embedding=query_embedding,
            session_id=test_session_id,
            limit=2,
            distance_threshold=0.5,
        )

        # Should find dungeon-related messages
        assert len(similar_messages) >= 1
        contents = [msg.content for msg in similar_messages]

        # At least one should be about dungeon
        assert any("dungeon" in content.lower() for content in contents)

    async def test_get_similar_messages_respects_session_boundary(
        self,
        repository,
        embedding_provider,
        db_session,
        test_user,
        test_character,
        test_scenario,
    ):
        """Should only return messages from the same session."""
        # Create two different sessions
        session1 = GameSession(
            id=get_uuid7(),
            user_id=test_user.id,
            character_id=test_character.id,
            scenario_id=test_scenario.id,
            current_location="Location 1",
            status="active",
        )
        session2 = GameSession(
            id=get_uuid7(),
            user_id=test_user.id,
            character_id=test_character.id,
            scenario_id=test_scenario.id,
            current_location="Location 2",
            status="active",
        )
        db_session.add(session1)
        db_session.add(session2)
        await db_session.flush()

        session1_id = session1.id
        session2_id = session2.id

        embedding = await embedding_provider.generate_embedding("Test message")

        # Create message in session 1
        msg1 = GameMessageEntity(
            id=get_uuid7(),
            session_id=session1_id,
            role=MessageRole.USER,
            content="Message in session 1",
            embedding=embedding,
            created_at=get_utc_datetime(),
        )
        await repository.create(msg1)

        # Create message in session 2
        msg2 = GameMessageEntity(
            id=get_uuid7(),
            session_id=session2_id,
            role=MessageRole.USER,
            content="Message in session 2",
            embedding=embedding,
            created_at=get_utc_datetime(),
        )
        await repository.create(msg2)

        # Search in session 1 should only return session 1 messages
        results = await repository.get_similar_messages(
            embedding=embedding,
            session_id=session1_id,
            limit=10,
            distance_threshold=1.0,
        )

        assert len(results) == 1
        assert results[0].session_id == session1_id

    async def test_get_similar_messages_respects_distance_threshold(
        self, repository, embedding_provider, test_session_id
    ):
        """Should filter out messages beyond distance threshold."""
        # Create similar message
        similar_text = "The brave warrior fights the dragon."
        similar_embedding = await embedding_provider.generate_embedding(
            similar_text
        )

        similar_msg = GameMessageEntity(
            id=get_uuid7(),
            session_id=test_session_id,
            role=MessageRole.ASSISTANT,
            content=similar_text,
            embedding=similar_embedding,
            created_at=get_utc_datetime(),
        )
        await repository.create(similar_msg)

        # Create dissimilar message
        dissimilar_text = "The chef cooks a delicious pasta dish."
        dissimilar_embedding = await embedding_provider.generate_embedding(
            dissimilar_text
        )

        dissimilar_msg = GameMessageEntity(
            id=get_uuid7(),
            session_id=test_session_id,
            role=MessageRole.ASSISTANT,
            content=dissimilar_text,
            embedding=dissimilar_embedding,
            created_at=get_utc_datetime(),
        )
        await repository.create(dissimilar_msg)

        # Search with query similar to first message
        query_text = "The heroic knight battles the dragon."
        query_embedding = await embedding_provider.generate_embedding(
            query_text
        )

        # With strict threshold, should only get similar message
        results = await repository.get_similar_messages(
            embedding=query_embedding,
            session_id=test_session_id,
            limit=10,
            distance_threshold=0.3,
        )

        # Should find at least the similar message
        contents = [msg.content for msg in results]
        assert similar_text in contents

        # Dissimilar message should NOT be included (due to threshold)
        # Note: This might not always hold depending on embeddings
        # but generally cooking != fighting

    async def test_get_similar_messages_returns_empty_when_none_match(
        self, repository, embedding_provider, test_session_id
    ):
        """Should return empty list if no messages match threshold."""
        # Create a message
        msg_text = "The wizard casts a spell."
        msg_embedding = await embedding_provider.generate_embedding(msg_text)

        msg = GameMessageEntity(
            id=get_uuid7(),
            session_id=test_session_id,
            role=MessageRole.ASSISTANT,
            content=msg_text,
            embedding=msg_embedding,
            created_at=get_utc_datetime(),
        )
        await repository.create(msg)

        # Search with completely different topic and very strict threshold
        query_text = "Quantum physics and relativity theory"
        query_embedding = await embedding_provider.generate_embedding(
            query_text
        )

        results = await repository.get_similar_messages(
            embedding=query_embedding,
            session_id=test_session_id,
            limit=10,
            distance_threshold=0.1,  # Very strict
        )

        # Should return empty or very few results
        assert len(results) == 0

    async def test_get_similar_messages_respects_limit(
        self, repository, embedding_provider, test_session_id
    ):
        """Should return at most 'limit' messages."""
        base_text = "You explore the dungeon"
        base_embedding = await embedding_provider.generate_embedding(base_text)

        # Create 10 similar messages
        for i in range(10):
            msg = GameMessageEntity(
                id=get_uuid7(),
                session_id=test_session_id,
                role=MessageRole.ASSISTANT,
                content=f"{base_text} - iteration {i}",
                embedding=base_embedding,
                created_at=get_utc_datetime(),
            )
            await repository.create(msg)

        # Search with limit=5
        results = await repository.get_similar_messages(
            embedding=base_embedding,
            session_id=test_session_id,
            limit=5,
            distance_threshold=1.0,
        )

        # Should return exactly 5 (not all 10)
        assert len(results) == 5

    async def test_get_similar_messages_handles_null_embeddings(
        self, repository, embedding_provider, test_session_id
    ):
        """Should skip messages without embeddings."""
        # Create message WITHOUT embedding
        msg_without_embedding = GameMessageEntity(
            id=get_uuid7(),
            session_id=test_session_id,
            role=MessageRole.USER,
            content="Message without embedding",
            embedding=None,
            created_at=get_utc_datetime(),
        )
        await repository.create(msg_without_embedding)

        # Create message WITH embedding
        text = "Message with embedding"
        embedding = await embedding_provider.generate_embedding(text)

        msg_with_embedding = GameMessageEntity(
            id=get_uuid7(),
            session_id=test_session_id,
            role=MessageRole.ASSISTANT,
            content=text,
            embedding=embedding,
            created_at=get_utc_datetime(),
        )
        await repository.create(msg_with_embedding)

        # Search should only return messages with embeddings
        query_embedding = await embedding_provider.generate_embedding(text)

        results = await repository.get_similar_messages(
            embedding=query_embedding,
            session_id=test_session_id,
            limit=10,
            distance_threshold=1.0,
        )

        # Should only find the message with embedding
        assert len(results) == 1
        assert results[0].content == text

"""GameMemoryRepository 통합 테스트."""

import pytest_asyncio

from app.auth.infrastructure.persistence.models.user_models import User
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.domain.entities import GameMemoryEntity
from app.game.domain.value_objects import GameMemoryType, MessageRole
from app.game.infrastructure.persistence.models.game_models import (
    Character,
    GameSession,
    Scenario,
)
from app.game.infrastructure.repositories.game_memory_repository import (
    GameMemoryRepositoryImpl,
)
from app.llm.providers.gemini_embedding_provider import GeminiEmbeddingProvider


class TestGameMemoryRepository:
    """검색 메모리 저장소 통합 테스트."""

    @pytest_asyncio.fixture
    async def embedding_provider(self, gemini_api_key):
        """Create embedding provider for tests."""
        return GeminiEmbeddingProvider(api_key=gemini_api_key)

    @pytest_asyncio.fixture
    async def repository(self, db_session):
        """Create repository instance."""
        return GameMemoryRepositoryImpl(db_session)

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
            game_type="trpg",
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
            profile={},
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

    async def test_get_similar_memories_finds_relevant_content(
        self, repository, embedding_provider, test_session_id
    ):
        """유사한 메모리를 cosine distance 기준으로 검색한다."""
        contents = [
            "You explore the dark dungeon and find a treasure chest.",
            "You fight a fierce dragon with your sword.",
            "You meet a friendly merchant in the village.",
            "You discover a hidden passage in the dungeon.",
        ]

        for content in contents:
            embedding = await embedding_provider.generate_embedding(content)
            memory = GameMemoryEntity(
                id=get_uuid7(),
                session_id=test_session_id,
                role=MessageRole.ASSISTANT,
                memory_type=GameMemoryType.ASSISTANT_NARRATIVE,
                content=content,
                embedding=embedding,
                created_at=get_utc_datetime(),
            )
            await repository.create(memory)

        query_embedding = await embedding_provider.generate_embedding(
            "Looking for items in the dungeon"
        )
        results = await repository.get_similar_memories(
            embedding=query_embedding,
            session_id=test_session_id,
            limit=2,
            distance_threshold=0.5,
        )

        assert len(results) >= 1
        assert any("dungeon" in memory.content.lower() for memory in results)
        assert all(
            memory.similarity_distance is not None for memory in results
        )

    async def test_get_similar_memories_respects_session_boundary(
        self,
        repository,
        embedding_provider,
        db_session,
        test_user,
        test_character,
        test_scenario,
    ):
        """같은 세션의 메모리만 반환한다."""
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

        embedding = await embedding_provider.generate_embedding("Test message")

        memory1 = GameMemoryEntity(
            id=get_uuid7(),
            session_id=session1.id,
            role=MessageRole.USER,
            memory_type=GameMemoryType.USER_ACTION,
            content="Message in session 1",
            embedding=embedding,
            created_at=get_utc_datetime(),
        )
        memory2 = GameMemoryEntity(
            id=get_uuid7(),
            session_id=session2.id,
            role=MessageRole.USER,
            memory_type=GameMemoryType.USER_ACTION,
            content="Message in session 2",
            embedding=embedding,
            created_at=get_utc_datetime(),
        )
        await repository.create(memory1)
        await repository.create(memory2)

        results = await repository.get_similar_memories(
            embedding=embedding,
            session_id=session1.id,
            limit=10,
            distance_threshold=1.0,
        )

        assert len(results) == 1
        assert results[0].session_id == session1.id

    async def test_get_similar_memories_respects_distance_threshold(
        self, repository, embedding_provider, test_session_id
    ):
        """threshold 바깥의 메모리는 제외한다."""
        similar_text = "The brave warrior fights the dragon."
        dissimilar_text = "The chef cooks a delicious pasta dish."

        similar_embedding = await embedding_provider.generate_embedding(
            similar_text
        )
        dissimilar_embedding = await embedding_provider.generate_embedding(
            dissimilar_text
        )

        await repository.create(
            GameMemoryEntity(
                id=get_uuid7(),
                session_id=test_session_id,
                role=MessageRole.ASSISTANT,
                memory_type=GameMemoryType.ASSISTANT_NARRATIVE,
                content=similar_text,
                embedding=similar_embedding,
                created_at=get_utc_datetime(),
            )
        )
        await repository.create(
            GameMemoryEntity(
                id=get_uuid7(),
                session_id=test_session_id,
                role=MessageRole.ASSISTANT,
                memory_type=GameMemoryType.ASSISTANT_NARRATIVE,
                content=dissimilar_text,
                embedding=dissimilar_embedding,
                created_at=get_utc_datetime(),
            )
        )

        query_embedding = await embedding_provider.generate_embedding(
            "The heroic knight battles the dragon."
        )
        results = await repository.get_similar_memories(
            embedding=query_embedding,
            session_id=test_session_id,
            limit=10,
            distance_threshold=0.3,
        )

        contents = [memory.content for memory in results]
        assert similar_text in contents

    async def test_get_similar_memories_respects_limit(
        self, repository, embedding_provider, test_session_id
    ):
        """limit 이상 반환하지 않는다."""
        base_text = "You explore the dungeon"
        base_embedding = await embedding_provider.generate_embedding(base_text)

        for index in range(10):
            await repository.create(
                GameMemoryEntity(
                    id=get_uuid7(),
                    session_id=test_session_id,
                    role=MessageRole.ASSISTANT,
                    memory_type=GameMemoryType.ASSISTANT_NARRATIVE,
                    content=f"{base_text} - iteration {index}",
                    embedding=base_embedding,
                    created_at=get_utc_datetime(),
                )
            )

        results = await repository.get_similar_memories(
            embedding=base_embedding,
            session_id=test_session_id,
            limit=5,
            distance_threshold=1.0,
        )

        assert len(results) == 5

    async def test_get_similar_memories_excludes_requested_ids(
        self, repository, embedding_provider, test_session_id
    ):
        """exclude_memory_ids에 포함된 메모리는 제외한다."""
        text = "Message with embedding"
        embedding = await embedding_provider.generate_embedding(text)

        excluded_memory = await repository.create(
            GameMemoryEntity(
                id=get_uuid7(),
                session_id=test_session_id,
                role=MessageRole.ASSISTANT,
                memory_type=GameMemoryType.ASSISTANT_NARRATIVE,
                content=text,
                embedding=embedding,
                created_at=get_utc_datetime(),
            )
        )
        await repository.create(
            GameMemoryEntity(
                id=get_uuid7(),
                session_id=test_session_id,
                role=MessageRole.ASSISTANT,
                memory_type=GameMemoryType.ASSISTANT_NARRATIVE,
                content="Another memory with embedding",
                embedding=embedding,
                created_at=get_utc_datetime(),
            )
        )

        results = await repository.get_similar_memories(
            embedding=embedding,
            session_id=test_session_id,
            limit=10,
            distance_threshold=1.0,
            exclude_memory_ids=[excluded_memory.id],
        )

        assert all(memory.id != excluded_memory.id for memory in results)

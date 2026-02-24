"""Game Dependency Injection Container.

FastAPI의 Depends와 연동하여 Use Case 및 Repository 의존성을 관리합니다.
외부 라이브러리 없이 순수 Python으로 구현된 간단한 DI 패턴입니다.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.infrastructure.repositories.user_progression_repository import (
    UserProgressionRepositoryImpl,
)
from app.game.application.ports import (
    CacheServiceInterface,
    CharacterRepositoryInterface,
    GameMessageRepositoryInterface,
    GameSessionRepositoryInterface,
    ImageGenerationServiceInterface,
    LLMServiceInterface,
    ScenarioRepositoryInterface,
    UserProgressionInterface,
)
from app.game.application.services.embedding_cache_service import (
    EmbeddingCacheService,
)
from app.game.application.use_cases import (
    CreateCharacterUseCase,
    DeleteSessionUseCase,
    GenerateEndingUseCase,
    GenerateIllustrationUseCase,
    ProcessActionUseCase,
    StartGameUseCase,
)
from app.game.infrastructure.adapters import (
    CacheServiceAdapter,
    LLMServiceAdapter,
)
from app.game.infrastructure.adapters.image_service import (
    ImageGenerationServiceAdapter,
)
from app.game.infrastructure.repositories import (
    CharacterRepositoryImpl,
    GameMessageRepositoryImpl,
    GameSessionRepositoryImpl,
    ScenarioRepositoryImpl,
)
from app.llm.embedding_service_interface import EmbeddingServiceInterface
from app.llm.providers.gemini_embedding_provider import GeminiEmbeddingProvider
from config.settings import settings


class GameContainer:
    """Game 모듈 의존성 컨테이너.

    Use Case와 Repository 인스턴스를 생성하고 관리합니다.
    DB 세션은 요청마다 주입받아 사용합니다.
    """

    def __init__(self, db: AsyncSession):
        self._db = db
        self._cache: CacheServiceInterface | None = None
        self._llm: LLMServiceInterface | None = None
        self._image: ImageGenerationServiceInterface | None = None
        self._embedding: EmbeddingServiceInterface | None = None
        self._embedding_cache: EmbeddingCacheService | None = None

    # === Service Singletons (per request) ===

    @property
    def cache_service(self) -> CacheServiceInterface:
        """캐시 서비스 (싱글톤)."""
        if self._cache is None:
            self._cache = CacheServiceAdapter()
        return self._cache

    @property
    def llm_service(self) -> LLMServiceInterface:
        """등록LLM 서비스 (싱글톤)."""
        if self._llm is None:
            self._llm = LLMServiceAdapter()
        return self._llm

    @property
    def image_service(self) -> ImageGenerationServiceInterface:
        """이미지 생성 서비스 (싱글톤)."""
        if self._image is None:
            self._image = ImageGenerationServiceAdapter()
        return self._image

    @property
    def embedding_service(self) -> EmbeddingServiceInterface:
        """Embedding 서비스 (싱글톤)."""
        if self._embedding is None:
            self._embedding = GeminiEmbeddingProvider(
                api_key=settings.gemini_api_key
            )
        return self._embedding

    @property
    def embedding_cache_service(self) -> EmbeddingCacheService:
        """Embedding 캐싱 서비스 (싱글톤)."""
        if self._embedding_cache is None:
            self._embedding_cache = EmbeddingCacheService(
                embedding_service=self.embedding_service,
                cache_service=self.cache_service,
            )
        return self._embedding_cache

    # === Repository Factories ===

    def session_repository(self) -> GameSessionRepositoryInterface:
        """게임 세션 저장소."""
        return GameSessionRepositoryImpl(self._db)

    def character_repository(self) -> CharacterRepositoryInterface:
        """캐릭터 저장소."""
        return CharacterRepositoryImpl(self._db)

    def scenario_repository(self) -> ScenarioRepositoryInterface:
        """시나리오 저장소."""
        return ScenarioRepositoryImpl(self._db)

    def message_repository(self) -> GameMessageRepositoryInterface:
        """메시지 저장소."""
        return GameMessageRepositoryImpl(self._db)

    def user_progression_repository(self) -> UserProgressionInterface:
        """유저 게임 진행도 저장소."""
        return UserProgressionRepositoryImpl(self._db)

    # === Use Case Factories ===

    def process_action_use_case(self) -> ProcessActionUseCase:
        """액션 처리 유스케이스."""
        return ProcessActionUseCase(
            session_repository=self.session_repository(),
            message_repository=self.message_repository(),
            character_repository=self.character_repository(),
            scenario_repository=self.scenario_repository(),
            llm_service=self.llm_service,
            cache_service=self.cache_service,
            image_service=self.image_service,
            embedding_service=self.embedding_cache_service,  # ✅ 캐싱 적용
            user_progression=self.user_progression_repository(),
        )

    def start_game_use_case(self) -> StartGameUseCase:
        """게임 시작 유스케이스."""
        return StartGameUseCase(
            session_repository=self.session_repository(),
            character_repository=self.character_repository(),
            scenario_repository=self.scenario_repository(),
            message_repository=self.message_repository(),
            llm_service=self.llm_service,
            image_service=self.image_service,
        )

    def generate_ending_use_case(self) -> GenerateEndingUseCase:
        """엔딩 생성 유스케이스."""

        return GenerateEndingUseCase(
            session_repository=self.session_repository(),
            message_repository=self.message_repository(),
            llm_service=self.llm_service,
            user_progression=self.user_progression_repository(),
        )

    def create_character_use_case(self) -> CreateCharacterUseCase:
        """캐릭터 생성 유스케이스."""
        return CreateCharacterUseCase(
            character_repository=self.character_repository(),
            session_repository=self.session_repository(),
            scenario_repository=self.scenario_repository(),
            user_progression=self.user_progression_repository(),
        )

    def delete_session_use_case(self) -> DeleteSessionUseCase:
        """세션 삭제 유스케이스."""
        return DeleteSessionUseCase(
            session_repository=self.session_repository(),
            character_repository=self.character_repository(),
        )

    def generate_illustration_use_case(self) -> GenerateIllustrationUseCase:
        return GenerateIllustrationUseCase(
            session_repository=self.session_repository(),
            message_repository=self.message_repository(),
            image_service=self.image_service,
        )

    # === Query Factories (CQRS Read Side) ===

    def get_scenarios_query(self):
        """시나리오 목록 조회 쿼리."""
        from app.game.application.queries import GetScenariosQuery

        return GetScenariosQuery(self._db)

    def get_user_sessions_query(self):
        """사용자 세션 목록 조회 쿼리."""
        from app.game.application.queries import GetUserSessionsQuery

        return GetUserSessionsQuery(self._db)

    async def get_session_history_query(self):
        """세션 히스토리 조회 쿼리."""
        from app.common.storage.redis import pools
        from app.game.application.queries import GetSessionHistoryQuery

        redis = await pools.get_connection()
        return GetSessionHistoryQuery(self._db, redis)

    def get_characters_query(self):
        """캐릭터 목록 조회 쿼리."""
        from app.game.application.queries.get_characters import (
            GetCharactersQuery,
        )

        return GetCharactersQuery(self._db)

    def get_session_query(self):
        """게임 세션 단건 조회 쿼리."""
        from app.game.application.queries import GetSessionQuery

        return GetSessionQuery(self.session_repository())


# === FastAPI Depends Integration ===


def get_game_container(db: AsyncSession) -> GameContainer:
    """FastAPI Depends용 팩토리."""
    return GameContainer(db)

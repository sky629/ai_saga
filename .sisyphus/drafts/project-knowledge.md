# AI Saga - Project Knowledge Base

> Prometheus가 프로젝트를 완벽히 숙지하기 위해 정리한 레퍼런스 문서
> 마지막 업데이트: 2026-02-19

---

## 1. Project Overview

**AI Saga** = AI 기반 텍스트 MUD(Multi-User Dungeon) 게임 백엔드

| 항목 | 기술 |
|------|------|
| Framework | FastAPI (async Python) |
| Python | 3.13 |
| DB | PostgreSQL 15 + pgvector (벡터 검색) |
| Cache | Redis 7 |
| AI | Google Gemini (텍스트 생성 + 임베딩) |
| Image | Imagen 3.0 + Cloudflare R2 |
| Architecture | Clean Architecture + CQRS |
| Testing | TDD (pytest + pytest-asyncio) |
| ID | UUID v7 (uuid-utils) |
| Package Manager | UV (`uv run`) |
| Message Queue | Kafka (향후 멀티플레이어) |

---

## 2. Clean Architecture Layers

**의존성 방향**: `Domain <- Application <- Infrastructure <- Presentation`

```
app/
├── auth/                    # 인증 도메인
│   ├── domain/              # Entity, VO, Service (순수 비즈니스 로직)
│   ├── application/         # Use Case, Query, Port (오케스트레이션)
│   ├── infrastructure/      # Repository, Adapter, ORM (기술적 구현)
│   ├── presentation/        # Route, Schema (API)
│   ├── container.py         # DI Container
│   └── dependencies.py      # FastAPI Depends
├── game/                    # 게임 도메인 (같은 구조)
├── llm/                     # LLM 통합 (Gemini)
├── common/                  # 공유 모듈 (storage, middleware, utils)
└── dev/                     # 개발 전용 라우트
```

---

## 3. Domain Models (핵심 엔티티)

### Auth Domain

**UserEntity** (frozen Pydantic)
- `id: UUID(v7)`, `email: str(unique)`, `name: str`, `profile_image_url: Optional[str]`
- `user_level: UserLevel`, `is_active: bool`, `email_verified: bool`
- `created_at`, `updated_at`, `last_login_at`

**SocialAccountEntity** (frozen Pydantic)
- `id: UUID(v7)`, `user_id: UUID(FK)`, `provider: AuthProvider(GOOGLE)`
- `provider_user_id: str`, `provider_data: dict`, `access/refresh_token`, `scope_granted: List[str]`

### Game Domain

**ScenarioEntity** (게임 시나리오 템플릿)
- `id`, `name(1-200)`, `description`, `world_setting`, `initial_location(max 200)`
- `genre: ScenarioGenre`, `difficulty: ScenarioDifficulty`
- `system_prompt_override: Optional[str]`, `max_turns(default=30)`, `is_active: bool`
- Methods: `deactivate()`, `activate()`, `is_playable`, `effective_system_prompt`

**CharacterEntity** (플레이어 캐릭터)
- `id`, `user_id(FK)`, `scenario_id(FK)`, `name(1-100)`, `description: Optional`
- `stats: CharacterStats(hp, max_hp, level, experience, current_experience)`
- `inventory: list[str]`, `is_active: bool`
- Methods: `update_stats()`, `add_to_inventory()`, `remove_from_inventory()`, `deactivate()`
- Properties: `is_alive` (stats.is_alive AND is_active)
- **CharacterStats**: `take_damage()`, `heal()`, `level_up()`, `gain_experience()` (자동 레벨업, 필요경험치 = level * 100)

**GameSessionEntity** (게임 세션)
- `id`, `user_id(FK)`, `character_id(FK)`, `scenario_id(FK)`
- `current_location: str`, `game_state: dict`, `status: SessionStatus`
- `turn_count(ge=0)`, `max_turns(gt=0)`, `ending_type: Optional[EndingType]`
- `started_at`, `ended_at: Optional`, `last_activity_at`
- Methods: `advance_turn()`, `complete(ending)`, `pause()`, `resume()`, `update_location()`, `update_game_state(changes)`
- Properties: `is_active`, `is_final_turn`, `remaining_turns`

**GameMessageEntity** (게임 메시지)
- `id`, `session_id(FK)`, `role: MessageRole(USER/ASSISTANT/SYSTEM)`
- `content(min=1)`, `parsed_response: Optional[dict]`, `token_count: Optional[int]`
- `image_url: Optional[str]`, `embedding: Optional[list[float]](768dim)`, `created_at`
- Properties: `is_player_message`, `is_ai_response`, `summary(100자)`

### Value Objects (Enum)

| VO | Values |
|----|--------|
| AuthProvider | GOOGLE |
| UserLevel | NORMAL=100, ADMIN=1000 |
| SessionStatus | ACTIVE, PAUSED, COMPLETED, ENDED |
| EndingType | VICTORY, DEFEAT, NEUTRAL |
| MessageRole | USER, ASSISTANT, SYSTEM |
| ScenarioGenre | FANTASY, SCI_FI, CYBERPUNK, HORROR, SURVIVAL, MYSTERY, HISTORICAL, POST_APOCALYPTIC |
| ScenarioDifficulty | EASY, NORMAL, HARD, NIGHTMARE |

**GameState** (frozen VO): `items`, `visited_locations`, `met_npcs`, `discoveries`
**StateChanges** (frozen VO): `hp_change`, `experience_gained`, `items_gained/lost`, `location`, `npcs_met`, `discoveries`

### Domain Services

| Service | 역할 |
|---------|------|
| GameMasterService | 게임 규칙, LLM 응답 파싱, 상태 변경 추출, 엔딩 판단 |
| GameStateService | StateChanges를 GameState에 적용 (아이템/위치/NPC/발견 관리) |
| VectorSimilarityService | 코사인 유사도 계산 (RAG 컨텍스트 검색용) |

---

## 4. Application Layer (Use Cases & Queries)

### Use Cases (Commands - 상태 변경)

| Use Case | Domain | 핵심 로직 |
|----------|--------|-----------|
| StartGameUseCase | game | 캐릭터/시나리오 검증 -> 세션 생성 -> LLM 초기 내러티브 -> 이미지 생성 |
| ProcessActionUseCase | game | 멱등성 체크 -> 턴 진행 -> 임베딩 -> 하이브리드 컨텍스트(SW+RAG) -> LLM -> 상태 업데이트 -> 캐시 |
| GenerateEndingUseCase | game | 세션 로드 -> 최근 메시지 컨텍스트 -> 엔딩 LLM -> 세션 완료 |
| CreateCharacterUseCase | game | 시나리오 검증 -> 캐릭터 생성 (초기 스탯 HP=100, Level=1) |
| DeleteSessionUseCase | game | 소유권 검증 -> 세션 삭제 -> 캐릭터 삭제 (1:1) |
| HandleOAuthCallbackUseCase | auth | OAuth 코드 교환 -> 사용자 생성/링크 -> JWT 발급 |
| CreateUserUseCase | auth | 소셜 계정 확인 -> 이메일 확인 -> 사용자 생성 (멱등) |
| RefreshTokenUseCase | auth | JWT 검증 -> 세션 확인 -> 새 액세스 토큰 |
| LogoutUseCase | auth | 토큰 블랙리스트 -> 세션 삭제 |
| UpdateUserProfileUseCase | auth | 부분 업데이트 (name, profile_image_url) |
| DisconnectSocialAccountUseCase | auth | 소유권 검증 -> 잠금 방지 -> 삭제 |
| RefreshGoogleTokenUseCase | auth | Google 리프레시 토큰 -> 새 액세스 토큰 |

### Queries (CQRS 읽기)

| Query | Domain | 패턴 |
|-------|--------|------|
| GetScenariosQuery | game | 활성 시나리오 목록 (필터) |
| GetUserSessionsQuery | game | 커서 기반 페이지네이션, 상태 필터 |
| GetSessionQuery | game | 단일 조회 + 소유권 검증 |
| GetSessionHistoryQuery | game | 커서 페이지네이션 + Redis 캐싱 (과거=캐시, 최신=DB) |
| GetCharactersQuery | game | 사용자별 활성 캐릭터 목록 |
| GetUserQuery | auth | ID/이메일로 조회 |
| GetSocialAccountsQuery | auth | 사용자별 소셜 계정 (프로바이더 필터) |

### Ports (Repository Interfaces)

**Game Ports**: GameSessionRepositoryInterface, CharacterRepositoryInterface, ScenarioRepositoryInterface, GameMessageRepositoryInterface, LLMServiceInterface, CacheServiceInterface, ImageGenerationServiceInterface

**Auth Ports**: UserRepositoryInterface, SocialAccountRepositoryInterface, TokenServiceInterface, AuthCacheInterface, OAuthProviderInterface

### Application Services

| Service | 역할 |
|---------|------|
| RAGContextBuilder | 슬라이딩 윈도우 + RAG 메시지 병합 & 중복 제거 |
| EmbeddingCacheService | SHA-256 해시 기반 임베딩 캐싱 (24시간 TTL, 30-50% API 절약) |

---

## 5. Infrastructure Layer

### ORM -> Entity 변환 패턴

```python
# Repository.save() 패턴
async def save(self, entity: Entity) -> Entity:
    result = await self._db.execute(select(ORM).where(ORM.id == entity.id))
    orm = result.scalar_one_or_none()
    if orm is None:
        orm = ORM(id=entity.id, ...)
        self._db.add(orm)
    else:
        for key, value in Mapper.to_dict(entity).items():
            setattr(orm, key, value)
    await self._db.flush()
    await self._db.refresh(orm)
    return Mapper.to_entity(orm)
```

### 외부 어댑터

| Adapter | 역할 |
|---------|------|
| LLMServiceAdapter | Gemini API 래퍼 (temperature=0.8) |
| CacheServiceAdapter | Redis get/set/delete + 분산 락 (자동 TTL 연장) |
| ImageGenerationServiceAdapter | Imagen 3 -> R2 업로드 (key: session/user/uuid.png) |
| GoogleAuthAdapter | OAuth 2.0 플로우 (state 검증, 토큰 교환) |
| TokenAdapter | JWT 생성/검증/블랙리스트 (HS256, JTI) |
| AuthCacheAdapter | Redis 기반 세션/토큰/OAuth 상태 관리 |

### DB Session 관리

- **Read/Write 분리**: `postgres_storage.read_db()` / `postgres_storage.write_db()`
- **Read pool**: size=8, overflow=15
- **Write pool**: size=10, overflow=20
- **Auto-commit**: Write session 컨텍스트 종료 시 자동 커밋
- **Auto-rollback**: 예외 발생 시 자동 롤백

### 벡터 검색 (pgvector)

```python
# cosine_distance 연산자 (<=>)
GameMessage.embedding.cosine_distance(embedding) < distance_threshold
```
- 768차원 (Gemini text-embedding-004)
- 기본 threshold: 0.3, 기본 limit: 5

---

## 6. Presentation Layer (API)

### 엔드포인트 요약

**Auth** (`/api/v1/auth`):
- `GET /google/login/` - OAuth 로그인 시작
- `GET /google/callback/` - OAuth 콜백
- `POST /refresh/` - 토큰 갱신
- `POST /google/refresh/` - Google 토큰 갱신 (인증필요)
- `POST /logout/` - 로그아웃 (인증필요)
- `GET /self/` - 내 정보 (인증필요)
- `PUT /self/` - 프로필 수정 (인증필요)
- `GET /self/social-accounts/` - 소셜 계정 목록 (인증필요)
- `DELETE /self/social-accounts/{id}/` - 소셜 연결 해제 (인증필요)

**Game** (`/api/v1/game`):
- `GET /scenarios/` - 시나리오 목록 (인증필요)
- `GET /characters/` - 캐릭터 목록 (인증필요)
- `POST /characters/` - 캐릭터 생성 (201) (인증필요)
- `GET /sessions/` - 세션 목록 (커서 페이지네이션) (인증필요)
- `POST /sessions/` - 게임 시작 (201, Idempotency-Key) (인증필요)
- `GET /sessions/{id}/` - 세션 상세 (인증필요)
- `DELETE /sessions/{id}/` - 세션 삭제 (204) (인증필요)
- `POST /sessions/{id}/actions/` - 액션 제출 (Idempotency-Key) (인증필요)
- `GET /sessions/{id}/messages/` - 메시지 히스토리 (커서 페이지네이션) (인증필요)

**기타**:
- `GET /api/ping/` - 헬스체크 (공개)
- `POST /api/v1/dev/token/` - 개발용 토큰 (dev only)
- `GET /api/v1/dev/health/` - 개발용 헬스 (dev only)
- `POST /api/v1/dev/seed-scenarios/` - 시나리오 시드 (dev only)

### 미들웨어 스택

1. AccessLogMiddleware (요청/응답 로깅)
2. CORSMiddleware (설정 기반 origins)
3. SlowAPIMiddleware (Redis 기반 레이트 리밋)
4. Exception Handlers (APIException -> JSON)

### 인증 플로우

- JWT Bearer 토큰 (HS256, 30분)
- Refresh Token: HttpOnly 쿠키 (7일)
- Token Blacklist: Redis 기반

### 에러 응답 형식

```json
{"message": "에러 설명"}
```
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 409: Conflict
- 422: Validation Error
- 429: Rate Limited
- 500: Server Error

---

## 7. DI (Dependency Injection) 패턴

```
Route Handler
  -> Depends(get_container) [write_db] 또는 get_read_container [read_db]
  -> Container.use_case_factory()
  -> UseCase.__init__(repository: Interface, service: Interface, ...)
  -> UseCase.execute(input) -> output
```

**Container 규칙**:
- Services: Lazy singleton (요청 당 1개)
- Repositories: 매번 새 인스턴스
- Use Cases: 매번 새 인스턴스 (모든 의존성 주입)
- Type Aliases: `ProcessActionDep = Annotated[ProcessActionUseCase, Depends(...)]`

---

## 8. Testing Patterns (TDD)

### 테스트 구조

```
tests/
├── conftest.py              # app, client, async_client 픽스처
├── unit/
│   ├── domain/              # 순수 로직 (mock 없음, DB 없음)
│   ├── application/         # AsyncMock으로 리포지토리 모킹
│   └── infrastructure/      # 어댑터 유닛 테스트
├── integration/
│   ├── conftest.py          # db_session (실제 DB + pgvector + auto-rollback)
│   └── infrastructure/      # 실제 DB로 리포지토리 테스트
├── e2e/                     # TestClient로 전체 HTTP 사이클
└── llm/                     # LLM 프로바이더 테스트
```

### 핵심 패턴

**Domain Unit Test**: Mock 없음 -> Entity 메서드 -> assert 불변성
**Application Unit Test**: `AsyncMock(spec=Interface)` -> Use Case -> `assert_called_once()`
**Integration Test**: `db_session` 픽스처 -> FK 먼저 생성 -> `flush()` -> DB 직접 쿼리 확인
**E2E Test**: `TestClient` -> HTTP 요청 -> 상태 코드 + 응답 본문 확인

### 테스트 실행

```bash
uv run pytest                          # 전체
uv run pytest --cov=app                # 커버리지 포함
uv run pytest tests/unit/ -v           # 유닛만
uv run pytest tests/integration/ -v    # 통합만
```

---

## 9. 새 기능 추가 체크리스트

1. **Domain**: Entity/VO/Service + Unit Test
2. **Application Port**: Repository Interface 정의
3. **Application Use Case/Query**: 오케스트레이션 + Unit Test (Mock)
4. **Infrastructure ORM**: SQLAlchemy 모델 + Mapper
5. **Infrastructure Repository**: Port 구현체 + Integration Test
6. **Infrastructure Adapter**: 외부 서비스 (필요시)
7. **DI**: Container factory + dependencies.py Dep
8. **Presentation Schema**: Request/Response DTO
9. **Presentation Route**: API 엔드포인트 + E2E Test
10. **Main.py**: Router 등록 (새 라우터인 경우)
11. **Migration**: `uv run alembic revision --autogenerate -m "desc"`
12. **Final**: `uv run pytest --cov=app`

---

## 10. Key Conventions

- **모든 ID**: UUID v7 (`uuid_utils.uuid7()`)
- **모든 Entity**: Frozen Pydantic (`model_config = {"frozen": True}`)
- **상태 변경**: `entity.model_copy(update={...})` 또는 도메인 메서드 (새 인스턴스 반환)
- **에러 처리**: Domain -> `ValueError`, Auth -> `Unauthorized/BadRequest/NotFound`, Infra -> `ServerError`
- **멱등성**: Redis 캐시 키 `game:idempotency:{session_id}:{key}` (TTL 600s)
- **하이브리드 컨텍스트**: 슬라이딩 윈도우(최근 10개) + RAG(유사 5개) 병합
- **이미지 생성**: 설정 간격에 따라 (0=매턴, N=N턴마다)
- **커서 페이지네이션**: UUID v7 기반, `(items, next_cursor, has_more)` 반환
- **JSONB 사용**: stats, inventory, game_state, parsed_response, provider_data

---

## 11. Frontend (ai_saga_front)

**위치**: `/Users/kitaekang/Documents/dev/ai_saga_front` (별도 git repo)

| 항목 | 기술 |
|------|------|
| Framework | React 19 |
| Build | Vite 7 |
| Language | TypeScript 5.9 |
| Styling | Tailwind CSS 4 + 사이버펑크 테마 |
| Data Fetching | TanStack Query v5 |
| Routing | React Router DOM v7 |
| HTTP | Axios (Bearer 토큰 자동 주입) |
| Font | DungGeunMo (픽셀 아트) |

### 프론트엔드 구조

```
src/
├── App.tsx              # QueryClient + BrowserRouter + AuthProvider + ErrorBoundary
├── AppRoutes.tsx        # 라우트 정의 (PrivateRoute 가드)
├── context/AuthContext  # 인증 상태 (token, user, login/logout)
├── pages/
│   ├── Login            # Google OAuth 로그인
│   ├── GoogleCallback   # OAuth 콜백 (토큰 추출)
│   ├── Dashboard        # 세션 목록, 새 게임 시작 플로우
│   └── GameSession      # 메인 게임 플레이 인터페이스
├── components/
│   ├── layout/          # PixelLayout, PixelCard, PixelButton, CyberpunkLayout, RetroWindow
│   ├── game/            # MessageHistory, ActionInput, StatusPanel, GameStatePanel, Modals
│   └── common/          # ErrorBoundary
├── services/gameService # Axios API 클라이언트 (모든 백엔드 엔드포인트)
├── types/               # API 타입 (Response/Request 인터페이스)
└── utils/cn.ts          # clsx + twMerge
```

### 라우트

| Path | Page | Auth | 설명 |
|------|------|------|------|
| `/login` | Login | Public | Google OAuth |
| `/auth/login/success` | GoogleCallback | Public | 콜백 처리 |
| `/` | Dashboard | Private | 세션 목록 |
| `/game/:characterId` | GameSession | Private | 게임 플레이 |

### API 연결

- **Base URL**: `http://localhost:8000/api/v1` (하드코딩)
- **토큰**: `localStorage.access_token` → Axios 인터셉터 Bearer 주입
- **멱등성**: `crypto.randomUUID()` Idempotency-Key
- **페이지네이션**: 커서 기반 (`CursorPaginatedResponse<T>`)

### 스타일 테마 (사이버펑크)

- Cyan #00F0FF (주요), Pink #FF0055 (위험), Gold #FFD700 (레벨/아이템)
- Green #00FF9D (긍정), BG #0B0C15 (배경), Panel #151621
- CRT 스캔라인, 네온 글로우, 3D 버튼 효과

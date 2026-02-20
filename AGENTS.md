# AGENTS.md — AI Saga Coding Agent Guide

## Commands

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run a single test file
uv run pytest tests/unit/domain/test_game_session_entity.py -v

# Run a single test class
uv run pytest tests/unit/domain/test_game_session_entity.py::TestGameSessionEntity -v

# Run a single test method
uv run pytest tests/unit/domain/test_game_session_entity.py::TestGameSessionEntity::test_advance_turn -v

# Run by directory
uv run pytest tests/unit/ -v          # Unit tests only
uv run pytest tests/integration/ -v   # Integration tests only

# Skip slow tests
uv run pytest -m "not slow"

# Formatting and linting (pre-commit runs these automatically)
uv run black app/ tests/
uv run isort app/ tests/
uv run flake8 app/ tests/

# Database migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head

# Start dev server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Architecture — Clean Architecture + CQRS

Dependency direction: **Domain <- Application <- Infrastructure <- Presentation**

```
app/{domain}/
├── domain/           # Pure business logic (entities, value objects, services)
│   ├── entities/     # Frozen Pydantic models — state changes return new instances
│   ├── value_objects/# Enums and immutable objects
│   └── services/     # Stateless domain services (no I/O, no external deps)
├── application/      # Orchestration
│   ├── ports/        # Repository interfaces (ABC) — dependency inversion
│   ├── use_cases/    # Commands (write operations)
│   └── queries/      # CQRS read side
├── infrastructure/   # Technical implementation
│   ├── persistence/  # ORM models + mappers (entity <-> ORM conversion)
│   ├── repositories/ # Port implementations (AsyncSession-based)
│   └── adapters/     # External services (LLM, cache, OAuth, image gen)
├── presentation/     # API layer
│   └── routes/       # FastAPI routers + schemas/ (request/response DTOs)
├── container.py      # DI container — factory methods for use cases and repos
└── dependencies.py   # FastAPI Depends() wiring + type aliases
```

Router registration: `app/main.py` -> `app.include_router(router)`

## TDD Workflow — MANDATORY

All development follows Red -> Green -> Refactor. No exceptions.

1. **RED**: Write a failing test first. Run it — it MUST fail.
2. **GREEN**: Write the minimum code to make it pass. Layer order: Domain -> Application -> Infrastructure -> Presentation.
3. **REFACTOR**: Clean up while keeping tests green.

Never write production code without a failing test first.

## Code Style

**Formatting**: Black (line-length=79), isort (profile=black). Pre-commit enforces both.
**Linting**: flake8 (max-line-length=88, ignores E501/W503/F722/E203).
**Types**: All entities are frozen Pydantic BaseModel (`model_config = {"frozen": True}`).

### Imports — isort black profile, 79-char lines

```python
# 1. stdlib
from datetime import datetime
from typing import Optional
from uuid import UUID

# 2. third-party
from pydantic import BaseModel, Field

# 3. local — always absolute imports from app.
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.domain.entities import GameSessionEntity
from app.game.domain.value_objects import EndingType, SessionStatus
```

### Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Entity | `{Name}Entity` | `GameSessionEntity`, `CharacterEntity` |
| Value Object | `{Name}` (enum) or `{Name}` (frozen model) | `SessionStatus`, `GameState` |
| Use Case | `{Verb}{Noun}UseCase` | `ProcessActionUseCase`, `StartGameUseCase` |
| Query | `Get{Noun}Query` | `GetUserSessionsQuery`, `GetScenariosQuery` |
| Repository impl | `{Name}RepositoryImpl` | `GameSessionRepositoryImpl` |
| Port/interface | `{Name}Interface` | `GameSessionRepositoryInterface` |
| Mapper | `{Name}Mapper` (static methods) | `GameSessionMapper.to_entity()` |
| Request DTO | `{Action}Request` | `StartGameRequest`, `GameActionRequest` |
| Response DTO | `{Name}Response` | `GameSessionResponse`, `GameActionResponse` |
| DI alias | `{Name}Dep` | `ProcessActionDep = Annotated[..., Depends(...)]` |
| Test class | `Test{Subject}` | `TestGameSessionEntity` |
| Test method | `test_{what_it_tests}` | `test_advance_turn_increments_count` |

### ID Generation — UUID v7 only

```python
from app.common.utils.id_generator import get_uuid7
entity_id = get_uuid7()  # NEVER use uuid4()
```

### Entity Immutability

Entities are frozen. Mutations return new instances:
```python
session = session.advance_turn()           # returns new GameSessionEntity
session = session.complete(EndingType.VICTORY)
character = character.add_to_inventory("sword")
updated = entity.model_copy(update={"field": new_value})
```

### Error Handling

- **Domain layer**: Raise `ValueError` for business rule violations.
- **Application layer**: Raise custom exceptions from `app.common.exception`:
  - `BadRequest` (400), `Unauthorized` (401), `Forbidden` (403)
  - `NotFound` (404), `Conflict` (409), `ServerError` (500)
- **Infrastructure layer**: Wrap external errors in `ServerError`.
- Error response format: `{"message": "description"}`.

### Docstrings

Module-level and class-level docstrings in Korean. Method docstrings are optional but use Korean when present. Comments are Korean.
```python
"""GameSession Domain Entity."""

class GameSessionEntity(BaseModel):
    """게임 세션 도메인 엔티티.

    불변(frozen) 모델로, 상태 변경 시 새 인스턴스를 반환합니다.
    """
```

## Testing Patterns

### Unit tests (domain) — no mocks, no DB
```python
# tests/unit/domain/test_{feature}.py
from app.common.utils.id_generator import get_uuid7
from app.common.utils.datetime import get_utc_datetime

class TestGameSessionEntity:
    def test_advance_turn(self):
        session = GameSessionEntity(id=get_uuid7(), ..., started_at=get_utc_datetime(), ...)
        updated = session.advance_turn()
        assert updated.turn_count == 1
        assert updated is not session  # immutability check
```

### Unit tests (application) — mock repositories with AsyncMock
```python
# tests/unit/application/test_{use_case}.py
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_repo():
    return AsyncMock(spec=GameSessionRepositoryInterface)

@pytest.mark.asyncio
async def test_use_case(mock_repo):
    mock_repo.get_by_id.return_value = session_entity
    use_case = StartGameUseCase(session_repository=mock_repo, ...)
    result = await use_case.execute(user_id, input_data)
    mock_repo.save.assert_called_once()
```

### Integration tests — real DB via db_session fixture
```python
# tests/integration/infrastructure/test_{repo}.py
@pytest.mark.asyncio
async def test_save(db_session):
    # Create FK dependencies first (User, Scenario, etc.)
    db_session.add(User(id=user_id, email="test@example.com", name="Test"))
    await db_session.flush()
    repo = GameSessionRepositoryImpl(db_session)
    saved = await repo.save(entity)
    await db_session.flush()
    # Query DB directly to verify
    result = await db_session.execute(select(GameSession).where(...))
    assert result.scalar_one().user_id == user_id
```

### E2E tests — full HTTP cycle via TestClient
```python
# tests/e2e/test_{feature}_routes.py
def test_endpoint_requires_auth(client):
    response = client.get("/api/v1/game/scenarios/")
    assert response.status_code == 401
```

## Key Conventions

- **Package manager**: UV — always `uv run` (never `poetry run` or bare `python`)
- **Python**: 3.13
- **API prefix**: `/api/v1/{domain}/` (e.g., `/api/v1/game/sessions/`)
- **Pagination**: Cursor-based (UUID v7), returns `(items, next_cursor, has_more)`
- **Idempotency**: Redis cache key `game:idempotency:{session_id}:{key}`, TTL 600s
- **DB sessions**: Read/write separation via `postgres_storage.read_db()` / `.write_db()`
- **DI pattern**: Container(db) -> factory methods -> Use Cases with interface deps
- **Embeddings**: pgvector 768-dim (Gemini text-embedding-004), cosine distance
- **Async**: All I/O is async/await. Repositories use `AsyncSession`.
- **Respond in Korean** when communicating with the user (per CLAUDE.md).

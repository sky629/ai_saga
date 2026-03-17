# AGENTS.md — AI Saga Backend

Coding agent guide for the AI Saga backend (AI-powered text MUD game).
Python 3.13 · FastAPI · Clean Architecture · TDD mandatory.

## Build / Lint / Test Commands

All commands use `uv run` (not poetry, not raw python).

```bash
# Lint and format (pre-commit runs these automatically)
uv run black --check app/ tests/        # Code formatting check
uv run black app/ tests/                 # Auto-format
uv run isort --check app/ tests/         # Import sort check
uv run isort app/ tests/                 # Auto-sort imports
uv run flake8 app/ tests/               # Linting

# Full quality gate (run before every commit)
uv run black --check app/ tests/ && uv run isort --check app/ tests/ && uv run flake8 app/ tests/

# Tests
uv run pytest                            # Full suite
uv run pytest tests/unit/                # Unit tests only
uv run pytest tests/integration/         # Integration tests only
uv run pytest tests/e2e/                 # E2E tests only
uv run pytest tests/unit/domain/test_dice_service.py           # Single file
uv run pytest tests/unit/domain/test_dice_service.py::TestDiceServiceRollD20::test_roll_d20_returns_int  # Single test
uv run pytest -k "test_dice"             # Pattern match
uv run pytest --cov=app                  # With coverage

# Dev server
uv run uvicorn app.main:app --reload     # http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

## Code Style

| Rule | Setting |
|------|---------|
| Formatter | black, line-length **79** |
| Import sorter | isort, profile=black, line-length 79 |
| Linter | flake8, max-line-length 88, ignores E501/W503/F722/E203 |
| Type hints | Required on all function signatures |
| Docstrings | Korean, module-level `"""..."""` for every file |
| Models | Pydantic `BaseModel` (frozen for value objects) |
| IDs | UUID v7 via `uuid_utils.uuid7()` — never use `uuid4` |
| Commit messages | `type: 한국어 제목` 형식 필수 (pre-commit hook enforced) |

### Import Order (isort profile=black)

```python
# 1. stdlib
import logging
from typing import Optional
from uuid import UUID

# 2. third-party
from pydantic import BaseModel, Field

# 3. local app
from app.common.utils.id_generator import get_uuid7
from app.game.domain.entities import CharacterEntity
```

### Naming Conventions

- Files: `snake_case.py`
- Classes: `PascalCase` — entities `FooEntity`, value objects `FooResult`, use cases `ProcessActionUseCase`
- Functions/methods: `snake_case`
- Constants/enums: `UPPER_SNAKE_CASE`
- Test files: `test_{feature}.py`, classes `TestFoo`, methods `test_foo_does_bar`

### Error Handling

- Domain errors: raise `ValueError` / custom domain exceptions
- Application errors: raise `app.common.exception.Conflict`, `NotFound`, etc.
- Never use bare `except:` — always catch specific exceptions
- Log with `logging.getLogger(__name__)`

## Architecture — Clean Architecture (Strict)

Dependency direction: **Domain ← Application ← Infrastructure ← Presentation**

```
app/
├── auth/                    # Auth domain
├── common/                  # Shared utilities, exceptions
├── game/                    # Game domain (primary)
│   ├── domain/
│   │   ├── entities/        # Pydantic models (business objects)
│   │   ├── value_objects/   # Frozen Pydantic models, Enums
│   │   └── services/        # Pure domain logic
│   ├── application/
│   │   ├── ports/           # Repository interfaces (ABC)
│   │   ├── use_cases/       # Command implementations
│   │   ├── queries/         # Read-only queries
│   │   └── services/        # Application services (RAG, etc.)
│   ├── infrastructure/
│   │   ├── persistence/     # SQLAlchemy ORM models and mappers
│   │   ├── repositories/    # Port implementations
│   │   └── adapters/        # External service adapters
│   └── presentation/
│       ├── routes/          # FastAPI routers and Pydantic schemas (DTOs)
│       └── websocket/
├── llm/                     # LLM integration (Gemini via google-genai)
└── main.py                  # App entry, router registration
```

### Test Structure (mirrors app/)

```
tests/
├── unit/
│   ├── domain/              # Pure logic, no I/O, no mocks needed
│   ├── application/         # Mocked repositories (unittest.mock)
│   └── infrastructure/      # Flush/commit behavior checks
├── integration/             # Real DB (testcontainers), real Redis
├── e2e/                     # Full HTTP request/response cycle
└── conftest.py              # Shared fixtures
```

## TDD Workflow (MANDATORY)

Every feature follows Red → Green → Refactor:

1. **RED**: Write failing test first → `uv run pytest path/to/test.py` must fail
2. **GREEN**: Write minimal code to pass → test passes
3. **REFACTOR**: Clean up, deduplicate → all tests still pass

Layer order: Domain → Application → Infrastructure → Presentation.
Never write production code without a failing test.

## Execution Orchestration Rules

Execution orchestration mode: sub-agent

- Change only the value on the line above to switch the default
  orchestration style between `thread` and `sub-agent`.
- For either mode, follow `TEAM_OPERATIONS_GUIDE.md` and use
  `docs/HANDOFF_TEMPLATE.md` for handoff artifacts, storing filled files
  in `docs/handoffs/`.
- For substantial, multi-phase, delegated, or parallel work, create or
  update a handoff document in `docs/handoffs/`.
- When resuming substantial work in a new session, check the relevant
  handoff document in `docs/handoffs/` before proceeding.
- If mode is `thread`, prefer phase-based thread handoff and use
  delegation only when explicitly requested or clearly justified.
- If mode is `sub-agent`, do not spawn sub-agents unless the task meets
  the activation, parallelization, and write-scope rules in
  `TEAM_OPERATIONS_GUIDE.md`.
- For parallel implementation or isolated high-risk work, follow
  `WORKTREE_GUIDE.md`.
- Prefer separate worktrees for independent implementation owners when
  tasks run in parallel or conflict risk is non-trivial.
- The main agent owns final integration, final user communication, and
  final acceptance judgment.

## Key Tech Decisions

| Area | Choice |
|------|--------|
| Python | 3.13 |
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL + pgvector |
| ORM | SQLAlchemy 2.0 (async) |
| Cache | Redis |
| LLM | Gemini (google-genai SDK, `app/llm/`) |
| Message Queue | Kafka (aiokafka) |
| Validation | Pydantic v2 (strict) |
| Migrations | Alembic |
| Object Storage | S3-compatible (boto3, R2) |
| Monitoring | Sentry |
| Package Manager | UV |

## Pre-commit Hooks

Runs automatically on `git commit`:
1. isort (import sorting)
2. black (formatting)
3. flake8 (linting)
4. trailing-whitespace, end-of-file-fixer, check-yaml, check-json
5. check-added-large-files (max 5MB)
6. check-merge-conflict, debug-statements
7. Commit message format validation (`type: 한국어 제목`)

## Quick Reference

```bash
# Check what Swagger says before implementing endpoints
open http://localhost:8000/docs

# Database schema lives here
cat app/game/infrastructure/persistence/models/game_models.py

# Request/Response DTOs
ls app/game/presentation/routes/schemas/

# Environment variables
cat .env.example
```

**Respond in Korean (응답은 한글로).**

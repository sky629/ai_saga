# AI Saga

AI Saga는 Google Gemini를 활용해 텍스트 어드벤처를 진행하는
FastAPI 백엔드입니다. 플레이어는 시나리오를 선택하고 캐릭터를
생성한 뒤, AI 게임 마스터가 생성하는 내러티브와 선택지를 따라
세션을 진행합니다.

현재 저장소는 다음 기능을 중심으로 구성되어 있습니다.

- Google OAuth + JWT 기반 인증
- 시나리오/캐릭터/세션 관리 API
- 턴 기반 액션 처리와 서버 주도 주사위 판정
- Redis 락과 idempotency key를 이용한 중복 요청 방지
- Gemini 임베딩 + pgvector 기반 하이브리드 RAG 컨텍스트 구성
- 유저 메타 프로그레션과 캐릭터 세션 내 경험치 시스템
- Sentry 연동, Rate Limit, 개발용 시나리오 시딩 엔드포인트
- R2 업로드 기반 이미지 생성 경로
  `IMAGE_GENERATION_ENABLED`가 꺼져 있으면 관련 API는 비활성화됨

## 운영 문서

큰 작업, 병렬 작업, 작업 재개는 아래 문서를 기준으로 진행합니다.

- 운영 규칙: [AGENTS.md](/Users/kitaekang/Documents/dev/ai_saga/AGENTS.md)
- 멀티에이전트/phase 운영:
  [TEAM_OPERATIONS_GUIDE.md](/Users/kitaekang/Documents/dev/ai_saga/TEAM_OPERATIONS_GUIDE.md)
- worktree 운영:
  [WORKTREE_GUIDE.md](/Users/kitaekang/Documents/dev/ai_saga/WORKTREE_GUIDE.md)
- 공용 handoff 양식:
  [docs/HANDOFF_TEMPLATE.md](/Users/kitaekang/Documents/dev/ai_saga/docs/HANDOFF_TEMPLATE.md)
- 실제 handoff 문서 저장 위치:
  [docs/handoffs/README.md](/Users/kitaekang/Documents/dev/ai_saga/docs/handoffs/README.md)

기본 실행 모드와 handoff 규칙은 `AGENTS.md`의
`Execution orchestration mode` 값을 기준으로 해석합니다.

큰 기능 작업은 채팅 지시문에서 바로 구현하지 않고, PRD를 먼저
작성한 뒤 Ralph loop로 구현/테스트/검증을 반복하는 스펙 주도
개발을 기본으로 합니다. 자세한 규칙은
[docs/spec_driven_ralph_workflow.md](/Users/kitaekang/Documents/dev/ai_saga/docs/spec_driven_ralph_workflow.md)를
참고하세요.

## 기술 스택

- Python 3.13+
- FastAPI
- SQLAlchemy 2.0 Async
- PostgreSQL 15+ with pgvector
- Redis 7+
- Google Gemini / Imagen
- Alembic
- Sentry
- UV

## 빠른 시작

### 1. 의존성 설치

```bash
uv sync
```

### 2. 환경 변수 준비

```bash
cp .env.example .env
```

최소한 아래 값은 채워야 합니다.

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `TEST_POSTGRES_DB`, `TEST_POSTGRES_USER`, `TEST_POSTGRES_PASSWORD`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- `GEMINI_API_KEY`

이미지 생성을 실제로 쓰려면 아래 값도 필요합니다.

- `IMAGE_GENERATION_ENABLED=true`
- `OBJECT_STORAGE_ACCESS_KEY_ID`, `OBJECT_STORAGE_SECRET_ACCESS_KEY`
- `OBJECT_STORAGE_ENDPOINT_URL`, `OBJECT_STORAGE_REGION`
- `OBJECT_STORAGE_BUCKET_NAME`, `OBJECT_STORAGE_PUBLIC_URL`

### 3. 로컬 인프라 실행

PostgreSQL과 Redis는 기본적으로 필요합니다.

```bash
docker compose up -d postgres redis
```

Kafka는 현재 핵심 플레이 플로우에 필수는 아니지만 로컬 스택에는
정의되어 있습니다.

```bash
docker compose up -d kafka
```

### 4. 마이그레이션 적용

```bash
uv run alembic upgrade head
```

### 5. 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

## 자주 쓰는 엔드포인트

개발 환경에서만 Swagger와 개발용 라우트가 열립니다.

- Swagger UI: `http://localhost:8000/api/docs/`
- OpenAPI JSON: `http://localhost:8000/api/docs/openapi.json`
- Ping: `http://localhost:8000/api/ping/`
- 개발용 토큰 발급: `POST /api/v1/dev/token/`
- 개발용 시나리오 시딩: `POST /api/v1/dev/seed-scenarios/`

주요 도메인 엔드포인트는 아래와 같습니다.

- 인증: `/api/v1/auth/*`
- 게임: `/api/v1/game/*`

## 현재 API 특징

### 인증

- Google 로그인 시작: `GET /api/v1/auth/google/login/`
- Google OAuth 콜백: `GET /api/v1/auth/google/callback/`
- 액세스 토큰 재발급: `POST /api/v1/auth/refresh/`
- 로그아웃: `POST /api/v1/auth/logout/`
- 내 정보 조회/수정: `GET|PUT /api/v1/auth/self/`
- 소셜 계정 조회/해제:
  `GET /api/v1/auth/self/social-accounts/`,
  `DELETE /api/v1/auth/self/social-accounts/{account_id}/`

### 게임

- 시나리오 목록 조회: `GET /api/v1/game/scenarios/`
- 캐릭터 생성/목록: `POST|GET /api/v1/game/characters/`
- 세션 시작: `POST /api/v1/game/sessions/`
- 세션 목록/단건 조회:
  `GET /api/v1/game/sessions/`,
  `GET /api/v1/game/sessions/{session_id}/`
- 액션 제출:
  `POST /api/v1/game/sessions/{session_id}/actions/`
- 메시지 히스토리 조회:
  `GET /api/v1/game/sessions/{session_id}/messages/`
- 메시지 기반 일러스트 생성:
  `POST /api/v1/game/sessions/{session_id}/messages/{message_id}/illustration/`

중복 요청 처리 규칙은 다음과 같습니다.

- 세션 시작은 `Idempotency-Key` 헤더를 선택적으로 지원합니다.
- 액션 제출은 `Idempotency-Key` 헤더가 필수입니다.
- 세션 시작과 액션 제출 모두 Redis 분산 락을 사용합니다.

## 로컬 개발 흐름

개발용 토큰과 시나리오 시딩을 이용하면 OAuth 없이 빠르게 플로우를
검증할 수 있습니다.

1. `POST /api/v1/dev/token/`으로 액세스 토큰 발급
2. `POST /api/v1/dev/seed-scenarios/`로 기본 시나리오 생성
3. `GET /api/v1/game/scenarios/`로 시나리오 확인
4. `POST /api/v1/game/characters/`로 캐릭터 생성
5. `POST /api/v1/game/sessions/`로 세션 시작
6. `POST /api/v1/game/sessions/{session_id}/actions/`로 턴 진행

## 권장 개발 프로세스

AI 에이전트 기반 구현은 아래 순서를 권장합니다.

1. 요구가 넓으면 `$plan --consensus`로 스펙 수렴
2. PRD 작성: `.omx/plans/prd-{slug}.md`
3. 필요 시 planning/design/test plan/qa checklist 작성
4. `$ralph` loop로 구현:
   - 실패 테스트 작성
   - 최소 구현
   - 테스트/린트 실행
   - 독립 검증
   - 남은 acceptance criteria가 0이 될 때까지 반복
5. handoff 문서와 PRD 상태 갱신

작은 단독 작업은 메인 에이전트의 별도 review pass로 독립 검증을
대체할 수 있지만, 고위험/아키텍처/병렬 작업은 별도 검증
에이전트를 둡니다.

## 품질 게이트

프로젝트 표준 명령은 모두 `uv run`으로 실행합니다.

```bash
uv run black --check app/ tests/
uv run isort --check app/ tests/
uv run flake8 app/ tests/
uv run pytest
```

커밋 메시지는 pre-commit 훅 기준으로 `type: 한국어 제목` 형식을
따라야 합니다. 예: `fix: 로그인 오류 수정`

## 디렉토리 개요

```text
app/
├── auth/          # 인증, 토큰, 소셜 계정
├── common/        # 예외, 미들웨어, 저장소, 공통 유틸
├── dev/           # 개발 전용 라우트
├── game/          # 시나리오, 캐릭터, 세션, 액션 처리
└── llm/           # Gemini provider, DTO, 프롬프트

config/            # 환경변수 기반 설정
migrations/        # Alembic 마이그레이션
tests/             # unit / integration / e2e
docs/              # ADR, 기능 문서
scripts/           # DB 초기화, 훅 스크립트
```

구조와 런타임 흐름은
[code_architecture.md](/Users/kitaekang/Documents/dev/ai_saga/code_architecture.md)에
정리되어 있습니다. 게임 진행 규칙과 응답 계약은
[GAME_GUIDE.md](/Users/kitaekang/Documents/dev/ai_saga/GAME_GUIDE.md)를
참고하면 됩니다.

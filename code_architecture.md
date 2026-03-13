# AI Saga 백엔드 코드 아키텍처

이 문서는 현재 저장소 기준으로 백엔드 구조, 주요 런타임 흐름,
핵심 진입점을 설명합니다. 파일 전수 목록보다 "어디서부터 읽고,
어떤 경계로 나뉘는가"에 초점을 둡니다.

## 1. 아키텍처 개요

프로젝트는 Clean Architecture와 CQRS를 기본 뼈대로 사용합니다.

- 의존성 방향:
  `Domain <- Application <- Infrastructure <- Presentation`
- 주요 도메인: `auth`, `game`
- 공통 모듈: `common`, `llm`, `dev`
- 설정/운영 모듈: `config`, `migrations`, `docs`, `scripts`

핵심 특징:

- Domain은 순수 규칙만 가진다
- Application은 유스케이스와 조회 흐름을 조율한다
- Infrastructure는 DB, Redis, Gemini, R2 같은 외부 의존성을 구현한다
- Presentation은 FastAPI 라우트와 DTO를 제공한다
- Query와 Command는 read/write DB 세션을 분리해 주입받는다

## 2. 최상위 구조

```text
app/
├── auth/
├── common/
├── dev/
├── game/
└── llm/

config/
migrations/
tests/
docs/
scripts/
```

### 최상위 디렉토리 역할

| 경로 | 역할 |
| --- | --- |
| `app/` | 런타임 애플리케이션 코드 |
| `config/` | 환경변수 기반 설정 모델 |
| `migrations/` | Alembic 환경과 revision |
| `tests/` | unit / integration / e2e 테스트 |
| `docs/` | 기능 문서와 의사결정 기록 |
| `scripts/` | DB 초기화, Git hook 보조 스크립트 |

## 3. 런타임 부트스트랩

앱 시작의 진입점은
[app/main.py](/Users/kitaekang/Documents/dev/ai_saga/app/main.py)입니다.

부트스트랩 순서는 대략 아래와 같습니다.

1. 로깅 설정 적용
2. FastAPI 앱 생성
3. CORS, access log, rate limit 미들웨어 등록
4. 공통 예외 핸들러 등록
5. `auth`, `game`, `dev` 라우터 포함
6. 환경 조건이 맞으면 Sentry 초기화
7. shutdown 시 Postgres/Redis 풀 정리

개발 환경에서만 아래 기능이 열립니다.

- `/api/docs/`
- `/api/docs/openapi.json`
- `/api/docs/redoc/`
- `/api/v1/dev/*`

## 4. 공통 인프라 계층

### 설정

[config/settings.py](/Users/kitaekang/Documents/dev/ai_saga/config/settings.py)는
환경변수를 Pydantic Settings로 로드합니다.

주요 설정 묶음:

- Postgres
- Redis
- JWT / OAuth
- Gemini / Imagen
- 게임 턴 수와 RAG 파라미터
- Sentry
- R2

### 저장소와 미들웨어

`app/common/`은 도메인 공용 기반을 제공합니다.

- `exception.py`
  공통 API 예외 타입
- `middleware/access_log.py`
  요청/응답 로깅
- `middleware/exception_handler.py`
  API/HTTP/일반 예외 응답 변환
- `middleware/rate_limiting.py`
  slowapi 기반 rate limit
- `storage/postgres.py`
  도메인별 read/write async session 관리
- `storage/redis.py`
  Redis 풀과 연결 획득
- `utils/id_generator.py`
  UUID v7 생성

특히 Postgres는 read/write 세션을 분리해 주입합니다.

- Command 라우트는 write 세션 사용
- Query 라우트는 read 세션 사용

## 5. Auth 모듈

`auth`는 인증과 계정 연결 관리에 집중합니다.

### Domain

- `domain/entities/user.py`
  유저 엔티티와 영구 게임 레벨/경험치 규칙
- `domain/entities/social_account.py`
  소셜 계정 엔티티
- `domain/value_objects/*`
  제공자와 유저 레벨 enum

### Application

- OAuth callback 처리
- refresh token 회전
- logout
- 프로필 수정
- 소셜 계정 조회/연결 해제

### Infrastructure

- `repositories/*`
  User, SocialAccount, UserProgression 구현체
- `adapters/token_adapter.py`
  JWT 생성/검증과 블랙리스트 처리
- `adapters/google_auth_adapter.py`
  Google OAuth 연동
- `adapters/auth_cache_adapter.py`
  OAuth state, 세션성 캐시 관리

### Presentation

[app/auth/presentation/routes/auth_routes.py](/Users/kitaekang/Documents/dev/ai_saga/app/auth/presentation/routes/auth_routes.py)
는 아래 공개 API를 제공합니다.

- Google login / callback
- refresh / logout
- self 조회 / 수정
- social account 조회 / 해제

## 6. Game 모듈

`game`은 이 저장소의 핵심 도메인입니다.

### Domain

핵심 엔티티:

- `entities/scenario.py`
  시나리오 템플릿
- `entities/character.py`
  캐릭터, 세션 내 경험치와 레벨업 규칙
- `entities/game_session.py`
  세션 상태, 턴 증가, 완료, pause/resume 규칙
- `entities/game_message.py`
  유저/AI 메시지

핵심 값 객체와 서비스:

- `value_objects/action_type.py`
  액션 타입과 주사위 필요 여부
- `value_objects/scenario_difficulty.py`
  난이도와 DC
- `value_objects/dice.py`
  주사위 결과 표현
- `services/dice_service.py`
  d20 판정, 데미지, 펌블 자해
- `services/game_master_service.py`
  LLM JSON 파싱, 엔딩 타입 판별, 실패 보정
- `services/user_progression_service.py`
  유저 XP와 시작 HP 계산
- `services/vector_similarity_service.py`
  코사인 유사도 계산

### Application

핵심 유스케이스:

- `use_cases/create_character.py`
  유저 게임 레벨을 캐릭터 초기 스탯에 반영
- `use_cases/start_game.py`
  세션 생성, 초기 내러티브 저장, 초기 이미지 생성 시도
- `use_cases/process_action.py`
  턴 진행, idempotency, RAG, 주사위, 상태 반영, 엔딩 처리
- `use_cases/generate_illustration.py`
  특정 AI 메시지에 대한 이미지 생성
- `use_cases/delete_session.py`
  세션 삭제
- `use_cases/generate_ending.py`
  별도 엔딩 생성 경로

핵심 쿼리:

- `queries/get_scenarios.py`
- `queries/get_characters.py`
- `queries/get_user_sessions.py`
- `queries/get_session.py`
- `queries/get_session_history.py`

보조 서비스:

- `application/services/rag_context_builder.py`
  최근 메시지와 유사 메시지 병합
- `application/services/embedding_cache_service.py`
  임베딩 생성 결과 캐시

### Infrastructure

저장소:

- `repositories/scenario_repository.py`
- `repositories/character_repository.py`
- `repositories/game_session_repository.py`
- `repositories/game_message_repository.py`

어댑터:

- `adapters/cache_service.py`
  Redis 기반 락과 캐시
- `adapters/llm_service.py`
  Gemini 텍스트 생성 연동
- `adapters/image_service.py`
  Imagen 생성 + R2 업로드
  local 환경에서는 dummy URL 반환

영속 모델:

[app/game/infrastructure/persistence/models/game_models.py](/Users/kitaekang/Documents/dev/ai_saga/app/game/infrastructure/persistence/models/game_models.py)
에는 `Scenario`, `Character`, `GameSession`, `GameMessage` SQLAlchemy
모델이 있습니다.

주요 저장 포인트:

- 세션과 캐릭터 상태는 JSONB 사용
- 메시지 임베딩은 `Vector(768)`
- 이미지 URL은 메시지 단위로 저장

### Presentation

[app/game/presentation/routes/game_routes.py](/Users/kitaekang/Documents/dev/ai_saga/app/game/presentation/routes/game_routes.py)
는 아래 HTTP 경계를 제공합니다.

- 시나리오 조회
- 캐릭터 생성/조회
- 세션 시작/조회/삭제
- 액션 제출
- 메시지 히스토리 조회
- 메시지 일러스트 생성

응답 DTO는
[app/game/presentation/routes/schemas/response.py](/Users/kitaekang/Documents/dev/ai_saga/app/game/presentation/routes/schemas/response.py)에
정의되어 있습니다.

현재 중요한 응답 특성:

- 세션 목록과 메시지 목록은 cursor pagination 사용
- 액션 응답은 typed option과 `dice_result` 포함
- 엔딩 응답은 유저 XP 결과 포함
- 세션 단건 조회는 일부 `game_state` 키를 정리해 반환

## 7. DI와 요청 경계

`game`과 `auth` 모두 컨테이너 기반 의존성 조립을 사용합니다.

대표 파일:

- [app/game/container.py](/Users/kitaekang/Documents/dev/ai_saga/app/game/container.py)
- [app/game/dependencies.py](/Users/kitaekang/Documents/dev/ai_saga/app/game/dependencies.py)

흐름은 아래와 같습니다.

1. FastAPI `Depends`가 read 또는 write DB 세션을 주입
2. 컨테이너가 repository, adapter, use case를 조립
3. 라우터는 DTO 변환과 HTTP 에러 매핑만 담당
4. 실제 비즈니스 흐름은 use case가 수행

이 구조 덕분에 테스트에서 repository/adapter를 mock으로 교체하기
쉽습니다.

## 8. 핵심 런타임 플로우

### 게임 시작

1. 캐릭터 소유권 검증
2. 시나리오 사용 가능 여부 검증
3. 활성 세션 중복 확인
4. 세션 생성
5. 초기 LLM 응답 생성
6. 초기 메시지 저장
7. 이미지 기능이 켜져 있으면 초기 이미지 생성 시도
8. commit 후 세션 응답 반환

### 액션 처리

1. idempotency cache 확인
2. 세션 소유권/상태 검증
3. 턴 증가
4. 유저 메시지 임베딩 생성 및 저장
5. 최근 메시지 + 유사 메시지로 컨텍스트 구성
6. 마지막 턴 여부 판단
7. 일반 턴이면 액션 타입 재추론 후 주사위 판정
8. LLM 응답 JSON 파싱
9. 실패한 주사위 결과에 맞춰 상태 변경 보정
10. 캐릭터 HP, 경험치, 인벤토리 갱신
11. 필요 시 사망 엔딩 처리
12. AI 메시지와 임베딩 저장
13. commit 후 응답을 idempotency cache에 기록

### 이미지 생성

1. 기능 플래그 확인
2. 세션 소유권 확인
3. 메시지 존재 여부와 AI 메시지 여부 확인
4. 기존 `image_url` 있으면 재사용
5. 없으면 프롬프트 생성 후 이미지 생성 서비스 호출
6. 메시지에 `image_url` 반영

## 9. 테스트 구조

테스트는 구현 레이어와 관심사에 맞춰 나뉘어 있습니다.

```text
tests/
├── unit/
├── integration/
├── e2e/
├── game/
└── llm/
```

의미는 다음과 같습니다.

- `unit/`
  순수 도메인 규칙과 유스케이스 단위 검증
- `integration/`
  Redis, pgvector, repository, provider 연동 검증
- `e2e/`
  HTTP 경계 기준 검증
- `game/`
  게임 도메인 횡단 시나리오 성격 테스트
- `llm/`
  프롬프트와 provider 단위 테스트

## 10. 현재 상태로 이해해야 할 부분

아래 디렉토리는 아직 실질 공개 기능보다 확장 여지를 나타냅니다.

- `app/game/presentation/websocket/`
- `app/game/events/`
- `app/common/kafka/`

즉, 코드베이스는 WebSocket, 이벤트 기반 확장을 염두에 두고 있지만
현재 공개 API의 핵심은 HTTP + DB + Redis + Gemini 흐름입니다.

## 11. 처음 읽기 좋은 순서

처음 진입할 때는 아래 순서를 권장합니다.

1. [app/main.py](/Users/kitaekang/Documents/dev/ai_saga/app/main.py)
2. [app/game/presentation/routes/game_routes.py](/Users/kitaekang/Documents/dev/ai_saga/app/game/presentation/routes/game_routes.py)
3. [app/game/application/use_cases/process_action.py](/Users/kitaekang/Documents/dev/ai_saga/app/game/application/use_cases/process_action.py)
4. [app/game/domain/services/game_master_service.py](/Users/kitaekang/Documents/dev/ai_saga/app/game/domain/services/game_master_service.py)
5. [app/game/container.py](/Users/kitaekang/Documents/dev/ai_saga/app/game/container.py)
6. [app/auth/presentation/routes/auth_routes.py](/Users/kitaekang/Documents/dev/ai_saga/app/auth/presentation/routes/auth_routes.py)

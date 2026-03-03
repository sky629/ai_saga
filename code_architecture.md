# AI Saga 백엔드 코드 구조

이 문서는 현재 저장소 기준으로 백엔드 디렉토리 구조와 각 파일의
책임을 정리한 문서다.

## 1. 전체 개요

- 아키텍처: Clean Architecture + CQRS
- 의존성 방향:
  `Domain <- Application <- Infrastructure <- Presentation`
- 도메인 단위 모듈: `auth`, `game`
- 공통 모듈: `common`, `llm`, `dev`, `config`, `migrations`

## 2. 최상위 디렉토리 역할

| 경로 | 역할 |
| --- | --- |
| `app/` | 서비스 실행 코드(도메인, 유스케이스, 라우터, 인프라) |
| `config/` | 환경변수 기반 설정 로딩 |
| `migrations/` | Alembic 마이그레이션 스크립트 |
| `tests/` | 단위/통합/e2e 테스트 |

## 3. 런타임 흐름

1. `app/main.py`에서 FastAPI 앱 생성
2. 공통 미들웨어(CORS, rate limit, access log, 예외 핸들러) 등록
3. `auth`, `game`, `dev` 라우터 등록
4. 요청 시 `dependencies.py`/`container.py`를 통해 유스케이스 구성
5. 유스케이스가 도메인 서비스 + 리포지토리 + 외부 어댑터를 오케스트레이션
6. 응답 DTO를 통해 API 응답 반환

## 4. 레이어별 책임

### 4.1 Domain
- 순수 비즈니스 규칙
- 외부 I/O 없음
- 엔티티/값 객체/도메인 서비스 포함

### 4.2 Application
- 유스케이스 실행 흐름 조율
- Port(인터페이스) 의존
- Command/Query 분리(CQRS)

### 4.3 Infrastructure
- DB/Redis/외부 API 구현
- ORM 모델/Mapper/Repository 구현체

### 4.4 Presentation
- FastAPI 라우트
- Request/Response 스키마
- HTTP 상태코드/에러 응답 경계

## 5. 파일별 책임 1줄 매핑표

아래 표는 주요 백엔드 파일의 책임을 1줄로 요약했다.
(`__pycache__`, `__init__.py`는 제외)

### 5.1 앱/설정/공통

| 파일 | 책임(1줄) |
| --- | --- |
| `app/main.py` | FastAPI 앱 생성, 미들웨어/예외핸들러/라우터/라이프사이클 등록 |
| `config/settings.py` | 환경변수 기반 설정 모델과 파생 DB URL 제공 |
| `app/common/exception.py` | 공통 API 예외 타입 정의 |
| `app/common/middleware/access_log.py` | 요청/응답 액세스 로그 기록 |
| `app/common/middleware/exception_handler.py` | API/HTTP/일반 예외를 표준 응답으로 변환 |
| `app/common/middleware/rate_limiting.py` | 레이트리밋 미들웨어 및 핸들러 구성 |
| `app/common/storage/postgres.py` | 도메인별 Postgres read/write 세션 및 엔진 풀 관리 |
| `app/common/storage/redis.py` | Redis 커넥션 풀/캐시 유틸 제공 |
| `app/common/utils/datetime.py` | UTC datetime 유틸 |
| `app/common/utils/id_generator.py` | UUID v7 생성 유틸 |
| `app/common/utils/singleton.py` | 싱글톤 메타클래스 제공 |
| `app/dev/routes.py` | 개발 전용 토큰 발급/시나리오 시딩 라우트 제공 |

### 5.2 Auth 도메인

#### Domain

| 파일 | 책임(1줄) |
| --- | --- |
| `app/auth/domain/entities/user.py` | 사용자 도메인 엔티티 정의 |
| `app/auth/domain/entities/social_account.py` | 소셜 계정 도메인 엔티티 정의 |
| `app/auth/domain/value_objects/auth_provider.py` | OAuth 제공자 값 객체(enum) 정의 |
| `app/auth/domain/value_objects/user_level.py` | 사용자 레벨 값 객체/규칙 정의 |

#### Application

| 파일 | 책임(1줄) |
| --- | --- |
| `app/auth/application/queries/get_user.py` | 사용자 조회 쿼리 처리 |
| `app/auth/application/queries/get_social_accounts.py` | 사용자 소셜 계정 조회 쿼리 처리 |
| `app/auth/application/use_cases/create_user.py` | 신규 사용자 생성 유스케이스 |
| `app/auth/application/use_cases/handle_oauth_callback.py` | OAuth 콜백 처리 및 로그인 토큰 발급 |
| `app/auth/application/use_cases/refresh_token.py` | 리프레시 토큰 기반 액세스 토큰 재발급 |
| `app/auth/application/use_cases/refresh_google_token.py` | Google 소셜 토큰 갱신 처리 |
| `app/auth/application/use_cases/logout.py` | 로그아웃 및 토큰 무효화 처리 |
| `app/auth/application/use_cases/update_user_profile.py` | 사용자 프로필 수정 처리 |
| `app/auth/application/use_cases/disconnect_social_account.py` | 소셜 계정 연결 해제 처리 |
| `app/auth/application/ports/__init__.py` | Auth 레이어 포트 인터페이스 export |

#### Infrastructure

| 파일 | 책임(1줄) |
| --- | --- |
| `app/auth/infrastructure/persistence/models/user_models.py` | Auth 관련 SQLAlchemy 모델(User, SocialAccount) 정의 |
| `app/auth/infrastructure/persistence/mappers.py` | ORM <-> 도메인 엔티티 매핑 |
| `app/auth/infrastructure/repositories/user_repository.py` | 사용자 저장소 구현체 |
| `app/auth/infrastructure/repositories/social_account_repository.py` | 소셜 계정 저장소 구현체 |
| `app/auth/infrastructure/repositories/user_progression_repository.py` | 사용자 게임 진행도 저장소 구현체 |
| `app/auth/infrastructure/adapters/token_adapter.py` | JWT 생성/검증 어댑터 |
| `app/auth/infrastructure/adapters/google_auth_adapter.py` | Google OAuth 연동 어댑터 |
| `app/auth/infrastructure/adapters/auth_cache_adapter.py` | 인증 캐시/토큰 상태 저장 어댑터 |

#### Presentation/DI

| 파일 | 책임(1줄) |
| --- | --- |
| `app/auth/presentation/routes/auth.py` | Auth HTTP 엔드포인트 정의 |
| `app/auth/presentation/routes/schemas/request.py` | Auth 요청 DTO 정의 |
| `app/auth/presentation/routes/schemas/response.py` | Auth 응답 DTO 정의 |
| `app/auth/container.py` | Auth 의존성 조립(팩토리) |
| `app/auth/dependencies.py` | FastAPI Depends 바인딩 및 인증 의존성 제공 |

### 5.3 Game 도메인

#### Domain

| 파일 | 책임(1줄) |
| --- | --- |
| `app/game/domain/entities/character.py` | 캐릭터 엔티티 및 상태 변경 로직 정의 |
| `app/game/domain/entities/game_session.py` | 게임 세션 엔티티 및 턴/종료 상태 로직 정의 |
| `app/game/domain/entities/game_message.py` | 세션 메시지 엔티티 정의 |
| `app/game/domain/entities/scenario.py` | 시나리오 엔티티 정의 |
| `app/game/domain/value_objects/session_status.py` | 세션 상태(enum) 정의 |
| `app/game/domain/value_objects/ending_type.py` | 엔딩 타입(enum) 정의 |
| `app/game/domain/value_objects/message_role.py` | 메시지 역할(enum) 정의 |
| `app/game/domain/value_objects/game_state.py` | 게임 상태/변화 값 객체 정의 |
| `app/game/domain/value_objects/scenario_genre.py` | 시나리오 장르 값 객체 정의 |
| `app/game/domain/value_objects/scenario_difficulty.py` | 시나리오 난이도 값 객체 정의 |
| `app/game/domain/value_objects/dice.py` | 주사위 관련 값 객체 정의 |
| `app/game/domain/services/game_master_service.py` | LLM 응답 파싱/게임 종료 판단 도메인 규칙 제공 |
| `app/game/domain/services/game_state_service.py` | 상태 변화 병합/적용 규칙 제공 |
| `app/game/domain/services/dice_service.py` | 주사위 판정/피해량 계산 규칙 제공 |
| `app/game/domain/services/vector_similarity_service.py` | 임베딩 유사도 계산 규칙 제공 |
| `app/game/domain/services/user_progression_service.py` | 유저 XP/시작 HP 계산 규칙 제공 |

#### Application

| 파일 | 책임(1줄) |
| --- | --- |
| `app/game/application/ports/__init__.py` | Game 유스케이스가 의존할 포트 인터페이스 export |
| `app/game/application/use_cases/start_game.py` | 게임 시작 및 초기 메시지/세션 생성 처리 |
| `app/game/application/use_cases/process_action.py` | 플레이어 액션 처리, 턴 진행, LLM 응답 생성 처리 |
| `app/game/application/use_cases/create_character.py` | 캐릭터 생성 처리 |
| `app/game/application/use_cases/delete_session.py` | 세션 삭제 처리 |
| `app/game/application/use_cases/generate_ending.py` | 엔딩 생성 처리 |
| `app/game/application/use_cases/generate_illustration.py` | 일러스트 생성 트리거 및 저장 처리 |
| `app/game/application/queries/get_scenarios.py` | 시나리오 목록 조회 |
| `app/game/application/queries/get_characters.py` | 캐릭터 목록 조회 |
| `app/game/application/queries/get_session.py` | 세션 단건 조회 |
| `app/game/application/queries/get_user_sessions.py` | 사용자 세션 목록 조회 |
| `app/game/application/queries/get_session_history.py` | 세션 히스토리(커서 페이징) 조회 |
| `app/game/application/services/rag_context_builder.py` | 최근 메시지 + 유사 메시지 컨텍스트 병합 |
| `app/game/application/services/embedding_cache_service.py` | 임베딩 결과 캐시 전략 적용 |

#### Infrastructure

| 파일 | 책임(1줄) |
| --- | --- |
| `app/game/infrastructure/persistence/models/game_models.py` | 게임 도메인 SQLAlchemy 모델 정의 |
| `app/game/infrastructure/persistence/mappers.py` | 게임 ORM <-> 도메인 엔티티 매핑 |
| `app/game/infrastructure/repositories/scenario_repository.py` | 시나리오 저장소 구현체 |
| `app/game/infrastructure/repositories/character_repository.py` | 캐릭터 저장소 구현체 |
| `app/game/infrastructure/repositories/game_session_repository.py` | 세션 저장소 구현체 |
| `app/game/infrastructure/repositories/game_message_repository.py` | 메시지 저장소 구현체(벡터 검색 포함) |
| `app/game/infrastructure/adapters/cache_service.py` | Cache 포트의 Redis 기반 구현 |
| `app/game/infrastructure/adapters/llm_service.py` | LLM 포트의 Gemini 연동 구현 |
| `app/game/infrastructure/adapters/image_service.py` | 이미지 생성/업로드 어댑터 구현 |

#### Presentation/DI

| 파일 | 책임(1줄) |
| --- | --- |
| `app/game/presentation/routes/game_routes.py` | 게임 HTTP 엔드포인트 정의 |
| `app/game/presentation/routes/schemas/request.py` | 게임 요청 DTO 정의 |
| `app/game/presentation/routes/schemas/response.py` | 게임 응답 DTO 정의 |
| `app/game/presentation/websocket/__init__.py` | 게임 websocket 패키지 진입점 |
| `app/game/container.py` | Game 의존성 조립(팩토리) |
| `app/game/dependencies.py` | FastAPI Depends 바인딩 제공 |

### 5.4 LLM 모듈

| 파일 | 책임(1줄) |
| --- | --- |
| `app/llm/embedding_service_interface.py` | 임베딩 서비스 포트 인터페이스 정의 |
| `app/llm/dto/llm_response.py` | LLM 응답 DTO 정의 |
| `app/llm/prompts/game_master.py` | 게임마스터 프롬프트 생성 로직 |
| `app/llm/providers/base.py` | LLM provider 공통 인터페이스 |
| `app/llm/providers/gemini.py` | Gemini 텍스트 생성 provider 구현 |
| `app/llm/providers/gemini_embedding_provider.py` | Gemini 임베딩 provider 구현 |

## 6. 데이터/마이그레이션 구조

| 파일 | 책임(1줄) |
| --- | --- |
| `migrations/env.py` | Alembic 실행 환경 및 메타데이터 연결 |
| `migrations/script.py.mako` | Alembic revision 템플릿 |
| `migrations/versions/07306584053f_initial_schema.py` | 초기 스키마 생성 |

## 7. 참고: 코드 읽기 시작점

처음 파악할 때는 아래 순서를 권장한다.

1. `app/main.py` (앱 조립 방식)
2. `app/game/presentation/routes/game_routes.py` (핵심 API 경계)
3. `app/game/application/use_cases/process_action.py` (핵심 유스케이스)
4. `app/game/domain/services/game_master_service.py` (도메인 규칙)
5. `app/game/infrastructure/repositories/*.py` (영속화 방식)
6. `app/auth/presentation/routes/auth.py` (인증 흐름)

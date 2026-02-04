# AI Saga (ai_saga)

**AI 기반 텍스트 어드벤처 MUD(Multi-User Dungeon) 게임 백엔드**

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-41%2F41%20passing-brightgreen.svg)](tests/)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

AI Saga는 Google Gemini AI를 활용한 인터랙티브 텍스트 기반 어드벤처 게임 백엔드입니다. 플레이어는 캐릭터를 생성하고 다양한 시나리오를 탐험하며, AI가 실시간으로 생성하는 동적인 내러티브를 경험할 수 있습니다. Clean Architecture 원칙을 적용하여 확장 가능하고 유지보수가 쉬운 구조로 설계되었습니다.

## ✨ 주요 기능

### 🎮 게임 기능
- **동적 AI 내러티브**: Gemini AI를 활용한 실시간 스토리 생성
- **캐릭터 생성**: 스탯과 인벤토리를 가진 커스터마이징 가능한 캐릭터
- **다양한 시나리오**: 여러 장르와 난이도의 게임 시나리오
- **턴 기반 게임플레이**: 턴 제한과 엔딩이 있는 전략적 게임플레이
- **세션 관리**: 게임 세션 저장 및 재개
- **실시간 멀티플레이어**: WebSocket 기반 실시간 상호작용 (개발 예정)

### 🏗️ 아키텍처 기능
- **Clean Architecture**: 도메인 주도 설계와 명확한 계층 분리
- **TDD 방식**: 테스트 주도 개발로 100% 테스트 커버리지
- **Repository Pattern**: 추상화된 데이터 접근 계층
- **CQRS Pattern**: 명령과 쿼리 분리
- **의존성 주입**: 컨테이너 기반 DI와 팩토리 메서드
- **UUID v7**: 시간 순서 보장 고유 식별자로 데이터베이스 성능 향상

### 🔧 기술적 특징
- **FastAPI**: 현대적인 비동기 Python 웹 프레임워크
- **PostgreSQL**: 비동기 지원이 가능한 강력한 관계형 데이터베이스
- **Redis**: 캐싱 및 세션 관리
- **Gemini AI**: Google의 최신 AI 모델을 활용한 내러티브 생성
- **Alembic**: 데이터베이스 마이그레이션
- **Pydantic v2**: 데이터 검증 및 설정 관리
- **Rate Limiting**: SlowAPI를 사용한 API 보호

## 📋 요구사항

- **Python**: 3.13+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **uv**: 빠른 Python 패키지 설치 도구

## 🎮 게임 방식

### 게임 플레이 플로우

```
1. 사용자 로그인 (Google OAuth)
   ↓
2. 캐릭터 생성 (이름, 설명 입력)
   ↓
3. 시나리오 선택 (장르, 난이도)
   ↓
4. 게임 세션 시작
   ↓
5. AI 내러티브 → 플레이어 액션 → AI 반응 (반복)
   ↓
6. 게임 엔딩 (승리/패배/중립)
```

### 게임 진행 방식

#### 1️⃣ 시작 단계
- **캐릭터 생성**: 캐릭터 이름과 설명을 입력합니다
- **시나리오 선택**: 다양한 장르(판타지, SF, 미스터리 등)와 난이도 중 선택
- **세션 시작**: AI가 시나리오의 초기 상황을 생성합니다

#### 2️⃣ 게임 진행
- **AI 내러티브**: Gemini AI가 현재 상황을 생생하게 묘사합니다
- **플레이어 액션**: 자유롭게 행동을 입력합니다 (예: "북쪽으로 이동한다", "상자를 연다")
- **AI 반응**: 플레이어의 행동에 따라 AI가 결과를 생성합니다
- **선택지 제공**: AI가 추천하는 다음 행동 옵션을 제시합니다

#### 3️⃣ 턴 시스템
- 각 게임은 **최대 턴 수**가 정해져 있습니다 (5~30턴)
- 턴마다 플레이어는 하나의 액션을 수행할 수 있습니다
- 현재 턴 수와 남은 턴 수가 표시됩니다

#### 4️⃣ 게임 엔딩
게임은 다음 조건에서 종료됩니다:
- **승리 (Victory)**: 목표 달성
- **패배 (Defeat)**: 캐릭터 사망 또는 미션 실패
- **중립 (Neutral)**: 최대 턴 수 도달 또는 게임 포기

### 게임 플레이 예시

```
🎭 시나리오: 던전 탐험
📖 상황: 당신은 어두운 던전 입구에 서 있습니다...

💬 AI 내러티브:
"오래된 돌계단이 어둠 속으로 이어져 있습니다.
희미한 불빛이 지하에서 새어 나오고, 어디선가
물방울 떨어지는 소리가 들립니다."

⚡ 선택지:
1. 조심스럽게 계단을 내려간다
2. 주변을 더 살펴본다
3. 횃불을 켠다

✍️ 플레이어 입력: "횃불을 켜고 조심스럽게 내려간다"

💬 AI 반응:
"횃불의 불빛이 주변을 밝히자, 벽에 새겨진
고대 문자들이 보입니다. 계단을 내려가니
넓은 홀이 나타나고..."

🎯 턴 5/20 | HP: 100/100
```

### 특징

- **자유도 높은 액션**: 정해진 명령어가 아닌 자연어로 행동 입력
- **동적 스토리**: AI가 플레이어의 선택에 따라 실시간으로 스토리 생성
- **컨텍스트 유지**: 이전 대화 내용을 기억하고 일관된 스토리 전개
- **다양한 결말**: 플레이어의 선택에 따라 다른 엔딩

## 🚀 빠른 시작

### 1. 클론 및 설정

```bash
# 저장소 클론
git clone <repository-url>
cd ai_saga

# 가상환경 생성 및 의존성 설치
uv sync

# 환경 변수 템플릿 복사
cp .env.example .env
```

### 2. 환경 변수 설정

`.env` 파일을 편집하여 실제 값으로 변경:

```bash
# PostgreSQL
POSTGRES_DB=ai_saga
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379

# Gemini AI (필수)
GEMINI_API_KEY=your_gemini_api_key_here

# JWT Secret
JWT_SECRET_KEY=your_secret_key_here

# Google OAuth (선택)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

### 3. 데이터베이스 설정

```bash
# PostgreSQL 및 Redis 시작 (Docker Compose 사용)
docker-compose up -d postgres redis

# 마이그레이션 실행
uv run alembic upgrade head

# (선택) 초기 데이터 입력
uv run python scripts/seed_data.py
```

### 4. 서버 실행

```bash
# 개발 모드
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드
uv run gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 5. API 문서 접속

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/docs/redoc/
- **Health Check**: http://localhost:8000/api/ping/

## 🎯 API 엔드포인트

### 인증 API (`/api/v1/auth`)

| 메서드 | 엔드포인트 | 설명 | 인증 |
|--------|----------|------|------|
| GET | `/google/login/` | Google OAuth 로그인 시작 | ❌ |
| GET | `/google/callback/` | OAuth 콜백 처리 | ❌ |
| POST | `/refresh/` | JWT 토큰 갱신 | ❌ |
| POST | `/logout/` | 로그아웃 | ✅ |
| GET | `/self/` | 현재 사용자 정보 조회 | ✅ |
| PUT | `/self/` | 사용자 프로필 수정 | ✅ |
| GET | `/self/social-accounts/` | 연결된 소셜 계정 목록 | ✅ |
| DELETE | `/self/social-accounts/{id}/` | 소셜 계정 연결 해제 | ✅ |

### 게임 API (`/api/v1/game`)

| 메서드 | 엔드포인트 | 설명 | 인증 |
|--------|----------|------|------|
| GET | `/scenarios/` | 사용 가능한 시나리오 목록 | ✅ |
| GET | `/scenarios/{id}/` | 시나리오 상세 정보 | ✅ |
| POST | `/characters/` | 캐릭터 생성 | ✅ |
| GET | `/characters/` | 사용자 캐릭터 목록 | ✅ |
| POST | `/sessions/start/` | 게임 세션 시작 | ✅ |
| GET | `/sessions/` | 사용자 세션 목록 | ✅ |
| GET | `/sessions/{id}/` | 세션 상세 정보 | ✅ |
| POST | `/sessions/{id}/action/` | 게임 액션 수행 | ✅ |
| GET | `/sessions/{id}/history/` | 메시지 히스토리 조회 | ✅ |
| POST | `/sessions/{id}/ending/` | 게임 엔딩 생성 | ✅ |

## 🏛️ 프로젝트 구조

```
ai_saga/
├── app/
│   ├── main.py                      # 애플리케이션 진입점
│   ├── auth/                        # 인증 도메인
│   │   ├── domain/                  # 도메인 계층
│   │   │   ├── entities/            # User, SocialAccount 엔티티
│   │   │   └── value_objects/       # AuthProvider, UserLevel
│   │   ├── application/             # 애플리케이션 계층
│   │   │   ├── ports/               # Repository 인터페이스
│   │   │   ├── use_cases/           # 비즈니스 로직 (명령)
│   │   │   └── queries/             # 읽기 작업
│   │   ├── infrastructure/          # 인프라 계층
│   │   │   ├── persistence/         # ORM 모델 & 매퍼
│   │   │   ├── repositories/        # Repository 구현체
│   │   │   └── adapters/            # 외부 서비스 어댑터
│   │   ├── presentation/            # 프레젠테이션 계층
│   │   │   └── routes/              # FastAPI 라우트 & DTO
│   │   ├── container.py             # DI 컨테이너
│   │   └── dependencies.py          # FastAPI 의존성
│   ├── game/                        # 게임 도메인 (동일한 구조)
│   │   ├── domain/
│   │   │   ├── entities/            # Character, GameSession 등
│   │   │   ├── value_objects/       # EndingType, SessionStatus
│   │   │   └── services/            # 도메인 서비스
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   ├── llm/                         # LLM 통합
│   │   ├── providers/               # Gemini 프로바이더
│   │   └── prompts/                 # 프롬프트 템플릿
│   └── common/                      # 공통 컴포넌트
│       ├── storage/                 # PostgreSQL, Redis
│       ├── middleware/              # 로깅, rate limiting
│       └── utils/                   # 유틸리티
├── config/
│   └── settings.py                  # Pydantic 설정
├── migrations/                      # Alembic 마이그레이션
├── tests/                          # 테스트 스위트
│   ├── unit/                       # 단위 테스트
│   ├── integration/                # 통합 테스트
│   └── conftest.py                 # 테스트 픽스처
├── scripts/                        # 유틸리티 스크립트
├── docker-compose.yml              # Docker 서비스
└── pyproject.toml                  # 프로젝트 설정
```

## 🧪 테스트

```bash
# 모든 테스트 실행
uv run pytest

# 커버리지 포함 실행
uv run pytest --cov=app --cov-report=term-missing

# 특정 테스트 파일 실행
uv run pytest tests/test_auth_routes.py -v

# 단위 테스트만 실행
uv run pytest tests/unit/ -v

# 마커로 실행
uv run pytest -m "not slow"
```

**현재 테스트 상태**: ✅ 41/41 테스트 통과 (100%)

## 🔐 보안 기능

- **JWT 인증**: Access/Refresh 토큰 시스템
- **OAuth 2.0**: Google OAuth 통합
- **토큰 블랙리스트**: Redis 기반 토큰 폐기
- **Rate Limiting**: 엔드포인트별 요청 제한
- **CORS**: 설정 가능한 교차 출처 정책
- **SQL Injection 방지**: SQLAlchemy ORM
- **비밀번호 해싱**: passlib와 bcrypt

## 🧩 Clean Architecture 계층

### 1. Domain Layer (핵심 비즈니스 로직)
- **엔티티**: `User`, `Character`, `GameSession`, `Scenario`
- **Value Objects**: `AuthProvider`, `UserLevel`, `EndingType`, `SessionStatus`
- **도메인 서비스**: `GameMasterService`
- **Ports**: Repository 인터페이스

### 2. Application Layer (Use Cases)
- **Commands**: `CreateUser`, `StartGame`, `ProcessAction`
- **Queries**: `GetUserSessions`, `GetSessionHistory`
- **DTOs**: 입출력 데이터 구조

### 3. Infrastructure Layer (기술적 세부사항)
- **Persistence**: SQLAlchemy 모델, Alembic 마이그레이션
- **Repositories**: PostgreSQL 구현체
- **Adapters**: Gemini AI, Google OAuth, Redis 캐시
- **Mappers**: Domain ↔ ORM 변환

### 4. Presentation Layer (API)
- **Routes**: FastAPI 엔드포인트
- **Schemas**: Pydantic 요청/응답 모델
- **WebSockets**: 실시간 통신 (개발 예정)

## 📊 데이터베이스 스키마

### 사용자 & 인증
- `users`: 사용자 계정
- `social_accounts`: OAuth 연결

### 게임
- `scenarios`: 게임 시나리오
- `characters`: 플레이어 캐릭터
- `game_sessions`: 진행 중/완료된 게임
- `game_messages`: 게임 내러티브 및 액션

## 🛠️ 개발 가이드

### 코드 품질

```bash
# 코드 포맷팅
uv run black .
uv run isort .

# 린팅
uv run flake8 .

# 모든 검사 실행
uv run black . && uv run isort . && uv run flake8 .
```

### 데이터베이스 마이그레이션

```bash
# 새 마이그레이션 생성
uv run alembic revision --autogenerate -m "설명"

# 마이그레이션 적용
uv run alembic upgrade head

# 롤백
uv run alembic downgrade -1

# 히스토리 확인
uv run alembic history
```

### Docker 배포

```bash
# 모든 서비스 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f app

# 서비스 중지
docker-compose down

# 재빌드
docker-compose up -d --build
```

## 🌟 핵심 기술 스택

| 분류 | 기술 | 용도 |
|------|------|------|
| **프레임워크** | FastAPI 0.116+ | 비동기 웹 프레임워크 |
| **언어** | Python 3.13 | 최신 Python 기능 |
| **데이터베이스** | PostgreSQL 15+ | 주 데이터 저장소 |
| **캐시** | Redis 7+ | 세션 & 캐싱 |
| **AI** | Gemini AI | 내러티브 생성 |
| **ORM** | SQLAlchemy 2.0 | 비동기 데이터베이스 접근 |
| **검증** | Pydantic v2 | 데이터 검증 |
| **마이그레이션** | Alembic | 스키마 관리 |
| **테스팅** | pytest | 테스트 프레임워크 |
| **패키지 관리** | uv | 빠른 의존성 관리 |

## 📝 환경 변수

전체 목록은 `.env.example` 파일을 참고하세요. 주요 변수:

| 변수 | 설명 | 필수 |
|------|------|------|
| `POSTGRES_DB` | 데이터베이스 이름 | ✅ |
| `POSTGRES_USER` | 데이터베이스 사용자 | ✅ |
| `POSTGRES_PASSWORD` | 데이터베이스 비밀번호 | ✅ |
| `REDIS_URL` | Redis 연결 URL | ✅ |
| `GEMINI_API_KEY` | Gemini AI API 키 | ✅ |
| `JWT_SECRET_KEY` | JWT 서명 키 | ✅ |
| `GOOGLE_CLIENT_ID` | Google OAuth 클라이언트 ID | ❌ |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 시크릿 | ❌ |

## 🚧 로드맵

- [x] 사용자 인증 (Google OAuth + JWT)
- [x] 캐릭터 생성 시스템
- [x] 시나리오 관리
- [x] 게임 세션 라이프사이클
- [x] AI 내러티브 생성 (Gemini)
- [x] 턴 기반 게임플레이
- [x] 게임 엔딩 시스템
- [x] 페이지네이션이 있는 메시지 히스토리
- [x] Clean Architecture 구현
- [x] 포괄적인 테스트 커버리지
- [x] Pydantic v2 마이그레이션
- [ ] WebSocket 실시간 게임플레이
- [ ] 멀티플레이어 세션 (Kafka)
- [ ] 캐릭터 인벤토리 시스템
- [ ] 업적 시스템
- [ ] 리더보드
- [ ] 추가 OAuth 제공자 (Apple, Kakao)
- [ ] 시나리오 벡터 검색 (pgvector)
- [ ] 관리자 패널

## 🤝 기여하기

1. 저장소 포크
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. TDD 방식 따르기: 테스트 먼저 작성
4. Clean Architecture를 따르는 기능 구현
5. 테스트 및 코드 품질 검사 실행
6. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
7. 브랜치에 푸시 (`git push origin feature/amazing-feature`)
8. Pull Request 생성

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

- **FastAPI**: 훌륭한 비동기 웹 프레임워크 제공
- **Google Gemini**: 강력한 AI 내러티브 생성 기능 제공
- **Clean Architecture**: Robert C. Martin의 아키텍처 패턴
- **MUD Games**: 고전 텍스트 기반 어드벤처 게임의 영감

## 📞 지원

문제 및 질문사항:
- 저장소에 이슈 생성
- 기존 문서 확인
- `/api/docs/`에서 API 문서 검토

---

**Clean Architecture와 TDD로 제작**

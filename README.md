# Kang Authentication Server

## 개요

FastAPI와 PostgreSQL을 사용한 Google OAuth 기반 인증 시스템입니다. Clean Architecture 패턴을 적용하여 확장 가능하고 유지보수가 쉬운 구조로 설계되었습니다.

**Current Version**: v2025.07.0

## 주요 기능

- Google OAuth 2.0 인증 (Apple OAuth 준비 완료)
- JWT 토큰 기반 인증 (Access/Refresh Token)
- PostgreSQL 읽기/쓰기 풀 분리 지원
- Redis 캐싱 및 토큰 블랙리스트 관리
- Rate Limiting (SlowAPI)
- 접근 로그 및 예외 처리 미들웨어
- API 문서화 (Swagger/OpenAPI)
- Docker 컨테이너 지원 (자동 마이그레이션 포함)

## 기술 스택

- **Backend**: FastAPI + Python 3.11
- **Database**: PostgreSQL 15 + SQLAlchemy 2.0 (Async)
- **Cache**: Redis 7
- **Authentication**: Google OAuth 2.0 + JWT
- **Package Manager**: uv
- **Container**: Docker + Docker Compose
- **Testing**: pytest + pytest-asyncio
- **Code Quality**: Black, isort, flake8 (통합 pyproject.toml 설정), Alembic

## 프로젝트 구조

```
app/
├── main.py                 # FastAPI 애플리케이션 진입점
├── auth/                   # 인증 도메인
│   ├── models/            # SQLAlchemy 모델 (User, SocialAccount)
│   ├── repositories/      # Repository Pattern 구현
│   │   └── cache/         # Redis 캐시 레포지토리
│   ├── services/          # 비즈니스 로직 (OAuth, Token, User)
│   ├── routes/            # API 엔드포인트
│   └── representations/   # Pydantic 요청/응답 모델
├── common/                # 공통 컴포넌트
│   ├── storage/           # PostgreSQL & Redis 연결 관리
│   ├── middleware/        # 미들웨어 (Rate Limiting, Exception, Access Log)
│   ├── utils/             # 유틸리티 함수 (DateTime, Singleton)
│   ├── enums/             # 열거형 정의 (UserLevel)
│   ├── logging/           # 로깅 설정
│   └── exception.py       # 커스텀 예외
config/
├── settings.py            # Pydantic Settings 설정 관리
migrations/                # Alembic 데이터베이스 마이그레이션
├── versions/              # 마이그레이션 버전 파일들
│   ├── 001_create_initial_auth_tables.py
│   └── 3ec070505365_add_apple_to_oauth_provider_enum.py
tests/                     # pytest 테스트 코드
scripts/                   # 데이터베이스 초기화 스크립트
```

## 설치 및 실행

### 1. 환경 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd kang

# .env 파일 생성 (템플릿에서 복사)
cp .env.example .env

# .env 파일을 편집하여 실제 값으로 변경
# - Google OAuth 클라이언트 ID/Secret
# - JWT Secret Key (운영환경에서는 반드시 변경)
# - 필요시 데이터베이스 연결 정보 수정
```

### 2. Docker를 사용한 실행 (권장)

**Docker 구성 요소:**
- PostgreSQL 15 (kang-postgres): 메인 데이터베이스
- Redis 7 (kang-redis): 캐시 및 토큰 블랙리스트
- FastAPI App (kang-app): 애플리케이션 서버

```bash
# 전체 스택 실행 (PostgreSQL + Redis + FastAPI)
docker-compose up -d

# 애플리케이션 로그 확인
docker-compose logs -f app

# 개별 서비스 실행
docker-compose up -d postgres redis  # DB만 실행

# 데이터베이스 초기화 (첫 실행 시 자동)
# - kang_db (메인 데이터베이스) 자동 생성
# - test_kang_db (테스트 데이터베이스) 자동 생성
# - uuid-ossp 확장 설치

# 컨테이너 상태 확인
docker-compose ps

# 데이터베이스 완전 초기화 (주의: 모든 데이터 삭제)
docker-compose down -v  # 볼륨 포함 삭제
docker-compose up -d    # 새로 시작
```

### 3. 로컬 개발 환경

**로컬 개발 시 두 가지 옵션:**

#### 옵션 A: Docker DB + 로컬 앱 (권장)
```bash
# Python 의존성 설치
uv sync

# 데이터베이스 및 Redis만 Docker로 실행
docker-compose up -d postgres redis

# 환경 변수 설정 (.env 파일 사용)
# POSTGRES_HOST=localhost로 설정된 상태에서 실행

# 데이터베이스 마이그레이션
uv run alembic upgrade head

# 개발 서버 실행
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 옵션 B: 모든 서비스 Docker (권장)
```bash
# 전체 Docker 환경 실행
docker-compose up -d

# 개발 시 코드 변경사항이 자동 반영됨 (볼륨 마운트)
# 로그 확인
docker-compose logs -f app
```

#### 코드 품질 도구
```bash
# 통합 pyproject.toml 설정 사용
uv run isort .          # Import 정렬
uv run black .          # 코드 포맷팅
uv run flake8 .         # 린팅 검사

# 테스트 실행
uv run pytest
```

## API 엔드포인트

### 인증 API (/api/v1/auth)

- `GET /health/` - Auth 서비스 상태 확인
- `GET /google/login/` - Google OAuth 로그인 URL 생성
- `POST /google/callback/` - Google OAuth 콜백 처리
- `POST /refresh/` - JWT 토큰 갱신
- `POST /google/refresh/` - Google 토큰 갱신 (인증 필요)
- `POST /logout/` - 로그아웃 (인증 필요)
- `GET /self/` - 현재 사용자 정보 (인증 필요)
- `PUT /self/` - 사용자 정보 수정 (인증 필요)
- `GET /self/social-accounts/` - 연결된 소셜 계정 조회 (인증 필요)
- `DELETE /self/social-accounts/{account_id}/` - 소셜 계정 연결 해제 (인증 필요)
- `DELETE /self/` - 사용자 계정 삭제 (인증 필요)

### 기타 API

- `GET /api/ping/` - 애플리케이션 상태 확인
- `GET /api/docs/` - Swagger UI API 문서
- `GET /api/docs/redoc/` - ReDoc API 문서

## 환경 변수

프로젝트 루트에 `.env` 파일을 생성하여 환경변수를 설정합니다:

```bash
# .env.example 파일을 복사하여 시작
cp .env.example .env
```

### 주요 환경변수

#### PostgreSQL 설정
| 환경변수 | 설명 | Docker 예시값 | 로컬 예시값 |
|---------|------|---------------|-------------|
| `POSTGRES_DB` | 데이터베이스 이름 | `kang_db` | `kang_db` |
| `POSTGRES_USER` | DB 사용자명 | `postgres` | `postgres` |
| `POSTGRES_PASSWORD` | DB 비밀번호 | `password` | `password` |
| `POSTGRES_HOST` | DB 호스트 | `postgres` | `localhost` |
| `POSTGRES_PORT` | DB 포트 | `5432` | `5432` |

#### 테스트 데이터베이스 설정
| 환경변수 | 설명 | 값 |
|---------|------|----|
| `TEST_POSTGRES_DB` | 테스트 DB 이름 | `test_kang_db` |
| `TEST_POSTGRES_USER` | 테스트 DB 사용자 | `postgres` |
| `TEST_POSTGRES_PASSWORD` | 테스트 DB 비밀번호 | `password` |
| `TEST_POSTGRES_HOST` | 테스트 DB 호스트 | `localhost` |

#### 기타 주요 환경변수
| 환경변수 | 설명 | 예시값 |
|---------|------|--------|
| `KANG_ENV` | 실행 환경 | `local`, `development`, `production` |
| `REDIS_URL` | Redis 연결 URL | `redis://redis:6379` (Docker) / `redis://localhost:6379` (로컬) |
| `JWT_SECRET_KEY` | JWT 토큰 시크릿 키 | **운영환경에서 반드시 변경** |
| `GOOGLE_CLIENT_ID` | Google OAuth 클라이언트 ID | Google Cloud Console에서 발급 |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 클라이언트 시크릿 | Google Cloud Console에서 발급 |

### 전체 환경변수 목록

`.env.example` 파일에서 전체 환경변수 목록과 설명을 확인할 수 있습니다.

**중요**: 
- `.env` 및 `.env.local` 파일은 Git에 커밋하지 않습니다 (이미 `.gitignore`에 포함됨)
- 운영환경에서는 반드시 보안키들을 변경해야 합니다

### 환경별 설정

#### Docker Compose 환경 (.env)
```bash
# PostgreSQL (Docker 서비스명 사용)
POSTGRES_HOST=postgres
REDIS_URL=redis://redis:6379

# 자동 데이터베이스 초기화
# - scripts/init-db.sql이 자동 실행됨
# - kang_db (메인), test_kang_db (테스트) 생성
# - uuid-ossp 확장 자동 설치
```

#### 로컬 개발 환경 (.env 또는 별도 파일)
```bash
# PostgreSQL (localhost 사용)
POSTGRES_HOST=localhost
REDIS_URL=redis://localhost:6379

# Docker로 DB만 실행하고 로컬에서 앱 실행 시
```

## 테스트

```bash
# 모든 테스트 실행
uv run pytest

# 특정 테스트 파일 실행
uv run pytest tests/test_auth_routes.py -v

# 비동기 테스트 포함
uv run pytest tests/ -v --tb=short
```

## 보안 기능

### 1. Authentication & Authorization
- JWT 토큰 기반 인증 (Access/Refresh Token)
- 토큰 블랙리스트 관리 (Redis)
- Google OAuth 2.0 연동
- Bearer Token 인증

### 2. Rate Limiting
- SlowAPI를 사용한 엔드포인트별 제한
- Redis 기반 분산 Rate Limiting
- IP 기반 요청 제한

### 3. Security Headers & CORS
- CORS 정책 설정 (설정 가능한 Origins)
- 전역 예외 처리 미들웨어
- 접근 로그 미들웨어

### 4. Data Protection
- 환경변수를 통한 민감정보 관리
- SQL Injection 방지 (SQLAlchemy ORM)
- 비밀번호 해싱 (Passlib + bcrypt)

## 아키텍처 패턴

### Clean Architecture 적용
- **Domain Layer**: Models (User, SocialAccount), Enums (UserLevel)
- **Application Layer**: Services (OAuth, Token, User), Use Cases  
- **Infrastructure Layer**: Repositories (User, SocialAccount, Token), Storage (PostgreSQL, Redis)
- **Presentation Layer**: Routes (auth_routes), Representations (Request/Response models)

### Repository Pattern
- 데이터 접근 로직 추상화
- BaseRepository를 상속한 도메인별 Repository
- PostgreSQL 읽기/쓰기 풀 분리 자동 라우팅
- Redis Cache Repository (토큰 블랙리스트, 캐싱)

## 데이터베이스 아키텍처

### 데이터베이스 초기화
Docker 환경에서 PostgreSQL이 시작될 때 `scripts/init-db.sql`이 자동 실행됩니다:

```sql
-- 메인 데이터베이스 (POSTGRES_DB 환경변수로 자동 생성)
-- kang_db

-- 테스트 데이터베이스 생성
CREATE DATABASE test_kang_db;
GRANT ALL PRIVILEGES ON DATABASE test_kang_db TO postgres;

-- 필요한 확장 설치
\c kang_db;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c test_kang_db;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 읽기/쓰기 풀 분리 지원
PostgreSQL의 읽기/쓰기 풀 분리를 지원합니다. `PostgresStorage` 클래스가 도메인별로 읽기/쓰기 세션을 자동 관리합니다.

```python
class PostgresStorage:
    async def get_domain_read_session(self, domain: str = "default"):
        # 읽기 전용 세션 - POSTGRES_READ_URL 또는 POSTGRES_URL 사용
        ...
    
    async def get_domain_write_session(self, domain: str = "default"):
        # 쓰기 세션 - POSTGRES_WRITE_URL 또는 POSTGRES_URL 사용
        ...
```

### 도메인별 데이터베이스 분리 (확장 가능)
`config/settings.py`에서 도메인별 데이터베이스 URL을 동적으로 구성합니다:

```python
# PostgreSQL URL 동적 구성 (settings.py)
@property
def postgres_url(self) -> str:
    return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

# 도메인별 URL 예시 (User 도메인)
@property
def user_postgres_url(self) -> str:
    return self.postgres_url  # 현재는 같은 DB 사용, 향후 분리 가능
```

#### 환경변수를 통한 개별 설정
```env
# 기본 PostgreSQL 설정
POSTGRES_DB=kang_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_HOST=postgres  # Docker: postgres, 로컬: localhost
POSTGRES_PORT=5432

# 확장 가능: 도메인별 설정
# USER_POSTGRES_READ_URL=postgresql://...
# USER_POSTGRES_WRITE_URL=postgresql://...
```

## 향후 확장 계획

- [x] 추가 소셜 로그인 지원 - Apple OAuth 준비 완료 (데이터베이스 스키마 및 환경설정)
- [ ] Apple OAuth 서비스 구현
- [ ] 추가 소셜 로그인 지원 (Kakao, Naver)
- [ ] 이메일/패스워드 로그인 옵션
- [ ] 사용자 권한 관리 시스템 (RBAC)
- [ ] API 키 기반 인증
- [ ] 관리자 패널 구현
- [ ] 이중 인증 (2FA) 지원

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

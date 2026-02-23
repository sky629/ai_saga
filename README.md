# AI Saga (ai_saga)

**AI 기반 텍스트 어드벤처 MUD(Multi-User Dungeon) 게임 백엔드**

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-254%2F254%20passing-brightgreen.svg)](tests/)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

AI Saga는 Google Gemini AI를 활용한 인터랙티브 텍스트 기반 어드벤처 게임 백엔드입니다. 플레이어는 캐릭터를 생성하고 다양한 시나리오를 탐험하며, AI가 실시간으로 생성하는 동적인 내러티브를 경험할 수 있습니다. Clean Architecture 원칙을 적용하여 확장 가능하고 유지보수가 쉬운 구조로 설계되었습니다.

## ✨ 주요 기능

### 🎮 게임 기능
- **동적 AI 내러티브**: Gemini AI를 활용한 실시간 스토리 생성
- **로그라이크 메타 프로그레션**: 유저 레벨 및 경험치(XP) 시스템 도입으로 다회차 플레이 보상 제공
- **인터랙티브 주사위 판정**: 주사위 굴리기 전 준비 묘사와 결과 공개를 분리하여 긴장감 있는 UX 구현
- **캐릭터 생성**: 유저 레벨에 따른 스탯 보너스가 적용되는 커스터마이징 가능한 캐릭터
- **다양한 시나리오**: 여러 장르와 난이도의 게임 시나리오 및 동적 결과 생성
- **턴 기반 게임플레이**: 전략적인 플레이를 위한 턴 제한 및 엔딩 시스템

### 🏗️ 아키텍처 기능
- **Clean Architecture**: 도메인 주도 설계(DDD)와 명확한 계층 분리로 높은 유지보수성 확보
- **TDD 방식**: 테스트 주도 개발을 통해 핵심 로직에 대한 높은 신뢰성 확보 (254개 테스트 통과)
- **Repository & CQRS Pattern**: 데이터 접근 추상화 및 명령/쿼리 책임 분리
- **의존성 주입**: DI 컨테이너 기반의 팩토리 메서드 구조
- **UserProgression Service**: 레벨별 보너스 및 XP 계산 로직의 도메인 서비스화

### 🔧 기술적 특징
- **FastAPI**: 고성능 비동기 Python 웹 프레임워크
- **PostgreSQL & pgvector**: 관계형 데이터 및 벡터 유사도 검색 지원
- **Redis**: 분산 락, 캐싱 및 세션 관리
- **Alembic**: 데이터베이스 스키마 마이그레이션 관리
- **Rate Limiting**: 429 Too Many Requests 대응 및 API 보호 로직

## 🚀 시작하기

### 1. 요구사항
- **Python**: 3.13+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **uv**: Python 패키지 관리 도구

### 2. 설치 및 실행
```bash
# 저장소 클론
git clone <repository-url>
cd ai_saga

# 의존성 설치
uv sync

# 환경 변수 설정
cp .env.example .env
# .env 파일 내 GEMINI_API_KEY 등을 설정하세요.

# 마이그레이션 적용
uv run alembic upgrade head

# 서버 실행
uv run uvicorn app.main:app --reload
```

## 🎯 API 문서
- **Swagger UI**: http://localhost:8000/api/docs/
- **Health Check**: http://localhost:8000/api/ping/

## 🏛️ 프로젝트 구조
```
app/
├── auth/            # 인증 및 유저 프로그레션 도메인
├── game/            # 게임 세션, 액션, 시나리오 도메인
├── llm/             # Gemini AI 프로바이더 및 프롬프트 관리
└── common/          # 공통 유틸리티 및 스토리지 설정
```

## 🚧 로드맵
- [x] 사용자 인증 (Google OAuth + JWT)
- [x] 캐릭터 생성 시스템
- [x] 로그라이크 메타 프로그레션 (유저 레벨/XP)
- [x] AI 내러티브 생성 및 인터랙티브 주사위 UX
- [x] 에러 핸들링 고도화 (429 Rate Limit 피드백)
- [ ] WebSocket 실시간 게임플레이
- [ ] 캐릭터 인벤토리 시스템 고도화
- [ ] 시나리오 벡터 검색 (pgvector)

---
**Clean Architecture와 TDD로 제작**

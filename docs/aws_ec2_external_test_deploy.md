# AWS EC2 외부 테스트 배포

외부 테스트용 최소 구성:

- 프론트엔드: S3 + CloudFront
- 백엔드: EC2 1대 + Docker Compose
- 백엔드 도메인: `api.example.com`

이 문서는 현재 저장소의 [docker-compose.prod.yml](/Users/kitaekang/Documents/dev/ai_saga/docker-compose.prod.yml)을 기준으로 한다.

## 1. EC2 준비

- Ubuntu 24.04 기준 권장
- 보안 그룹 오픈:
  - `22/tcp`: 본인 IP만
  - `80/tcp`: CloudFront origin 용도
- Route 53 또는 사용 중인 DNS에서 `api.example.com`을 CloudFront Distribution 도메인으로 연결

## 2. EC2에 Docker / Compose 설치

```bash
bash scripts/install_docker_ubuntu.sh
newgrp docker
```

## 3. EC2에 코드 배치

가장 빠른 방법은 EC2에서 저장소를 바로 clone하는 것이다.

```bash
git clone <repo-url>
cd ai_saga
```

## 4. EC2에 .env 작성

`.env`는 [.env.example](/Users/kitaekang/Documents/dev/ai_saga/.env.example)을 기반으로 작성한다.

```bash
cp .env.example .env
```

중요:

- `APP_DOMAIN`: `api.example.com`
- `POSTGRES_HOST=postgres`
- `TEST_POSTGRES_HOST=postgres`
- `REDIS_URL=redis://redis:6379`
- `ALLOWED_ORIGINS`: CloudFront 프론트 도메인
- `GOOGLE_REDIRECT_URI`: `https://api.example.com/api/v1/auth/google/callback/`
- `FRONTEND_LOGIN_SUCCESS_URL`: 프론트 도메인
- `KANG_ENV=prod`

`KANG_ENV=prod`이면 개발용 라우트는 비활성화된다.

## 5. EC2에서 빌드 후 실행

스크립트를 쓸 수 있다.

```bash
chmod +x scripts/deploy_ec2_compose.sh
./scripts/deploy_ec2_compose.sh
```

수동으로 실행하려면:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

## 6. 확인

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f app
curl http://127.0.0.1/api/ping/
```

정상 응답:

```json
{"ping":"pong!"}
```

## 7. 코드 수정 후 재배포

EC2에서 최신 코드를 받고 다시 빌드하면 된다.

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

## 주의사항

- 현재 [start.sh](/Users/kitaekang/Documents/dev/ai_saga/start.sh)는 앱 컨테이너 시작 시 Alembic 마이그레이션을 자동 실행한다.
- 단일 EC2 외부 테스트에서는 괜찮지만, 다중 인스턴스 운영 전환 시에는 마이그레이션을 별도 작업으로 분리하는 편이 안전하다.
- CloudFront에서 API를 custom origin으로 붙일 때는 `CachingDisabled` 같은 비캐시 정책을 쓰는 편이 안전하다.
- CloudFront는 기본적으로 쿠키, 쿼리스트링, 헤더를 origin에 보내지 않으므로, 로그인/세션/API 요청에 필요한 값은 cache policy와 origin request policy로 명시적으로 전달해야 한다.

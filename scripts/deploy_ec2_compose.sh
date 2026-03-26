#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
사용법:
  ./scripts/deploy_ec2_compose.sh

기본 동작:
  1. docker compose 설정 검증
  2. 앱 이미지 로컬 빌드
  3. docker compose up -d

선택 환경 변수:
  ENV_FILE=.env
  COMPOSE_FILE=docker-compose.prod.yml
EOF
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "필수 명령어가 없습니다: $command_name" >&2
    exit 1
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_command docker

ENV_FILE="${ENV_FILE:-.env}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "환경 변수 파일을 찾을 수 없습니다: ${ENV_FILE}" >&2
  exit 1
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "compose 파일을 찾을 수 없습니다: ${COMPOSE_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

echo "[1/3] compose 설정 검증"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" config \
  >/tmp/ai_saga_compose_config

echo "[2/3] 서비스 빌드 및 기동"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --build

echo "[3/3] 상태 확인"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps

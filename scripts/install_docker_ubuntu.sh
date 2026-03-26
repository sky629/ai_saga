#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
사용법:
  bash scripts/install_docker_ubuntu.sh

설치 대상:
  - docker-ce
  - docker-ce-cli
  - containerd.io
  - docker-buildx-plugin
  - docker-compose-plugin

대상 환경:
  - Ubuntu (EC2)
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

require_command sudo
require_command apt-get
require_command curl
require_command gpg
require_command dpkg

if [[ ! -f /etc/os-release ]]; then
  echo "/etc/os-release 를 찾을 수 없습니다." >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release

if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "이 스크립트는 Ubuntu 전용입니다. 현재 OS: ${ID:-unknown}" >&2
  exit 1
fi

echo "[1/6] 필수 패키지 설치"
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

echo "[2/6] Docker GPG 키 등록"
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "[3/6] Docker apt 저장소 추가"
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  ${VERSION_CODENAME} stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

echo "[4/6] Docker 패키지 설치"
sudo apt-get update
sudo apt-get install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

echo "[5/6] 현재 사용자 docker 그룹 추가"
sudo usermod -aG docker "${USER}"

echo "[6/6] 설치 확인"
docker --version || true
docker compose version || true

cat <<'EOF'

설치가 끝났습니다.
현재 세션에서 docker 그룹 반영이 안 될 수 있으니 아래 중 하나를 실행하세요.

  newgrp docker

또는 다시 로그인 후 진행하세요.
EOF

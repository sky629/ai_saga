#!/bin/bash

# 스크립트 실행 중 오류가 발생하면 즉시 중단
set -e

# 데이터베이스 마이그레이션 실행
echo "Running database migrations..."
uv run alembic upgrade head

# 애플리케이션 서버 시작
echo "Starting application..."
exec uv run gunicorn app.main:app -w 3 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
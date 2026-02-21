#!/usr/bin/env sh
set -eu

echo "[worker-entrypoint] Starting Celery worker..."

# Wait for Postgres if configured.
if [ "${DB_ENGINE:-sqlite}" = "postgres" ] || [ "${DB_ENGINE:-sqlite}" = "postgresql" ] || [ "${DB_ENGINE:-sqlite}" = "psql" ]; then
  echo "[worker-entrypoint] Waiting for Postgres at ${DB_HOST:-db}:${DB_PORT:-5432}..."
  python - <<'PY'
import os
import time

import psycopg2

host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", "5432"))
name = os.getenv("DB_NAME", "ai_legal")
user = os.getenv("DB_USER", "postgres")
pwd = os.getenv("DB_PASSWORD", "postgres")

for i in range(60):
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=name, user=user, password=pwd)
        conn.close()
        print("[worker-entrypoint] Postgres is ready.")
        break
    except Exception:
        if i == 59:
            raise
        time.sleep(1)
PY
fi

# Wait for Redis (broker) before starting worker.
echo "[worker-entrypoint] Waiting for Redis at ${REDIS_HOST:-redis}:${REDIS_PORT:-6379}..."
python - <<'PY'
import os
import socket
import time

host = os.getenv("REDIS_HOST", "redis")
port = int(os.getenv("REDIS_PORT", "6379"))

for i in range(60):
    try:
        with socket.create_connection((host, port), timeout=1):
            print("[worker-entrypoint] Redis is ready.")
            break
    except OSError:
        if i == 59:
            raise
        time.sleep(1)
PY

exec celery -A backend worker -l info

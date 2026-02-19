#!/usr/bin/env sh
set -eu

echo "[entrypoint] Starting AI Legal Assistant (Compose)..."

# Wait for Postgres if configured
if [ "${DB_ENGINE:-sqlite}" = "postgres" ] || [ "${DB_ENGINE:-sqlite}" = "postgresql" ] || [ "${DB_ENGINE:-sqlite}" = "psql" ]; then
  echo "[entrypoint] Waiting for Postgres at ${DB_HOST:-db}:${DB_PORT:-5432}..."
  python - <<'PY'
import os, time
import psycopg2

host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", "5432"))
name = os.getenv("DB_NAME", "ai_legal")
user = os.getenv("DB_USER", "postgres")
pwd  = os.getenv("DB_PASSWORD", "postgres")

for i in range(60):
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=name, user=user, password=pwd)
        conn.close()
        print("[entrypoint] Postgres is ready.")
        break
    except Exception:
        if i == 59:
            raise
        time.sleep(1)
PY
fi

echo "[entrypoint] Applying migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Starting Django dev server on 0.0.0.0:8000"
exec python manage.py runserver 0.0.0.0:8000

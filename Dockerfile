# AI Legal Assistant - Dockerfile
# Local dev container (Compose). Uses Django's dev server for fast iteration.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (psycopg2 runtime dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Install python deps first for better caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Copy app source
COPY . /app

# Ensure entrypoint script is executable
RUN chmod +x /app/docker/entrypoint.sh
RUN chmod +x /app/docker/worker-entrypoint.sh

EXPOSE 8000

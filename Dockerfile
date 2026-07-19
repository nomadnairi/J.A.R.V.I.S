# syntax=docker/dockerfile:1

# ---- base -------------------------------------------------------------------
FROM python:3.11-slim AS base

# ffmpeg is needed only if you use local Whisper (STT_BACKEND=local); it is
# small and harmless to include so voice works out of the box.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install "fastapi>=0.110" "uvicorn[standard]>=0.29" "aiogram>=3.0,<4.0"

COPY . .
RUN pip install --no-deps .

# Run as a non-root user.
RUN useradd --create-home --uid 1000 jarvis \
    && mkdir -p /app/data /app/logs \
    && chown -R jarvis:jarvis /app
USER jarvis

# Persist the database and audit log across restarts.
VOLUME ["/app/data", "/app/logs"]

EXPOSE 8000

# Default: run the HTTP/WebSocket API. Override the command to run the bot:
#   docker run ... python -m jarvis.interfaces.telegram_bot
CMD ["python", "-m", "jarvis.api"]

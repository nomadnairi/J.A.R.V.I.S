# syntax=docker/dockerfile:1

# ---- base -------------------------------------------------------------------
FROM python:3.11-slim AS base

# ffmpeg is needed only for local Whisper STT (STT_BACKEND=local). Build with
# --build-arg WITH_VOICE=false for a smaller image without it.
ARG WITH_VOICE=true
RUN if [ "$WITH_VOICE" = "true" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends ffmpeg \
        && rm -rf /var/lib/apt/lists/*; \
    fi

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
# extra-ca.cr[t]: optional PEM bundle for TLS-inspecting (corporate) proxies —
# drop a file named extra-ca.crt next to the Dockerfile and it is trusted;
# the glob keeps the build working when the file is absent.
COPY requirements.txt extra-ca.cr[t] ./
RUN if [ -f extra-ca.crt ]; then \
        cp extra-ca.crt /usr/local/share/ca-certificates/extra-ca.crt \
        && update-ca-certificates \
        && pip config set global.cert /etc/ssl/certs/ca-certificates.crt; \
    fi
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

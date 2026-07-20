# Deploying J.A.R.V.I.S. on a VPS

This guide covers two ways to run J.A.R.V.I.S. on a server: **Docker** (recommended)
and a **systemd** service. Both run the same two processes:

- **API** — the HTTP/WebSocket server (`python -m jarvis.api`), for desktop/mobile
  clients and scripts.
- **Bot** — the Telegram interface (`python -m jarvis.interfaces.telegram_bot`),
  which uses long-polling and needs **no open inbound port**.

They share the same `data/` (SQLite memory) and `logs/` (audit log) directories,
so the assistant remembers you no matter which surface you use.

---

## 1. Prerequisites

- A Linux VPS (Ubuntu 22.04+ / Debian 12+ recommended), 1 vCPU / 1 GB RAM is enough.
- An LLM key: `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`).
- Optional: a Telegram bot token from [@BotFather](https://t.me/BotFather).

### Security first

- **Set `API_KEY`.** With an empty key the API is *open*. Generate a strong one:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- **Never commit `.env`.** It stays on the server only. The repo ships only
  `.env.example`.
- Keep dangerous capabilities off on a server (`ALLOW_SHELL`, `ALLOW_FILE_WRITE`,
  `ALLOW_DESKTOP_CONTROL` = `false`) unless you specifically need them.

---

## 2. Docker (recommended)

Install Docker + the Compose plugin, then:

```bash
git clone https://github.com/nomadnairi/J.A.R.V.I.S.git jarvis
cd jarvis

cp .env.example .env
nano .env            # fill ANTHROPIC_API_KEY, API_KEY, and (optional) TELEGRAM_BOT_TOKEN

docker compose up -d --build
```

Check it:

```bash
docker compose ps
curl -fsS http://localhost:8000/health | python -m json.tool
docker compose logs -f            # follow logs (Ctrl-C to stop following)
```

Update to a new version:

```bash
git pull
docker compose up -d --build
```

Stop / remove:

```bash
docker compose down               # keeps the named volumes (your data)
docker compose down -v            # also deletes data + logs volumes
```

> **Only want the API** (no Telegram bot)? Leave `TELEGRAM_BOT_TOKEN` empty and
> run just that service: `docker compose up -d --build api`.

### Two bots: public (sales) + personal (yours)

The same image runs as many bots as you like — you just give each a different
token and env file. A common setup is **two**:

- **Public bot** — your sales/user bot (the default `bot` service): subscription
  gate on, `/buy` enabled, customers use it, and you manage them via the admin
  panel. Configured in `.env`.
- **Personal bot** — your own private J.A.R.V.I.S. with a **separate token** and
  its own memory: no gate, no sales, just you.

```bash
cp .env.personal.example .env.personal   # second @BotFather token, your id
docker compose --profile personal up -d bot-personal
```

Both are the same code, isolated by token and by data volume — the public bot's
customers and your personal chats never mix. Anyone who clones the repo only
gets the **code**: your tokens, database and admin id live in your `.env` files
(never committed), so they can only run their own empty instance, never touch
yours.

### Build options

- **Smaller image without voice:** `ffmpeg` is only needed for local Whisper
  (`STT_BACKEND=local`). Skip it with
  `docker build --build-arg WITH_VOICE=false -t jarvis-assistant .`
- **Behind a TLS-inspecting (corporate) proxy:** drop your proxy's PEM bundle
  next to the Dockerfile as `extra-ca.crt` — it is added to the container's
  trust store automatically (the file is gitignored; never commit it).
- If Docker Hub is blocked in your network, pull the base image through
  Google's mirror first:
  `docker pull mirror.gcr.io/library/python:3.11-slim && docker tag mirror.gcr.io/library/python:3.11-slim python:3.11-slim`

---

## 3. systemd (no Docker)

Run directly on the host with a dedicated user and a virtualenv.

```bash
# Create a service user and app directory
sudo useradd --system --create-home --home-dir /opt/jarvis jarvis
sudo -u jarvis git clone https://github.com/nomadnairi/J.A.R.V.I.S.git /opt/jarvis

cd /opt/jarvis
sudo -u jarvis python3 -m venv .venv
sudo -u jarvis .venv/bin/pip install --upgrade pip
sudo -u jarvis .venv/bin/pip install -r requirements.txt
sudo -u jarvis .venv/bin/pip install "fastapi>=0.110" "uvicorn[standard]>=0.29" "aiogram>=3.0,<4.0"

# Configure
sudo -u jarvis cp .env.example .env
sudo -u jarvis nano .env          # fill in your keys
sudo -u jarvis mkdir -p data logs

# Install the units
sudo cp deploy/systemd/jarvis-api.service /etc/systemd/system/
sudo cp deploy/systemd/jarvis-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jarvis-api jarvis-bot
```

Manage:

```bash
systemctl status jarvis-api jarvis-bot
journalctl -u jarvis-api -f
sudo systemctl restart jarvis-api
```

After a `git pull`, reinstall the package deps if needed and restart:

```bash
cd /opt/jarvis && sudo -u jarvis git pull
sudo systemctl restart jarvis-api jarvis-bot
```

---

## 4. Exposing the API safely

The API listens on `:8000`. For anything beyond local testing, put it behind a
reverse proxy with TLS instead of exposing the port directly.

Minimal nginx example:

```nginx
server {
    listen 443 ssl;
    server_name jarvis.example.com;

    # ssl_certificate / ssl_certificate_key — e.g. from certbot

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        # WebSocket upgrade for /ws/{session}
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }
}
```

Then reach it with your key:

```bash
curl -s https://jarvis.example.com/chat \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Good evening."}'
```

Checklist for a public deployment:

- [ ] `API_KEY` is set to a long random secret.
- [ ] Firewall allows only 443 (and 22); `:8000` is not exposed directly.
- [ ] TLS terminated at the proxy.
- [ ] `ALLOW_SHELL` / `ALLOW_FILE_WRITE` / `ALLOW_DESKTOP_CONTROL` stay `false`
      unless you truly need them.
- [ ] `TELEGRAM_ALLOWED_USERS` restricts the bot to your own user IDs.

---

## 5. Health & troubleshooting

- **Health:** `GET /health` returns per-subsystem checks (LLM, memory,
  integrations, security posture). `ok: true` means all green.
- **Logs:** Docker — `docker compose logs -f`; systemd — `journalctl -u jarvis-api -f`.
- **Audit trail:** sensitive actions are recorded in `logs/audit.log`
  (secrets redacted).
- **Bot doesn't answer:** confirm `TELEGRAM_BOT_TOKEN` is set and the process is
  running; the bot uses outbound long-polling, so no inbound port is required.

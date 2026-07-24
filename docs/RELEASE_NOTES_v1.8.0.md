# J.A.R.V.I.S. v1.8.0

A big product release on top of the v1.7.0 Enterprise Update: a full desktop
Command Deck, an agent-tools ecosystem via MCP, task automation, auto-updates
and more. **510 automated tests, all green.**

## ✨ Highlights

### 🛰 Command Deck — a real desktop dashboard
A brand-new web dashboard with its own identity (amber-on-green, an animated
arc-reactor core), embedded live in the desktop app:
- A hover-expanding sidebar, a boot splash, and a status bar.
- **Home** — reactor + live system telemetry, capabilities and quick actions.
- **Models** — the real model catalog (categories, providers, search, ratings).
- **Chat** — real conversations with a history sidebar.
- **Settings** — accent colour, font size, density, animations, AI + security
  status, all reflecting the real backend.
- **MCP** — connected servers and their tools.
The desktop app serves this over a bundled local API, so it's **live in-window**
(real chat, stats, models) with a real-time WebSocket feed — no external server.

### 🧩 MCP — mount external agent tools (agentskills.io / Hermes)
J.A.R.V.I.S. is now an MCP client: connect any MCP server and its tools become
native skills the model can call. Point at a standard `mcpServers` config or add
one at runtime from the dashboard.

### 🔁 Task automation ("living AI")
Tell the bot "каждый день в 9:00 сделай сводку" / "каждые 3 часа проверь почту"
and it runs the task on schedule, delivers the result and reschedules itself.

### ⬆️ Auto-update
Check for updates from GitHub releases, one-tap update, and an opt-in
auto-update that silently downloads and runs the installer. Gated behind a
subscription as a paid privilege.

### 🔗 Per-user integrations, tier-gated
Users connect their own Home Assistant (token verified against the HA API) or a
webhook, capped by their plan (Free 2 / Plus 6 / Pro unlimited), with an upsell
at the limit.

### 👤 Roles + Telegram login
The desktop distinguishes the owner (full admin app) from a signed-in guest
(limited app). Sign in with a username/password **or with Telegram** — the bot
issues a login code you redeem in the app.

### 🖥 Local & self-hosted models
Run Ollama, LM Studio, vLLM or llama.cpp via backend presets — no cloud key.

## 🔄 Upgrading your server
```
git pull
python3 scripts/sync_env.py
docker compose up -d --force-recreate
```

## 💻 Desktop app
Windows installer and portable build are attached below (early / grey access).
Owner runs it locally (full app); hand others the app + a Telegram login code.

---
🤖 Built with automated tests and CI on every commit.

<div align="center">

# KER

**Your own AI assistant — one you name, run, and actually own.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/Version-1.9.1-orange)](https://github.com/nomadnairi/KER/releases)

**English** · [Русский](README.ru.md) · [O'zbek](README.uz.md)

</div>

---

## What this is

KER is a personal AI assistant you host yourself. You talk to it in Telegram
or in a desktop app, and behind the scenes it's a real engine — it remembers
your conversations, calls tools to get things done, speaks and listens, runs
tasks on a schedule, and can plug into your smart home.

Two things make it different from "just another chatbot wrapper":

- **It's yours.** No name is baked in. Call it KER, call it anything — each
  person can name their own assistant, and it'll answer to that name (and to a
  second nickname too, if you want). You bring your own API key, your own
  server, your own data.
- **It's a whole product, not a script.** A polished Telegram bot with buttons
  instead of commands, a desktop "Command Deck" with a live dashboard,
  accounts and subscription tiers, auto-updates — the pieces you'd actually
  need if you wanted to give this to other people (or sell it).

Everything runs locally. The simple stuff (time, math, diagnostics) works even
without an API key.

> **⚡ Free vs. full version.** What's here on GitHub is the **free core** —
> enough to run your own assistant. The **full version** (all premium features
> and higher limits) is available **only through the Telegram bot**, by
> subscription. Start the bot: [@jar_v1_s](https://t.me/jar_v1_s).

---

## What it can do

**Talk & remember.** Chat by text or voice. It keeps a real memory — it
remembers your conversations across restarts and quietly distils lasting facts
about you so it can bring them up later. Pasted passwords, tokens and card
numbers are stripped out before anything is ever stored.

**Actually do things.** The model doesn't just answer — it can call tools:
search the web, read and write files, run shell commands, control the desktop,
check the weather, talk to your smart home. Dangerous powers are off by default
and switched on one at a time.

**Plug in more tools (MCP).** KER speaks the Model Context Protocol, so any MCP
server's tools show up as native skills the assistant can use. Point it at a
config or add one at runtime from the dashboard.

**Run on its own.** Tell it "every day at 9am give me a summary" or "check my
email every 3 hours" and it schedules the task, does it, and reports back —
then reschedules itself.

**Speak your language.** Full interface and replies in English, Russian and
Uzbek. Send a voice note and it transcribes, answers, and can speak back — in
whatever language you used. Voice can run fully free and offline.

**Bring your own brain.** Works with Anthropic (Claude), OpenAI (GPT),
OpenRouter, or a local model (Ollama, LM Studio, vLLM, llama.cpp) — no cloud
key needed if you go local. It retries and falls back automatically, and a
router can send easy questions to a fast model and hard ones to a strong one.

---

## Make it yours (white-label)

This is the part most assistants don't give you.

- **Name it.** Ships as **KER**, but every user can rename their assistant from
  the bot's settings — the new name shows up in the menu, in the replies, and
  on the desktop dashboard. Operators can set a default name for the whole
  deployment.
- **Extra nicknames.** Set `ASSISTANT_ALIASES` and it'll answer to more than one
  name — handy as a personal wake-word. (Left blank by default so a copy you
  hand to someone else stays clean.)
- **Your key, your server, your data.** Users can even bring their own API key
  (BYOK). Nothing phones home.

```env
ASSISTANT_NAME=KER
ASSISTANT_ALIASES=Jarvis   # optional — answers to both
```

---

## Quick start

**You'll need:** Python 3.10+ and an API key (or a local model).

```bash
git clone https://github.com/nomadnairi/KER.git
cd KER

python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # add ANTHROPIC_API_KEY (or OPENAI_API_KEY),
                                 # or point it at a local model
python -m jarvis
```

Prefer `make`? `make install`, `make run`, `make test`, `make lint`.

---

## Talk to it in Telegram

The friendliest way to use KER. It's a button-driven bot — no commands to
memorise — with per-user sessions, so it remembers each person separately.

```bash
pip install aiogram

# .env:
#   TELEGRAM_BOT_TOKEN=...   (from @BotFather)
#   ANTHROPIC_API_KEY=...    (or OPENAI_API_KEY, or a local model)

python -m jarvis.interfaces.telegram_bot     # or: jarvis-bot
```

Inside the bot you get settings tucked into tidy nested menus: language, the
assistant's name, your AI model, memory, voice, integrations, and more. Send a
voice note and it'll answer by voice. There are subscription tiers (Free / Plus
/ Pro) with per-plan limits if you want to run it as a product.

---

## The desktop app — "Command Deck"

`jarvis-desktop` is a real desktop app (PySide6, builds to a Windows `.exe`)
with a live web dashboard inside it: an animated reactor home screen with system
telemetry, a chat with history, the model catalogue, MCP servers, and settings —
all wired to the real engine over a bundled local API, updating in real time.

The owner runs it locally with full control of their PC; other people can sign
in with a username/password or a **Telegram login code** the bot hands them, and
get a limited version. It can check for and install updates on its own.

Downloads (Windows installer + portable build) are on the
[**Releases**](https://github.com/nomadnairi/KER/releases) page. Build
details for the `.exe` / `.apk` are in [docs/CLIENTS.md](docs/CLIENTS.md).

---

## Put it on a server

Run the bot and the HTTP/WebSocket API on a VPS with Docker:

```bash
cp .env.example .env      # fill in your keys
docker compose up -d --build
```

The bot uses long-polling (no inbound port), the API listens on `:8000`, and
both share persistent `data/` and `logs/` volumes. A systemd unit, an nginx +
TLS example and a security checklist are in [docs/DEPLOY.md](docs/DEPLOY.md).

Other apps can talk to the same engine over the API — `GET /health`,
`POST /chat`, and a `/ws/{session}` WebSocket for streaming. Set `API_KEY`
before you expose it publicly.

---

## Under the hood

Python 3.10+, async throughout. A provider-agnostic LLM client with retry and
fallback, a skill/tool system with a fast deterministic path, SQLite-backed
memory with semantic recall, a pub/sub event bus, a capability-gated security
layer, FastAPI + WebSocket, and an aiogram Telegram bot. Config is typed
(pydantic-settings). Tested with pytest and linted with ruff on every commit.

```
jarvis/
├── core/            engine, pipeline, sessions, rate limiting, diagnostics
├── llm/ · routing/  provider-agnostic LLM client + model-tier router
├── skills/ · mcp/   built-in tools + Model Context Protocol client
├── memory/          persistent history + semantic recall (RAG)
├── voice/ · i18n/   STT/TTS backends + EN/RU/UZ localisation
├── integrations/    weather, Home Assistant, per-user connectors
├── interfaces/      Telegram bot, reminders, automations
├── desktop_app/     PySide6 app + live Command Deck dashboard
├── api/             FastAPI + WebSocket server
├── licensing/ · billing/   accounts, login codes, plans
└── security/        capability gating + audit
```

The bigger picture and component status live in [VISION.md](VISION.md) and
[ROADMAP.md](ROADMAP.md); the design is in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## What's next

Done: the assistant core, memory, the Telegram bot, voice, integrations, the
API, the desktop Command Deck, MCP, task automation, auto-updates, accounts and
tiers, and full white-label naming.

On the way: an always-listening voice assistant on a Raspberry Pi (say the name
from across the room), more integrations (calendar, email), and multi-room
setups.

---

## Contributing & contact

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md), and please run
`make test` and `make lint` first.

- Telegram: [@deathgu11](https://t.me/deathgu11)
- Channel: [@jar_v1_s](https://t.me/jar_v1_s)
- Bugs & ideas: [GitHub Issues](https://github.com/nomadnairi/KER/issues)

Licensed under the [MIT License](LICENSE).

<div align="center">

# 🤖 J.A.R.V.I.S.

### Just A Rather Very Intelligent System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/Version-0.17.0-orange)](https://github.com/nomadnairi/J.A.R.V.I.S)
[![Status](https://img.shields.io/badge/Status-Early%20Development-yellow)](https://github.com/nomadnairi/J.A.R.V.I.S)

**A modular personal AI assistant framework — inspired by Tony Stark's companion.**

**English** · [Русский](README.ru.md) · [O'zbek](README.uz.md)

</div>

---

## About

J.A.R.V.I.S. is an open-source framework for building a personal AI assistant:
an LLM-powered intelligence core, a plugin/skill system, tool calling, and a
layered architecture designed to grow into voice, smart-home, and automation
capabilities.

> **Project status:** early development. The core is built and working — an
> async engine, LLM integration (Anthropic / OpenAI), a skill & tool system,
> streaming, an interactive CLI, and a **memory system** (persistent history +
> semantic recall). Voice, integrations, automation, and a web/API are planned.
> See the [Roadmap](#roadmap) below for exactly what's done and what isn't.

---

## What works today

- **🧠 LLM core** — provider-agnostic client for **Anthropic (Claude)** and
  **OpenAI (GPT)**, with automatic retry and fallback between providers.
- **🔧 Tool / function calling** — an agentic loop where the model can call
  tools (skills) to get things done, then answer with the results.
- **🧩 Skill / plugin system** — deterministic, zero-cost handling of common
  requests (date/time, calculator, system diagnostics) before hitting the LLM.
- **🧠 Memory** — persistent conversation history (survives restarts) plus
  semantic recall (RAG): the LLM distils **durable facts** from each turn and
  recalls the relevant ones later. Async, SQLite-backed, with similarity
  threshold + recency weighting; pluggable embeddings (offline / local / OpenAI).
  Bounded per user, deduplicated, and **secret-redacted** — pasted tokens, API
  keys and card numbers are never stored.
- **⚡ Streaming** — token-by-token streamed replies in the CLI.
- **💬 Telegram bot** — chat with the assistant from Telegram; each user gets
  their own persistent session and memory. Localized UI (English / Russian /
  Uzbek) with a command menu and inline language picker; the assistant replies
  in the user's chosen language.
- **🎙 Voice (in the bot)** — send a voice message; it's transcribed, answered,
  and (optionally) spoken back. **Pluggable backends**: STT via OpenAI Whisper
  API or **local Whisper** (free, offline); TTS via OpenAI, **edge-tts** or
  **gTTS** (both free). Multilingual — replies in whatever language you spoke.
- **🔌 Integrations** — external services exposed to the LLM as callable tools:
  **weather** (Open-Meteo, free, no key) and **smart home** (Home Assistant).
  A pluggable framework (connect/health/tool-bridge) makes adding more easy.
- **👥 Multi-session** — many independent conversations via a session manager.
- **📡 Event-driven** — an internal pub/sub bus with passive telemetry.
- **🖥️ Interactive CLI** — chat plus `/skills`, `/stats`, `/state`, `/reset`.

Everything above runs locally; skill/tool commands work even without an API key.

---

## Architecture

```
┌───────────────────────────────────────────────┐
│  Interfaces:  CLI (now)  ·  Web / API (planned)│
└───────────────────────────┬───────────────────┘
                           │  Request
┌───────────────────────────▼───────────────────┐
│                   JarvisEngine                 │
│   StateMachine · Pipeline · SessionManager     │
│        ┌───────────────┴───────────────┐       │
│        ▼                               ▼       │
│  SkillRegistry (tools)          LLMClient (AI) │
│   fast path + tool exec       retry + fallback │
└───────────────────────────┬───────────────────┘
                           │ events
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   EventBus            Telemetry          Memory ·
   (pub/sub)           (metrics)         Integrations
```

Full details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The north-star
vision and component status live in [VISION.md](VISION.md) and
[ROADMAP.md](ROADMAP.md).

---

## Tech stack

| Area | Tools |
|------|-------|
| Language | Python 3.10+ |
| Config | pydantic-settings |
| LLM | Anthropic SDK, OpenAI SDK |
| CLI | rich |
| Testing | pytest, pytest-asyncio |
| Lint / CI | ruff, GitHub Actions |

Optional dependencies (vector DB, voice, FastAPI) are listed but kept inactive
until the feature that needs them is enabled.

---

## Project structure

```
jarvis/
├── __main__.py        # interactive CLI (python -m jarvis)
├── config/            # typed settings & constants
├── core/              # engine, DI container, pipeline, state, sessions
├── llm/               # provider-agnostic client + Anthropic/OpenAI + tools
├── skills/            # skill/tool system + built-ins (datetime, calc, system)
├── events/            # pub/sub event bus
├── telemetry/         # metrics collector
├── voice/             # STT/TTS backends (OpenAI / local Whisper / edge / gTTS)
├── interfaces/        # Telegram bot (CLI lives in __main__.py)
├── models/            # Message/Conversation, Request/Response
├── memory/            # persistent history + semantic recall (SQLite + vectors)
├── integrations/      # external connectors as tools (weather, Home Assistant)
└── utils/             # logging, retry, timing, exceptions, text
tests/                 # pytest suite
docs/                  # architecture documentation
```

---

## Quick start

**Requirements:** Python 3.10+

```bash
# Clone
git clone https://github.com/nomadnairi/J.A.R.V.I.S.git
cd J.A.R.V.I.S

# Install
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure (add your API key)
cp .env.example .env            # set ANTHROPIC_API_KEY or OPENAI_API_KEY

# Run
python -m jarvis
```

Prefer `make`? `make install`, `make run`, `make test`, `make lint`.

---

## Usage

Inside the CLI:

```
Sir › calc (12.5/100)*320
J.A.R.V.I.S. › (12.5/100)*320 = 40

Sir › what time is it
J.A.R.V.I.S. › It is 14:05.

Sir › system status
J.A.R.V.I.S. › All systems nominal. …

Sir › /skills      # list skills and which are exposed as LLM tools
Sir › /stats       # session telemetry
Sir › /memory      # memory statistics
Sir › /reset       # clear conversation (keeps long-term memory)
Sir › /forget      # wipe history and long-term memory
```

Anything a skill doesn't handle is answered by the LLM (which may call tools
along the way).

---

## Telegram bot

Chat with J.A.R.V.I.S. from Telegram. Each user gets their own persistent
session, so the assistant remembers each person independently.

```bash
pip install aiogram            # optional interface dependency

# In your .env:
#   TELEGRAM_BOT_TOKEN=...      (from @BotFather)
#   ANTHROPIC_API_KEY=...       (or OPENAI_API_KEY)

python -m jarvis.interfaces.telegram_bot     # or: jarvis-bot
```

Bot commands: `/language` (switch UI/reply language), `/reset` (clear the
current conversation), `/forget` (wipe everything remembered about you),
`/help`. The command menu and interface are localized in **English, Russian and
Uzbek**, and the assistant replies in the language each user picks. Access can
be limited to specific user IDs via `TELEGRAM_ALLOWED_USERS`.

**Voice messages:** send the bot a voice note — it transcribes it, answers, and
(optionally) replies with a spoken message. It understands and speaks any
language, matching the one you used. Backends are configurable:

- **STT** (`STT_BACKEND`): `openai` (Whisper API, paid) or `local`
  (open-source Whisper — free & offline, `pip install openai-whisper`).
- **TTS** (`TTS_BACKEND`): `openai` (paid), `edge` (free, `pip install edge-tts`)
  or `gtts` (free, `pip install gTTS`).

So you can run voice **fully free** (`STT_BACKEND=local`, `TTS_BACKEND=edge`) or
with cloud quality. Other knobs: `VOICE_ENABLED`, `TTS_VOICE`, `VOICE_REPLIES`,
`LOCAL_WHISPER_MODEL`.

---

## Roadmap

| Area | Status |
|------|--------|
| Core: async engine, LLM, skills/tools, streaming, CLI, tests, CI | ✅ done |
| Memory: persistent history + semantic recall | ✅ done |
| Telegram bot (per-user sessions + memory) | ✅ done |
| Voice in the bot: speech-to-text / text-to-speech (multilingual) | ✅ done |
| Integrations framework + weather + smart home (Home Assistant) | ✅ done |
| Desktop voice + Raspberry Pi (mic/speaker) | planned |
| More integrations: calendar, email | planned |
| Task automation: scheduler, workflows | planned |
| API layer: FastAPI + WebSocket | planned |
| Web dashboard | planned |

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
the layer layout, and how to add a skill. Please run `make test` and
`make lint` before opening a pull request.

---

## Contact

- Telegram (personal): [@deathgu11](https://t.me/deathgu11)
- Telegram (channel): [@jar_v1_s](https://t.me/jar_v1_s)
- Issues & feature requests: [GitHub Issues](https://github.com/nomadnairi/J.A.R.V.I.S/issues)

---

## License

Licensed under the [MIT License](LICENSE).

<div align="center">

*Built for intelligent automation.* 🤖

</div>

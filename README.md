<div align="center">

# 🤖 J.A.R.V.I.S.

### Just A Rather Very Intelligent System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/Version-0.5.0-orange)](https://github.com/nomadnairi/J.A.R.V.I.S)
[![Status](https://img.shields.io/badge/Status-Early%20Development-yellow)](https://github.com/nomadnairi/J.A.R.V.I.S)

**A modular personal AI assistant framework — inspired by Tony Stark's companion.**

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
- **⚡ Streaming** — token-by-token streamed replies in the CLI.
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
   EventBus            Telemetry          Memory /
   (pub/sub)           (metrics)         Integrations
                                          (planned)
```

Full details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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
├── models/            # Message/Conversation, Request/Response
├── memory/            # persistent history + semantic recall (SQLite + vectors)
├── integrations/      # contracts (implementation planned)
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

## Roadmap

| Area | Status |
|------|--------|
| Core: async engine, LLM, skills/tools, streaming, CLI, tests, CI | ✅ done |
| Memory: persistent history + semantic recall | ✅ done |
| Voice: speech-to-text / text-to-speech | planned |
| Integrations: smart home, calendar, email | planned |
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

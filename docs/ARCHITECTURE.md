# Architecture

J.A.R.V.I.S. is built as a set of **layers** that stack on top of a single
orchestrator (`JarvisEngine`). Each layer is added in its own stage so the
system stays runnable at every point.

```
┌──────────────────────────────────────────────┐
│  Interfaces:  CLI (Stage 1) · API/Web (later) │
└───────────────────────┬──────────────────────┘
                        │
┌───────────────────────▼──────────────────────┐
│              JarvisEngine (core)              │
│   persona · conversation flow · routing      │
└───────────────────────┬──────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐    ┌──────────┐    ┌──────────────┐
   │  LLM    │    │  Memory  │    │ Integrations │
   │ client  │    │ (Stage 2)│    │  (Stage 4)   │
   └─────────┘    └──────────┘    └──────────────┘
        ▲               ▲               ▲
        └───────────────┴───────────────┘
              Task Automation (Stage 5)
```

## Build stages

| Stage | Scope | Status |
|-------|-------|--------|
| **1** | Foundation: config, logging, LLM core, CLI | ✅ done |
| 2 | Memory system (conversation store + vector DB) | planned |
| 3 | Voice layer (STT / TTS) | planned |
| 4 | Integrations (smart home, calendar, email) | planned |
| 5 | Task automation (scheduler, workflows) | planned |
| 6 | API layer (FastAPI + WebSocket) | planned |
| 7 | Frontend (React dashboard) | planned |

## Stage 1 — Foundation

Package layout:

```
jarvis/
├── __init__.py          # package metadata, version
├── __main__.py          # `python -m jarvis` interactive CLI
├── config/
│   └── settings.py      # pydantic-settings, loaded from .env
├── core/
│   ├── engine.py        # JarvisEngine — orchestrator + persona
│   └── llm.py           # provider-agnostic LLM client (Anthropic/OpenAI)
└── utils/
    └── logger.py        # rich console + rotating file logging
```

### Design decisions

- **Provider-agnostic LLM.** `LLMClient` hides the vendor SDK. Switching
  between Anthropic and OpenAI is a `.env` change (`LLM_PROVIDER`), not a code
  change. SDKs are imported lazily so the package imports without them.
- **Typed config.** All settings live in one validated `Settings` object,
  cached as a singleton via `get_settings()`.
- **Runnable from day one.** The CLI gives a real, testable surface before any
  heavier layers exist.

### Try it

```bash
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
python -m jarvis
```

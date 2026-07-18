# Architecture

J.A.R.V.I.S. is built as a set of **layers** stacked on a single orchestrator
(`JarvisEngine`), wired together by a dependency-injection container and
connected by an event bus. Each layer is added in its own stage, and the
system stays runnable at every point.

## System overview

```
┌───────────────────────────────────────────────────────────┐
│  Interfaces:  CLI (Stage 1)  ·  API / Web (Stage 6)        │
└───────────────────────────────┬───────────────────────────┘
                                │  Request
┌───────────────────────────────▼───────────────────────────┐
│                        JarvisEngine                        │
│  ┌──────────────┐   ┌───────────────┐   ┌──────────────┐  │
│  │ StateMachine │   │   Pipeline    │   │ SessionCtx   │  │
│  └──────────────┘   │ (middleware)  │   └──────────────┘  │
│                     └───────┬───────┘                      │
│              ┌──────────────┴──────────────┐               │
│              ▼                             ▼               │
│      ┌───────────────┐            ┌────────────────┐       │
│      │ SkillRegistry │  (local)   │   LLMClient    │ (AI)  │
│      │  + builtins   │            │ retry+fallback │       │
│      └───────────────┘            └────────────────┘       │
└───────────────────────────────┬───────────────────────────┘
                                │ events
      ┌─────────────────────────┼─────────────────────────┐
      ▼                         ▼                         ▼
┌───────────┐            ┌────────────┐            ┌──────────────┐
│ EventBus  │            │ Telemetry  │            │  Memory /    │
│ (pub/sub) │            │ (metrics)  │            │ Integrations │
└───────────┘            └────────────┘            │ (contracts)  │
                                                    └──────────────┘
```

Everything is constructed once by the **`ServiceContainer`** (dependency
injection) and shared. Components communicate through the **`EventBus`** rather
than by calling each other directly, which keeps cross-cutting concerns
(telemetry, logging, later the UI) fully decoupled from the engine.

## Request lifecycle

```
user text
   │
   ▼
Request ──► Pipeline (normalise, log, …)
                │
                ▼
        SkillRegistry.find()  ── match? ──► Skill.handle() ──► Response (SKILL)
                │ no match
                ▼
           LLMClient.complete()  ──► Response (LLM)
                │
                ▼
        events: RESPONSE_READY ──► Telemetry
```

Skills are tried **first** and deterministically (e.g. "what time is it",
"system status"), so common requests never incur an LLM call. Anything a skill
doesn't claim falls through to the language model.

## Build stages

| Stage | Scope | Status |
|-------|-------|--------|
| **1** | Foundation: config, events, DI, state machine, pipeline, LLM core, skills, telemetry, CLI, tests, CI | ✅ done |
| 2 | Memory system (conversation store + vector DB) | planned |
| 3 | Voice layer (STT / TTS) | planned |
| 4 | Integrations (smart home, calendar, email) | planned |
| 5 | Task automation (scheduler, workflows) | planned |
| 6 | API layer (FastAPI + WebSocket) | planned |
| 7 | Frontend (React dashboard) | planned |

## Package layout (Stage 1)

```
jarvis/
├── __init__.py            # package metadata, public exports
├── __main__.py            # `python -m jarvis` interactive CLI
│
├── config/
│   ├── settings.py        # pydantic-settings, loaded from .env
│   └── constants.py       # enums: Provider, Role, State, EventType, …
│
├── core/
│   ├── engine.py          # JarvisEngine — orchestrator
│   ├── container.py       # ServiceContainer — dependency injection
│   ├── pipeline.py        # middleware chain (normalise, log, …)
│   ├── state.py           # assistant state machine
│   └── context.py         # per-session context
│
├── llm/
│   ├── client.py          # unified client: retry + provider fallback
│   ├── base.py            # LLMProvider ABC, LLMResult
│   ├── prompts.py         # persona / system-prompt builder
│   └── providers/         # anthropic_provider.py, openai_provider.py
│
├── skills/
│   ├── base.py            # BaseSkill ABC, SkillResult
│   ├── registry.py        # registration + priority dispatch
│   └── builtin/           # datetime, system, help
│
├── events/
│   ├── bus.py             # synchronous pub/sub EventBus
│   └── events.py          # Event dataclass
│
├── telemetry/
│   └── metrics.py         # MetricsCollector (attaches to the bus)
│
├── models/
│   ├── message.py         # Message, Conversation
│   └── response.py        # Request, Response envelopes
│
├── memory/                # Stage 2 contracts (BaseMemoryStore)
├── integrations/          # Stage 4 contracts (BaseIntegration)
└── utils/
    ├── logger.py          # rich console + rotating file logging
    ├── exceptions.py      # typed exception hierarchy
    ├── retry.py           # exponential-backoff retry decorator
    ├── timing.py          # Stopwatch / measure / timed
    └── text.py            # text helpers
```

## Design decisions

- **Provider-agnostic LLM.** `LLMClient` hides the vendor SDK behind
  `LLMProvider`. Switching providers is a `.env` change; a failed primary
  provider automatically falls back to any other configured one, with
  exponential-backoff retries for transient errors.
- **Skills before the model.** Deterministic, testable, zero-cost handling of
  common intents — and the foundation of the plugin ecosystem.
- **Event-driven.** Telemetry (and later the UI) subscribe to the bus instead
  of being called by the engine, so the core stays lean.
- **Dependency injection.** One container builds and shares singletons, making
  components trivial to substitute in tests (see `tests/conftest.py`).
- **Typed everything.** Config, messages, requests/responses, and errors are
  all structured types, not loose dicts and strings.

## Try it

```bash
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
python -m jarvis              # then try: "system status", "what time is it"
```

Even without an API key, skill-backed commands work. Run the tests with:

```bash
make test
```

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
| **1** | Foundation: config, events, DI, state machine, pipeline, LLM core (async, tools, streaming), skills, telemetry, multi-session, CLI, tests, CI | ✅ done |
| **2** | Memory system: persistent conversation store + semantic recall (RAG) | ✅ done |
| 3 | Voice layer (STT / TTS) | planned |
| 4 | Integrations (smart home, calendar, email) | planned |
| 5 | Task automation (scheduler, workflows) | planned |
| 6 | API layer (FastAPI + WebSocket) | planned |
| 7 | Frontend (React dashboard) | planned |

## Stage 2 — Memory

Two complementary stores behind a single **async** :class:`MemoryManager`:

* **Conversation store** (`SQLiteConversationStore`) — persists every turn to
  SQLite (stdlib, no external DB). Sessions reload their recent history on
  first access, so conversations survive restarts.
* **Semantic memory** (`SQLiteVectorStore`, default) — embeds durable takeaways
  and recalls the most relevant ones by cosine similarity. Recalled memories
  are injected into the system prompt (retrieval-augmented generation) so the
  assistant "remembers" facts across turns and sessions.

Hardening (Stage 2+):

* **Async, non-blocking** — writes, recall, and embeddings run in worker
  threads via `asyncio.to_thread`, so memory never stalls the event loop.
* **Incremental persistence** — the SQLite vector store appends one row per
  memory (no rewriting a whole JSON file); recall applies a **similarity
  threshold** and a **recency** weight so weak or stale memories are dropped.
* **Fact extraction** — instead of storing raw transcripts, a `FactExtractor`
  uses the LLM to distil durable facts ("the user's dog is named Rex"). It runs
  **in the background** after the reply, adding no latency; `engine.drain()`
  awaits pending work.
* **Pluggable embeddings** — `HashingEmbedder` (offline default, zero deps),
  `LocalEmbedder` (semantic, via optional `fastembed`), or `OpenAIEmbedder`.
* **Pluggable vector backend** — `SQLiteVectorStore` (default), `InMemoryVectorStore`,
  or `ChromaVectorStore`; all implement `BaseMemoryStore`.

Memory is optional (`MEMORY_ENABLED`) and adds **no required dependencies**.

```
turn ──► ConversationStore (persist inline) ──► reload on next session
    └──► FactExtractor (LLM, background) ──► VectorStore (embed & store)
                                                    │
             query ──► recall (threshold + recency) ┘──► system prompt (RAG)
```

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

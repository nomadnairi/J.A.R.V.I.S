# Roadmap

Status of every capability, tracked against the [vision](VISION.md). This is a
living document — updated as components land.

Legend: ✅ done · 🟡 partial · ⬜ planned

## Foundation (done)

- ✅ Async engine, DI container, pipeline, state machine, multi-session
- ✅ LLM core (Anthropic/OpenAI) — tools, streaming, retry + fallback
- ✅ Event bus + telemetry
- ✅ Interactive CLI

## Desktop Edition

| Capability | Status | Notes |
|------------|--------|-------|
| Text Interface | ✅ | CLI + Telegram bot |
| Voice Interface | 🟡 | In the bot (STT/TTS, pluggable, multilingual). Desktop mic/speaker + wake word planned |
| Memory | ✅ | Persistent history + semantic recall + facts; bounded, deduped, secret-redacted |
| Tool Manager | ✅ | Skill/tool registry + integration & capability tools |
| Goal System | ✅ | Per-session goals; LLM tools to add/list/complete/cancel; open goals surfaced in context |
| Agent System | 🟡 | Agentic tool loop done; autonomous sub-agents planned |
| AI Router | ✅ | Provider fallback + task→model-tier routing (fast/strong) with transparent heuristics; per-call model override |
| File Manager | ✅ | Sandboxed read/list/search/write tools; write gated by security |
| Coding Assistant | ✅ | Read/search/write code (file tools) + run_command / run_tests (shell gated by security) |
| Desktop Control | ⬜ | Apps, windows, keyboard/mouse (desktop-only) |
| Security Module | ✅ | Capability gating (file/shell/desktop OFF by default) + audit log + secret redaction |

## Integrations

| Integration | Status |
|-------------|--------|
| Weather (Open-Meteo, free) | ✅ |
| Smart home (Home Assistant) | ✅ |
| Calendar | ⬜ |
| Email | ⬜ |

## Full / Smart-Home Edition

| Capability | Status |
|------------|--------|
| Home Assistant | ✅ |
| Smart devices | ✅ (via Home Assistant) |
| Wake word ("Hey Jarvis") | ⬜ |
| Raspberry Pi nodes | ⬜ |
| Sensors | ⬜ |
| Cameras & computer vision | ⬜ |
| Network control | ⬜ |

## Interfaces & delivery

| Item | Status |
|------|--------|
| Telegram bot | ✅ |
| Desktop voice app | ⬜ |
| API layer (FastAPI + WebSocket) | ⬜ |
| Web dashboard | ⬜ (later) |

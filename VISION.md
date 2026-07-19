# Vision

**J.A.R.V.I.S. is a real personal AI — a mind you talk to, that remembers you,
acts on your behalf, and runs your digital (and physical) world.**

Inspired by Tony Stark's assistant, the goal is not a chatbot but a capable
companion: it listens and speaks naturally, keeps context about you over time,
reasons through multi-step tasks, uses tools and agents to get things done, and
controls your computer and your home.

We build the *real* parts of that fiction from real building blocks. Holograms
and a flying suit are cinema; an intelligent, proactive, voice-driven assistant
with memory, agency, tools, and home/edge control is achievable — and this
project is that assistant.

## Two editions

### 1. Desktop Edition
JARVIS running on your computer — always available, voice + text.

| Capability | What it means |
|------------|---------------|
| Voice Interface | Talk to it; it talks back. Wake word later. |
| Text Interface | CLI and Telegram. |
| Memory | Remembers conversations and durable facts about you. |
| Goal System | Tracks goals/tasks and works toward them proactively. |
| AI Router | Sends each task to the right model (fast vs. powerful). |
| Agent System | Sub-agents that execute multi-step work autonomously. |
| Tool Manager | Registers and governs the tools the AI can call. |
| File Manager | Reads, writes and searches files (sandboxed). |
| Coding Assistant | Helps read, write and run code. |
| Desktop Control | Controls apps, windows, keyboard/mouse. |
| Security Module | Gates dangerous actions; audits; redacts secrets. |

### 2. Full / Smart-Home Edition
Desktop Edition **plus** a local, private home nervous system:

Raspberry Pi nodes · Wake word ("Hey Jarvis") · Home Assistant ·
Sensors · Cameras & vision · Smart devices · Network control.

Principle: **maximum privacy and control** — runs locally where possible, your
data stays yours.

## Principles

- **Agentic, not passive** — it does things, it doesn't just answer.
- **Memory-first** — every interaction makes it know you better.
- **Local & private where possible** — free/offline backends are first-class.
- **Safe by construction** — dangerous capabilities are gated and audited.
- **Layered & pluggable** — every capability is a module behind a contract.

See [ROADMAP.md](ROADMAP.md) for exactly what's done and what's next.

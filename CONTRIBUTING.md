# Contributing to J.A.R.V.I.S.

Thanks for your interest in improving J.A.R.V.I.S.! This guide covers the
essentials for getting a change merged.

## Development setup

```bash
git clone https://github.com/nomadnairi/J.A.R.V.I.S.git
cd J.A.R.V.I.S

python -m venv venv
source venv/bin/activate

make install-dev      # runtime + dev dependencies
cp .env.example .env  # add your API key(s)
```

## Everyday commands

```bash
make run     # launch the interactive CLI
make test    # run the test suite
make lint    # lint with ruff
make format  # auto-format with ruff
```

## Project layout

The codebase is organised into layers (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)):

| Package | Responsibility |
|---------|----------------|
| `jarvis/config` | Typed settings & constants |
| `jarvis/core` | Engine, container (DI), pipeline, state machine |
| `jarvis/llm` | Provider-agnostic LLM client & providers |
| `jarvis/skills` | Plugin/skill system + built-ins |
| `jarvis/events` | Publish/subscribe event bus |
| `jarvis/telemetry` | Metrics collection |
| `jarvis/memory` | Memory contracts (impl in Stage 2) |
| `jarvis/integrations` | Integration contracts (impl in Stage 4) |

## Adding a skill

1. Subclass `jarvis.skills.base.BaseSkill`.
2. Implement `can_handle(text)` and `handle(text, context)`.
3. Register it in `jarvis/skills/builtin/__init__.py` (or via the registry).
4. Add a test under `tests/`.

## Pull request checklist

- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] New behaviour is covered by tests
- [ ] Public functions/classes have docstrings
- [ ] Commits are focused and clearly described

## Code style

- Python 3.10+, type hints on public APIs.
- Keep modules small and single-purpose.
- Prefer composition and the existing layer boundaries over shortcuts.

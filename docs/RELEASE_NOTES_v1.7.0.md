# J.A.R.V.I.S. v1.7.0 — Enterprise Update

A big under-the-hood and UX release. Everything is button-driven, provider-agnostic
and self-checking. **450 automated tests, all green.**

## ✨ Highlights

### 🧭 New in-app navigation
Every menu screen now carries a consistent nav row — **⬅️ Back · 🏠 Home · ❌ Close**.
Nested screens expose all three; top-level screens show Back + Close. Close actually
dismisses the card. Available in English, Russian and Uzbek.

### 🖥 Local / self-hosted models (AI Manager)
Run your own model with one line: **Ollama, LM Studio, vLLM, llama.cpp** over their
OpenAI-compatible endpoints via backend presets — no cloud key required. `local`
becomes a switchable model profile. A new **AI Manager** reports which providers are
configured, their models and the default.

```
LLM_PROVIDER=local
LOCAL_LLM_BACKEND=ollama      # ollama | lmstudio | vllm | llamacpp | custom
LOCAL_LLM_MODEL=llama3
```

### 🌍 Internet for the AI (Search Provider Manager)
Web search is now a **gated tool** the model can call. A category-aware router picks
the provider — 🤖 AI search (Perplexity, Tavily, Exa) → 🌐 Web (Brave, Google, SerpAPI,
DuckDuckGo) → 🧭 Browser (Playwright). **DuckDuckGo works with no key**, so search runs
out of the box. A new **Search providers** screen in Settings shows each provider's
category and readiness (✅ ready · ❌ needs a key · ⭐ active).

### 📂 Document reading (File Manager)
Extract text from **PDF, DOCX and plain-text** files via a `read_document` tool.
Missing an optional parser? You get an actionable hint instead of a crash.

### 🔧 Configuration Manager
Cross-field validation catches misconfigurations Pydantic can't: provider selected
without a key, OpenRouter without a model, image mode without a key, a bot allowlist
that locks out every admin, and more. Surfaced in the startup banner and `/doctor`.

### 🎛 Capability Manager
Every feature now reports a clear state — **✅ Enabled · 🔶 Restricted · ❌ Disabled** —
unifying the master switches and fine-grained permissions (e.g. read-only files, coding
without shell, image mode without a key).

### 🔴 Security self-audit
A settings-only posture review grades findings (high/medium/low/info): dangerous
capabilities on, an unauthenticated API, secret redaction off, a public bot. Plus a
real fix: search providers no longer leak API keys carried in a request URL.

## 🔄 Upgrading your server
```
git pull
python3 scripts/sync_env.py          # adds new keys to your .env, keeps your values
docker compose up -d --force-recreate
```

## 💻 Desktop app
Windows installer and portable builds are attached below (early / grey access),
built automatically for this tag. Windows x64 is the primary target; other platforms
are experimental.

---
🤖 Built with automated tests and CI on every commit.

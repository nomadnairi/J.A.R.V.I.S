# KER v1.9.0

The assistant now ships as **KER** — a clean, ownable brand instead of a
third-party name — and it's fully white-label: rename it to anything, and it
can answer to more than one name. **513 automated tests, all green.**

## ✨ What's new

### 🏷 Meet KER — and make it yours
The assistant is named **KER** out of the box. Everything the user sees —
the Telegram menu header, the desktop Command Deck (wordmark, arc-reactor
core, boot splash, About card, status bar) and the assistant's own persona —
now uses this name.

### 🎛 White-label: name your own assistant
- **Per-user rename** — a new **🏷 Assistant name** button in the bot's
  Preferences lets every user name their assistant. The chosen name flows
  into the menu, the replies (persona) and the dashboard, live.
- **Operator default** — set `ASSISTANT_NAME` to ship it under any brand.

### 🗣 Answers to more than one name
New `ASSISTANT_ALIASES` setting: extra names the assistant also responds to
(e.g. a personal wake-word). Blank by default so resold copies stay clean;
set e.g. `ASSISTANT_ALIASES=Jarvis` for a personal build that answers to
both.

## 🔄 Upgrading your server
```
git pull
python3 scripts/sync_env.py
docker compose up -d --force-recreate
```

## 💻 Desktop app
Windows installer and portable build are attached below (early / grey access).
Owner runs it locally (full app); hand others the app + a Telegram login code.

---
🤖 Built with automated tests and CI on every commit.

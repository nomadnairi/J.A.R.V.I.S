# Desktop (.exe) & Android (.apk) clients

Both clients talk to the same brain. The difference is where the engine runs:

| Client | Engine | PC control | Sign-in |
|--------|--------|-----------|---------|
| **Desktop app** (local mode) | on your PC | ✅ granular, per-function | not required |
| **Desktop app** (account mode) | on your server | — | username/password |
| **Android app** | on your server | — | username/password |

Memory is shared per surface: in local mode the desktop keeps its own memory
on the PC; in account/remote mode all clients (desktop, Android, Telegram via
`/link`) share the server-side memory of your account.

---

## Desktop app

```bash
pip install ".[gui]"          # PySide6
python -m jarvis.desktop_app  # or: jarvis-desktop
```

Tabs:

- **Chat** — talk to J.A.R.V.I.S.; language switch (EN/RU/UZ) in the corner.
- **Assistant** — LLM provider (Anthropic/OpenAI), model, API keys.
- **PC Access** — granular per-function permissions, all dangerous ones OFF by
  default: read files / write files / run shell commands / control
  keyboard-mouse-screen, plus the workspace sandbox folder.
- **Integrations** — weather, Home Assistant, Telegram bot token, the
  "allow sending Telegram messages/posts" switch and the channel for posts.
- **Memory** — clear the conversation, wipe memory, link Telegram
  (shows a `/link CODE` to send to the bot).
- **Logs** — the last lines of `jarvis.log` / `audit.log`.

Settings persist in `%APPDATA%\JARVIS\desktop.json` (Windows) or
`~/.config/jarvis/desktop.json` (Linux/macOS), file mode 0600.

### Working together with the Telegram bot

Run the bot (`jarvis-bot`) and the desktop app at the same time — they don't
conflict. The bot answers people in Telegram; the desktop assistant can *send*
messages and publish channel posts through the same bot token when you enable
**Integrations → allow sending** (tools `telegram_send` / `telegram_post`).
Example: "запость в канал новость о релизе" from the desktop chat.

### Build a binary yourself

```powershell
pip install ".[gui]" pyinstaller
pyinstaller deploy/desktop/jarvis-desktop.spec
# → dist\JARVIS.exe (Windows) / dist/JARVIS (Linux, macOS)
```

The one-file binary bundles Python, Qt and the whole engine, so expect
**roughly 100–180 MB** — that's normal for a self-contained desktop AI app.
PyInstaller builds for the OS/architecture it runs on; it cannot cross-compile.

### Prebuilt binaries for every platform (CI)

The **Desktop builds** GitHub Actions workflow builds all targets natively:

| Target | Runner | Status |
|--------|--------|--------|
| `JARVIS-windows-amd64.exe` | windows-latest | ✅ |
| `JARVIS-windows-arm64.exe` | windows-11-arm | experimental |
| `JARVIS-linux-amd64` | ubuntu-latest | ✅ |
| `JARVIS-linux-arm64` | ubuntu-24.04-arm | ✅ |
| `JARVIS-macos-amd64` | macos-13 (Intel) | ✅ |
| `JARVIS-macos-arm64` | macos-latest (Apple Silicon) | ✅ |

How to get them:

- **Any time:** GitHub → Actions → *Desktop builds* → **Run workflow**; when it
  finishes, download the artifacts from the run page.
- **On release:** push a version tag (`git tag v1.3.0 && git push --tags`) —
  the binaries are attached to the GitHub Release automatically.

> **32-bit Windows (x86)?** Not possible: Qt 6 / PySide6 are 64-bit only.
> All modern Windows installs are 64-bit (amd64 or arm64), so this covers
> real users.

---

## Android app

See [clients/android/README.md](../clients/android/README.md) — a Kivy client
built with buildozer. It needs a deployed server (`docs/DEPLOY.md`) with
`AUTH_ENABLED=true`.

---

## Accounts: issuing access after a purchase

On the server:

```bash
jarvis-admin create-user tony                # generates & prints a password
jarvis-admin issue-license tony --days 365   # prints the license key once
jarvis-admin list tony
```

Hand the username + password to the buyer. Login checks the password AND that
an active (unexpired, unrevoked) license exists; `jarvis-admin disable tony`
or `revoke-license` cuts access at any time. Tokens expire after
`AUTH_TOKEN_TTL_HOURS` (30 days by default).

Optional Telegram confirmation: with `AUTH_REQUIRE_TELEGRAM=true` a user must
link their Telegram (`/link CODE` to the bot; the code comes from the desktop
app or `POST /auth/pairing-code`) before sign-in is allowed.

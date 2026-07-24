# KER v1.9.1

A branding-cleanup release: the app now lives at **github.com/nomadnairi/K.E.R**
and the downloads are named after the brand.

## ✨ What's new

- **KER-named binaries.** The Windows installer is now **`KER-Setup.exe`** and
  the portable build is **`KER-windows-amd64.exe`** (installs as `KER.exe`,
  under a `KER` program folder). No more leftover third-party filenames.
- **Repository renamed** to `nomadnairi/K.E.R`; all links, the clone URL and the
  built-in updater now point at the new home. (GitHub redirects the old
  address, so existing clones keep working.)
- Everything from **v1.9.0** — the KER rebrand and full white-label naming
  (per-user rename + `ASSISTANT_ALIASES`) — carried forward. 513 tests green.

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

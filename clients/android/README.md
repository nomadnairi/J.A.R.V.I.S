# J.A.R.V.I.S. for Android

A thin Kivy client for the J.A.R.V.I.S. HTTP API. The engine runs on your
server; the phone signs in with the username/password issued after purchase
and chats over the same API the desktop app uses. Memory is shared
server-side, so the assistant remembers you across the Telegram bot, desktop
and phone.

## Build the .apk

Building requires Linux (or WSL on Windows) with the Android SDK/NDK — the
`buildozer` tool downloads those automatically on first run:

```bash
pip install buildozer cython
cd clients/android
buildozer android debug          # first run takes a while (SDK/NDK download)
# → bin/jarvis-*-debug.apk
```

Install on your phone:

```bash
buildozer android deploy run     # over adb/USB
# or copy bin/jarvis-*-debug.apk to the phone and open it
```

For a signed release build see the buildozer docs (`buildozer android release`).

## Requirements on the server side

- The API must be reachable from the phone — deploy it per `docs/DEPLOY.md`
  (nginx + TLS recommended; use `https://…` in the app).
- `AUTH_ENABLED=true` on the server, with an account and license issued via
  `jarvis-admin` (or the `/admin` API).

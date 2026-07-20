# J.A.R.V.I.S. for Android — native (Kotlin + Jetpack Compose)

A native Android client built with Kotlin and Jetpack Compose (Material 3),
matching the desktop app's dark arc-reactor look. It signs in to a
J.A.R.V.I.S. server and chats with streaming replies; memory is shared with
your other surfaces (desktop, Telegram) via your account.

This is the modern native alternative to the Kivy client in `../android`.

## Features

- Login screen (server URL + username/password), token saved on device.
- **Multiple conversations** with a navigation drawer — new chat, switch,
  auto-titled from the first message; history stored on the device.
- Streaming chat (reads `/chat/stream` incrementally), long-press a bubble to
  copy it, empty-state welcome.
- **Settings**: switch the AI model (from `GET /models`), reply language,
  theme (System / Dark / Light), link Telegram (pairing code), sign out.
- Material 3 theme with the JARVIS cyan accent; follows system dark/light.
- No third-party HTTP dependency — standard `HttpURLConnection` + `org.json`.

## Build

Easiest — **Android Studio** (Koala or newer):

1. `File → Open` → select this `android-kotlin` folder.
2. Let Gradle sync (it downloads the SDK/Kotlin/Compose automatically).
3. `Run` on a device/emulator, or `Build → Build APK(s)` for a `.apk`.

Command line (needs the Android SDK and JDK 17):

```bash
cd clients/android-kotlin
# First time only — generate the Gradle wrapper if it isn't present:
gradle wrapper --gradle-version 8.9
./gradlew assembleDebug        # → app/build/outputs/apk/debug/app-debug.apk
```

Signed release build: `./gradlew assembleRelease` (configure a keystore first;
see the Android docs).

## Server requirements

- The API must be reachable from the phone (deploy per `../../docs/DEPLOY.md`).
- `AUTH_ENABLED=true` with an account + license issued via `jarvis-admin`.
- For local testing over plain HTTP, cleartext traffic is allowed in the
  manifest; use `https://` in production (put the API behind nginx + TLS).

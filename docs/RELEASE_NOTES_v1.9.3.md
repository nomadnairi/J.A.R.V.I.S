# KER v1.9.3

Real data, no fakes — and a genuine 3D reactor.

## ✨ What's new

- **Dashboard shows only real data.** Removed every placeholder that looked
  like live data but wasn't: the hardcoded Python version and fake
  "Telegram Online" pill, the invented CPU/RAM demo numbers, the fabricated
  provider counts, and the fake sample chat history. When the engine isn't
  connected, panels now honestly show "—" / offline instead of made-up values.
- **Real telemetry from the backend.** `/dashboard/state` now reports the real
  Python version and the real live-session count; CPU/RAM report `null` (shown
  as "—") when psutil isn't available rather than faking `0`.
- **True 3D reactor.** The home core is now a real WebGL shader — a pulsing,
  rotating volumetric arc-reactor rendered on the GPU, tinted with your accent
  colour. Falls back to the CSS reactor if WebGL is unavailable.

## ℹ️ Reminder

Run the desktop app standalone with the live dashboard by choosing
**"Continue locally"** on sign-in — the bundled engine then serves everything
online.

## 💻 Desktop app
Windows installer and portable build are attached below.

---
🤖 Built with automated tests and CI on every commit.

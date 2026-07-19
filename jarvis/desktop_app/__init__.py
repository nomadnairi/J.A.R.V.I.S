"""J.A.R.V.I.S. Desktop — a PySide6 (Qt) GUI over the local engine.

Run with ``python -m jarvis.desktop_app`` (or the ``jarvis-desktop`` script).
PySide6 is an optional dependency (``pip install 'jarvis-assistant[gui]'``);
everything in this package other than :mod:`jarvis.desktop_app.app` is
GUI-free and works headless (config store, API client, engine thread).

The app has two modes, chosen on the login screen:

* **Local** — the full engine runs on this machine with your own LLM keys;
  file/shell/desktop control capabilities apply to this PC.
* **Account** — sign in with the username/password issued after purchase; the
  app talks to a remote J.A.R.V.I.S. server over the HTTP API.
"""

from jarvis.desktop_app.config import AppConfig

__all__ = ["AppConfig"]

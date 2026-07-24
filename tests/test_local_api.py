"""The desktop bundled local API: serve the engine over HTTP on its own loop."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")

from jarvis.config.settings import Settings  # noqa: E402
from jarvis.desktop_app.engine_thread import EngineThread  # noqa: E402


# Talk to localhost directly, never through an env proxy.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _get(url: str, key: str | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url)
    if key:
        req.add_header("X-API-Key", key)
    try:
        with _OPENER.open(req, timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, ""
    except urllib.error.URLError:
        return 0, ""            # not up yet — caller retries


def test_start_api_serves_live_engine():
    settings = Settings(log_file="", memory_enabled=False,
                        integrations_enabled=False, goals_enabled=False,
                        rate_limit_enabled=False, memory_db_path=":memory:")
    thread = EngineThread(settings)
    thread.start()
    try:
        conn = thread.start_api()
        assert conn is not None
        base, key = conn
        # Wait for uvicorn to come up.
        deadline = time.time() + 10
        status = 0
        while time.time() < deadline:
            status, _ = _get(base + "/health")
            if status:
                break
            time.sleep(0.2)
        assert status == 200                       # /health is open
        # A protected endpoint needs the generated key.
        assert _get(base + "/dashboard/state")[0] == 401
        assert _get(base + "/dashboard/state", key=key)[0] == 200
    finally:
        server = getattr(thread, "_api_server", None)
        if server is not None:
            server.should_exit = True
        thread.stop()

"""Tests for the account/login flow on the API (auth enabled)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from jarvis.api.app import create_app  # noqa: E402
from jarvis.config.settings import Settings  # noqa: E402
from jarvis.core.container import ServiceContainer  # noqa: E402
from jarvis.core.engine import JarvisEngine  # noqa: E402
from jarvis.llm.client import LLMClient  # noqa: E402
from tests.conftest import FakeProvider  # noqa: E402

ADMIN = {"X-Admin-Key": "admin-secret"}


def _app():
    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
        api_key="", auth_enabled=True, auth_db_path=":memory:",
        auth_admin_key="admin-secret",
    )
    engine = JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider())))
    return create_app(engine=engine, settings=settings)


def _seed(client) -> str:
    """Create an account + license via the admin API, return the password."""
    r = client.post("/admin/accounts",
                    json={"username": "tony", "password": "arcreactor"},
                    headers=ADMIN)
    assert r.status_code == 200, r.text
    r = client.post("/admin/licenses", json={"username": "tony"}, headers=ADMIN)
    assert r.status_code == 200, r.text
    assert r.json()["license_key"].startswith("JVS-")
    return "arcreactor"


def test_admin_requires_key():
    with TestClient(_app()) as client:
        r = client.post("/admin/accounts",
                        json={"username": "x", "password": "y"})
        assert r.status_code == 403


def test_login_and_authenticated_chat():
    with TestClient(_app()) as client:
        _seed(client)
        # Wrong password rejected.
        assert client.post("/auth/login",
                        json={"username": "tony", "password": "nope"}
                        ).status_code == 401
        # Correct login returns a bearer token.
        r = client.post("/auth/login",
                        json={"username": "tony", "password": "arcreactor"})
        assert r.status_code == 200
        token = r.json()["token"]

        # Chat is rejected without a token, accepted with one.
        assert client.post("/chat", json={"message": "hi"}).status_code == 401
        auth = {"Authorization": f"Bearer {token}"}
        ok = client.post("/chat", json={"message": "hi"}, headers=auth)
        assert ok.status_code == 200
        assert ok.json()["reply"] == "Certainly, Sir."

        # /auth/me reflects the account.
        me = client.get("/auth/me", headers=auth).json()
        assert me["username"] == "tony" and me["telegram_verified"] is False


def test_login_requires_license():
    with TestClient(_app()) as client:
        client.post("/admin/accounts",
                    json={"username": "bruce", "password": "hulk"}, headers=ADMIN)
        # No license issued → login fails.
        assert client.post("/auth/login",
                        json={"username": "bruce", "password": "hulk"}
                        ).status_code == 401


def test_logout_revokes_token():
    with TestClient(_app()) as client:
        _seed(client)
        token = client.post("/auth/login",
                            json={"username": "tony", "password": "arcreactor"}
                            ).json()["token"]
        auth = {"Authorization": f"Bearer {token}"}
        assert client.post("/auth/logout", headers=auth).status_code == 200
        assert client.get("/auth/me", headers=auth).status_code == 401


def test_pairing_code_issued():
    with TestClient(_app()) as client:
        _seed(client)
        token = client.post("/auth/login",
                            json={"username": "tony", "password": "arcreactor"}
                            ).json()["token"]
        auth = {"Authorization": f"Bearer {token}"}
        r = client.post("/auth/pairing-code", headers=auth)
        assert r.status_code == 200
        assert len(r.json()["code"]) == 8


def test_websocket_requires_token():
    from starlette.websockets import WebSocketDisconnect

    with TestClient(_app()) as client:
        _seed(client)
        token = client.post("/auth/login",
                            json={"username": "tony", "password": "arcreactor"}
                            ).json()["token"]
        # No token → rejected.
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/s1") as ws:
                ws.receive_text()
        # With token → streams.
        import json
        with client.websocket_connect(f"/ws/s1?key={token}") as ws:
            ws.send_text("hello")
            chunks = []
            while True:
                frame = ws.receive_text()
                try:
                    payload = json.loads(frame)
                except json.JSONDecodeError:
                    chunks.append(frame)
                    continue
                if isinstance(payload, dict) and payload.get("event") == "done":
                    break
                chunks.append(frame)
            assert "".join(chunks) == "Certainly, Sir."

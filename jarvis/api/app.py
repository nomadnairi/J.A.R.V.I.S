"""
FastAPI application factory.

Endpoints:
    GET  /                — service info (open).
    GET  /health          — diagnostics (open).
    POST /chat            — send a message, get a reply (auth).
    WS   /ws/{session}    — stream a reply chunk by chunk (auth via ?key=).
    POST /auth/login …    — per-user accounts (only when AUTH_ENABLED).
    POST /admin/…         — operator endpoints (only when AUTH_ENABLED).

Authentication resolves a *principal* for each request:

* A per-user login token (``AUTH_ENABLED``) — the strongest, and it namespaces
  the caller's sessions/memory to their account.
* The shared ``API_KEY`` — a single bearer/``X-API-Key`` secret.

If neither accounts nor a shared key are configured the API is **open** — for
local development only.
"""

from contextlib import asynccontextmanager

from pydantic import BaseModel

from jarvis import __version__
from jarvis.api.auth import install_auth_routes, resolve_principal
from jarvis.config.settings import Settings, get_settings
from jarvis.core.engine import JarvisEngine
from jarvis.licensing import LicenseService
from jarvis.models.response import Request
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class ChatIn(BaseModel):
    message: str
    session_id: str = "default"


class ChatOut(BaseModel):
    reply: str
    session_id: str


def create_app(engine: JarvisEngine | None = None,
            settings: Settings | None = None):
    """Build the FastAPI application over an engine."""
    try:
        from fastapi import (
            Depends,
            FastAPI,
            Header,
            HTTPException,
            WebSocket,
            WebSocketDisconnect,
        )
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "The API needs 'fastapi' and 'uvicorn'. Install with: "
            "pip install fastapi 'uvicorn[standard]'"
        ) from exc

    settings = settings or get_settings()
    engine = engine or JarvisEngine(settings)

    service: LicenseService | None = None
    if settings.auth_enabled:
        service = LicenseService(
            settings.auth_db_path, token_ttl_hours=settings.auth_token_ttl_hours
        )

    @asynccontextmanager
    async def lifespan(_app):
        await engine.start()
        try:
            yield
        finally:
            await engine.shutdown()
            if service is not None:
                service.close()

    app = FastAPI(title="J.A.R.V.I.S. API", version=__version__, lifespan=lifespan)

    def _principal(provided: str | None) -> str | None:
        return resolve_principal(provided, settings, service)

    def _scoped(principal: str, session_id: str) -> str:
        """Namespace a session by its owner so users never share memory."""
        return f"{principal}::{session_id}"

    async def require_principal(
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> str:
        provided = None
        if authorization and authorization.startswith("Bearer "):
            provided = authorization[len("Bearer "):]
        provided = provided or x_api_key
        principal = _principal(provided)
        if principal is None:
            raise HTTPException(status_code=401, detail="Invalid or missing credentials.")
        return principal

    # -- routes -------------------------------------------------------------

    @app.get("/")
    async def root() -> dict:
        return {
            "name": "J.A.R.V.I.S.",
            "version": __version__,
            "status": "online",
            "auth": "accounts" if service is not None else "shared-key",
        }

    @app.get("/health")
    async def health() -> dict:
        from jarvis.core.diagnostics import all_ok, diagnose
        checks = diagnose(engine)
        return {
            "ok": all_ok(checks),
            "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail}
                    for c in checks],
        }

    @app.post("/chat", response_model=ChatOut)
    async def chat(body: ChatIn,
                principal: str = Depends(require_principal)) -> ChatOut:
        reply = await engine.ask(
            body.message, session_id=_scoped(principal, body.session_id)
        )
        return ChatOut(reply=reply, session_id=body.session_id)

    @app.post("/chat/stream")
    async def chat_stream(body: ChatIn,
                        principal: str = Depends(require_principal)):
        """Stream the reply as plain-text chunks (chunked transfer encoding).

        Easy to consume from any HTTP client — no WebSocket needed: read the
        body incrementally until EOF.
        """
        from fastapi.responses import StreamingResponse

        scoped = _scoped(principal, body.session_id)

        async def _generate():
            async for chunk in engine.stream(
                Request(text=body.message, session_id=scoped)
            ):
                yield chunk

        return StreamingResponse(_generate(), media_type="text/plain; charset=utf-8")

    @app.websocket("/ws/{session_id}")
    async def ws(websocket: WebSocket, session_id: str) -> None:
        principal = _principal(websocket.query_params.get("key"))
        if principal is None:
            await websocket.close(code=1008)  # policy violation
            return
        await websocket.accept()
        scoped = _scoped(principal, session_id)
        try:
            while True:
                text = await websocket.receive_text()
                async for chunk in engine.stream(
                    Request(text=text, session_id=scoped)
                ):
                    await websocket.send_text(chunk)
                await websocket.send_json({"event": "done"})
        except WebSocketDisconnect:
            return

    if service is not None:
        install_auth_routes(app, settings, service)
        if settings.billing_enabled and settings.billing_webhook_secret:
            from jarvis.api.billing_routes import install_billing_routes
            install_billing_routes(app, settings, service)

    app.state.engine = engine
    app.state.license_service = service
    return app

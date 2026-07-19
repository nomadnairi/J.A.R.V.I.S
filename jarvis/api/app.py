"""
FastAPI application factory.

Endpoints:
    GET  /health         — diagnostics (open).
    POST /chat           — send a message, get a reply (auth).
    WS   /ws/{session}   — stream a reply chunk by chunk (auth via ?key=).

Authentication: if ``api_key`` is configured, every protected route requires it
via ``Authorization: Bearer <key>`` or an ``X-API-Key`` header (or ``?key=`` for
the WebSocket). An empty key means the API is open — for local development only.
"""

from contextlib import asynccontextmanager

from pydantic import BaseModel

from jarvis import __version__
from jarvis.config.settings import Settings, get_settings
from jarvis.core.engine import JarvisEngine
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

    @asynccontextmanager
    async def lifespan(_app):
        await engine.start()
        try:
            yield
        finally:
            await engine.shutdown()

    app = FastAPI(title="J.A.R.V.I.S. API", version=__version__, lifespan=lifespan)

    class ChatIn(BaseModel):
        message: str
        session_id: str = "default"

    class ChatOut(BaseModel):
        reply: str
        session_id: str

    def _check_key(provided: str | None) -> bool:
        return not settings.api_key or provided == settings.api_key

    async def require_key(
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> None:
        provided = None
        if authorization and authorization.startswith("Bearer "):
            provided = authorization[len("Bearer "):]
        provided = provided or x_api_key
        if not _check_key(provided):
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    # -- routes -------------------------------------------------------------

    @app.get("/")
    async def root() -> dict:
        return {"name": "J.A.R.V.I.S.", "version": __version__, "status": "online"}

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
    async def chat(body: ChatIn, _: None = Depends(require_key)) -> ChatOut:
        reply = await engine.ask(body.message, session_id=body.session_id)
        return ChatOut(reply=reply, session_id=body.session_id)

    @app.websocket("/ws/{session_id}")
    async def ws(websocket: WebSocket, session_id: str) -> None:
        if not _check_key(websocket.query_params.get("key")):
            await websocket.close(code=1008)  # policy violation
            return
        await websocket.accept()
        try:
            while True:
                text = await websocket.receive_text()
                async for chunk in engine.stream(
                    Request(text=text, session_id=session_id)
                ):
                    await websocket.send_text(chunk)
                await websocket.send_json({"event": "done"})
        except WebSocketDisconnect:
            return

    app.state.engine = engine
    return app

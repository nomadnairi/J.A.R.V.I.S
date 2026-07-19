"""
Async request-processing pipeline.

A request passes through an ordered list of :class:`Middleware` before and
after the core handler runs. This gives clean extension points for
normalisation, logging, rate-limiting, and (later) authentication — without
touching the engine's core logic.

Middleware form an onion: ``process`` receives the request and a ``next``
awaitable it must invoke to continue the chain, then may inspect/modify the
resulting :class:`Response`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from jarvis.models.response import Request, Response
from jarvis.utils.logger import get_logger
from jarvis.utils.redaction import redact_secrets
from jarvis.utils.text import normalize

logger = get_logger(__name__)

Next = Callable[[Request], Awaitable[Response]]


class Middleware(ABC):
    """Base class for pipeline middleware."""

    @abstractmethod
    async def process(self, request: Request, next_: Next) -> Response:
        """Handle ``request``, awaiting ``next_`` to continue the chain."""
        raise NotImplementedError


class NormalizeMiddleware(Middleware):
    """Collapse whitespace on inbound request text."""

    async def process(self, request: Request, next_: Next) -> Response:
        request.text = normalize(request.text)
        return await next_(request)


class RateLimitMiddleware(Middleware):
    """Reject requests from a session that exceeds its rate limit."""

    def __init__(self, limiter, message: str = "You're sending requests too "
                "quickly — please slow down a moment.") -> None:
        self._limiter = limiter
        self._message = message

    async def process(self, request: Request, next_: Next) -> Response:
        if not self._limiter.allow(request.session_id):
            from jarvis.config.constants import ResponseType
            return Response(text=self._message, request_id=request.request_id,
                            type=ResponseType.SYSTEM, source="ratelimit")
        return await next_(request)


class LoggingMiddleware(Middleware):
    """Log each request/response pair at debug level."""

    async def process(self, request: Request, next_: Next) -> Response:
        # Redact secrets so a pasted token/key never lands in the logs.
        logger.debug("→ [%s] %s", request.request_id, redact_secrets(request.text))
        response = await next_(request)
        logger.debug(
            "← [%s] %s (%s, %.0fms)",
            request.request_id,
            response.type.value,
            response.source,
            response.latency_ms,
        )
        return response


class Pipeline:
    """Composes middleware around a core async handler."""

    def __init__(self, middleware: list[Middleware] | None = None) -> None:
        self._middleware = middleware or []

    def use(self, middleware: Middleware) -> "Pipeline":
        self._middleware.append(middleware)
        return self

    async def run(self, request: Request, handler: Next) -> Response:
        """Execute the middleware chain around ``handler``."""
        chain: Next = handler
        for mw in reversed(self._middleware):
            chain = self._wrap(mw, chain)
        return await chain(request)

    @staticmethod
    def _wrap(mw: Middleware, next_: Next) -> Next:
        async def _call(request: Request) -> Response:
            return await mw.process(request, next_)

        return _call

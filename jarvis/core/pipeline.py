"""
Request-processing pipeline.

A request passes through an ordered list of :class:`Middleware` before and
after the core handler runs. This gives clean extension points for
normalisation, logging, rate-limiting, and (later) authentication — without
touching the engine's core logic.

Middleware form an onion: ``process`` receives the request and a ``next``
callable it must invoke to continue the chain, then may inspect/modify the
resulting :class:`Response`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from jarvis.models.response import Request, Response
from jarvis.utils.logger import get_logger
from jarvis.utils.text import normalize

logger = get_logger(__name__)

Next = Callable[[Request], Response]


class Middleware(ABC):
    """Base class for pipeline middleware."""

    @abstractmethod
    def process(self, request: Request, next_: Next) -> Response:
        """Handle ``request``, calling ``next_`` to continue the chain."""
        raise NotImplementedError


class NormalizeMiddleware(Middleware):
    """Collapse whitespace on inbound request text."""

    def process(self, request: Request, next_: Next) -> Response:
        request.text = normalize(request.text)
        return next_(request)


class LoggingMiddleware(Middleware):
    """Log each request/response pair at debug level."""

    def process(self, request: Request, next_: Next) -> Response:
        logger.debug("→ [%s] %s", request.request_id, request.text)
        response = next_(request)
        logger.debug(
            "← [%s] %s (%s, %.0fms)",
            request.request_id,
            response.type.value,
            response.source,
            response.latency_ms,
        )
        return response


class Pipeline:
    """Composes middleware around a core handler."""

    def __init__(self, middleware: list[Middleware] | None = None) -> None:
        self._middleware = middleware or []

    def use(self, middleware: Middleware) -> "Pipeline":
        self._middleware.append(middleware)
        return self

    def run(self, request: Request, handler: Next) -> Response:
        """Execute the middleware chain around ``handler``."""
        chain: Next = handler
        for mw in reversed(self._middleware):
            chain = self._wrap(mw, chain)
        return chain(request)

    @staticmethod
    def _wrap(mw: Middleware, next_: Next) -> Next:
        def _call(request: Request) -> Response:
            return mw.process(request, next_)

        return _call

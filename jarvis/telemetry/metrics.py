"""
In-process metrics collection.

Tracks counters, latency samples, and provider/skill usage. The collector can
subscribe itself to the event bus so metrics are gathered passively, without
the core engine having to call it directly.

For a production deployment this would export to Prometheus/StatsD; here it
keeps an in-memory summary that powers the CLI ``/stats`` command.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import mean, median

from jarvis.config.constants import EventType
from jarvis.events.bus import EventBus
from jarvis.events.events import Event


@dataclass
class MetricsCollector:
    """Aggregates counters and latency samples."""

    counters: Counter = field(default_factory=Counter)
    latencies_ms: list[float] = field(default_factory=list)
    provider_usage: Counter = field(default_factory=Counter)
    skill_usage: Counter = field(default_factory=Counter)
    total_tokens: int = 0

    # -- recording ----------------------------------------------------------

    def incr(self, name: str, amount: int = 1) -> None:
        self.counters[name] += amount

    def record_latency(self, ms: float) -> None:
        self.latencies_ms.append(ms)

    def record_response(self, *, source: str, latency_ms: float, tokens: int = 0,
                        via_skill: bool = False) -> None:
        self.incr("responses_total")
        self.record_latency(latency_ms)
        self.total_tokens += tokens
        if via_skill:
            self.skill_usage[source] += 1
        else:
            self.provider_usage[source] += 1

    # -- event-bus integration ---------------------------------------------

    def attach(self, bus: EventBus) -> None:
        """Subscribe the collector to relevant events on ``bus``."""
        bus.subscribe(EventType.USER_INPUT, lambda e: self.incr("requests_total"))
        bus.subscribe(EventType.ERROR, lambda e: self.incr("errors_total"))
        bus.subscribe(EventType.RESPONSE_READY, self._on_response)

    def _on_response(self, event: Event) -> None:
        # The producing source (skill name / provider) is carried on
        # ``event.source``; response metadata rides in the payload.
        self.record_response(
            source=event.source or "unknown",
            latency_ms=float(event.get("latency_ms", 0.0)),
            tokens=int(event.get("tokens", 0)),
            via_skill=bool(event.get("via_skill", False)),
        )

    # -- reporting ----------------------------------------------------------

    def summary(self) -> dict[str, object]:
        """Return a snapshot dict suitable for display or export."""
        lat = self.latencies_ms
        return {
            "requests_total": self.counters.get("requests_total", 0),
            "responses_total": self.counters.get("responses_total", 0),
            "errors_total": self.counters.get("errors_total", 0),
            "total_tokens": self.total_tokens,
            "latency_ms": {
                "count": len(lat),
                "avg": round(mean(lat), 1) if lat else 0.0,
                "median": round(median(lat), 1) if lat else 0.0,
                "min": round(min(lat), 1) if lat else 0.0,
                "max": round(max(lat), 1) if lat else 0.0,
            },
            "provider_usage": dict(self.provider_usage),
            "skill_usage": dict(self.skill_usage),
        }

    def reset(self) -> None:
        self.counters.clear()
        self.latencies_ms.clear()
        self.provider_usage.clear()
        self.skill_usage.clear()
        self.total_tokens = 0

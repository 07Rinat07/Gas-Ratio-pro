"""Bounded runtime diagnostics for expensive engineering operations.

The collector is framework-neutral and intentionally stores only compact event
metadata.  It is suitable for Streamlit session state and plain-dict tests.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from time import perf_counter, time
from typing import Any, Deque, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class RuntimeDiagnosticEvent:
    stage: str
    duration_ms: float
    status: str
    cache_status: str = "none"
    renderer: str = ""
    item_count: int = 0
    memory_bytes: int = 0
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)




class RuntimeStageTimer:
    """Context manager that records one bounded diagnostic stage.

    The timer owns no framework objects and keeps only primitive metadata. It
    can therefore be used around repository, renderer and cache boundaries
    without leaking runtime resources into serializable application state.
    """

    def __init__(
        self,
        diagnostics: "RuntimeDiagnostics",
        *,
        stage: str,
        cache_status: str = "none",
        renderer: str = "",
        item_count: int = 0,
        memory_bytes: int = 0,
    ) -> None:
        self._diagnostics = diagnostics
        self._stage = str(stage)
        self._cache_status = str(cache_status)
        self._renderer = str(renderer)
        self._item_count = max(0, int(item_count))
        self._memory_bytes = max(0, int(memory_bytes))
        self._started = 0.0
        self.event: RuntimeDiagnosticEvent | None = None

    def __enter__(self) -> "RuntimeStageTimer":
        self._started = perf_counter()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        status = "success" if exc is None else "failed"
        self.event = self._diagnostics.record(
            stage=self._stage,
            duration_ms=(perf_counter() - self._started) * 1000.0,
            status=status,
            cache_status=self._cache_status,
            renderer=self._renderer,
            item_count=self._item_count,
            memory_bytes=self._memory_bytes,
        )
        return False


class RuntimeDiagnostics:
    """Small ring buffer of performance and renderer events."""

    def __init__(self, *, max_events: int = 64) -> None:
        if int(max_events) < 1:
            raise ValueError("max_events must be positive")
        self.max_events = int(max_events)
        self._events: Deque[RuntimeDiagnosticEvent] = deque(maxlen=self.max_events)

    def record(
        self,
        *,
        stage: str,
        duration_ms: float,
        status: str = "success",
        cache_status: str = "none",
        renderer: str = "",
        item_count: int = 0,
        memory_bytes: int = 0,
    ) -> RuntimeDiagnosticEvent:
        event = RuntimeDiagnosticEvent(
            stage=str(stage),
            duration_ms=max(0.0, float(duration_ms)),
            status=str(status),
            cache_status=str(cache_status),
            renderer=str(renderer),
            item_count=max(0, int(item_count)),
            memory_bytes=max(0, int(memory_bytes)),
            timestamp=time(),
        )
        self._events.append(event)
        return event

    def latest(self, stage: str | None = None) -> RuntimeDiagnosticEvent | None:
        if stage is None:
            return self._events[-1] if self._events else None
        wanted = str(stage)
        for event in reversed(self._events):
            if event.stage == wanted:
                return event
        return None

    def snapshot(self) -> tuple[RuntimeDiagnosticEvent, ...]:
        return tuple(self._events)

    def mark(self) -> float:
        """Return a wall-clock marker for isolating one render cycle."""

        return time()

    def snapshot_since(self, marker: float) -> tuple[RuntimeDiagnosticEvent, ...]:
        """Return only events recorded at or after ``marker``.

        This prevents stale slow events from previous Streamlit reruns from
        contaminating the current workspace performance assessment.
        """

        threshold = float(marker)
        return tuple(event for event in self._events if event.timestamp >= threshold)

    def timer(
        self,
        stage: str,
        *,
        cache_status: str = "none",
        renderer: str = "",
        item_count: int = 0,
        memory_bytes: int = 0,
    ) -> RuntimeStageTimer:
        """Create a stage timer bound to this collector."""

        return RuntimeStageTimer(
            self,
            stage=stage,
            cache_status=cache_status,
            renderer=renderer,
            item_count=item_count,
            memory_bytes=memory_bytes,
        )

    def cache_summary(self, *, stage_prefix: str = "") -> dict[str, int | float]:
        """Return compact hit/miss statistics for diagnostics UI and logs."""

        events = tuple(
            event for event in self._events
            if not stage_prefix or event.stage.startswith(str(stage_prefix))
        )
        hits = sum(1 for event in events if event.cache_status == "hit")
        misses = sum(1 for event in events if event.cache_status == "miss")
        measured = hits + misses
        return {
            "hits": hits,
            "misses": misses,
            "measured": measured,
            "hit_rate": round((hits / measured) * 100.0, 2) if measured else 0.0,
        }

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)

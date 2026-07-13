"""Bounded runtime diagnostics for expensive engineering operations.

The collector is framework-neutral and intentionally stores only compact event
metadata.  It is suitable for Streamlit session state and plain-dict tests.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from time import time
from typing import Any, Deque, Iterable


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

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)

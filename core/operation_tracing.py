"""Structured operation tracing for performance and runtime diagnostics.

The tracer stores compact primitive metadata only. It may be registered as a
runtime service, while live context is held in ``contextvars`` and therefore is
never copied into serializable application state.
"""
from __future__ import annotations

from collections import Counter, deque
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import asdict, dataclass
from time import perf_counter, time
from typing import Any, Deque, Iterable, Iterator, Mapping
import uuid

from core.logging_config import configure_logging, safe_log_value
from core.runtime_diagnostics import RuntimeDiagnosticEvent

_TRACE_CONTEXT: ContextVar[dict[str, str]] = ContextVar("gas_ratio_trace_context", default={})


def current_trace_context() -> dict[str, str]:
    return dict(_TRACE_CONTEXT.get())


def set_trace_context(**values: object) -> Token[dict[str, str]]:
    current = current_trace_context()
    for key, value in values.items():
        text = safe_log_value(value, 120)
        if text:
            current[str(key)] = text
        else:
            current.pop(str(key), None)
    return _TRACE_CONTEXT.set(current)


def reset_trace_context(token: Token[dict[str, str]]) -> None:
    _TRACE_CONTEXT.reset(token)


@contextmanager
def trace_context(**values: object) -> Iterator[dict[str, str]]:
    token = set_trace_context(**values)
    try:
        yield current_trace_context()
    finally:
        reset_trace_context(token)


@dataclass(frozen=True, slots=True)
class OperationTraceEvent:
    execution_id: str
    category: str
    operation: str
    duration_ms: float
    status: str
    timestamp: float
    project_id: str = ""
    session_id: str = ""
    route_id: str = ""
    stage: str = ""
    cache_status: str = "none"
    item_count: int = 0
    payload_bytes: int = 0
    slow: bool = False
    details: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["details"] = dict(self.details)
        return payload


class OperationTraceRegistry:
    """Bounded trace buffer and aggregate metrics for diagnostics UI."""

    def __init__(self, *, max_events: int = 256, slow_threshold_ms: float = 1000.0) -> None:
        if int(max_events) < 1:
            raise ValueError("max_events must be positive")
        if float(slow_threshold_ms) < 0:
            raise ValueError("slow_threshold_ms must not be negative")
        self.max_events = int(max_events)
        self.slow_threshold_ms = float(slow_threshold_ms)
        self._events: Deque[OperationTraceEvent] = deque(maxlen=self.max_events)

    def record(
        self,
        *,
        operation: str,
        duration_ms: float,
        status: str = "success",
        category: str = "runtime",
        execution_id: str | None = None,
        stage: str = "",
        cache_status: str = "none",
        item_count: int = 0,
        payload_bytes: int = 0,
        details: Mapping[str, object] | None = None,
        slow_threshold_ms: float | None = None,
    ) -> OperationTraceEvent:
        context = current_trace_context()
        threshold = self.slow_threshold_ms if slow_threshold_ms is None else max(0.0, float(slow_threshold_ms))
        duration = max(0.0, float(duration_ms))
        event = OperationTraceEvent(
            execution_id=str(execution_id or context.get("execution_id") or f"op-{uuid.uuid4().hex[:12]}"),
            category=str(category or "runtime"),
            operation=str(operation or stage or "operation"),
            duration_ms=round(duration, 3),
            status=str(status or "success"),
            timestamp=time(),
            project_id=str(context.get("project_id") or ""),
            session_id=str(context.get("session_id") or ""),
            route_id=str(context.get("route_id") or ""),
            stage=str(stage or ""),
            cache_status=str(cache_status or "none"),
            item_count=max(0, int(item_count)),
            payload_bytes=max(0, int(payload_bytes)),
            slow=duration >= threshold,
            details=tuple(sorted((str(key), safe_log_value(value, 240)) for key, value in dict(details or {}).items())),
        )
        self._events.append(event)
        return event

    def ingest_runtime_events(
        self,
        events: Iterable[RuntimeDiagnosticEvent],
        *,
        category: str = "performance",
        execution_id: str | None = None,
    ) -> tuple[OperationTraceEvent, ...]:
        resolved_execution_id = execution_id or f"trace-{uuid.uuid4().hex[:12]}"
        return tuple(
            self.record(
                operation=event.stage,
                stage=event.stage,
                duration_ms=event.duration_ms,
                status=event.status,
                category=category,
                execution_id=resolved_execution_id,
                cache_status=event.cache_status,
                item_count=event.item_count,
                payload_bytes=event.memory_bytes,
                details={"renderer": event.renderer},
            )
            for event in events
        )

    def snapshot(self, *, limit: int | None = None) -> tuple[OperationTraceEvent, ...]:
        events = tuple(self._events)
        if limit is None:
            return events
        return events[-max(0, int(limit)):]

    def summary(self) -> dict[str, Any]:
        events = tuple(self._events)
        categories = Counter(event.category for event in events)
        statuses = Counter(event.status for event in events)
        slow_count = sum(1 for event in events if event.slow)
        total_duration = sum(event.duration_ms for event in events)
        return {
            "events": len(events),
            "slow_events": slow_count,
            "failed_events": sum(1 for event in events if event.status != "success"),
            "average_duration_ms": round(total_duration / len(events), 2) if events else 0.0,
            "maximum_duration_ms": round(max((event.duration_ms for event in events), default=0.0), 2),
            "categories": dict(sorted(categories.items())),
            "statuses": dict(sorted(statuses.items())),
        }

    def clear(self) -> None:
        self._events.clear()

    def close(self) -> None:
        self.clear()


@contextmanager
def trace_operation(
    operation: str,
    *,
    registry: OperationTraceRegistry | None = None,
    category: str = "runtime",
    slow_threshold_ms: float | None = None,
    details: Mapping[str, object] | None = None,
) -> Iterator[str]:
    """Time one operation, record it, and emit one structured log event."""

    execution_id = current_trace_context().get("execution_id") or f"op-{uuid.uuid4().hex[:12]}"
    started = perf_counter()
    status = "success"
    try:
        yield execution_id
    except Exception:
        status = "failed"
        raise
    finally:
        duration_ms = (perf_counter() - started) * 1000.0
        event = (registry or OperationTraceRegistry(max_events=1)).record(
            operation=operation,
            duration_ms=duration_ms,
            status=status,
            category=category,
            execution_id=execution_id,
            details=details,
            slow_threshold_ms=slow_threshold_ms,
        )
        logger = configure_logging()
        log_method = logger.warning if event.slow or status != "success" else logger.info
        log_method(
            "operation_trace category=%s operation=%s execution_id=%s status=%s duration_ms=%.2f slow=%s project_id=%s route_id=%s details=%s",
            safe_log_value(event.category),
            safe_log_value(event.operation),
            safe_log_value(event.execution_id),
            safe_log_value(event.status),
            event.duration_ms,
            event.slow,
            safe_log_value(event.project_id),
            safe_log_value(event.route_id),
            dict(event.details),
        )

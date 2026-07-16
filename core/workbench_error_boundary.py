"""UI-neutral error boundary contracts for Workbench operations.

The boundary records full diagnostics through the existing runtime diagnostics
service and exposes only a compact, serializable incident descriptor to UI
adapters.  Renderer code should not duplicate traceback handling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, MutableMapping, TypeVar

from core.workbench_runtime_diagnostics import record_runtime_exception

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class WorkbenchIncident:
    correlation_id: str
    boundary: str
    operation: str
    exception_type: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def capture_workbench_exception(
    state: MutableMapping[str, Any],
    exc: BaseException,
    *,
    boundary: str,
    operation: str,
    context: dict[str, Any] | None = None,
) -> WorkbenchIncident:
    """Record an exception and return a stable UI-safe incident contract."""

    incident = record_runtime_exception(
        state,
        exc,
        boundary=boundary,
        operation=operation,
        context=context,
    )
    return WorkbenchIncident(
        correlation_id=str(incident["correlation_id"]),
        boundary=str(incident["boundary"]),
        operation=str(incident["operation"]),
        exception_type=str(incident["exception_type"]),
        message=str(incident["message"]),
    )


def run_with_workbench_boundary(
    state: MutableMapping[str, Any],
    operation_fn: Callable[[], T],
    *,
    boundary: str,
    operation: str,
    context: dict[str, Any] | None = None,
) -> tuple[T | None, WorkbenchIncident | None]:
    """Execute an operation and convert failures to a serializable incident."""

    try:
        return operation_fn(), None
    except Exception as exc:  # noqa: BLE001 - this is the outer renderer boundary
        return None, capture_workbench_exception(
            state,
            exc,
            boundary=boundary,
            operation=operation,
            context=context,
        )

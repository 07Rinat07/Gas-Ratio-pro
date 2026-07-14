"""Session-scoped registry for non-serializable runtime services.

Application state should contain data that can be copied for transactional
rollback.  Live services such as executors, queues, locks and in-memory caches
are process resources instead.  This module keeps those objects behind one
explicit namespace so state snapshot code can exclude the namespace without
silently weakening rollback for ordinary data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, MutableMapping, TypeVar

RUNTIME_SERVICES_STATE_KEY = "runtime::services"

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RuntimeServiceDescriptor:
    """Serializable diagnostic description of one registered service."""

    key: str
    type_name: str


@dataclass(frozen=True, slots=True)
class RuntimeServiceShutdownResult:
    """Serializable outcome of closing one registered runtime service."""

    key: str
    type_name: str
    closed: bool
    method: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "type_name": self.type_name,
            "closed": self.closed,
            "method": self.method,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class RuntimeServiceShutdownSummary:
    """Serializable aggregate used by lifecycle events and diagnostics."""

    total: int
    closed: int
    failed: int
    noop: int
    failures: tuple[RuntimeServiceShutdownResult, ...] = ()

    @property
    def successful(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "closed": self.closed,
            "failed": self.failed,
            "noop": self.noop,
            "successful": self.successful,
            "failures": [item.to_dict() for item in self.failures],
        }


def summarize_runtime_service_shutdown(
    results: tuple[RuntimeServiceShutdownResult, ...],
) -> RuntimeServiceShutdownSummary:
    """Build a stable aggregate without retaining live service references."""

    failures = tuple(item for item in results if not item.closed)
    return RuntimeServiceShutdownSummary(
        total=len(results),
        closed=sum(1 for item in results if item.closed),
        failed=len(failures),
        noop=sum(1 for item in results if item.method == "none"),
        failures=failures,
    )


class RuntimeServiceRegistry:
    """Own non-copyable services for one application session."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}

    def get(self, key: str, default: T | None = None) -> Any | T | None:
        return self._services.get(str(key), default)

    def set(self, key: str, service: T) -> T:
        clean_key = str(key).strip()
        if not clean_key:
            raise ValueError("Runtime service key must not be empty.")
        self._services[clean_key] = service
        return service

    def ensure(self, key: str, factory: Callable[[], T], *, expected_type: type[T] | None = None) -> T:
        clean_key = str(key).strip()
        if not clean_key:
            raise ValueError("Runtime service key must not be empty.")
        current = self._services.get(clean_key)
        if current is not None and (expected_type is None or isinstance(current, expected_type)):
            return current
        service = factory()
        if expected_type is not None and not isinstance(service, expected_type):
            raise TypeError(
                f"Runtime service factory for {clean_key!r} returned "
                f"{type(service).__name__}, expected {expected_type.__name__}."
            )
        self._services[clean_key] = service
        return service

    def remove(self, key: str, default: T | None = None) -> Any | T | None:
        return self._services.pop(str(key), default)

    @staticmethod
    def _close_service(key: str, service: Any) -> RuntimeServiceShutdownResult:
        """Close one service without allowing cleanup failures to abort shutdown."""

        type_name = type(service).__name__
        closer = getattr(service, "close", None)
        method = "close"
        if not callable(closer):
            closer = getattr(service, "shutdown", None)
            method = "shutdown"
        if not callable(closer):
            return RuntimeServiceShutdownResult(key, type_name, True, method="none")
        try:
            if method == "shutdown":
                try:
                    closer(wait=False)
                except TypeError:
                    closer()
            else:
                closer()
        except Exception as exc:  # cleanup must remain best-effort
            return RuntimeServiceShutdownResult(
                key, type_name, False, method=method, error=f"{type(exc).__name__}: {exc}"
            )
        return RuntimeServiceShutdownResult(key, type_name, True, method=method)

    def shutdown(self, *, remove: bool = True) -> tuple[RuntimeServiceShutdownResult, ...]:
        """Best-effort shutdown for every registered process-local service."""

        results = tuple(
            self._close_service(key, service)
            for key, service in tuple(self._services.items())
        )
        if remove:
            self._services.clear()
        return results

    def clear(self, *, close: bool = False) -> tuple[str, ...]:
        keys = tuple(self._services)
        if close:
            self.shutdown(remove=True)
        else:
            self._services.clear()
        return keys

    def descriptors(self) -> tuple[RuntimeServiceDescriptor, ...]:
        return tuple(
            RuntimeServiceDescriptor(key=key, type_name=type(service).__name__)
            for key, service in sorted(self._services.items())
        )


def runtime_service_registry(state: MutableMapping[str, Any]) -> RuntimeServiceRegistry:
    """Return the registry attached to ``state``, replacing invalid legacy data."""

    current = state.get(RUNTIME_SERVICES_STATE_KEY)
    if isinstance(current, RuntimeServiceRegistry):
        return current
    registry = RuntimeServiceRegistry()
    state[RUNTIME_SERVICES_STATE_KEY] = registry
    return registry

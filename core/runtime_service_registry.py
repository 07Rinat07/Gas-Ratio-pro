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

    def clear(self, *, close: bool = False) -> tuple[str, ...]:
        keys = tuple(self._services)
        if close:
            for service in tuple(self._services.values()):
                closer = getattr(service, "close", None) or getattr(service, "shutdown", None)
                if callable(closer):
                    try:
                        closer()
                    except Exception:
                        # Cleanup is best-effort; application shutdown must continue.
                        pass
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

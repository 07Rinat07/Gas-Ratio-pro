"""Serializable audit of Streamlit-compatible session state.

The audit never serializes or deep-copies values. It reports key ownership,
runtime objects, suspicious unscoped keys and stale transient entries so the
application can clean state without touching live services accidentally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.runtime_service_registry import RUNTIME_SERVICES_STATE_KEY
from core.session_state_manager import (
    DEFAULT_PRESERVED_KEYS, DEFAULT_TRANSIENT_KEYS, DEFAULT_TRANSIENT_PREFIXES,
    is_transient_session_key,
)
from core.session_key_registry import build_default_session_key_registry

KNOWN_SCOPES = (
    "runtime::",
    "workbench.",
    "workspace.",
    "correlation_",
    "interpretation_",
    "las_",
    "plot_",
    "diagnostic_",
    "diagnostics_",
    "calculation_",
    "report_",
    "export_",
)

PRIMITIVE_TYPES = (str, int, float, bool, bytes, type(None))


@dataclass(frozen=True, slots=True)
class SessionStateAudit:
    total_keys: int
    primitive_keys: int
    container_keys: int
    runtime_keys: tuple[str, ...]
    transient_keys: tuple[str, ...]
    unscoped_keys: tuple[str, ...]
    type_counts: tuple[tuple[str, int], ...]
    owner_counts: tuple[tuple[str, int], ...] = ()
    lifecycle_counts: tuple[tuple[str, int], ...] = ()
    unregistered_keys: tuple[str, ...] = ()

    @property
    def runtime_count(self) -> int:
        return len(self.runtime_keys)

    @property
    def transient_count(self) -> int:
        return len(self.transient_keys)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_keys": self.total_keys,
            "primitive_keys": self.primitive_keys,
            "container_keys": self.container_keys,
            "runtime_count": self.runtime_count,
            "runtime_keys": list(self.runtime_keys),
            "transient_count": self.transient_count,
            "transient_keys": list(self.transient_keys),
            "unscoped_keys": list(self.unscoped_keys),
            "type_counts": dict(self.type_counts),
            "owner_counts": dict(self.owner_counts),
            "lifecycle_counts": dict(self.lifecycle_counts),
            "unregistered_keys": list(self.unregistered_keys),
        }


def _is_runtime_value(value: Any) -> bool:
    module = type(value).__module__
    name = type(value).__name__
    if module.startswith(("threading", "queue", "concurrent.futures", "_thread")):
        return True
    return name in {
        "RuntimeServiceRegistry",
        "ThreadPoolExecutor",
        "Queue",
        "Lock",
        "RLock",
        "Event",
        "Semaphore",
    }


def audit_session_state(
    state: Mapping[str, Any],
    *,
    known_scopes: Sequence[str] = KNOWN_SCOPES,
) -> SessionStateAudit:
    runtime_keys: list[str] = []
    transient_keys: list[str] = []
    unscoped_keys: list[str] = []
    primitive_keys = 0
    container_keys = 0
    counts: dict[str, int] = {}
    descriptors = []
    key_registry = build_default_session_key_registry(
        transient_prefixes=DEFAULT_TRANSIENT_PREFIXES,
        transient_keys=DEFAULT_TRANSIENT_KEYS,
        preserved_keys=DEFAULT_PRESERVED_KEYS,
    )

    for raw_key, value in state.items():
        key = str(raw_key)
        descriptor = key_registry.describe(key)
        descriptors.append(descriptor)
        type_name = type(value).__name__
        counts[type_name] = counts.get(type_name, 0) + 1
        if isinstance(value, PRIMITIVE_TYPES):
            primitive_keys += 1
        elif isinstance(value, (tuple, list, dict, set, frozenset)):
            container_keys += 1
        if key == RUNTIME_SERVICES_STATE_KEY or _is_runtime_value(value):
            runtime_keys.append(key)
        if is_transient_session_key(key):
            transient_keys.append(key)
        if not key.startswith(tuple(known_scopes)) and "::" not in key:
            unscoped_keys.append(key)

    return SessionStateAudit(
        total_keys=len(state),
        primitive_keys=primitive_keys,
        container_keys=container_keys,
        runtime_keys=tuple(sorted(runtime_keys)),
        transient_keys=tuple(sorted(transient_keys)),
        unscoped_keys=tuple(sorted(unscoped_keys)),
        type_counts=tuple(sorted(counts.items())),
        owner_counts=tuple(key_registry.ownership_counts(item.key for item in descriptors).items()),
        lifecycle_counts=tuple(key_registry.lifecycle_counts(item.key for item in descriptors).items()),
        unregistered_keys=tuple(sorted(item.key for item in descriptors if not item.registered)),
    )

"""Application state controller for Streamlit-safe workspace switching.

The controller is intentionally framework-neutral.  It works with ``st.session_state``
but can also be tested with a plain dict.  Its main responsibility is to keep a
single source of truth for the active project/well/LAS/workspace and to clear all
derived UI data when one of these boundaries changes.

Why this module exists
----------------------
Streamlit does not allow changing a session-state key after a widget with the
same key has already been instantiated in the current script run.  Therefore UI
widgets must use their own widget keys, while the application context must be
kept in separate state keys controlled by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, MutableMapping

from core.session_state_manager import (
    SessionCleanupResult,
    clear_on_las_change,
    clear_on_project_change,
    clear_on_well_change,
    clear_on_workspace_change,
)
from core.event_bus import ApplicationEvent, ApplicationEventBus
from core.runtime_service_registry import RuntimeServiceRegistry, runtime_service_registry

ACTIVE_PROJECT_ID_KEY = "active_project_id"
ACTIVE_WELL_ID_KEY = "active_well_id"
ACTIVE_LAS_ID_KEY = "active_las_id"
ACTIVE_WORKSPACE_ID_KEY = "active_workspace_id"

PENDING_ACTIVE_PROJECT_ID_KEY = "pending_active_project_id"
PENDING_ACTIVE_WELL_ID_KEY = "pending_active_well_id"
PENDING_ACTIVE_LAS_ID_KEY = "pending_active_las_id"
PENDING_ACTIVE_WORKSPACE_ID_KEY = "pending_active_workspace_id"


class ApplicationStateKeys(str, Enum):
    """Compatibility names for application-owned context keys."""

    ACTIVE_PROJECT_ID = ACTIVE_PROJECT_ID_KEY
    ACTIVE_WELL_ID = ACTIVE_WELL_ID_KEY
    ACTIVE_LAS_ID = ACTIVE_LAS_ID_KEY
    ACTIVE_WORKSPACE_ID = ACTIVE_WORKSPACE_ID_KEY


@dataclass(frozen=True)
class ApplicationContext:
    """Current persistent application context."""

    project_id: str = ""
    well_id: str = ""
    las_id: str = ""
    workspace_id: str = ""

    @classmethod
    def from_state(cls, state: MutableMapping[str, Any]) -> "ApplicationContext":
        return cls(
            project_id=str(state.get(ACTIVE_PROJECT_ID_KEY, "") or ""),
            well_id=str(state.get(ACTIVE_WELL_ID_KEY, "") or ""),
            las_id=str(state.get(ACTIVE_LAS_ID_KEY, "") or ""),
            workspace_id=str(state.get(ACTIVE_WORKSPACE_ID_KEY, "") or ""),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "project_id": self.project_id,
            "well_id": self.well_id,
            "las_id": self.las_id,
            "workspace_id": self.workspace_id,
        }


@dataclass(frozen=True)
class StateTransition:
    """Result of an application context transition."""

    before: ApplicationContext
    after: ApplicationContext
    changed: bool
    cleanup: SessionCleanupResult | None = None


class ApplicationStateController:
    """Single entry point for context changes and stale-state cleanup."""

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state

    def context(self) -> ApplicationContext:
        return ApplicationContext.from_state(self.state)

    def get_value(self, key: str, default: Any = None) -> Any:
        """Read a session value through the application-state boundary.

        UI code should prefer this helper over direct ``st.session_state`` access
        for application-owned keys.  The method stays intentionally small so it
        remains compatible with Streamlit session state and plain dict tests.
        """

        return self.state.get(str(key), default)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a state value using the standard mapping-compatible API.

        ``ApplicationStateController`` is deliberately not a mutable mapping, but
        older UI helpers historically received ``st.session_state`` directly and
        therefore call ``get``.  Keeping this read-only compatibility alias avoids
        route-wide failures during the state-controller migration while all new
        code continues to use :meth:`get_value`.
        """

        return self.get_value(key, default)

    def set_value(self, key: str, value: Any) -> None:
        """Write a serializable session value through the application-state boundary."""

        self.state[str(key)] = value

    def runtime_services(self) -> RuntimeServiceRegistry:
        """Return the session-scoped registry for live, non-copyable services."""

        return runtime_service_registry(self.state)

    def get_runtime_service(self, key: str, default: Any = None) -> Any:
        """Read a process-local service without mixing it into rollback data."""

        return self.runtime_services().get(key, default)

    def set_runtime_service(self, key: str, service: Any, *, scope: str = "session") -> Any:
        """Register a process-local service and return it."""

        return self.runtime_services().set(key, service, scope=scope)

    def ensure_runtime_service(
        self,
        key: str,
        factory: Any,
        *,
        expected_type: type[Any] | None = None,
        scope: str = "session",
    ) -> Any:
        """Return an existing runtime service or construct it exactly once."""

        return self.runtime_services().ensure(
            key, factory, expected_type=expected_type, scope=scope
        )

    def remove_runtime_service(self, key: str, default: Any = None) -> Any:
        """Remove one process-local service from the registry."""

        return self.runtime_services().remove(key, default)

    def shutdown_runtime_services(self, *, remove: bool = True) -> tuple[Any, ...]:
        """Close all process-local services owned by the current session.

        When ``remove`` is true, the registry container itself is detached from
        application state after shutdown. A later runtime-service request will
        create a fresh empty registry instead of retaining a disposed container.
        """

        registry = self.runtime_services()
        results = registry.shutdown(remove=remove)
        if remove:
            from core.runtime_service_registry import RUNTIME_SERVICES_STATE_KEY

            if self.state.get(RUNTIME_SERVICES_STATE_KEY) is registry:
                self.state.pop(RUNTIME_SERVICES_STATE_KEY, None)
        return results

    def update_values(self, values: dict[str, Any]) -> None:
        """Write multiple application-owned session values atomically."""

        for key, value in values.items():
            self.set_value(key, value)

    def remove_value(self, key: str, default: Any = None) -> Any:
        """Remove an application-owned state value through the controller."""

        return self.state.pop(str(key), default)

    def keys(self) -> tuple[str, ...]:
        """Return a stable snapshot of currently known state keys."""

        return tuple(str(key) for key in self.state.keys())

    def clear_matching(self, *, exact_keys: set[str] | None = None, prefixes: tuple[str, ...] = ()) -> tuple[str, ...]:
        """Remove state values matching exact keys or prefixes.

        This helper is intended for non-widget application data such as cached
        LAS editor sheets, calculated tables and graph state.  It keeps the
        cleanup policy centralized and testable instead of scattering direct
        ``st.session_state.pop`` calls through UI code.
        """

        exact = {str(key) for key in (exact_keys or set())}
        removed: list[str] = []
        for key in self.keys():
            if key in exact or any(key.startswith(prefix) for prefix in prefixes):
                self.remove_value(key, None)
                removed.append(key)
        return tuple(removed)

    def ensure_value(self, key: str, default: Any) -> Any:
        """Return an application-owned value, initializing it when missing.

        This keeps UI modules from performing direct membership checks and
        assignments against ``st.session_state`` for non-widget state.  The
        default is stored as-is so callers can intentionally seed immutable
        values such as tuples or mutable containers such as dictionaries.
        """

        clean_key = str(key)
        if clean_key not in self.state:
            self.state[clean_key] = default
        return self.state[clean_key]

    def get_dict(self, key: str) -> dict[Any, Any]:
        """Read a mapping value as a defensive dictionary copy."""

        value = self.get_value(key, {})
        return dict(value) if isinstance(value, dict) else {}

    def get_list(self, key: str) -> list[Any]:
        """Read a sequence value as a defensive list copy."""

        value = self.get_value(key, [])
        return list(value) if isinstance(value, (list, tuple)) else []

    def get_tuple(self, key: str) -> tuple[Any, ...]:
        """Read a sequence value as a defensive tuple copy."""

        value = self.get_value(key, ())
        return tuple(value) if isinstance(value, (list, tuple)) else ()

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        """Return a defensive copy of one application-state namespace."""

        key = f"state::{str(namespace).strip()}"
        value = self.get_value(key, {})
        return dict(value) if isinstance(value, dict) else {}

    def update_namespace(self, namespace: str, values: dict[str, Any]) -> dict[str, Any]:
        """Atomically merge values into an isolated state namespace."""

        key = f"state::{str(namespace).strip()}"
        current = self.get_namespace(namespace)
        current.update(dict(values))
        self.set_value(key, current)
        return dict(current)

    def clear_namespace(self, namespace: str) -> dict[str, Any]:
        """Remove and return one isolated state namespace."""

        key = f"state::{str(namespace).strip()}"
        value = self.remove_value(key, {})
        return dict(value) if isinstance(value, dict) else {}

    def ensure_project(self, project_id: str) -> StateTransition:
        """Initialize active project if missing without clearing existing state."""

        current = self.context()
        clean_project_id = str(project_id or "")
        if current.project_id:
            return StateTransition(before=current, after=current, changed=False)
        self.state[ACTIVE_PROJECT_ID_KEY] = clean_project_id
        after = self.context()
        return StateTransition(before=current, after=after, changed=True)

    def activate_project(self, project_id: str) -> StateTransition:
        """Switch project and clear every derived workspace artifact."""

        before = self.context()
        clean_project_id = str(project_id or "")
        if before.project_id == clean_project_id:
            return StateTransition(before=before, after=before, changed=False)
        cleanup = clear_on_project_change(self.state, clean_project_id)
        after = self.context()
        self._event_bus().publish(
            "project.changed",
            {
                "project_id": clean_project_id,
                "previous_project_id": before.project_id,
                "cleared_keys": list(cleanup.cleared_keys),
            },
            source="ApplicationStateController",
        )
        return StateTransition(before=before, after=after, changed=True, cleanup=cleanup)

    def activate_well(self, well_id: str) -> StateTransition:
        """Switch well inside the active project and clear well/LAS-derived state."""

        before = self.context()
        clean_well_id = str(well_id or "")
        if before.well_id == clean_well_id:
            return StateTransition(before=before, after=before, changed=False)
        cleanup = clear_on_well_change(self.state, before.project_id, clean_well_id)
        after = self.context()
        return StateTransition(before=before, after=after, changed=True, cleanup=cleanup)

    def activate_las(self, las_id: str) -> StateTransition:
        """Switch LAS and clear all derived tables, charts, diagnostics and stats."""

        before = self.context()
        clean_las_id = str(las_id or "")
        if before.las_id == clean_las_id:
            return StateTransition(before=before, after=before, changed=False)
        cleanup = clear_on_las_change(self.state, before.project_id, before.well_id, clean_las_id)
        after = self.context()
        return StateTransition(before=before, after=after, changed=True, cleanup=cleanup)

    def activate_workspace(self, workspace_id: str) -> StateTransition:
        """Switch workspace and clear workspace-local artifacts."""

        before = self.context()
        clean_workspace_id = str(workspace_id or "")
        if before.workspace_id == clean_workspace_id:
            return StateTransition(before=before, after=before, changed=False)
        cleanup = clear_on_workspace_change(
            self.state,
            before.project_id,
            before.well_id,
            before.las_id,
            clean_workspace_id,
        )
        after = self.context()
        return StateTransition(before=before, after=after, changed=True, cleanup=cleanup)

    def request_project_activation(self, project_id: str) -> None:
        """Store a pending project switch for the next safe render cycle."""

        self.state[PENDING_ACTIVE_PROJECT_ID_KEY] = str(project_id or "")

    def consume_pending_project_activation(self) -> StateTransition | None:
        """Apply and remove a pending project switch before project widgets render."""

        pending = self.state.pop(PENDING_ACTIVE_PROJECT_ID_KEY, None)
        if not pending:
            return None
        return self.activate_project(str(pending))


    def publish_event(self, name: str, payload: dict[str, Any] | None = None, *, source: str = "ApplicationStateController") -> ApplicationEvent:
        """Publish an application event through the central state-backed bus."""

        return self._event_bus().publish(name, payload or {}, source=source)

    def request_well_activation(self, well_id: str) -> None:
        self.state[PENDING_ACTIVE_WELL_ID_KEY] = str(well_id or "")

    def consume_pending_well_activation(self) -> StateTransition | None:
        pending = self.state.pop(PENDING_ACTIVE_WELL_ID_KEY, None)
        if not pending:
            return None
        return self.activate_well(str(pending))

    def request_las_activation(self, las_id: str) -> None:
        self.state[PENDING_ACTIVE_LAS_ID_KEY] = str(las_id or "")

    def consume_pending_las_activation(self) -> StateTransition | None:
        pending = self.state.pop(PENDING_ACTIVE_LAS_ID_KEY, None)
        if not pending:
            return None
        return self.activate_las(str(pending))

    def request_workspace_activation(self, workspace_id: str) -> None:
        self.state[PENDING_ACTIVE_WORKSPACE_ID_KEY] = str(workspace_id or "")

    def consume_pending_workspace_activation(self) -> StateTransition | None:
        pending = self.state.pop(PENDING_ACTIVE_WORKSPACE_ID_KEY, None)
        if not pending:
            return None
        return self.activate_workspace(str(pending))

    def clear_current_context(self, reason: str = "manual_clear") -> SessionCleanupResult:
        """Clear derived data while keeping the current context values."""

        context = self.context()
        from core.session_state_manager import clear_transient_session_state

        cleanup = clear_transient_session_state(
            self.state,
            reason=reason,
            project_id=context.project_id,
            well_id=context.well_id,
            las_id=context.las_id,
            workspace_id=context.workspace_id,
        )
        self.publish_event(
            "session.cleared",
            {
                "reason": reason,
                "cleared_keys": list(cleanup.cleared_keys),
                "active_context": cleanup.active_context,
            },
            source="ApplicationStateController",
        )
        return cleanup

    def _event_bus(self) -> ApplicationEventBus:
        """Return the state-backed application event bus."""

        return ApplicationEventBus(self.state)

    def consume_events(self) -> tuple[ApplicationEvent, ...]:
        """Consume pending application events."""

        return self._event_bus().consume()

    def request_refresh(self, reason: str, *, source: str = "ApplicationStateController") -> None:
        """Request a safe UI refresh through the application event bus."""

        self._event_bus().request_refresh(reason, source=source)

    def consume_refresh_request(self) -> dict[str, Any] | None:
        """Consume a pending refresh request if present."""

        return self._event_bus().consume_refresh_request()


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
from typing import Any, MutableMapping

from core.session_state_manager import (
    SessionCleanupResult,
    clear_on_las_change,
    clear_on_project_change,
    clear_on_well_change,
    clear_on_workspace_change,
)

ACTIVE_PROJECT_ID_KEY = "active_project_id"
ACTIVE_WELL_ID_KEY = "active_well_id"
ACTIVE_LAS_ID_KEY = "active_las_id"
ACTIVE_WORKSPACE_ID_KEY = "active_workspace_id"

PENDING_ACTIVE_PROJECT_ID_KEY = "pending_active_project_id"
PENDING_ACTIVE_WELL_ID_KEY = "pending_active_well_id"
PENDING_ACTIVE_LAS_ID_KEY = "pending_active_las_id"
PENDING_ACTIVE_WORKSPACE_ID_KEY = "pending_active_workspace_id"


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

    def set_value(self, key: str, value: Any) -> None:
        """Write a session value through the application-state boundary."""

        self.state[str(key)] = value

    def update_values(self, values: dict[str, Any]) -> None:
        """Write multiple application-owned session values atomically."""

        for key, value in values.items():
            self.set_value(key, value)

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

    def clear_current_context(self, reason: str = "manual_clear") -> SessionCleanupResult:
        """Clear derived data while keeping the current context values."""

        context = self.context()
        from core.session_state_manager import clear_transient_session_state

        return clear_transient_session_state(
            self.state,
            reason=reason,
            project_id=context.project_id,
            well_id=context.well_id,
            las_id=context.las_id,
            workspace_id=context.workspace_id,
        )

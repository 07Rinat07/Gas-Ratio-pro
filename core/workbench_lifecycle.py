"""Lifecycle manager for the Modern Workbench.

The lifecycle manager coordinates Workbench initialization, workspace opening,
closing and state restoration.  It is intentionally UI-neutral and publishes
all changes through the application event bus so Streamlit remains a renderer
instead of a state owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, MutableMapping, TYPE_CHECKING

from core.application_state import ApplicationStateController
from core.runtime_service_registry import summarize_runtime_service_shutdown
from core.workspace_session import WorkspaceSession, WorkspaceSessionManager
from core.workbench_context import (
    WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY,
    WORKBENCH_LIFECYCLE_STATE_KEY,
    WorkspaceContext,
)
if TYPE_CHECKING:
    from core.workbench_controller import WorkbenchController

WORKBENCH_LIFECYCLE_INITIALIZED = "initialized"
WORKBENCH_LIFECYCLE_OPEN = "open"
WORKBENCH_LIFECYCLE_CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class WorkbenchLifecycleResult:
    """Result returned by lifecycle operations."""

    executed: bool
    state: str
    context: WorkspaceContext
    message: str = ""
    affected_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "executed": self.executed,
            "state": self.state,
            "context": self.context.to_dict(),
            "message": self.message,
            "affected_keys": list(self.affected_keys),
        }


class WorkbenchLifecycleManager:
    """Lifecycle boundary used by controllers and future UI adapters."""

    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        controller: "WorkbenchController" | None = None,
        sessions_dir: str | Path = "data/sessions",
    ) -> None:
        self.state = state
        if controller is None:
            from core.workbench_controller import build_workbench_controller
            controller = build_workbench_controller(state)
        self.controller = controller
        self.state_controller = ApplicationStateController(state)
        self.session_manager = WorkspaceSessionManager(state, sessions_dir=sessions_dir)

    def context(self) -> WorkspaceContext:
        return WorkspaceContext.from_state(self.state, self.controller.shell())

    def initialize(self) -> WorkbenchLifecycleResult:
        """Initialize Workbench state without opening a project workspace."""

        self.controller.shell()  # Build once to normalize command/navigation defaults.
        self.state[WORKBENCH_LIFECYCLE_STATE_KEY] = WORKBENCH_LIFECYCLE_INITIALIZED
        event = self.state_controller.publish_event(
            "workbench.initialized",
            self.context().to_dict(),
            source="WorkbenchLifecycleManager",
        )
        return WorkbenchLifecycleResult(
            executed=True,
            state=WORKBENCH_LIFECYCLE_INITIALIZED,
            context=self.context(),
            message="Workbench initialized.",
            affected_keys=(WORKBENCH_LIFECYCLE_STATE_KEY, event.name),
        )

    def open_workspace(self, session: WorkspaceSession | None = None) -> WorkbenchLifecycleResult:
        """Open a workspace, optionally restoring a saved lightweight session."""

        affected = [WORKBENCH_LIFECYCLE_STATE_KEY]
        if session is not None:
            restore_result = self.session_manager.restore(session, conflict_policy="overwrite")
            affected.extend(restore_result.affected_keys)
            self.state[WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY] = session.session_id()
            affected.append(WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY)
        else:
            self.state[WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY] = self.session_manager.capture().session_id()
            affected.append(WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY)

        self.state[WORKBENCH_LIFECYCLE_STATE_KEY] = WORKBENCH_LIFECYCLE_OPEN
        event = self.state_controller.publish_event(
            "workbench.workspace.opened",
            self.context().to_dict(),
            source="WorkbenchLifecycleManager",
        )
        affected.append(event.name)
        return WorkbenchLifecycleResult(
            executed=True,
            state=WORKBENCH_LIFECYCLE_OPEN,
            context=self.context(),
            message="Workbench workspace opened.",
            affected_keys=tuple(sorted(set(affected))),
        )

    def close_workspace(self, *, save: bool = False, path: str | Path | None = None) -> WorkbenchLifecycleResult:
        """Close the active workspace and optionally save the lightweight session."""

        affected = [WORKBENCH_LIFECYCLE_STATE_KEY]
        if save:
            save_result = self.session_manager.save(path)
            affected.extend(save_result.affected_keys)
        shutdown_results = self.state_controller.shutdown_runtime_services(remove=True)
        shutdown_summary = summarize_runtime_service_shutdown(shutdown_results)
        affected.extend(f"runtime_service:{item.key}" for item in shutdown_results)
        shutdown_event = self.state_controller.publish_event(
            "workbench.runtime_services.shutdown",
            shutdown_summary.to_dict(),
            source="WorkbenchLifecycleManager",
        )
        affected.append(shutdown_event.name)
        self.state[WORKBENCH_LIFECYCLE_STATE_KEY] = WORKBENCH_LIFECYCLE_CLOSED
        self.state.pop(WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY, None)
        affected.append(WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY)
        event = self.state_controller.publish_event(
            "workbench.workspace.closed",
            self.context().to_dict(),
            source="WorkbenchLifecycleManager",
        )
        affected.append(event.name)
        message = "Workbench workspace closed."
        if shutdown_summary.failed:
            message = (
                "Workbench workspace closed with "
                f"{shutdown_summary.failed} runtime service shutdown failure(s)."
            )
        return WorkbenchLifecycleResult(
            executed=True,
            state=WORKBENCH_LIFECYCLE_CLOSED,
            context=self.context(),
            message=message,
            affected_keys=tuple(sorted(set(affected))),
        )

    def restore_from_file(self, path: str | Path) -> WorkbenchLifecycleResult:
        """Load a saved workspace session and open it in the Workbench."""

        session = self.session_manager.load(path)
        return self.open_workspace(session)

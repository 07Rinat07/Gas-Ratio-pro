from __future__ import annotations

"""Controller layer for active Workspace workflows.

The controller connects the UI-facing WorkspaceManager with the framework-neutral
ApplicationStateController.  UI modules should use this layer when an operation
must both touch persisted workspace metadata and update the active application
context.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, MutableMapping

from core.application_state import ApplicationStateController, StateTransition
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.workspace_manager import WorkspaceManager, WorkspaceManagerDeleteResult, WorkspaceManagerItem
from projects.workspace_repository import WorkspaceRecord, safe_workspace_id


@dataclass(frozen=True)
class WorkspaceControllerResult:
    """Result returned by controller workflows that may change app state."""

    workspace: WorkspaceRecord
    transition: StateTransition
    created: bool = False


@dataclass(frozen=True)
class WorkspaceControllerDeleteResult:
    """Deletion result with application-context cleanup information."""

    delete_result: WorkspaceManagerDeleteResult
    transition: StateTransition | None = None


class WorkspaceController:
    """Single UI-safe entry point for workspace context operations.

    Responsibilities:
    - delegate persistence to ``WorkspaceManager``;
    - delegate active workspace state changes to ``ApplicationStateController``;
    - keep UI modules from mixing repository/service calls with direct
      ``st.session_state`` reads and writes.
    """

    def __init__(
        self,
        state: MutableMapping[str, Any],
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        *,
        manager: WorkspaceManager | None = None,
        state_controller: ApplicationStateController | None = None,
    ) -> None:
        self.state_controller = state_controller or ApplicationStateController(state)
        self.manager = manager or WorkspaceManager(root)

    def active_workspace_id(self) -> str:
        """Return the current active workspace identifier from app context."""

        return self.state_controller.context().workspace_id

    def list_project_workspaces(self, project_id: str) -> tuple[WorkspaceManagerItem, ...]:
        """List workspaces and mark the currently active one."""

        return self.manager.list_project_workspaces(
            safe_project_id(project_id),
            active_workspace_id=self.active_workspace_id(),
        )

    def open_workspace(self, project_id: str, workspace_id: str) -> WorkspaceControllerResult:
        """Open a persisted workspace and activate it in application state."""

        workspace = self.manager.open_workspace(
            safe_project_id(project_id),
            safe_workspace_id(workspace_id),
        )
        transition = self.state_controller.activate_workspace(workspace.id)
        return WorkspaceControllerResult(workspace=workspace, transition=transition, created=False)

    def create_workspace(
        self,
        project_id: str,
        name: str,
        *,
        kind: str = "general",
        description: str = "",
        settings: dict[str, Any] | None = None,
        workspace_id: str | None = None,
        activate: bool = True,
    ) -> WorkspaceControllerResult:
        """Create a workspace through the manager and optionally activate it."""

        created = self.manager.create_project_workspace(
            safe_project_id(project_id),
            name,
            kind=kind,
            description=description,
            settings=settings,
            workspace_id=workspace_id,
        )
        transition = (
            self.state_controller.activate_workspace(created.workspace.id)
            if activate
            else StateTransition(
                before=self.state_controller.context(),
                after=self.state_controller.context(),
                changed=False,
            )
        )
        return WorkspaceControllerResult(workspace=created.workspace, transition=transition, created=True)

    def ensure_active_workspace(
        self,
        project_id: str,
        *,
        name: str = "Workspace",
        kind: str = "general",
        workspace_id: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> WorkspaceControllerResult:
        """Load the active workspace or create/activate a stable default.

        If ``workspace_id`` is omitted, the current active workspace is reused.
        When neither exists, the manager creates a default workspace and this
        controller activates it through ``ApplicationStateController``.
        """

        clean_project_id = safe_project_id(project_id)
        target_id = workspace_id or self.active_workspace_id()
        created = False
        if target_id:
            try:
                workspace = self.manager.open_workspace(clean_project_id, safe_workspace_id(target_id))
            except FileNotFoundError:
                workspace = self.manager.ensure_project_workspace(
                    clean_project_id,
                    name=name,
                    kind=kind,
                    workspace_id=target_id,
                    settings=settings,
                )
                created = True
        else:
            workspace = self.manager.ensure_project_workspace(
                clean_project_id,
                name=name,
                kind=kind,
                workspace_id=workspace_id,
                settings=settings,
            )
            created = True

        transition = self.state_controller.activate_workspace(workspace.id)
        return WorkspaceControllerResult(workspace=workspace, transition=transition, created=created)

    def update_active_workspace_settings(
        self,
        project_id: str,
        settings: dict[str, Any],
    ) -> WorkspaceRecord:
        """Update settings of the active workspace through the manager boundary."""

        workspace_id = self.active_workspace_id()
        if not workspace_id:
            raise ValueError("Нет активного рабочего пространства для обновления настроек.")
        return self.manager.update_workspace_settings(
            safe_project_id(project_id),
            safe_workspace_id(workspace_id),
            dict(settings or {}),
        )

    def close_workspace(self) -> StateTransition:
        """Clear the active workspace context without deleting persisted files."""

        return self.state_controller.activate_workspace("")

    def delete_workspace(self, project_id: str, workspace_id: str) -> WorkspaceControllerDeleteResult:
        """Delete a workspace and clear context if that workspace was active."""

        clean_workspace_id = safe_workspace_id(workspace_id)
        was_active = self.active_workspace_id() == clean_workspace_id
        result = self.manager.delete_project_workspace(safe_project_id(project_id), clean_workspace_id)
        transition = self.close_workspace() if was_active and result.deleted else None
        return WorkspaceControllerDeleteResult(delete_result=result, transition=transition)

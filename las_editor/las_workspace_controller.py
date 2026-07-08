from __future__ import annotations

"""Controller boundary for LAS Workspace 3.0.

This module is intentionally renderer-independent.  It connects the generic
project Workspace Framework with LAS-specific home state so UI code can prepare
or activate a LAS workspace without directly touching persistence or
``st.session_state``.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, MutableMapping

from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.workspace_controller import WorkspaceController, WorkspaceControllerResult
from projects.workspace_repository import WorkspaceRecord

from las_editor.las_workspace_home import LasWorkspaceHomeState, build_las_workspace_home_state

LAS_WORKSPACE_KIND = "las"
LAS_WORKSPACE_DEFAULT_ID = "las-workspace-3"
LAS_WORKSPACE_DEFAULT_NAME = "LAS Workspace 3.0"
LAS_WORKSPACE_SCHEMA = "gas-ratio-pro.las-workspace.v3"


@dataclass(frozen=True)
class LasWorkspaceControllerState:
    """UI-ready LAS workspace state returned by the controller boundary."""

    schema: str
    project_id: str
    workspace: WorkspaceRecord
    home: LasWorkspaceHomeState
    created: bool
    is_active: bool


def default_las_workspace_settings() -> dict[str, Any]:
    """Return default persisted settings for a project LAS workspace."""

    return {
        "schema": LAS_WORKSPACE_SCHEMA,
        "workspace_version": "3.0",
        "default_panel": "home",
        "enabled_tools": [
            "create_las",
            "open_las",
            "import_csv",
            "import_excel",
            "templates",
            "validator",
        ],
        "storage_scope": "project",
    }


class LasWorkspaceController:
    """LAS-specific facade over the generic WorkspaceController.

    Responsibilities:
    - ensure that each project has a stable LAS Workspace 3.0 record;
    - activate the workspace through ApplicationStateController indirectly;
    - expose a renderer-independent LAS home state for UI/tests.
    """

    def __init__(
        self,
        state: MutableMapping[str, Any],
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        *,
        workspace_controller: WorkspaceController | None = None,
    ) -> None:
        self.workspace_controller = workspace_controller or WorkspaceController(state, root)

    def ensure_project_las_workspace(
        self,
        project_id: str,
        *,
        activate: bool = True,
        recent_files: tuple[str, ...] = (),
    ) -> LasWorkspaceControllerState:
        """Ensure the project-level LAS workspace exists and optionally activate it."""

        clean_project_id = safe_project_id(project_id)
        result: WorkspaceControllerResult = self.workspace_controller.ensure_active_workspace(
            clean_project_id,
            name=LAS_WORKSPACE_DEFAULT_NAME,
            kind=LAS_WORKSPACE_KIND,
            workspace_id=LAS_WORKSPACE_DEFAULT_ID,
            settings=default_las_workspace_settings(),
        )
        if not activate and result.transition.changed:
            self.workspace_controller.close_workspace()

        active_id = self.workspace_controller.active_workspace_id()
        return LasWorkspaceControllerState(
            schema=LAS_WORKSPACE_SCHEMA,
            project_id=clean_project_id,
            workspace=result.workspace,
            home=build_las_workspace_home_state(recent_files=recent_files),
            created=result.created,
            is_active=active_id == result.workspace.id,
        )

    def open_project_las_workspace(
        self,
        project_id: str,
        *,
        recent_files: tuple[str, ...] = (),
    ) -> LasWorkspaceControllerState:
        """Open and activate the stable LAS Workspace 3.0 record."""

        clean_project_id = safe_project_id(project_id)
        result = self.workspace_controller.open_workspace(clean_project_id, LAS_WORKSPACE_DEFAULT_ID)
        return LasWorkspaceControllerState(
            schema=LAS_WORKSPACE_SCHEMA,
            project_id=clean_project_id,
            workspace=result.workspace,
            home=build_las_workspace_home_state(recent_files=recent_files),
            created=False,
            is_active=self.workspace_controller.active_workspace_id() == result.workspace.id,
        )

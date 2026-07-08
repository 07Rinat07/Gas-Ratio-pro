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

import pandas as pd

from importers.las_importer import read_las

from las_editor.las_creation_wizard import (
    LasCreationWizardDraft,
    LasCreationWizardFinalizeResult,
    LasCreationWizardPreviewV2,
    build_las_creation_wizard_preview_v2,
    finalize_las_creation_wizard,
)
from las_editor.las_safe_export import LasSafeExportManifest, export_las_text_safely

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




@dataclass(frozen=True)
class LasWorkspaceWorkingCopyItem:
    """Renderer-independent descriptor for a LAS working copy stored in workspace."""

    filename: str
    path: str
    bytes_count: int
    modified_at: float


@dataclass(frozen=True)
class LasWorkspaceOpenedLasResult:
    """Result of opening a LAS working copy through the workspace boundary."""

    workspace_state: LasWorkspaceControllerState
    item: LasWorkspaceWorkingCopyItem
    data: pd.DataFrame
    workspace: WorkspaceRecord


@dataclass(frozen=True)
class LasWorkspaceCreationPreviewState:
    """Preview of a create-LAS workflow prepared through the workspace boundary."""

    workspace_state: LasWorkspaceControllerState
    preview: LasCreationWizardPreviewV2


@dataclass(frozen=True)
class LasWorkspaceCreatedLasResult:
    """Result of writing a new LAS working copy under the active LAS workspace."""

    workspace_state: LasWorkspaceControllerState
    final: LasCreationWizardFinalizeResult
    manifest: LasSafeExportManifest
    workspace: WorkspaceRecord


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



    def _working_copies_dir(self, project_id: str, workspace_id: str = LAS_WORKSPACE_DEFAULT_ID) -> Path:
        """Return the workspace-scoped directory for generated LAS working copies."""

        return (
            self.workspace_controller.manager.root
            / safe_project_id(project_id)
            / "workspaces"
            / workspace_id
            / "las"
            / "working_copies"
        )

    def list_las_working_copies(self, project_id: str) -> tuple[LasWorkspaceWorkingCopyItem, ...]:
        """List LAS working copies saved inside the project LAS workspace.

        The method does not activate the workspace and does not touch UI state.
        It only exposes storage-scoped LAS files that belong to
        ``workspaces/las-workspace-3/las/working_copies``.
        """

        workspace_state = self.ensure_project_las_workspace(project_id, activate=False)
        copies_dir = self._working_copies_dir(workspace_state.project_id, workspace_state.workspace.id)
        if not copies_dir.exists():
            return ()

        items: list[LasWorkspaceWorkingCopyItem] = []
        for path in sorted(copies_dir.glob("*.las"), key=lambda candidate: candidate.name.lower()):
            if not path.is_file():
                continue
            stat = path.stat()
            items.append(
                LasWorkspaceWorkingCopyItem(
                    filename=path.name,
                    path=str(path),
                    bytes_count=stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )
        return tuple(items)

    def open_las_working_copy(
        self,
        project_id: str,
        filename: str,
        *,
        recent_files: tuple[str, ...] = (),
    ) -> LasWorkspaceOpenedLasResult:
        """Open a saved LAS working copy through the LAS Workspace boundary.

        ``filename`` is sanitized to a basename and resolved only inside the
        workspace working-copy directory.  This prevents UI code from opening
        arbitrary filesystem paths while still allowing a selected LAS copy to
        be parsed and placed into the application session by the caller.
        """

        workspace_state = self.ensure_project_las_workspace(
            project_id,
            activate=True,
            recent_files=recent_files,
        )
        clean_filename = Path(filename or "").name.strip()
        if not clean_filename:
            raise ValueError("LAS working copy filename is required.")
        if not clean_filename.lower().endswith(".las"):
            clean_filename = f"{clean_filename}.las"

        target = self._working_copies_dir(workspace_state.project_id, workspace_state.workspace.id) / clean_filename
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"LAS working copy was not found: {clean_filename}")

        data = read_las(target)
        stat = target.stat()
        item = LasWorkspaceWorkingCopyItem(
            filename=target.name,
            path=str(target),
            bytes_count=stat.st_size,
            modified_at=stat.st_mtime,
        )
        updated = self.workspace_controller.manager.update_workspace_settings(
            workspace_state.project_id,
            workspace_state.workspace.id,
            {
                "last_opened_las": item.path,
                "last_opened_las_rows": len(data),
                "last_opened_las_curves": len(data.columns),
            },
        )
        return LasWorkspaceOpenedLasResult(
            workspace_state=workspace_state,
            item=item,
            data=data,
            workspace=updated,
        )

    def preview_create_las_workflow(
        self,
        project_id: str,
        draft: LasCreationWizardDraft,
        *,
        activate: bool = True,
        recent_files: tuple[str, ...] = (),
    ) -> LasWorkspaceCreationPreviewState:
        """Prepare a new-LAS workflow through the LAS Workspace boundary.

        The method deliberately returns a renderer-independent preview.  UI code
        can display the wizard state, validation issues and generated table
        without constructing LAS data directly and without touching
        ``st.session_state``.
        """

        workspace_state = self.ensure_project_las_workspace(
            project_id,
            activate=activate,
            recent_files=recent_files,
        )
        preview = build_las_creation_wizard_preview_v2(draft)
        return LasWorkspaceCreationPreviewState(workspace_state=workspace_state, preview=preview)

    def create_las_working_copy(
        self,
        project_id: str,
        draft: LasCreationWizardDraft,
        *,
        filename: str | None = None,
        allow_overwrite: bool = False,
        recent_files: tuple[str, ...] = (),
    ) -> LasWorkspaceCreatedLasResult:
        """Create and persist a LAS working copy inside the project workspace.

        This keeps the workflow behind UI → Controller → Workspace Framework:
        the controller prepares the stable LAS workspace, delegates LAS document
        generation to the creation wizard service functions, writes only into the
        workspace-scoped ``working_copies`` directory, and stores the latest
        output path in workspace settings.
        """

        workspace_state = self.ensure_project_las_workspace(
            project_id,
            activate=True,
            recent_files=recent_files,
        )
        final = finalize_las_creation_wizard(draft)
        clean_filename = Path(filename or final.filename).name.strip() or final.filename
        if not clean_filename.lower().endswith(".las"):
            clean_filename = f"{clean_filename}.las"

        target = self._working_copies_dir(workspace_state.project_id, workspace_state.workspace.id) / clean_filename
        manifest = export_las_text_safely(
            final.las_text,
            target,
            allow_overwrite=allow_overwrite,
            dataframe=final.preview.data,
        )
        if not manifest.is_ready:
            return LasWorkspaceCreatedLasResult(
                workspace_state=workspace_state,
                final=final,
                manifest=manifest,
                workspace=workspace_state.workspace,
            )

        updated = self.workspace_controller.manager.update_workspace_settings(
            workspace_state.project_id,
            workspace_state.workspace.id,
            {
                "last_created_las": manifest.target_path,
                "last_created_las_rows": final.preview.data.shape[0],
                "last_created_las_curves": max(0, final.preview.data.shape[1] - 1),
            },
        )
        return LasWorkspaceCreatedLasResult(
            workspace_state=workspace_state,
            final=final,
            manifest=manifest,
            workspace=updated,
        )

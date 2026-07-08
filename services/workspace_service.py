from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECTS_ROOT, load_project, safe_project_id
from projects.workspace_repository import (
    WorkspaceRecord,
    create_workspace,
    delete_workspace,
    list_workspaces,
    load_workspace,
    safe_workspace_id,
    update_workspace,
)


@dataclass(frozen=True)
class WorkspaceCreateResult:
    """Result of a workspace creation workflow."""

    workspace: WorkspaceRecord
    project_exists: bool


@dataclass(frozen=True)
class WorkspaceDeleteResult:
    """Result of a workspace deletion workflow."""

    project_id: str
    workspace_id: str
    deleted: bool


class WorkspaceService:
    """Service boundary for project-scoped workspace operations.

    UI code should use this service instead of reading or writing workspace
    JSON files directly. The service validates the parent project and delegates
    persistence to ``projects.workspace_repository``.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)

    def list_workspaces(self, project_id: str) -> tuple[WorkspaceRecord, ...]:
        return list_workspaces(self.root, safe_project_id(project_id))

    def load_workspace(self, project_id: str, workspace_id: str) -> WorkspaceRecord:
        return load_workspace(self.root, safe_project_id(project_id), safe_workspace_id(workspace_id))

    def create_workspace(
        self,
        project_id: str,
        name: str,
        *,
        kind: str = "general",
        description: str = "",
        settings: dict[str, Any] | None = None,
        workspace_id: str | None = None,
    ) -> WorkspaceCreateResult:
        clean_project_id = safe_project_id(project_id)
        load_project(self.root, clean_project_id)
        workspace = create_workspace(
            self.root,
            clean_project_id,
            name=name,
            kind=kind,
            description=description,
            settings=settings,
            workspace_id=workspace_id,
        )
        return WorkspaceCreateResult(workspace=workspace, project_exists=True)

    def update_workspace(
        self,
        project_id: str,
        workspace_id: str,
        *,
        name: str | None = None,
        kind: str | None = None,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> WorkspaceRecord:
        return update_workspace(
            self.root,
            safe_project_id(project_id),
            safe_workspace_id(workspace_id),
            name=name,
            kind=kind,
            description=description,
            settings=settings,
        )

    def delete_workspace(self, project_id: str, workspace_id: str) -> WorkspaceDeleteResult:
        clean_project_id = safe_project_id(project_id)
        clean_workspace_id = safe_workspace_id(workspace_id)
        deleted = delete_workspace(self.root, clean_project_id, clean_workspace_id)
        return WorkspaceDeleteResult(project_id=clean_project_id, workspace_id=clean_workspace_id, deleted=deleted)

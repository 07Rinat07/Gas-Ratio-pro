from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.workspace_repository import WorkspaceRecord, safe_workspace_id
from services.workspace_service import WorkspaceCreateResult, WorkspaceDeleteResult, WorkspaceService


@dataclass(frozen=True)
class WorkspaceManagerItem:
    """UI-friendly workspace row produced by the workspace manager layer."""

    id: str
    project_id: str
    name: str
    kind: str
    description: str
    settings_count: int
    created_at: str
    updated_at: str
    is_active: bool = False


@dataclass(frozen=True)
class WorkspaceManagerDeleteResult:
    """UI-friendly delete result with enough context for notifications."""

    project_id: str
    workspace_id: str
    deleted: bool
    message: str


class WorkspaceManager:
    """Manager facade for project-scoped workspace workflows.

    The manager is intentionally thin: UI code can depend on this class for
    list/open/create/update/delete workflows while persistence remains behind
    ``WorkspaceService`` and ``projects.workspace_repository``. This keeps the
    Sprint 2 Workspace Framework aligned with the existing
    UI -> Service -> Repository -> Storage boundary.
    """

    def __init__(
        self,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        *,
        service: WorkspaceService | None = None,
    ) -> None:
        self.root = Path(root)
        self.service = service or WorkspaceService(self.root)

    def list_project_workspaces(
        self,
        project_id: str,
        *,
        active_workspace_id: str = "",
    ) -> tuple[WorkspaceManagerItem, ...]:
        """Return workspaces formatted for project explorer/workspace UI."""

        clean_project_id = safe_project_id(project_id)
        active_id = active_workspace_id.strip()
        return tuple(
            self._to_item(record, is_active=record.id == active_id)
            for record in self.service.list_workspaces(clean_project_id)
        )

    def open_workspace(self, project_id: str, workspace_id: str) -> WorkspaceRecord:
        """Load a workspace through the service boundary."""

        return self.service.load_workspace(
            safe_project_id(project_id),
            safe_workspace_id(workspace_id),
        )

    def create_project_workspace(
        self,
        project_id: str,
        name: str,
        *,
        kind: str = "general",
        description: str = "",
        settings: dict[str, Any] | None = None,
        workspace_id: str | None = None,
    ) -> WorkspaceCreateResult:
        """Create a project workspace through the service boundary."""

        return self.service.create_workspace(
            safe_project_id(project_id),
            name,
            kind=kind,
            description=description,
            settings=settings,
            workspace_id=workspace_id,
        )

    def update_project_workspace(
        self,
        project_id: str,
        workspace_id: str,
        *,
        name: str | None = None,
        kind: str | None = None,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> WorkspaceRecord:
        """Update workspace metadata through the service boundary."""

        return self.service.update_workspace(
            safe_project_id(project_id),
            safe_workspace_id(workspace_id),
            name=name,
            kind=kind,
            description=description,
            settings=settings,
        )

    def update_workspace_settings(
        self,
        project_id: str,
        workspace_id: str,
        settings: dict[str, Any],
    ) -> WorkspaceRecord:
        """Merge new settings into an existing workspace record."""

        return self.update_project_workspace(
            project_id,
            workspace_id,
            settings=dict(settings or {}),
        )

    def delete_project_workspace(self, project_id: str, workspace_id: str) -> WorkspaceManagerDeleteResult:
        """Delete a workspace and return a user-facing status message."""

        result: WorkspaceDeleteResult = self.service.delete_workspace(
            safe_project_id(project_id),
            safe_workspace_id(workspace_id),
        )
        message = (
            f"Workspace '{result.workspace_id}' deleted."
            if result.deleted
            else f"Workspace '{result.workspace_id}' was not found."
        )
        return WorkspaceManagerDeleteResult(
            project_id=result.project_id,
            workspace_id=result.workspace_id,
            deleted=result.deleted,
            message=message,
        )

    def ensure_project_workspace(
        self,
        project_id: str,
        *,
        name: str = "Workspace",
        kind: str = "general",
        workspace_id: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> WorkspaceRecord:
        """Return an existing workspace by id or create it when missing.

        This helper is useful for application shell modules that need a stable
        workspace context before rendering a Workspace page.
        """

        clean_project_id = safe_project_id(project_id)
        if workspace_id:
            try:
                return self.open_workspace(clean_project_id, workspace_id)
            except FileNotFoundError:
                pass
        created = self.create_project_workspace(
            clean_project_id,
            name,
            kind=kind,
            settings=settings,
            workspace_id=workspace_id,
        )
        return created.workspace

    @staticmethod
    def _to_item(record: WorkspaceRecord, *, is_active: bool = False) -> WorkspaceManagerItem:
        return WorkspaceManagerItem(
            id=record.id,
            project_id=record.project_id,
            name=record.name,
            kind=record.kind,
            description=record.description,
            settings_count=len(record.settings or {}),
            created_at=record.created_at,
            updated_at=record.updated_at,
            is_active=is_active,
        )

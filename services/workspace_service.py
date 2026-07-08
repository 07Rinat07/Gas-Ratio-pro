from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.storage_lifecycle import (
    CacheManager,
    DeleteEngine,
    FileHandleManager,
    IndexManager,
    ResourceManager,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, load_project, safe_project_id
from projects.workspace_repository import (
    WorkspaceRecord,
    create_workspace,
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
    index_entries_count: int = 0


@dataclass(frozen=True)
class WorkspaceDeleteResult:
    """Result of a workspace deletion workflow."""

    project_id: str
    workspace_id: str
    deleted: bool
    index_entries_count: int = 0
    released_resources: int = 0


class WorkspaceService:
    """Service boundary for project-scoped workspace operations.

    UI code should use this service instead of reading or writing workspace
    JSON files directly. The service validates the parent project and delegates
    persistence to ``projects.workspace_repository``. Destructive operations go
    through the Storage Lifecycle Framework so open resources/caches are
    released before workspace folders are removed and Project Database indexes
    are synchronized after changes.
    """

    def __init__(
        self,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        *,
        resource_manager: ResourceManager | None = None,
        cache_manager: CacheManager | None = None,
        file_handle_manager: FileHandleManager | None = None,
        delete_engine: DeleteEngine | None = None,
        index_manager: IndexManager | None = None,
    ) -> None:
        self.root = Path(root)
        self.resource_manager = resource_manager or ResourceManager()
        self.cache_manager = cache_manager or CacheManager()
        self.file_handle_manager = file_handle_manager or FileHandleManager(self.resource_manager)
        self.delete_engine = delete_engine or DeleteEngine(
            self.resource_manager,
            cache_manager=self.cache_manager,
            file_handle_manager=self.file_handle_manager,
        )
        self.index_manager = index_manager or IndexManager(self.root)

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
        index_result = self.index_manager.rebuild_project_index(clean_project_id)
        return WorkspaceCreateResult(
            workspace=workspace,
            project_exists=True,
            index_entries_count=index_result.entries_count,
        )

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
        clean_project_id = safe_project_id(project_id)
        updated = update_workspace(
            self.root,
            clean_project_id,
            safe_workspace_id(workspace_id),
            name=name,
            kind=kind,
            description=description,
            settings=settings,
        )
        self.index_manager.rebuild_project_index(clean_project_id)
        return updated

    def delete_workspace(self, project_id: str, workspace_id: str) -> WorkspaceDeleteResult:
        clean_project_id = safe_project_id(project_id)
        clean_workspace_id = safe_workspace_id(workspace_id)
        workspace_dir = self.workspace_dir(clean_project_id, clean_workspace_id)
        if not workspace_dir.exists():
            index_result = self.index_manager.validate_project_index(clean_project_id)
            return WorkspaceDeleteResult(
                project_id=clean_project_id,
                workspace_id=clean_workspace_id,
                deleted=False,
                index_entries_count=index_result.entries_count,
            )

        released = self.release_workspace_resources(clean_project_id, clean_workspace_id)
        delete_result = self.delete_engine.delete_path(workspace_dir, missing_ok=True)
        index_result = self.index_manager.sync_after_delete(clean_project_id)
        return WorkspaceDeleteResult(
            project_id=clean_project_id,
            workspace_id=clean_workspace_id,
            deleted=delete_result.deleted,
            index_entries_count=index_result.entries_count,
            released_resources=released + delete_result.released_resources,
        )

    def refresh(self, project_id: str) -> tuple[WorkspaceRecord, ...]:
        """Synchronize Project Database and return current workspaces."""

        clean_project_id = safe_project_id(project_id)
        self.index_manager.rebuild_project_index(clean_project_id)
        return self.list_workspaces(clean_project_id)

    def workspace_dir(self, project_id: str, workspace_id: str) -> Path:
        return self.root / safe_project_id(project_id) / "workspaces" / safe_workspace_id(workspace_id)

    def register_workspace_file(
        self,
        project_id: str,
        workspace_id: str,
        path: Path | str,
        *,
        owner: str = "WorkspaceService",
        description: str = "workspace file",
    ):
        clean_project_id = safe_project_id(project_id)
        clean_workspace_id = safe_workspace_id(workspace_id)
        resource_id = f"workspace:file:{clean_project_id}:{clean_workspace_id}:{Path(path).name}"
        return self.file_handle_manager.register_file(
            path,
            owner=owner,
            resource_id=resource_id,
            description=description,
        )

    def register_workspace_cache(
        self,
        project_id: str,
        workspace_id: str,
        *,
        key: str | None = None,
        description: str = "workspace cache",
    ):
        clean_project_id = safe_project_id(project_id)
        clean_workspace_id = safe_workspace_id(workspace_id)
        cache_key = key or f"workspace:cache:{clean_project_id}:{clean_workspace_id}"
        return self.cache_manager.register(
            cache_key,
            owner="WorkspaceService",
            path=self.workspace_dir(clean_project_id, clean_workspace_id),
            description=description,
        )

    def release_workspace_resources(self, project_id: str, workspace_id: str) -> int:
        workspace_path = self.workspace_dir(project_id, workspace_id)
        released = self.file_handle_manager.release_path(workspace_path)
        released += self.resource_manager.release_path(workspace_path)
        released += self.cache_manager.clear_path(workspace_path)
        return released

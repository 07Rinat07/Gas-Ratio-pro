from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from pathlib import Path

from core.storage_lifecycle import DeleteEngine, IndexManager, ResourceManager, DEFAULT_DELETE_ENGINE, DEFAULT_RESOURCE_MANAGER
from projects.exports import clear_project_exports
from projects.recent_projects import (
    clear_recent_projects,
    list_recent_projects,
    remove_recent_project,
    set_recent_project_flags,
    touch_recent_project,
)
from projects.project_manager import (
    ProjectRestoreResult,
    create_project_backup,
    restore_project_backup,
    save_project_recovery_state,
)
from projects.repository import (
    DEFAULT_PROJECT_ID,
    DEFAULT_PROJECTS_ROOT,
    ProjectRecord,
    create_project,
    delete_project,
    ensure_default_project,
    list_projects,
    load_project,
    safe_project_id,
)


@dataclass(frozen=True)
class ProjectCreateResult:
    """Result of a project creation workflow."""

    project: ProjectRecord
    touched_recent_history: bool

    def __getattr__(self, name: str) -> Any:
        return getattr(self.project, name)


@dataclass(frozen=True)
class ProjectBackupResult:
    """Result of a project backup workflow."""

    project_id: str
    backup_id: str
    file_name: str
    size_bytes: int


@dataclass(frozen=True)
class ProjectDeleteResult:
    """Result of a complete project deletion workflow."""

    project_id: str
    project_deleted: bool
    recent_history_removed: bool
    exports_removed: int
    fallback_project_id: str
    delete_result: Any | None = None

    @property
    def deleted(self) -> bool:
        return self.project_deleted


class ProjectManagerService:
    """High-level project manager used by UI/controllers.

    The Streamlit layer should not call low-level repository delete/cleanup
    functions directly. This service keeps project deletion, recent-history
    updates and related project cleanup in one place.
    """

    def __init__(
        self,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        default_project_id: str = DEFAULT_PROJECT_ID,
        *,
        resource_manager: ResourceManager | None = None,
        delete_engine: DeleteEngine | None = None,
        index_manager: IndexManager | None = None,
    ) -> None:
        self.root = Path(root)
        self.default_project_id = safe_project_id(default_project_id)
        self.resource_manager = resource_manager or DEFAULT_RESOURCE_MANAGER
        self.delete_engine = delete_engine or DEFAULT_DELETE_ENGINE
        self.index_manager = index_manager or IndexManager(self.root)

    def ensure_default(self) -> ProjectRecord:
        return ensure_default_project(self.root)

    def list_projects(self, *, include_archived: bool = False) -> tuple[ProjectRecord, ...]:
        """Return project records for UI/service consumers.

        The current repository model does not have archived projects yet, but
        older UI code and integration tests may already call this service with
        ``include_archived=...``. Keeping the keyword here makes the service a
        stable compatibility boundary while Project Archive support is finalized.
        """
        _ = include_archived
        default_project = self.ensure_default()
        projects = list_projects(self.root)
        return projects or (default_project,)

    def load_project(self, project_id: str) -> ProjectRecord:
        return load_project(self.root, safe_project_id(project_id))

    def get_project(self, project_id: str) -> ProjectRecord:
        """Compatibility alias for load_project()."""

        return self.load_project(project_id)

    def record_recent_project(self, project: ProjectRecord) -> None:
        """Compatibility alias for touch_recent()."""

        self.touch_recent(project)

    def list_recent_projects(self, *, include_missing: bool = True):
        """Compatibility alias for list_recent()."""

        return self.list_recent(include_missing=include_missing)

    def create_project(self, name: str, description: str = "") -> ProjectCreateResult:
        project = create_project(root=self.root, name=name, description=description)
        touch_recent_project(self.root, project)
        return ProjectCreateResult(project=project, touched_recent_history=True)

    def touch_recent(self, project: ProjectRecord) -> None:
        touch_recent_project(self.root, project)

    def list_recent(self, *, include_missing: bool = True):
        return list_recent_projects(self.root, include_missing=include_missing)

    def clear_recent_history(self) -> int:
        return clear_recent_projects(self.root)

    def remove_recent_entry(self, project_id: str) -> bool:
        return remove_recent_project(self.root, safe_project_id(project_id))

    def set_recent_flags(self, project_id: str, *, pinned: bool | None = None, favorite: bool | None = None):
        return set_recent_project_flags(self.root, safe_project_id(project_id), pinned=pinned, favorite=favorite)

    def create_backup(self, project_id: str, description: str = "") -> ProjectBackupResult:
        """Create a managed Project Manager 2.0 backup for a project."""
        clean_project_id = safe_project_id(project_id)
        record = create_project_backup(self.root, clean_project_id, description)
        return ProjectBackupResult(
            project_id=record.project_id,
            backup_id=record.id,
            file_name=record.file_name,
            size_bytes=record.size_bytes,
        )

    def restore_backup(self, backup_id: str, *, target_project_id: str | None = None, overwrite: bool = False) -> ProjectRestoreResult:
        """Restore a managed backup through the service boundary."""
        result = restore_project_backup(
            self.root,
            backup_id,
            target_project_id=target_project_id,
            overwrite=overwrite,
        )
        self.ensure_default()
        restored = self.load_project(result.project_id)
        self.touch_recent(restored)
        return result

    def save_recovery_checkpoint(self, project_id: str, active_step: str, message: str, payload: dict | None = None):
        """Save a metadata-only recovery checkpoint through the service layer."""
        return save_project_recovery_state(
            self.root,
            safe_project_id(project_id),
            active_step,
            message,
            payload or {},
        )

    def delete_project_complete(self, project_id: str) -> ProjectDeleteResult:
        """Delete a project and all managed project-scoped records.

        The default project is protected by the repository layer. Before the
        directory is removed, project-scoped manifests such as exports are
        cleared so the operation is explicit and testable. Deleting the project
        directory then removes the remaining LAS/reports/cache files stored
        under the project folder.
        """
        clean_project_id = safe_project_id(project_id)
        if clean_project_id == self.default_project_id:
            raise ValueError("Основной проект нельзя удалить.")

        exports_removed = clear_project_exports(self.root, clean_project_id)
        project_dir = self.root / clean_project_id
        delete_result = None
        if project_dir.exists():
            self.resource_manager.release_path(project_dir)
            delete_result = self.delete_engine.delete_path(project_dir, missing_ok=True)
            project_deleted = bool(delete_result.deleted)
        else:
            project_deleted = delete_project(self.root, clean_project_id)
        recent_history_removed = remove_recent_project(self.root, clean_project_id)
        self.ensure_default()

        return ProjectDeleteResult(
            project_id=clean_project_id,
            project_deleted=project_deleted,
            recent_history_removed=recent_history_removed,
            exports_removed=exports_removed,
            fallback_project_id=self.default_project_id,
            delete_result=delete_result,
        )


# Compatibility methods bound after class definition.
def _project_service_create(self, name: str, description: str = ""):
    return self.create_project(name, description)

def _project_service_list(self, *, include_archived: bool = False):
    return self.list_projects(include_archived=include_archived)

def _project_service_load(self, project_id: str):
    return self.load_project(project_id)

def _project_service_open_project(self, project_id: str):
    return self.load_project(project_id)

def _project_service_delete(self, project_id: str):
    return self.delete_project_complete(project_id)

def _project_service_rebuild_index(self, project_id: str):
    return self.index_manager.rebuild_project_index(safe_project_id(project_id))

@dataclass(frozen=True)
class ProjectServiceHealth:
    projects_count: int
    default_project_exists: bool

def _project_service_health(self):
    projects = self.list_projects()
    return ProjectServiceHealth(
        projects_count=len(projects),
        default_project_exists=any(project.id == self.default_project_id for project in projects),
    )

ProjectManagerService.create = _project_service_create
ProjectManagerService.list = _project_service_list
ProjectManagerService.load = _project_service_load
ProjectManagerService.open_project = _project_service_open_project
ProjectManagerService.delete = _project_service_delete
ProjectManagerService.rebuild_index = _project_service_rebuild_index
ProjectManagerService.health = _project_service_health
ProjectManagerService.delete_project = _project_service_delete

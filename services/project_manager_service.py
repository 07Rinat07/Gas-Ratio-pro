from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core.storage_lifecycle import (
    DEFAULT_CACHE_MANAGER,
    DEFAULT_DELETE_ENGINE,
    DEFAULT_RESOURCE_MANAGER,
    DeleteEngine,
    DeleteResult,
    IndexManager,
    IndexSyncResult,
    StorageDeleteError,
)
from projects.exports import list_project_exports
from projects.recent_projects import (
    RecentProjectEntry,
    clear_recent_projects,
    list_recent_projects,
    remove_recent_project,
    set_recent_project_flags,
    touch_recent_project,
)
from projects.repository import (
    DEFAULT_PROJECT_ID,
    DEFAULT_PROJECTS_ROOT,
    ProjectRecord,
    create_project,
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
    index_sync: IndexSyncResult | None = None


@dataclass(frozen=True)
class ProjectDeleteResult:
    """Result of a complete project deletion workflow."""

    project_id: str
    project_deleted: bool
    recent_history_removed: bool
    exports_removed: int
    fallback_project_id: str
    delete_result: DeleteResult | None = None
    fallback_index_sync: IndexSyncResult | None = None


@dataclass(frozen=True)
class ProjectRepositoryHealth:
    """Small compatibility DTO for UI/diagnostic panels."""

    projects_count: int
    recent_count: int
    default_project_exists: bool


class ProjectManagerService:
    """High-level project manager used by UI/controllers.

    Public compatibility contract:
    - project CRUD and selection helpers stay behind this service;
    - UI must not call low-level project repositories or filesystem removal;
    - destructive project operations go through Storage Lifecycle ``DeleteEngine``;
    - project index is synchronized after create/delete operations.
    """

    def __init__(
        self,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        default_project_id: str = DEFAULT_PROJECT_ID,
        *,
        delete_engine: DeleteEngine | None = None,
        index_manager: IndexManager | None = None,
    ) -> None:
        self.root = Path(root)
        self.default_project_id = safe_project_id(default_project_id)
        self.delete_engine = delete_engine or DEFAULT_DELETE_ENGINE
        self.index_manager = index_manager or IndexManager(self.root)

    @property
    def projects_root(self) -> Path:
        """Compatibility alias used by older UI/debug code."""

        return self.root

    def project_dir(self, project_id: str) -> Path:
        return self.root / safe_project_id(project_id)

    def ensure_default(self) -> ProjectRecord:
        project = ensure_default_project(self.root)
        self._sync_index_if_possible(project.id)
        return project

    # Compatibility alias.
    ensure_default_project = ensure_default

    def list_projects(self, *, include_archived: bool = False) -> tuple[ProjectRecord, ...]:
        """Return project records for UI/service consumers.

        ``include_archived`` is retained as a stable keyword while archive
        support is still represented outside the minimal project repository.
        """

        _ = include_archived
        default_project = self.ensure_default()
        projects = list_projects(self.root)
        return projects or (default_project,)

    # Compatibility alias.
    list = list_projects

    def count_projects(self, *, include_archived: bool = False) -> int:
        return len(self.list_projects(include_archived=include_archived))

    def load_project(self, project_id: str) -> ProjectRecord:
        return load_project(self.root, safe_project_id(project_id))

    # Compatibility aliases.
    load = load_project
    open_project = load_project

    def create_project(self, name: str, description: str = "", project_id: str | None = None) -> ProjectCreateResult:
        project = create_project(root=self.root, name=name, description=description, project_id=project_id)
        touch_recent_project(self.root, project)
        index_sync = self._sync_index_if_possible(project.id)
        return ProjectCreateResult(project=project, touched_recent_history=True, index_sync=index_sync)

    # Compatibility alias.
    create = create_project

    def touch_recent(self, project: ProjectRecord) -> RecentProjectEntry:
        return touch_recent_project(self.root, project)

    def list_recent(self, *, include_missing: bool = True) -> tuple[RecentProjectEntry, ...]:
        return list_recent_projects(self.root, include_missing=include_missing)

    def clear_recent_history(self) -> int:
        return clear_recent_projects(self.root)

    def remove_recent_entry(self, project_id: str) -> bool:
        return remove_recent_project(self.root, safe_project_id(project_id))

    def set_recent_flags(self, project_id: str, *, pinned: bool | None = None, favorite: bool | None = None) -> RecentProjectEntry:
        return set_recent_project_flags(self.root, safe_project_id(project_id), pinned=pinned, favorite=favorite)

    def list_project_exports(self, project_id: str):
        """Compatibility helper for project diagnostics before full Export pass."""

        return list_project_exports(self.root, safe_project_id(project_id))

    def delete_project_complete(self, project_id: str) -> ProjectDeleteResult:
        """Delete a project through Storage Lifecycle and clean related UI state.

        This method intentionally does not call ``projects.repository.delete_project``
        because that repository performs a raw ``shutil.rmtree``. The service is
        now the compatibility boundary that enforces lifecycle-managed deletion.
        """

        clean_project_id = safe_project_id(project_id)
        if clean_project_id == self.default_project_id:
            raise ValueError("Основной проект нельзя удалить.")

        project_dir = self.project_dir(clean_project_id)
        exports_removed = len(list_project_exports(self.root, clean_project_id))
        delete_result = self.delete_engine.delete_path(project_dir, missing_ok=True)
        recent_history_removed = remove_recent_project(self.root, clean_project_id)
        self.ensure_default()
        fallback_index_sync = self._sync_index_if_possible(self.default_project_id)

        return ProjectDeleteResult(
            project_id=clean_project_id,
            project_deleted=delete_result.deleted,
            recent_history_removed=recent_history_removed,
            exports_removed=exports_removed,
            fallback_project_id=self.default_project_id,
            delete_result=delete_result,
            fallback_index_sync=fallback_index_sync,
        )

    # Compatibility aliases.
    delete_project = delete_project_complete
    delete = delete_project_complete
    remove_project = delete_project_complete

    def rebuild_index(self, project_id: str) -> IndexSyncResult:
        return self.index_manager.rebuild_project_index(safe_project_id(project_id))

    def validate_index(self, project_id: str) -> IndexSyncResult:
        return self.index_manager.validate_project_index(safe_project_id(project_id))

    def sync_indexes(self, project_ids: Iterable[str] | None = None) -> tuple[IndexSyncResult, ...]:
        ids = tuple(safe_project_id(project_id) for project_id in project_ids) if project_ids is not None else tuple(
            project.id for project in self.list_projects()
        )
        results: list[IndexSyncResult] = []
        for project_id in ids:
            sync = self._sync_index_if_possible(project_id)
            if sync is not None:
                results.append(sync)
        return tuple(results)

    def health(self) -> ProjectRepositoryHealth:
        projects = self.list_projects()
        recent = self.list_recent(include_missing=True)
        return ProjectRepositoryHealth(
            projects_count=len(projects),
            recent_count=len(recent),
            default_project_exists=any(project.id == self.default_project_id for project in projects),
        )

    def _sync_index_if_possible(self, project_id: str) -> IndexSyncResult | None:
        try:
            return self.index_manager.rebuild_project_index(safe_project_id(project_id))
        except (FileNotFoundError, OSError, ValueError, StorageDeleteError):
            return None

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from projects.exports import clear_project_exports
from projects.recent_projects import (
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


@dataclass(frozen=True)
class ProjectDeleteResult:
    """Result of a complete project deletion workflow."""

    project_id: str
    project_deleted: bool
    recent_history_removed: bool
    exports_removed: int
    fallback_project_id: str


class ProjectManagerService:
    """High-level project manager used by UI/controllers.

    The Streamlit layer should not call low-level repository delete/cleanup
    functions directly. This service keeps project deletion, recent-history
    updates and related project cleanup in one place.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT, default_project_id: str = DEFAULT_PROJECT_ID) -> None:
        self.root = Path(root)
        self.default_project_id = safe_project_id(default_project_id)

    def ensure_default(self) -> ProjectRecord:
        return ensure_default_project(self.root)

    def list_projects(self) -> tuple[ProjectRecord, ...]:
        default_project = self.ensure_default()
        projects = list_projects(self.root)
        return projects or (default_project,)

    def load_project(self, project_id: str) -> ProjectRecord:
        return load_project(self.root, safe_project_id(project_id))

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
        project_deleted = delete_project(self.root, clean_project_id)
        recent_history_removed = remove_recent_project(self.root, clean_project_id)
        self.ensure_default()

        return ProjectDeleteResult(
            project_id=clean_project_id,
            project_deleted=project_deleted,
            recent_history_removed=recent_history_removed,
            exports_removed=exports_removed,
            fallback_project_id=self.default_project_id,
        )

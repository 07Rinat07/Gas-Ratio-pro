from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from projects.repository import (
    DEFAULT_PROJECT_ID,
    DEFAULT_PROJECTS_ROOT,
    ProjectRecord,
    create_project,
    delete_project,
    ensure_default_project,
    list_projects,
    load_project,
)


@dataclass(frozen=True)
class ProjectDeleteResult:
    project_id: str
    deleted: bool
    fallback_project_id: str = DEFAULT_PROJECT_ID


class ProjectManagerService:
    """Application service for project lifecycle operations.

    UI code must call this service instead of calling project repository helpers
    directly.  The service keeps project operations centralized and makes it
    possible to add cross-cutting cleanup, journaling and events later without
    changing every Streamlit panel.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)

    def ensure_default(self) -> ProjectRecord:
        return ensure_default_project(self.root)

    def list_projects(self) -> tuple[ProjectRecord, ...]:
        default_project = self.ensure_default()
        projects = list_projects(self.root)
        return projects or (default_project,)

    def get_project(self, project_id: str) -> ProjectRecord:
        return load_project(self.root, project_id)

    def create_project(self, name: str, description: str = "") -> ProjectRecord:
        return create_project(self.root, name=name, description=description)

    def delete_project(self, project_id: str) -> ProjectDeleteResult:
        deleted = delete_project(self.root, project_id)
        self.ensure_default()
        return ProjectDeleteResult(project_id=project_id, deleted=deleted)

    def choose_existing_project_id(self, requested_project_id: str | None) -> str:
        projects = self.list_projects()
        project_ids = {project.id for project in projects}
        if requested_project_id and requested_project_id in project_ids:
            return requested_project_id
        if DEFAULT_PROJECT_ID in project_ids:
            return DEFAULT_PROJECT_ID
        return projects[0].id

"""Project-scoped application boundary for LAS persistence workflows."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from services.las_manager_service import LasManagerService
from las_correlation.settings import LasCorrelationSettings
from las_correlation.settings_store import (
    load_project_correlation_settings,
    save_project_correlation_settings,
)


class LasWorkspaceApplicationService:
    """Expose LAS operations for exactly one project.

    The bound project id prevents accidental cross-project mutations and keeps
    UI code from constructing storage/repository infrastructure directly.
    """

    def __init__(self, *, root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)
        self._manager = LasManagerService(self.root)

    def list_files(self, *, include_archived: bool = False):
        return self._manager.list_files(self.project_id, include_archived=include_archived)

    def list_wells(self, *, include_archived: bool = False):
        return self._manager.list_wells(self.project_id, include_archived=include_archived)

    def save_file(self, *, data: bytes, file_name: str = "source.las", well_name: str = "", version_label: str = "Исходный LAS", metadata: dict[str, Any] | None = None):
        return self._manager.save_file(project_id=self.project_id, data=data, file_name=file_name, well_name=well_name, version_label=version_label, metadata=metadata)

    def archive_file(self, las_file_id: str):
        return self._manager.archive_file(self.project_id, las_file_id)

    def restore_file(self, las_file_id: str):
        return self._manager.restore_file(self.project_id, las_file_id)

    def delete_file(self, las_file_id: str):
        return self._manager.delete_file(self.project_id, las_file_id)

    def clear_files(self, *, include_archived: bool = True):
        return self._manager.clear_files(self.project_id, include_archived=include_archived)

    def refresh(self):
        return self._manager.refresh(self.project_id)

    def read_bytes(self, las_file_id: str) -> bytes:
        return self._manager.read_bytes(self.project_id, las_file_id)

    def read_dataframe(self, las_file_id: str):
        return self._manager.read_dataframe(self.project_id, las_file_id)

    def export_zip(self, las_file_ids, formats=("LAS", "CSV", "XLSX")) -> bytes:
        return self._manager.export_zip(self.project_id, las_file_ids, formats=formats)


    def load_correlation_settings(self) -> LasCorrelationSettings | None:
        """Load project-scoped LAS correlation settings through the application boundary."""
        return load_project_correlation_settings(root=self.root, project_id=self.project_id)

    def save_correlation_settings(self, settings: LasCorrelationSettings):
        """Persist project-scoped LAS correlation settings through the application boundary."""
        if not isinstance(settings, LasCorrelationSettings):
            raise TypeError("settings must be LasCorrelationSettings")
        return save_project_correlation_settings(
            settings, root=self.root, project_id=self.project_id
        )

    def health_snapshot(self) -> dict[str, Any]:
        return {"service": type(self).__name__, "project_id": self.project_id, "root": str(self.root.resolve()), "files": len(self.list_files(include_archived=True))}

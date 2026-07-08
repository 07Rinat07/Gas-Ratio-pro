from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from projects.exports import (
    ProjectExportRecord,
    clear_project_exports,
    delete_project_export,
    list_project_exports,
    read_project_export_file_bytes,
    save_project_export,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id


@dataclass(frozen=True)
class ExportSaveResult:
    """Result of saving one project export through the service layer."""

    record: ProjectExportRecord


@dataclass(frozen=True)
class ExportDeleteResult:
    """Result of deleting one export from project storage."""

    project_id: str
    export_id: str
    deleted: bool


@dataclass(frozen=True)
class ExportClearResult:
    """Result of clearing all exports from one project."""

    project_id: str
    removed_count: int


class ExportManagerService:
    """High-level export manager used by UI/controllers.

    The Streamlit UI must not manipulate export manifests or export folders
    directly. This service keeps listing, saving, reading and deletion of
    project exports behind one stable API.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)

    def list_exports(self, project_id: str) -> tuple[ProjectExportRecord, ...]:
        return list_project_exports(self.root, safe_project_id(project_id))

    def count_exports(self, project_id: str) -> int:
        return len(self.list_exports(project_id))

    def read_export_bytes(self, project_id: str, export_id: str) -> bytes:
        return read_project_export_file_bytes(self.root, safe_project_id(project_id), export_id)

    def save_export(
        self,
        *,
        project_id: str,
        data: bytes,
        label: str,
        file_name: str,
        mime_type: str,
        kind: str,
        source: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ExportSaveResult:
        record = save_project_export(
            data,
            root=self.root,
            project_id=safe_project_id(project_id),
            label=label,
            file_name=file_name,
            mime_type=mime_type,
            kind=kind,
            source=source,
            metadata=metadata,
        )
        return ExportSaveResult(record=record)

    def delete_export(self, project_id: str, export_id: str) -> ExportDeleteResult:
        clean_project_id = safe_project_id(project_id)
        deleted = delete_project_export(self.root, clean_project_id, export_id)
        return ExportDeleteResult(project_id=clean_project_id, export_id=export_id, deleted=deleted)

    def clear_exports(self, project_id: str) -> ExportClearResult:
        clean_project_id = safe_project_id(project_id)
        removed = clear_project_exports(self.root, clean_project_id)
        return ExportClearResult(project_id=clean_project_id, removed_count=removed)

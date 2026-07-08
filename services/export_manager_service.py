from __future__ import annotations

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
from projects.repository import DEFAULT_PROJECTS_ROOT


class ExportManagerService:
    """Application service for project export records and files."""

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)

    def list_exports(self, project_id: str) -> tuple[ProjectExportRecord, ...]:
        return list_project_exports(self.root, project_id)

    def read_export_bytes(self, project_id: str, export_id: str) -> bytes:
        return read_project_export_file_bytes(self.root, project_id, export_id)

    def save_export(
        self,
        *,
        project_id: str,
        data: bytes,
        label: str = "Экспорт",
        file_name: str = "export.bin",
        mime_type: str = "application/octet-stream",
        kind: str = "",
        source: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ProjectExportRecord:
        return save_project_export(
            data,
            root=self.root,
            project_id=project_id,
            label=label,
            file_name=file_name,
            mime_type=mime_type,
            kind=kind,
            source=source,
            metadata=metadata,
        )

    def delete_export(self, project_id: str, export_id: str) -> bool:
        return delete_project_export(self.root, project_id, export_id)

    def clear_exports(self, project_id: str) -> int:
        return clear_project_exports(self.root, project_id)

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from projects.las_files import (
    ProjectLasFile,
    ProjectLasWellCard,
    clear_project_las_files,
    delete_project_las_file,
    export_project_las_files_zip,
    list_project_las_files,
    list_project_las_wells,
    read_project_las_file_bytes,
    read_project_las_file_dataframe,
    save_project_las_file,
    set_project_las_file_archived,
)
from projects.repository import DEFAULT_PROJECTS_ROOT


class LasManagerService:
    """Application service for project LAS versions."""

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)

    def list_las_files(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasFile, ...]:
        return list_project_las_files(self.root, project_id, include_archived=include_archived)

    def list_las_wells(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasWellCard, ...]:
        return list_project_las_wells(self.root, project_id, include_archived=include_archived)

    def save_las_file(
        self,
        *,
        project_id: str,
        data: bytes,
        file_name: str = "source.las",
        well_name: str = "",
        version_label: str = "Исходный LAS",
        metadata: dict[str, Any] | None = None,
    ) -> ProjectLasFile:
        return save_project_las_file(
            data,
            root=self.root,
            project_id=project_id,
            file_name=file_name,
            well_name=well_name,
            version_label=version_label,
            metadata=metadata,
        )

    def archive_las_file(self, project_id: str, las_file_id: str, *, archived: bool = True) -> ProjectLasFile:
        return set_project_las_file_archived(self.root, project_id, las_file_id, archived=archived)

    def delete_las_file(self, project_id: str, las_file_id: str) -> bool:
        return delete_project_las_file(self.root, project_id, las_file_id)

    def clear_las_files(self, project_id: str) -> int:
        return clear_project_las_files(self.root, project_id)

    def read_las_bytes(self, project_id: str, las_file_id: str) -> bytes:
        return read_project_las_file_bytes(self.root, project_id, las_file_id)

    def read_las_dataframe(self, project_id: str, las_file_id: str) -> pd.DataFrame:
        return read_project_las_file_dataframe(self.root, project_id, las_file_id)

    def export_las_zip(self, project_id: str, las_file_ids: tuple[str, ...] | list[str], formats: tuple[str, ...] | list[str]) -> bytes:
        return export_project_las_files_zip(self.root, project_id, las_file_ids, formats=formats)

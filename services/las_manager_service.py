from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from projects.las_files import (
    PROJECT_LAS_EXPORT_FORMATS,
    ProjectLasFile,
    ProjectLasWellCard,
    delete_project_las_file,
    export_project_las_files_zip,
    list_project_las_files,
    list_project_las_wells,
    read_project_las_file_bytes,
    read_project_las_file_dataframe,
    save_project_las_file,
    set_project_las_file_archived,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id


@dataclass(frozen=True)
class LasSaveResult:
    """Result of saving one LAS file into an active project."""

    record: ProjectLasFile


@dataclass(frozen=True)
class LasArchiveResult:
    """Result of changing an archive flag for one project LAS version."""

    project_id: str
    las_file_id: str
    archived: bool
    record: ProjectLasFile


@dataclass(frozen=True)
class LasDeleteResult:
    """Result of physically deleting one project LAS version."""

    project_id: str
    las_file_id: str
    deleted: bool


@dataclass(frozen=True)
class LasExportZipResult:
    """Result of exporting selected project LAS versions to a ZIP archive."""

    project_id: str
    las_file_ids: tuple[str, ...]
    formats: tuple[str, ...]
    data: bytes


class LasManagerService:
    """High-level LAS manager for project-scoped LAS files.

    Streamlit UI should not read/write the project LAS manifest directly and
    should not physically delete LAS folders. This service centralizes project
    LAS listing, saving, archiving, restoring, deletion, reading and ZIP export.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)

    def list_files(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasFile, ...]:
        return list_project_las_files(self.root, safe_project_id(project_id), include_archived=include_archived)

    def list_wells(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasWellCard, ...]:
        return list_project_las_wells(self.root, safe_project_id(project_id), include_archived=include_archived)

    def count_files(self, project_id: str, *, include_archived: bool = False) -> int:
        return len(self.list_files(project_id, include_archived=include_archived))

    def save_file(
        self,
        *,
        project_id: str,
        data: bytes,
        file_name: str = "source.las",
        well_name: str = "",
        version_label: str = "Исходный LAS",
        metadata: dict[str, Any] | None = None,
    ) -> LasSaveResult:
        record = save_project_las_file(
            data=data,
            root=self.root,
            project_id=safe_project_id(project_id),
            file_name=file_name,
            well_name=well_name,
            version_label=version_label,
            metadata=metadata,
        )
        return LasSaveResult(record=record)

    def archive_file(self, project_id: str, las_file_id: str) -> LasArchiveResult:
        clean_project_id = safe_project_id(project_id)
        record = set_project_las_file_archived(self.root, clean_project_id, las_file_id, archived=True)
        return LasArchiveResult(project_id=clean_project_id, las_file_id=las_file_id, archived=True, record=record)

    def restore_file(self, project_id: str, las_file_id: str) -> LasArchiveResult:
        clean_project_id = safe_project_id(project_id)
        record = set_project_las_file_archived(self.root, clean_project_id, las_file_id, archived=False)
        return LasArchiveResult(project_id=clean_project_id, las_file_id=las_file_id, archived=False, record=record)

    def delete_file(self, project_id: str, las_file_id: str) -> LasDeleteResult:
        clean_project_id = safe_project_id(project_id)
        deleted = delete_project_las_file(self.root, clean_project_id, las_file_id)
        return LasDeleteResult(project_id=clean_project_id, las_file_id=las_file_id, deleted=deleted)

    def read_file_bytes(self, project_id: str, las_file_id: str) -> bytes:
        return read_project_las_file_bytes(self.root, safe_project_id(project_id), las_file_id)

    def read_dataframe(self, project_id: str, las_file_id: str) -> pd.DataFrame:
        return read_project_las_file_dataframe(self.root, safe_project_id(project_id), las_file_id)

    def export_zip(
        self,
        project_id: str,
        las_file_ids: tuple[str, ...] | list[str],
        formats: tuple[str, ...] | list[str] = PROJECT_LAS_EXPORT_FORMATS,
    ) -> LasExportZipResult:
        clean_project_id = safe_project_id(project_id)
        selected_ids = tuple(dict.fromkeys(str(item) for item in las_file_ids if str(item)))
        selected_formats = tuple(dict.fromkeys(str(item).lower() for item in formats if str(item)))
        data = export_project_las_files_zip(self.root, clean_project_id, selected_ids, selected_formats)
        return LasExportZipResult(
            project_id=clean_project_id,
            las_file_ids=selected_ids,
            formats=selected_formats,
            data=data,
        )

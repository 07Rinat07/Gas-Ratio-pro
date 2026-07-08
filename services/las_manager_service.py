from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    """Result of saving a LAS file into project storage."""

    record: ProjectLasFile


@dataclass(frozen=True)
class LasDeleteResult:
    """Result of a physical LAS delete operation."""

    project_id: str
    las_file_id: str
    deleted: bool


@dataclass(frozen=True)
class LasArchiveResult:
    """Result of changing archive state for a LAS version."""

    project_id: str
    las_file_id: str
    archived: bool
    record: ProjectLasFile


@dataclass(frozen=True)
class LasClearResult:
    """Result of clearing all LAS versions from a project."""

    project_id: str
    deleted_count: int


class LasManagerService:
    """High-level service for project LAS versions.

    UI code should use this service instead of calling ``projects.las_files``
    functions directly.  This keeps all project LAS operations on the same
    service-layer path as Project/Well/Export management.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)

    def list_files(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasFile, ...]:
        return list_project_las_files(self.root, safe_project_id(project_id), include_archived=include_archived)

    def list_wells(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasWellCard, ...]:
        return list_project_las_wells(self.root, safe_project_id(project_id), include_archived=include_archived)

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
        record = set_project_las_file_archived(self.root, safe_project_id(project_id), las_file_id, archived=True)
        return LasArchiveResult(project_id=safe_project_id(project_id), las_file_id=las_file_id, archived=True, record=record)

    def restore_file(self, project_id: str, las_file_id: str) -> LasArchiveResult:
        record = set_project_las_file_archived(self.root, safe_project_id(project_id), las_file_id, archived=False)
        return LasArchiveResult(project_id=safe_project_id(project_id), las_file_id=las_file_id, archived=False, record=record)

    def delete_file(self, project_id: str, las_file_id: str) -> LasDeleteResult:
        clean_project_id = safe_project_id(project_id)
        deleted = delete_project_las_file(self.root, clean_project_id, las_file_id)
        return LasDeleteResult(project_id=clean_project_id, las_file_id=las_file_id, deleted=deleted)

    def clear_files(self, project_id: str, *, include_archived: bool = True) -> LasClearResult:
        clean_project_id = safe_project_id(project_id)
        records = self.list_files(clean_project_id, include_archived=include_archived)
        deleted_count = 0
        for record in records:
            if delete_project_las_file(self.root, clean_project_id, record.id):
                deleted_count += 1
        return LasClearResult(project_id=clean_project_id, deleted_count=deleted_count)

    def read_bytes(self, project_id: str, las_file_id: str) -> bytes:
        return read_project_las_file_bytes(self.root, safe_project_id(project_id), las_file_id)

    def read_dataframe(self, project_id: str, las_file_id: str):
        return read_project_las_file_dataframe(self.root, safe_project_id(project_id), las_file_id)

    def export_zip(
        self,
        project_id: str,
        las_file_ids: tuple[str, ...] | list[str],
        formats: tuple[str, ...] | list[str] = PROJECT_LAS_EXPORT_FORMATS,
    ) -> bytes:
        return export_project_las_files_zip(self.root, safe_project_id(project_id), las_file_ids, formats=formats)

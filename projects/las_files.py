from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from importers.las_importer import read_las
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from reports.export_csv import export_csv_bytes
from reports.export_xlsx import export_xlsx_bytes


PROJECT_WELLS_DIR_NAME = "wells"
PROJECT_LAS_MANIFEST_FILE_NAME = "las_files.json"
PROJECT_LAS_SOURCE_FILE_NAME = "source.las"
PROJECT_LAS_FILES_SCHEMA_VERSION = 3
PROJECT_LAS_EXPORT_FORMATS = ("las", "xlsx", "csv")


@dataclass(frozen=True)
class ProjectLasFile:
    id: str
    name: str
    original_file_name: str
    saved_at: str
    size_bytes: int
    well_id: str = ""
    version_label: str = ""
    archived_at: str = ""
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProjectLasWellCard:
    id: str
    name: str
    updated_at: str
    versions: tuple[ProjectLasFile, ...]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "las"


def _safe_las_file_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор LAS-файла проекта.")
    return value


def _safe_export_stem(value: str) -> str:
    stem = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "_", value.strip()).strip("_")
    return stem or "project_las"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _project_wells_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_WELLS_DIR_NAME


def _manifest_path(root: Path | str, project_id: str) -> Path:
    return _project_wells_dir(root, project_id) / PROJECT_LAS_MANIFEST_FILE_NAME


def _las_file_dir(root: Path | str, project_id: str, las_file_id: str) -> Path:
    return _project_wells_dir(root, project_id) / _safe_las_file_id(las_file_id)


def _record_from_dict(raw: dict[str, Any]) -> ProjectLasFile:
    name = str(raw.get("name", "")) or "Без названия"
    original_file_name = str(raw.get("original_file_name", "")) or "source.las"
    saved_at = str(raw.get("saved_at", ""))
    well_id = str(raw.get("well_id", "")) or _slugify(name)
    version_label = str(raw.get("version_label", "")) or "Исходный LAS"
    return ProjectLasFile(
        id=str(raw.get("id", "")),
        name=name,
        original_file_name=original_file_name,
        saved_at=saved_at,
        size_bytes=int(raw.get("size_bytes", 0) or 0),
        well_id=well_id,
        version_label=version_label,
        archived_at=str(raw.get("archived_at", "")),
        metadata=dict(raw.get("metadata", {}) or {}),
    )


def _record_to_dict(record: ProjectLasFile) -> dict[str, Any]:
    return {
        "id": record.id,
        "well_id": record.well_id or _slugify(record.name),
        "name": record.name,
        "version_label": record.version_label or "Исходный LAS",
        "original_file_name": record.original_file_name,
        "saved_at": record.saved_at,
        "size_bytes": record.size_bytes,
        "archived_at": record.archived_at,
        "metadata": dict(record.metadata or {}),
    }


def _read_manifest(root: Path | str, project_id: str) -> tuple[ProjectLasFile, ...]:
    path = _manifest_path(root, project_id)
    if not path.exists():
        return ()

    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("las_files", ()) if isinstance(payload, dict) else ()
    return tuple(_record_from_dict(record) for record in records)


def _write_manifest(root: Path | str, project_id: str, records: tuple[ProjectLasFile, ...]) -> Path:
    path = _manifest_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_LAS_FILES_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "las_files": [_record_to_dict(record) for record in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_project_las_files(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectLasFile, ...]:
    try:
        records = _read_manifest(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()
    if not include_archived:
        records = tuple(record for record in records if not record.archived_at)
    return tuple(sorted(records, key=lambda record: record.saved_at, reverse=True))


def list_project_las_wells(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectLasWellCard, ...]:
    grouped: dict[str, list[ProjectLasFile]] = {}
    for record in list_project_las_files(root, project_id, include_archived=include_archived):
        grouped.setdefault(record.well_id or _slugify(record.name), []).append(record)

    cards: list[ProjectLasWellCard] = []
    for well_id, versions in grouped.items():
        sorted_versions = tuple(sorted(versions, key=lambda record: record.saved_at, reverse=True))
        latest = next((record for record in sorted_versions if not record.archived_at), sorted_versions[0])
        cards.append(
            ProjectLasWellCard(
                id=well_id,
                name=latest.name,
                updated_at=latest.saved_at,
                versions=sorted_versions,
            )
        )
    return tuple(sorted(cards, key=lambda card: card.updated_at, reverse=True))


def save_project_las_file(
    data: bytes,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    file_name: str = "source.las",
    well_name: str = "",
    version_label: str = "Исходный LAS",
    metadata: dict[str, Any] | None = None,
) -> ProjectLasFile:
    if not data:
        raise ValueError("Нет данных LAS для сохранения в проект.")

    safe_original_name = Path(str(file_name)).name or "source.las"
    clean_well_name = well_name.strip() or Path(safe_original_name).stem or "LAS"
    clean_version_label = version_label.strip() or "Исходный LAS"
    well_id = _slugify(clean_well_name)
    now = _utc_now()
    base_id = f"{now[:10].replace('-', '')}-{well_id}-{_slugify(clean_version_label)}"
    las_file_id = base_id
    counter = 2
    while _las_file_dir(root, project_id, las_file_id).exists():
        las_file_id = f"{base_id}-{counter}"
        counter += 1

    las_dir = _las_file_dir(root, project_id, las_file_id)
    las_dir.mkdir(parents=True, exist_ok=True)
    (las_dir / PROJECT_LAS_SOURCE_FILE_NAME).write_bytes(data)

    record = ProjectLasFile(
        id=las_file_id,
        well_id=well_id,
        name=clean_well_name,
        version_label=clean_version_label,
        original_file_name=safe_original_name,
        saved_at=now,
        size_bytes=len(data),
        metadata=metadata or {},
    )
    records = (record, *tuple(item for item in _read_manifest(root, project_id) if item.id != record.id))
    _write_manifest(root, project_id, records)
    return record


def set_project_las_file_archived(
    root: Path | str,
    project_id: str,
    las_file_id: str,
    archived: bool = True,
) -> ProjectLasFile:
    _safe_las_file_id(las_file_id)
    records = list(_read_manifest(root, project_id))
    updated_records: list[ProjectLasFile] = []
    updated_record: ProjectLasFile | None = None
    archived_at = _utc_now() if archived else ""

    for record in records:
        if record.id == las_file_id:
            updated_record = ProjectLasFile(
                id=record.id,
                name=record.name,
                original_file_name=record.original_file_name,
                saved_at=record.saved_at,
                size_bytes=record.size_bytes,
                well_id=record.well_id,
                version_label=record.version_label,
                archived_at=archived_at,
                metadata=record.metadata,
            )
            updated_records.append(updated_record)
        else:
            updated_records.append(record)

    if updated_record is None:
        raise FileNotFoundError(f"Project LAS file not found: {las_file_id}")

    _write_manifest(root, project_id, tuple(updated_records))
    return updated_record


def delete_project_las_file(
    root: Path | str,
    project_id: str,
    las_file_id: str,
) -> bool:
    """Physically delete one LAS version from a project.

    This is different from archiving: the record is removed from the project
    LAS manifest and the corresponding data directory is deleted from disk.
    """
    clean_las_file_id = _safe_las_file_id(las_file_id)
    records = tuple(_read_manifest(root, project_id))
    remaining = tuple(record for record in records if record.id != clean_las_file_id)
    if len(remaining) == len(records):
        return False

    las_dir = _las_file_dir(root, project_id, clean_las_file_id)
    if las_dir.exists():
        import shutil

        shutil.rmtree(las_dir)
    _write_manifest(root, project_id, remaining)
    return True



def delete_all_project_las_files(
    root: Path | str,
    project_id: str,
) -> int:
    """Physically delete every LAS version from a project and reset its manifest.

    This removes both active and archived LAS entries. It is used by the UI
    when the user wants to clean the project/correlation workspace completely,
    not just hide records from the current Streamlit session.
    """
    records = tuple(_read_manifest(root, project_id))
    wells_dir = _project_wells_dir(root, project_id)
    deleted_count = 0

    for record in records:
        las_dir = _las_file_dir(root, project_id, record.id)
        if las_dir.exists():
            import shutil

            shutil.rmtree(las_dir)
        deleted_count += 1

    _write_manifest(root, project_id, ())

    # Remove empty well/LAS directories left after deleting the records, but keep
    # the project itself and its manifest path valid for future imports.
    for child in tuple(wells_dir.iterdir()) if wells_dir.exists() else ():
        if child.name == PROJECT_LAS_MANIFEST_FILE_NAME:
            continue
        if child.is_dir():
            import shutil

            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)

    return deleted_count

def read_project_las_file_bytes(
    root: Path | str,
    project_id: str,
    las_file_id: str,
) -> bytes:
    records = {record.id: record for record in list_project_las_files(root, project_id, include_archived=True)}
    if las_file_id not in records:
        raise FileNotFoundError(f"Project LAS file not found: {las_file_id}")
    return (_las_file_dir(root, project_id, las_file_id) / PROJECT_LAS_SOURCE_FILE_NAME).read_bytes()


def read_project_las_file_dataframe(
    root: Path | str,
    project_id: str,
    las_file_id: str,
) -> pd.DataFrame:
    return read_las(BytesIO(read_project_las_file_bytes(root, project_id, las_file_id)))


def export_project_las_files_zip(
    root: Path | str,
    project_id: str,
    las_file_ids: tuple[str, ...] | list[str],
    formats: tuple[str, ...] | list[str] = PROJECT_LAS_EXPORT_FORMATS,
) -> bytes:
    selected_ids = tuple(
        dict.fromkeys(str(las_file_id) for las_file_id in las_file_ids if str(las_file_id))
    )
    if not selected_ids:
        raise ValueError("Не выбраны LAS-версии проекта для выгрузки.")

    selected_formats = tuple(dict.fromkeys(format_name.lower() for format_name in formats if format_name))
    unsupported_formats = tuple(
        format_name for format_name in selected_formats if format_name not in PROJECT_LAS_EXPORT_FORMATS
    )
    if unsupported_formats:
        raise ValueError("Неподдерживаемый формат выгрузки: " + ", ".join(unsupported_formats))

    records_by_id = {
        record.id: record
        for record in list_project_las_files(root, project_id, include_archived=True)
    }
    missing_ids = tuple(las_file_id for las_file_id in selected_ids if las_file_id not in records_by_id)
    if missing_ids:
        raise FileNotFoundError("Project LAS file not found: " + ", ".join(missing_ids))

    exported_at = _utc_now()
    manifest_entries: list[dict[str, Any]] = []

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for las_file_id in selected_ids:
            record = records_by_id[las_file_id]
            las_bytes = read_project_las_file_bytes(root, project_id, record.id)
            file_stem = _safe_export_stem(f"{record.name}_{record.version_label}_{record.id}")
            dataframe: pd.DataFrame | None = None
            exported_files: list[dict[str, Any]] = []

            if "las" in selected_formats:
                file_name = f"{file_stem}.las"
                archive.writestr(file_name, las_bytes)
                exported_files.append(
                    {
                        "name": file_name,
                        "format": "las",
                        "size_bytes": len(las_bytes),
                        "sha256": _sha256_hex(las_bytes),
                    }
                )
            if "csv" in selected_formats or "xlsx" in selected_formats:
                dataframe = read_las(BytesIO(las_bytes))
            if "csv" in selected_formats and dataframe is not None:
                file_name = f"{file_stem}.csv"
                csv_bytes = export_csv_bytes(dataframe)
                archive.writestr(file_name, csv_bytes)
                exported_files.append(
                    {
                        "name": file_name,
                        "format": "csv",
                        "size_bytes": len(csv_bytes),
                        "sha256": _sha256_hex(csv_bytes),
                    }
                )
            if "xlsx" in selected_formats and dataframe is not None:
                file_name = f"{file_stem}.xlsx"
                xlsx_bytes = export_xlsx_bytes(dataframe, sheet_name=record.name)
                archive.writestr(file_name, xlsx_bytes)
                exported_files.append(
                    {
                        "name": file_name,
                        "format": "xlsx",
                        "size_bytes": len(xlsx_bytes),
                        "sha256": _sha256_hex(xlsx_bytes),
                    }
                )

            manifest_entries.append(
                {
                    "id": record.id,
                    "well_id": record.well_id,
                    "well_name": record.name,
                    "version_label": record.version_label,
                    "original_file_name": record.original_file_name,
                    "saved_at": record.saved_at,
                    "archived_at": record.archived_at,
                    "size_bytes": record.size_bytes,
                    "exported_files": exported_files,
                    "metadata": dict(record.metadata or {}),
                }
            )

        manifest = {
            "schema_version": 1,
            "project_id": safe_project_id(project_id),
            "exported_at": exported_at,
            "formats": list(selected_formats),
            "las_files": manifest_entries,
        }
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr(
            "README.txt",
            "Project LAS export\n"
            f"Project: {safe_project_id(project_id)}\n"
            f"Exported at: {exported_at}\n"
            "\n"
            "The archive contains selected LAS versions and converted CSV/XLSX files. "
            "Use manifest.json to check well names, version labels, original file names, "
            "archive status, exported file names, file sizes and SHA-256 checksums.\n",
        )

    return buffer.getvalue()


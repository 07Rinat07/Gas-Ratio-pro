from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from reports.export_csv import export_csv_bytes
from reports.export_las import export_las_bytes
from reports.export_xlsx import export_xlsx_bytes


DEFAULT_WELLS_ROOT = Path("data/wells")
MANIFEST_FILE_NAME = "manifest.json"


@dataclass(frozen=True)
class WellVersion:
    id: str
    label: str
    kind: str
    created_at: str
    files: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WellRecord:
    id: str
    name: str
    area: str = ""
    status: str = "draft"
    comment: str = ""
    created_at: str = ""
    updated_at: str = ""
    versions: tuple[WellVersion, ...] = ()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "well"


def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор скважины или версии.")
    return value


def _well_dir(root: Path, well_id: str) -> Path:
    return root / _safe_id(well_id)


def _manifest_path(root: Path, well_id: str) -> Path:
    return _well_dir(root, well_id) / MANIFEST_FILE_NAME


def _version_from_dict(raw: dict[str, Any]) -> WellVersion:
    return WellVersion(
        id=str(raw.get("id", "")),
        label=str(raw.get("label", "")),
        kind=str(raw.get("kind", "")),
        created_at=str(raw.get("created_at", "")),
        files=dict(raw.get("files", {})),
        metadata=dict(raw.get("metadata", {})),
    )


def _record_from_dict(raw: dict[str, Any]) -> WellRecord:
    versions = tuple(_version_from_dict(version) for version in raw.get("versions", ()))
    return WellRecord(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        area=str(raw.get("area", "")),
        status=str(raw.get("status", "draft")),
        comment=str(raw.get("comment", "")),
        created_at=str(raw.get("created_at", "")),
        updated_at=str(raw.get("updated_at", "")),
        versions=versions,
    )


def _record_to_dict(record: WellRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "area": record.area,
        "status": record.status,
        "comment": record.comment,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "versions": [
            {
                "id": version.id,
                "label": version.label,
                "kind": version.kind,
                "created_at": version.created_at,
                "files": version.files,
                "metadata": version.metadata,
            }
            for version in record.versions
        ],
    }


def load_well_record(root: Path | str, well_id: str) -> WellRecord:
    root_path = Path(root)
    path = _manifest_path(root_path, well_id)
    if not path.exists():
        raise FileNotFoundError(f"Well manifest not found: {well_id}")
    return _record_from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_wells(root: Path | str = DEFAULT_WELLS_ROOT) -> tuple[WellRecord, ...]:
    root_path = Path(root)
    if not root_path.exists():
        return ()

    records: list[WellRecord] = []
    for manifest_path in sorted(root_path.glob(f"*/{MANIFEST_FILE_NAME}")):
        try:
            records.append(_record_from_dict(json.loads(manifest_path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return tuple(sorted(records, key=lambda record: record.updated_at, reverse=True))


def _write_record(root: Path, record: WellRecord) -> None:
    well_dir = _well_dir(root, record.id)
    well_dir.mkdir(parents=True, exist_ok=True)
    _manifest_path(root, record.id).write_text(
        json.dumps(_record_to_dict(record), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_new_record(
    root: Path,
    well_name: str,
    area: str = "",
    status: str = "draft",
    comment: str = "",
) -> WellRecord:
    now = _utc_now()
    base_id = f"{now[:10].replace('-', '')}-{_slugify(well_name)}"
    well_id = base_id
    counter = 2
    while _well_dir(root, well_id).exists():
        well_id = f"{base_id}-{counter}"
        counter += 1

    return WellRecord(
        id=well_id,
        name=well_name.strip() or "Без названия",
        area=area.strip(),
        status=status.strip() or "draft",
        comment=comment.strip(),
        created_at=now,
        updated_at=now,
        versions=(),
    )


def save_well_version(
    df: pd.DataFrame,
    root: Path | str = DEFAULT_WELLS_ROOT,
    well_name: str = "",
    well_id: str | None = None,
    area: str = "",
    status: str = "draft",
    comment: str = "",
    version_label: str = "prepared",
    kind: str = "prepared_las",
    depth_column: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> WellRecord:
    if df is None or df.empty:
        raise ValueError("Нет данных для сохранения скважины.")

    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)

    if well_id:
        record = load_well_record(root_path, well_id)
        created_at = record.created_at
        versions = list(record.versions)
        name = well_name.strip() or record.name
        area_value = area.strip() or record.area
        status_value = status.strip() or record.status
        comment_value = comment.strip() or record.comment
    else:
        record = _build_new_record(root_path, well_name, area=area, status=status, comment=comment)
        created_at = record.created_at
        versions = []
        name = record.name
        area_value = record.area
        status_value = record.status
        comment_value = record.comment

    now = _utc_now()
    base_version_id = f"{now.replace(':', '').replace('-', '')}-{_slugify(version_label)}"
    version_id = base_version_id
    version_dir = _well_dir(root_path, record.id) / "versions" / version_id
    counter = 2
    while version_dir.exists():
        version_id = f"{base_version_id}-{counter}"
        version_dir = _well_dir(root_path, record.id) / "versions" / version_id
        counter += 1
    version_dir.mkdir(parents=True, exist_ok=True)

    csv_name = "prepared.csv"
    xlsx_name = "prepared.xlsx"
    las_name = "prepared.las"
    (version_dir / csv_name).write_bytes(export_csv_bytes(df))
    (version_dir / xlsx_name).write_bytes(export_xlsx_bytes(df, sheet_name="prepared"))
    (version_dir / las_name).write_bytes(export_las_bytes(df, well_name=name, depth_column=depth_column))

    version = WellVersion(
        id=version_id,
        label=version_label.strip() or "prepared",
        kind=kind,
        created_at=now,
        files={"csv": csv_name, "xlsx": xlsx_name, "las": las_name},
        metadata=metadata or {},
    )
    versions.append(version)

    updated_record = WellRecord(
        id=record.id,
        name=name,
        area=area_value,
        status=status_value,
        comment=comment_value,
        created_at=created_at,
        updated_at=now,
        versions=tuple(versions),
    )
    _write_record(root_path, updated_record)
    return updated_record


def read_well_file_bytes(
    root: Path | str,
    well_id: str,
    version_id: str,
    file_key: str,
) -> bytes:
    record = load_well_record(root, well_id)
    version = next((candidate for candidate in record.versions if candidate.id == version_id), None)
    if version is None:
        raise FileNotFoundError(f"Well version not found: {version_id}")
    file_name = version.files.get(file_key)
    if not file_name:
        raise FileNotFoundError(f"Well file not found for key: {file_key}")
    path = _well_dir(Path(root), well_id) / "versions" / version_id / file_name
    return path.read_bytes()


def delete_well_version(root: Path | str, well_id: str, version_id: str) -> WellRecord:
    """Delete one saved well version from persistent storage and update manifest."""
    root_path = Path(root)
    record = load_well_record(root_path, well_id)
    clean_version_id = _safe_id(version_id)
    versions = [version for version in record.versions if version.id != clean_version_id]
    if len(versions) == len(record.versions):
        raise FileNotFoundError(f"Well version not found: {version_id}")

    version_dir = _well_dir(root_path, record.id) / "versions" / clean_version_id
    if version_dir.exists():
        shutil.rmtree(version_dir)

    updated_record = WellRecord(
        id=record.id,
        name=record.name,
        area=record.area,
        status=record.status,
        comment=record.comment,
        created_at=record.created_at,
        updated_at=_utc_now(),
        versions=tuple(versions),
    )
    _write_record(root_path, updated_record)
    return updated_record


def delete_well_record(root: Path | str, well_id: str) -> bool:
    """Delete a saved well directory from persistent storage."""
    root_path = Path(root)
    well_dir = _well_dir(root_path, well_id)
    if not well_dir.exists():
        return False
    shutil.rmtree(well_dir)
    return True



def delete_well(root: Path | str, well_id: str) -> bool:
    """Backward-compatible alias for deleting a complete well directory."""
    return delete_well_record(root, well_id)

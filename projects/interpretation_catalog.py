from __future__ import annotations

"""Project/well-scoped catalog for manual interpretation workspaces.

The catalog manages interpretation directories without coupling them to Streamlit.
All persisted values are JSON-compatible. Deletion is implemented as a reversible
move to a per-well trash directory, while duplication is written through a
staging directory before it becomes visible.
"""

import json
import os
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from projects.interpretation_intervals import DEFAULT_INTERPRETATION_ID, _safe_interpretation_id
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

CATALOG_SCHEMA = "gas-ratio-pro/interpretation-catalog/v1"
CATALOG_FILE_NAME = "catalog.json"
TRASH_DIR_NAME = ".trash"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean_text(value: Any, label: str, *, max_length: int, required: bool = False) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{label}: максимум {max_length} символов.")
    return text


def _slug(value: str) -> str:
    clean = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip()).strip("-_").lower()
    return clean or "interpretation"


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


@dataclass(frozen=True)
class InterpretationCatalogItem:
    id: str
    name: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    duplicated_from: str = ""


@dataclass(frozen=True)
class DeletedInterpretationItem:
    trash_id: str
    interpretation_id: str
    name: str
    deleted_at: str


class InterpretationCatalogRepository:
    def __init__(
        self,
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        well_id: str,
    ) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)
        self.well_id = safe_well_id(well_id)
        self.base_dir = self.root / self.project_id / "wells" / self.well_id / "interpretations"
        self.catalog_path = self.base_dir / CATALOG_FILE_NAME
        self.trash_dir = self.base_dir / TRASH_DIR_NAME

    def list(self) -> tuple[InterpretationCatalogItem, ...]:
        items = self._load_items()
        known = {item.id for item in items}
        discovered = []
        if self.base_dir.exists():
            for path in sorted(self.base_dir.iterdir()):
                if not path.is_dir() or path.name.startswith("."):
                    continue
                try:
                    interpretation_id = _safe_interpretation_id(path.name)
                except ValueError:
                    continue
                if interpretation_id not in known:
                    now = _utc_now()
                    discovered.append(
                        InterpretationCatalogItem(
                            id=interpretation_id,
                            name="Основная интерпретация" if interpretation_id == DEFAULT_INTERPRETATION_ID else interpretation_id,
                            created_at=now,
                            updated_at=now,
                        )
                    )
        items.extend(discovered)
        synthesized = False
        if not items:
            now = _utc_now()
            items.append(
                InterpretationCatalogItem(
                    id=DEFAULT_INTERPRETATION_ID,
                    name="Основная интерпретация",
                    created_at=now,
                    updated_at=now,
                )
            )
            synthesized = True
        if discovered or synthesized:
            self._save_items(items)
        return tuple(sorted(items, key=lambda item: (item.name.lower(), item.id)))

    def get(self, interpretation_id: str) -> InterpretationCatalogItem:
        clean_id = _safe_interpretation_id(interpretation_id)
        item = next((row for row in self.list() if row.id == clean_id), None)
        if item is None:
            raise KeyError(f"Интерпретация не найдена: {clean_id}")
        return item

    def create(self, *, name: str, description: str = "", interpretation_id: str | None = None) -> InterpretationCatalogItem:
        clean_name = _clean_text(name, "Название интерпретации", max_length=160, required=True)
        clean_description = _clean_text(description, "Описание", max_length=1200)
        existing = {item.id for item in self.list()}
        if interpretation_id:
            clean_id = _safe_interpretation_id(interpretation_id)
            if clean_id in existing:
                raise ValueError(f"Интерпретация с ID «{clean_id}» уже существует.")
        else:
            base = _safe_interpretation_id(_slug(clean_name))
            clean_id = base
            counter = 2
            while clean_id in existing:
                clean_id = _safe_interpretation_id(f"{base}-{counter}")
                counter += 1
        now = _utc_now()
        item = InterpretationCatalogItem(
            id=clean_id,
            name=clean_name,
            description=clean_description,
            created_at=now,
            updated_at=now,
        )
        target = self.base_dir / clean_id
        target.mkdir(parents=True, exist_ok=False)
        items = list(self.list())
        items.append(item)
        self._save_items(items)
        return item

    def update(self, interpretation_id: str, *, name: str, description: str = "") -> InterpretationCatalogItem:
        clean_id = _safe_interpretation_id(interpretation_id)
        clean_name = _clean_text(name, "Название интерпретации", max_length=160, required=True)
        clean_description = _clean_text(description, "Описание", max_length=1200)
        items = list(self.list())
        index = next((idx for idx, item in enumerate(items) if item.id == clean_id), None)
        if index is None:
            raise KeyError(f"Интерпретация не найдена: {clean_id}")
        updated = replace(items[index], name=clean_name, description=clean_description, updated_at=_utc_now())
        items[index] = updated
        self._save_items(items)
        return updated

    def duplicate(
        self,
        interpretation_id: str,
        *,
        name: str,
        description: str | None = None,
        target_id: str | None = None,
    ) -> InterpretationCatalogItem:
        source = self.get(interpretation_id)
        clean_name = _clean_text(name, "Название копии", max_length=160, required=True)
        clean_description = source.description if description is None else _clean_text(description, "Описание", max_length=1200)
        existing = {item.id for item in self.list()}
        if target_id:
            clean_target_id = _safe_interpretation_id(target_id)
            if clean_target_id in existing:
                raise ValueError(f"Интерпретация с ID «{clean_target_id}» уже существует.")
        else:
            base = _safe_interpretation_id(_slug(clean_name))
            clean_target_id = base
            counter = 2
            while clean_target_id in existing:
                clean_target_id = _safe_interpretation_id(f"{base}-{counter}")
                counter += 1

        source_dir = self.base_dir / source.id
        target_dir = self.base_dir / clean_target_id
        self.base_dir.mkdir(parents=True, exist_ok=True)
        stage_dir = self.base_dir / f".{clean_target_id}.staging-{uuid4().hex}"
        try:
            if source_dir.exists():
                shutil.copytree(source_dir, stage_dir, ignore=shutil.ignore_patterns(".revisions", ".workflow"))
            else:
                stage_dir.mkdir(parents=True)
            self._rewrite_scope_metadata(stage_dir, clean_target_id)
            os.replace(stage_dir, target_dir)
        except Exception:
            shutil.rmtree(stage_dir, ignore_errors=True)
            raise

        now = _utc_now()
        item = InterpretationCatalogItem(
            id=clean_target_id,
            name=clean_name,
            description=clean_description,
            created_at=now,
            updated_at=now,
            duplicated_from=source.id,
        )
        items = list(self.list())
        items.append(item)
        self._save_items(items)
        return item

    def delete(self, interpretation_id: str) -> DeletedInterpretationItem:
        clean_id = _safe_interpretation_id(interpretation_id)
        current = list(self.list())
        item = next((row for row in current if row.id == clean_id), None)
        if item is None:
            raise KeyError(f"Интерпретация не найдена: {clean_id}")
        if len(current) <= 1:
            raise ValueError("Нельзя удалить единственную интерпретацию скважины.")
        deleted_at = _utc_now()
        trash_id = f"{clean_id}--{deleted_at.replace(':', '').replace('-', '')}--{uuid4().hex[:8]}"
        source_dir = self.base_dir / clean_id
        target_dir = self.trash_dir / trash_id
        self.trash_dir.mkdir(parents=True, exist_ok=True)
        if source_dir.exists():
            os.replace(source_dir, target_dir)
        else:
            target_dir.mkdir(parents=True)
        _atomic_json_write(
            target_dir / "deleted_interpretation.json",
            {
                "schema": CATALOG_SCHEMA,
                "trash_id": trash_id,
                "deleted_at": deleted_at,
                "item": asdict(item),
            },
        )
        self._save_items([row for row in current if row.id != clean_id])
        return DeletedInterpretationItem(trash_id, clean_id, item.name, deleted_at)

    def list_deleted(self) -> tuple[DeletedInterpretationItem, ...]:
        result: list[DeletedInterpretationItem] = []
        if not self.trash_dir.exists():
            return ()
        for directory in sorted(self.trash_dir.iterdir(), reverse=True):
            metadata = self._read_json(directory / "deleted_interpretation.json", {})
            item = metadata.get("item", {}) if isinstance(metadata, Mapping) else {}
            if not isinstance(item, Mapping):
                continue
            result.append(
                DeletedInterpretationItem(
                    trash_id=directory.name,
                    interpretation_id=str(item.get("id", "")),
                    name=str(item.get("name", item.get("id", ""))),
                    deleted_at=str(metadata.get("deleted_at", "")),
                )
            )
        return tuple(result)

    def restore(self, trash_id: str) -> InterpretationCatalogItem:
        clean_trash_id = str(trash_id or "").strip()
        if not clean_trash_id or "/" in clean_trash_id or "\\" in clean_trash_id:
            raise ValueError("Некорректный ID удалённой интерпретации.")
        source_dir = self.trash_dir / clean_trash_id
        metadata = self._read_json(source_dir / "deleted_interpretation.json", {})
        item_data = metadata.get("item", {}) if isinstance(metadata, Mapping) else {}
        if not isinstance(item_data, Mapping):
            raise ValueError("Метаданные удалённой интерпретации повреждены.")
        item = self._parse_item(item_data)
        if any(row.id == item.id for row in self.list()) or (self.base_dir / item.id).exists():
            raise ValueError(f"Интерпретация с ID «{item.id}» уже существует.")
        (source_dir / "deleted_interpretation.json").unlink(missing_ok=True)
        os.replace(source_dir, self.base_dir / item.id)
        restored = replace(item, updated_at=_utc_now())
        items = list(self.list())
        items.append(restored)
        self._save_items(items)
        return restored

    def _load_items(self) -> list[InterpretationCatalogItem]:
        payload = self._read_json(self.catalog_path, {})
        rows = payload.get("items", []) if isinstance(payload, Mapping) else []
        result = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            try:
                result.append(self._parse_item(row))
            except (TypeError, ValueError):
                continue
        return result

    def _save_items(self, items: list[InterpretationCatalogItem]) -> None:
        unique = {item.id: item for item in items}
        _atomic_json_write(
            self.catalog_path,
            {
                "schema": CATALOG_SCHEMA,
                "project_id": self.project_id,
                "well_id": self.well_id,
                "items": [asdict(item) for item in sorted(unique.values(), key=lambda row: row.id)],
                "updated_at": _utc_now(),
            },
        )

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def _parse_item(row: Mapping[str, Any]) -> InterpretationCatalogItem:
        return InterpretationCatalogItem(
            id=_safe_interpretation_id(str(row.get("id", ""))),
            name=_clean_text(row.get("name", ""), "Название интерпретации", max_length=160, required=True),
            description=_clean_text(row.get("description", ""), "Описание", max_length=1200),
            created_at=str(row.get("created_at", "") or ""),
            updated_at=str(row.get("updated_at", "") or ""),
            duplicated_from=str(row.get("duplicated_from", "") or ""),
        )

    @staticmethod
    def _rewrite_scope_metadata(directory: Path, interpretation_id: str) -> None:
        for path in directory.rglob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                continue
            if isinstance(payload, dict) and "interpretation_id" in payload:
                payload["interpretation_id"] = interpretation_id
                _atomic_json_write(path, payload)

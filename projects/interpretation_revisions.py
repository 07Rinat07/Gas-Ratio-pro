from __future__ import annotations

"""Persistent revision snapshots for one manual interpretation workspace.

A revision stores JSON-compatible files from the interpretation directory while
excluding the revision store itself.  Restore uses a stale-state token and a
rollback snapshot so a failed restore never leaves a partially written workspace.
"""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from projects.interpretation_intervals import (
    INTERPRETATION_INTERVALS_FILE_NAME,
    InterpretationInterval,
    _interval_from_dict,
    _safe_interpretation_id,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

REVISION_SCHEMA = "gas-ratio-pro/interpretation-revision/v1"
REVISION_INDEX_SCHEMA = "gas-ratio-pro/interpretation-revision-index/v1"
REVISION_DIR_NAME = ".revisions"
REVISION_INDEX_FILE_NAME = "index.json"
MAX_REVISION_NAME_LENGTH = 160
MAX_REVISION_NOTE_LENGTH = 1200


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _clean_text(value: Any, label: str, *, max_length: int, required: bool = False) -> str:
    clean = str(value or "").strip()
    if required and not clean:
        raise ValueError(f"{label}: значение обязательно.")
    if len(clean) > max_length:
        raise ValueError(f"{label}: максимум {max_length} символов.")
    return clean


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class InterpretationRevision:
    id: str
    name: str
    note: str
    created_at: str
    file_count: int
    interval_count: int
    state_token: str


@dataclass(frozen=True)
class InterpretationRevisionDiff:
    revision_id: str
    added: tuple[InterpretationInterval, ...]
    removed: tuple[InterpretationInterval, ...]
    changed: tuple[tuple[InterpretationInterval, InterpretationInterval], ...]
    unchanged_count: int
    current_state_token: str


class InterpretationRevisionRepository:
    def __init__(
        self,
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        well_id: str,
        interpretation_id: str,
    ) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)
        self.well_id = safe_well_id(well_id)
        self.interpretation_id = _safe_interpretation_id(interpretation_id)
        self.workspace_dir = (
            self.root / self.project_id / "wells" / self.well_id / "interpretations" / self.interpretation_id
        )
        self.revision_dir = self.workspace_dir / REVISION_DIR_NAME
        self.index_path = self.revision_dir / REVISION_INDEX_FILE_NAME

    def list(self) -> tuple[InterpretationRevision, ...]:
        payload = self._read_json(self.index_path, {})
        rows = payload.get("items", []) if isinstance(payload, Mapping) else []
        result: list[InterpretationRevision] = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            try:
                result.append(self._parse_metadata(row))
            except (TypeError, ValueError):
                continue
        return tuple(sorted(result, key=lambda item: item.created_at, reverse=True))

    def create(self, *, name: str, note: str = "") -> InterpretationRevision:
        clean_name = _clean_text(name, "Название ревизии", max_length=MAX_REVISION_NAME_LENGTH, required=True)
        clean_note = _clean_text(note, "Комментарий ревизии", max_length=MAX_REVISION_NOTE_LENGTH)
        files = self._capture_files()
        revision_id = str(uuid4())
        created_at = _utc_now()
        token = _canonical_hash(files)
        interval_count = len(self._intervals_from_files(files))
        metadata = InterpretationRevision(
            id=revision_id,
            name=clean_name,
            note=clean_note,
            created_at=created_at,
            file_count=len(files),
            interval_count=interval_count,
            state_token=token,
        )
        _atomic_json_write(
            self.revision_dir / f"{revision_id}.json",
            {
                "schema": REVISION_SCHEMA,
                "project_id": self.project_id,
                "well_id": self.well_id,
                "interpretation_id": self.interpretation_id,
                "metadata": asdict(metadata),
                "files": files,
            },
        )
        items = [item for item in self.list() if item.id != revision_id]
        items.append(metadata)
        self._save_index(items)
        return metadata

    def get(self, revision_id: str) -> InterpretationRevision:
        clean_id = self._validate_revision_id(revision_id)
        metadata = next((item for item in self.list() if item.id == clean_id), None)
        if metadata is None:
            raise KeyError(f"Ревизия не найдена: {clean_id}")
        return metadata

    def compare(self, revision_id: str) -> InterpretationRevisionDiff:
        revision_files = self._load_revision_files(revision_id)
        current_files = self._capture_files()
        revision_intervals = {item.id: item for item in self._intervals_from_files(revision_files)}
        current_intervals = {item.id: item for item in self._intervals_from_files(current_files)}
        added = tuple(current_intervals[key] for key in sorted(current_intervals.keys() - revision_intervals.keys()))
        removed = tuple(revision_intervals[key] for key in sorted(revision_intervals.keys() - current_intervals.keys()))
        changed: list[tuple[InterpretationInterval, InterpretationInterval]] = []
        unchanged = 0
        for interval_id in sorted(current_intervals.keys() & revision_intervals.keys()):
            before = revision_intervals[interval_id]
            after = current_intervals[interval_id]
            if before == after:
                unchanged += 1
            else:
                changed.append((before, after))
        return InterpretationRevisionDiff(
            revision_id=self._validate_revision_id(revision_id),
            added=added,
            removed=removed,
            changed=tuple(changed),
            unchanged_count=unchanged,
            current_state_token=_canonical_hash(current_files),
        )

    def restore(self, revision_id: str, *, expected_current_state_token: str) -> InterpretationRevision:
        clean_id = self._validate_revision_id(revision_id)
        current_files = self._capture_files()
        current_token = _canonical_hash(current_files)
        if current_token != str(expected_current_state_token or ""):
            raise ValueError("Текущее состояние интерпретации изменилось после построения preview.")
        revision_files = self._load_revision_files(clean_id)
        self._restore_files(revision_files, rollback_files=current_files)
        return self.get(clean_id)

    def delete(self, revision_id: str) -> bool:
        clean_id = self._validate_revision_id(revision_id)
        path = self.revision_dir / f"{clean_id}.json"
        if not path.exists():
            return False
        path.unlink()
        self._save_index([item for item in self.list() if item.id != clean_id])
        return True

    def prune(self, *, keep_latest: int) -> tuple[str, ...]:
        keep = int(keep_latest)
        if keep < 1:
            raise ValueError("Необходимо сохранить хотя бы одну последнюю ревизию.")
        items = list(self.list())
        removed: list[str] = []
        for item in items[keep:]:
            if self.delete(item.id):
                removed.append(item.id)
        return tuple(removed)

    def current_state_token(self) -> str:
        return _canonical_hash(self._capture_files())

    def _capture_files(self) -> dict[str, Any]:
        files: dict[str, Any] = {}
        if not self.workspace_dir.exists():
            return files
        for path in sorted(self.workspace_dir.rglob("*.json")):
            try:
                relative = path.relative_to(self.workspace_dir)
            except ValueError:
                continue
            if relative.parts and relative.parts[0] == REVISION_DIR_NAME:
                continue
            payload = self._read_json(path, None)
            if payload is not None:
                files[relative.as_posix()] = payload
        return files

    def _restore_files(self, files: Mapping[str, Any], *, rollback_files: Mapping[str, Any]) -> None:
        try:
            current_paths = {
                path.relative_to(self.workspace_dir).as_posix(): path
                for path in self.workspace_dir.rglob("*.json")
                if self.workspace_dir.exists()
                and path.relative_to(self.workspace_dir).parts[0] != REVISION_DIR_NAME
            }
            target_names = set(files)
            for relative, path in current_paths.items():
                if relative not in target_names:
                    path.unlink(missing_ok=True)
            for relative, payload in files.items():
                self._validate_relative_path(relative)
                _atomic_json_write(self.workspace_dir / relative, payload if isinstance(payload, Mapping) else {"value": payload})
        except Exception:
            self._force_restore(rollback_files)
            raise

    def _force_restore(self, files: Mapping[str, Any]) -> None:
        if self.workspace_dir.exists():
            for path in self.workspace_dir.rglob("*.json"):
                relative = path.relative_to(self.workspace_dir)
                if relative.parts[0] != REVISION_DIR_NAME:
                    path.unlink(missing_ok=True)
        for relative, payload in files.items():
            self._validate_relative_path(relative)
            _atomic_json_write(self.workspace_dir / relative, payload if isinstance(payload, Mapping) else {"value": payload})

    def _load_revision_files(self, revision_id: str) -> dict[str, Any]:
        clean_id = self._validate_revision_id(revision_id)
        payload = self._read_json(self.revision_dir / f"{clean_id}.json", {})
        if not isinstance(payload, Mapping) or payload.get("schema") != REVISION_SCHEMA:
            raise ValueError("Файл ревизии повреждён или имеет неподдерживаемую схему.")
        files = payload.get("files", {})
        if not isinstance(files, Mapping):
            raise ValueError("Файл ревизии не содержит корректного снимка.")
        result: dict[str, Any] = {}
        for relative, value in files.items():
            clean_relative = str(relative)
            self._validate_relative_path(clean_relative)
            result[clean_relative] = value
        return result

    @staticmethod
    def _intervals_from_files(files: Mapping[str, Any]) -> tuple[InterpretationInterval, ...]:
        payload = files.get(INTERPRETATION_INTERVALS_FILE_NAME, {})
        rows = payload.get("intervals", []) if isinstance(payload, Mapping) else []
        result: list[InterpretationInterval] = []
        for row in rows:
            if isinstance(row, dict):
                result.append(_interval_from_dict(row))
        return tuple(sorted(result, key=lambda item: (item.top, item.base, item.label.lower())))

    def _save_index(self, items: list[InterpretationRevision]) -> None:
        _atomic_json_write(
            self.index_path,
            {
                "schema": REVISION_INDEX_SCHEMA,
                "project_id": self.project_id,
                "well_id": self.well_id,
                "interpretation_id": self.interpretation_id,
                "updated_at": _utc_now(),
                "items": [asdict(item) for item in sorted(items, key=lambda row: row.created_at, reverse=True)],
            },
        )

    @staticmethod
    def _parse_metadata(row: Mapping[str, Any]) -> InterpretationRevision:
        return InterpretationRevision(
            id=InterpretationRevisionRepository._validate_revision_id(str(row.get("id", ""))),
            name=_clean_text(row.get("name", ""), "Название ревизии", max_length=MAX_REVISION_NAME_LENGTH, required=True),
            note=_clean_text(row.get("note", ""), "Комментарий ревизии", max_length=MAX_REVISION_NOTE_LENGTH),
            created_at=str(row.get("created_at", "")),
            file_count=max(0, int(row.get("file_count", 0))),
            interval_count=max(0, int(row.get("interval_count", 0))),
            state_token=str(row.get("state_token", "")),
        )

    @staticmethod
    def _validate_revision_id(value: str) -> str:
        clean = str(value or "").strip()
        try:
            from uuid import UUID
            return str(UUID(clean))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Некорректный UUID ревизии.") from exc

    @staticmethod
    def _validate_relative_path(value: str) -> None:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] == REVISION_DIR_NAME:
            raise ValueError("Некорректный путь файла в ревизии.")

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return default

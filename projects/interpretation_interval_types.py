from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from projects.interpretation_intervals import load_interpretation_intervals, save_interpretation_intervals
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

INTERVAL_TYPES_SCHEMA = "gas-ratio-pro/interpretation-interval-types/v1"
INTERVAL_TYPES_FILE_NAME = "interpretation_interval_types.json"
INTERVAL_TYPE_OPERATIONS_SCHEMA = "gas-ratio-pro/interpretation-interval-type-operations/v1"
INTERVAL_TYPE_OPERATIONS_FILE_NAME = "interpretation_interval_type_operations.json"
INTERVAL_TYPE_OPERATIONS_LIMIT = 200
INTERVAL_TYPE_OPERATION_BACKUPS_DIR = "interpretation_interval_type_operation_backups"


@dataclass(frozen=True)
class InterpretationIntervalType:
    id: str
    name: str
    color: str = "#4C78A8"
    description: str = ""
    created_at: str = ""
    updated_at: str = ""




@dataclass(frozen=True)
class InterpretationIntervalTypeUsage:
    type_id: str
    interval_count: int
    well_count: int
    interpretation_count: int

    @property
    def in_use(self) -> bool:
        return self.interval_count > 0




@dataclass(frozen=True)
class InterpretationIntervalTypeReassignmentPreviewItem:
    interval_id: str
    label: str
    well_id: str
    interpretation_id: str
    top: float
    base: float
    color: str

    @property
    def thickness(self) -> float:
        return round(self.base - self.top, 6)


@dataclass(frozen=True)
class InterpretationIntervalTypeReassignmentPreview:
    source_type_id: str
    target_type_id: str
    interval_count: int
    well_count: int
    interpretation_count: int
    target_color_applied: bool
    items: tuple[InterpretationIntervalTypeReassignmentPreviewItem, ...]
    confirmation_token: str


@dataclass(frozen=True)
class InterpretationIntervalTypeReassignmentResult:
    source_type_id: str
    target_type_id: str
    interval_count: int
    well_count: int
    interpretation_count: int
    target_color_applied: bool


@dataclass(frozen=True)
class InterpretationIntervalTypeOperation:
    id: str
    operation: str
    source_type_id: str
    target_type_id: str
    interval_count: int
    well_count: int
    interpretation_count: int
    target_color_applied: bool
    created_at: str
    undo_available: bool = False
    undone_at: str = ""


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".rollback", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _reassignment_confirmation_token(
    *,
    source_type_id: str,
    target_type_id: str,
    apply_target_color: bool,
    catalog: tuple[InterpretationIntervalType, ...],
    project_root: Path,
    paths: list[Path],
) -> str:
    files = []
    for path in paths:
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise ValueError(f"Не удалось прочитать интервалы для подтверждения: {path}") from exc
        files.append(
            {
                "path": path.relative_to(project_root).as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    payload = {
        "source_type_id": source_type_id,
        "target_type_id": target_type_id,
        "apply_target_color": bool(apply_target_color),
        "catalog": [asdict(item) for item in catalog],
        "files": files,
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


DEFAULT_INTERVAL_TYPES: tuple[InterpretationIntervalType, ...] = (
    InterpretationIntervalType("undefined", "Не определён", "#4C78A8", "Тип не назначен."),
    InterpretationIntervalType("reservoir", "Коллектор", "#59A14F", "Интервал коллектора."),
    InterpretationIntervalType("pay", "Продуктивный", "#F28E2B", "Продуктивный интервал."),
    InterpretationIntervalType("gas", "Газ", "#E15759", "Газонасыщенный интервал."),
    InterpretationIntervalType("oil", "Нефть", "#B07AA1", "Нефтенасыщенный интервал."),
    InterpretationIntervalType("water", "Вода", "#4E79A7", "Водонасыщенный интервал."),
    InterpretationIntervalType("non_reservoir", "Неколлектор", "#9D9D9D", "Неколлекторская порода."),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _storage_path(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / INTERVAL_TYPES_FILE_NAME


def _operations_path(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / INTERVAL_TYPE_OPERATIONS_FILE_NAME


def _load_type_operations(
    root: Path | str,
    project_id: str,
) -> tuple[InterpretationIntervalTypeOperation, ...]:
    path = _operations_path(root, project_id)
    if not path.exists():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Не удалось прочитать журнал операций типов интервалов.") from exc
    if payload.get("schema") != INTERVAL_TYPE_OPERATIONS_SCHEMA:
        raise ValueError("Неподдерживаемая схема журнала операций типов интервалов.")
    items = []
    for raw in payload.get("operations", ()):
        try:
            items.append(InterpretationIntervalTypeOperation(**raw))
        except (TypeError, ValueError) as exc:
            raise ValueError("Журнал операций типов интервалов повреждён.") from exc
    return tuple(items)


def _append_type_operation(
    root: Path | str,
    project_id: str,
    operation: InterpretationIntervalTypeOperation,
) -> None:
    current = list(_load_type_operations(root, project_id))
    current.append(operation)
    current = current[-INTERVAL_TYPE_OPERATIONS_LIMIT:]
    _atomic_write(
        _operations_path(root, project_id),
        {
            "schema": INTERVAL_TYPE_OPERATIONS_SCHEMA,
            "project_id": safe_project_id(project_id),
            "updated_at": _utc_now(),
            "operations": [asdict(item) for item in current],
        },
    )



def _operation_backup_path(root: Path | str, project_id: str, operation_id: str) -> Path:
    return (
        Path(root)
        / safe_project_id(project_id)
        / INTERVAL_TYPE_OPERATION_BACKUPS_DIR
        / f"{operation_id}.json"
    )


def _file_state_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save_type_operation_backup(
    root: Path | str,
    project_id: str,
    operation_id: str,
    *,
    catalog_path: Path,
    interval_paths: list[Path],
) -> None:
    project_root = Path(root) / safe_project_id(project_id)
    payload = {
        "schema": "gas-ratio-pro/interpretation-interval-type-operation-backup/v1",
        "operation_id": operation_id,
        "catalog": {
            "path": catalog_path.relative_to(project_root).as_posix(),
            "content": catalog_path.read_text(encoding="utf-8") if catalog_path.exists() else None,
        },
        "intervals": [
            {
                "path": path.relative_to(project_root).as_posix(),
                "content": path.read_text(encoding="utf-8"),
            }
            for path in interval_paths
        ],
    }
    _atomic_write(_operation_backup_path(root, project_id, operation_id), payload)


def _seal_type_operation_backup(root: Path | str, project_id: str, operation_id: str) -> None:
    path = _operation_backup_path(root, project_id, operation_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    project_root = Path(root) / safe_project_id(project_id)
    tracked = [payload["catalog"]["path"]] + [item["path"] for item in payload.get("intervals", ())]
    payload["post_state"] = {relative: _file_state_hash(project_root / relative) for relative in tracked}
    _atomic_write(path, payload)


def _replace_type_operations(
    root: Path | str, project_id: str, operations: Iterable[InterpretationIntervalTypeOperation]
) -> None:
    normalized = list(operations)[-INTERVAL_TYPE_OPERATIONS_LIMIT:]
    _atomic_write(
        _operations_path(root, project_id),
        {
            "schema": INTERVAL_TYPE_OPERATIONS_SCHEMA,
            "project_id": safe_project_id(project_id),
            "updated_at": _utc_now(),
            "operations": [asdict(item) for item in normalized],
        },
    )

def _clean_id(value: str) -> str:
    clean = re.sub(r"[^a-z0-9_-]+", "_", str(value or "").strip().lower()).strip("_")
    if not clean:
        raise ValueError("Идентификатор типа интервала не задан.")
    if len(clean) > 80:
        raise ValueError("Идентификатор типа интервала длиннее 80 символов.")
    return clean


def _clean_text(value: str, label: str, max_length: int, *, required: bool = False) -> str:
    clean = str(value or "").strip()
    if required and not clean:
        raise ValueError(f"Поле «{label}» обязательно.")
    if len(clean) > max_length:
        raise ValueError(f"Поле «{label}» длиннее {max_length} символов.")
    return clean


def _clean_color(value: str) -> str:
    clean = str(value or "#4C78A8").strip()
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", clean):
        raise ValueError("Цвет типа должен быть HEX-значением вида #RRGGBB.")
    return clean.upper()


def build_interval_type(
    *,
    type_id: str,
    name: str,
    color: str = "#4C78A8",
    description: str = "",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> InterpretationIntervalType:
    now = _utc_now()
    return InterpretationIntervalType(
        id=_clean_id(type_id),
        name=_clean_text(name, "Название", 120, required=True),
        color=_clean_color(color),
        description=_clean_text(description, "Описание", 1000),
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def _from_dict(raw: dict[str, Any]) -> InterpretationIntervalType:
    return build_interval_type(
        type_id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        color=str(raw.get("color", "#4C78A8")),
        description=str(raw.get("description", "")),
        created_at=str(raw.get("created_at", "")) or None,
        updated_at=str(raw.get("updated_at", "")) or None,
    )


def _defaults() -> tuple[InterpretationIntervalType, ...]:
    return tuple(
        build_interval_type(
            type_id=item.id,
            name=item.name,
            color=item.color,
            description=item.description,
        )
        for item in DEFAULT_INTERVAL_TYPES
    )


def load_interval_types(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[InterpretationIntervalType, ...]:
    path = _storage_path(root, project_id)
    if not path.exists():
        return _defaults()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Не удалось прочитать справочник типов интервалов: {path}") from exc
    if raw.get("schema") != INTERVAL_TYPES_SCHEMA:
        raise ValueError("Неподдерживаемая схема справочника типов интервалов.")
    items = tuple(_from_dict(item) for item in raw.get("types", ()))
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Идентификаторы типов интервалов должны быть уникальными.")
    return tuple(sorted(items, key=lambda item: (item.name.lower(), item.id)))


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def save_interval_types(
    items: Iterable[InterpretationIntervalType],
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[InterpretationIntervalType, ...]:
    normalized = tuple(sorted(items, key=lambda item: (item.name.lower(), item.id)))
    ids = [item.id for item in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("Идентификаторы типов интервалов должны быть уникальными.")
    _atomic_write(
        _storage_path(root, project_id),
        {
            "schema": INTERVAL_TYPES_SCHEMA,
            "project_id": safe_project_id(project_id),
            "updated_at": _utc_now(),
            "types": [asdict(item) for item in normalized],
        },
    )
    return normalized


def get_interval_type_usage(
    type_id: str,
    *,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> InterpretationIntervalTypeUsage:
    clean_id = _clean_id(type_id)
    project_root = Path(root) / safe_project_id(project_id) / "wells"
    interval_count = 0
    wells: set[str] = set()
    interpretations: set[tuple[str, str]] = set()
    if project_root.exists():
        for path in project_root.glob("*/interpretations/*/intervals.json"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                continue
            matching = sum(
                1
                for item in raw.get("intervals", ())
                if str(item.get("interval_type", "undefined")).strip() == clean_id
            )
            if matching:
                well_id = path.parents[2].name
                interpretation_id = path.parent.name
                interval_count += matching
                wells.add(well_id)
                interpretations.add((well_id, interpretation_id))
    return InterpretationIntervalTypeUsage(
        type_id=clean_id,
        interval_count=interval_count,
        well_count=len(wells),
        interpretation_count=len(interpretations),
    )


class InterpretationIntervalTypeRepository:
    def __init__(self, *, root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)

    def list(self) -> tuple[InterpretationIntervalType, ...]:
        return load_interval_types(self.root, self.project_id)

    def get(self, type_id: str) -> InterpretationIntervalType | None:
        clean_id = _clean_id(type_id)
        return next((item for item in self.list() if item.id == clean_id), None)

    def upsert(self, *, type_id: str, name: str, color: str, description: str = "") -> InterpretationIntervalType:
        current = list(self.list())
        clean_id = _clean_id(type_id)
        existing = next((item for item in current if item.id == clean_id), None)
        item = build_interval_type(
            type_id=clean_id,
            name=name,
            color=color,
            description=description,
            created_at=existing.created_at if existing else None,
        )
        current = [candidate for candidate in current if candidate.id != clean_id]
        current.append(item)
        save_interval_types(current, self.root, self.project_id)
        return item

    def usage(self, type_id: str) -> InterpretationIntervalTypeUsage:
        return get_interval_type_usage(
            type_id,
            root=self.root,
            project_id=self.project_id,
        )

    def _filtered_operations(
        self,
        *,
        status: str = "all",
        query: str = "",
    ) -> tuple[InterpretationIntervalTypeOperation, ...]:
        normalized_status = str(status or "all").strip().lower()
        if normalized_status not in {"all", "completed", "undone"}:
            raise ValueError("Неподдерживаемый статус журнала операций типов.")
        normalized_query = str(query or "").strip().casefold()

        filtered: list[InterpretationIntervalTypeOperation] = []
        for operation in reversed(_load_type_operations(self.root, self.project_id)):
            is_undone = bool(operation.undone_at)
            if normalized_status == "completed" and is_undone:
                continue
            if normalized_status == "undone" and not is_undone:
                continue
            if normalized_query:
                haystack = " ".join(
                    (
                        operation.id,
                        operation.operation,
                        operation.source_type_id,
                        operation.target_type_id,
                    )
                ).casefold()
                if normalized_query not in haystack:
                    continue
            filtered.append(operation)
        return tuple(filtered)

    def list_operations(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str = "all",
        query: str = "",
    ) -> tuple[InterpretationIntervalTypeOperation, ...]:
        """Return one newest-first page of journal operations.

        ``status`` accepts ``all``, ``completed`` or ``undone``. Text search
        matches UUID, operation and source/target type IDs. Filtering happens
        before ``offset`` and ``limit`` are applied.
        """

        bounded_limit = max(1, min(int(limit), INTERVAL_TYPE_OPERATIONS_LIMIT))
        bounded_offset = max(0, int(offset))
        filtered = self._filtered_operations(status=status, query=query)
        return filtered[bounded_offset : bounded_offset + bounded_limit]

    def count_operations(self, *, status: str = "all", query: str = "") -> int:
        """Return the number of journal operations matching the filters."""

        return len(self._filtered_operations(status=status, query=query))

    def get_operation(self, operation_id: str) -> InterpretationIntervalTypeOperation | None:
        """Find a project journal operation by its stable UUID."""

        clean_id = str(operation_id or "").strip()
        if not clean_id:
            return None
        return next(
            (item for item in _load_type_operations(self.root, self.project_id) if item.id == clean_id),
            None,
        )

    def preview_reassignment(
        self,
        source_type_id: str,
        target_type_id: str,
        *,
        apply_target_color: bool = True,
    ) -> InterpretationIntervalTypeReassignmentPreview:
        source_id = _clean_id(source_type_id)
        target_id = _clean_id(target_type_id)
        if source_id == target_id:
            raise ValueError("Исходный и целевой типы должны отличаться.")
        source = self.get(source_id)
        if source is None:
            raise KeyError(f"Тип интервала не найден: {source_id}")
        target = self.get(target_id)
        if target is None:
            raise KeyError(f"Тип интервала не найден: {target_id}")

        project_root = self.root / self.project_id / "wells"
        paths = sorted(project_root.glob("*/interpretations/*/intervals.json")) if project_root.exists() else []
        items: list[InterpretationIntervalTypeReassignmentPreviewItem] = []
        wells: set[str] = set()
        interpretations: set[tuple[str, str]] = set()
        for path in paths:
            well_id = path.parents[2].name
            interpretation_id = path.parent.name
            interval_set = load_interpretation_intervals(
                self.root, self.project_id, well_id, interpretation_id
            )
            for interval in interval_set.intervals:
                if interval.interval_type != source_id:
                    continue
                items.append(
                    InterpretationIntervalTypeReassignmentPreviewItem(
                        interval_id=interval.id,
                        label=interval.label,
                        well_id=well_id,
                        interpretation_id=interpretation_id,
                        top=interval.top,
                        base=interval.base,
                        color=interval.color,
                    )
                )
                wells.add(well_id)
                interpretations.add((well_id, interpretation_id))

        normalized_items = tuple(
            sorted(items, key=lambda item: (item.well_id, item.interpretation_id, item.top, item.base, item.label.lower()))
        )
        return InterpretationIntervalTypeReassignmentPreview(
            source_type_id=source_id,
            target_type_id=target_id,
            interval_count=len(normalized_items),
            well_count=len(wells),
            interpretation_count=len(interpretations),
            target_color_applied=bool(apply_target_color),
            items=normalized_items,
            confirmation_token=_reassignment_confirmation_token(
                source_type_id=source_id,
                target_type_id=target_id,
                apply_target_color=apply_target_color,
                catalog=self.list(),
                project_root=project_root,
                paths=paths,
            ),
        )

    def reassign(
        self,
        source_type_id: str,
        target_type_id: str,
        *,
        apply_target_color: bool = True,
        expected_confirmation_token: str | None = None,
    ) -> InterpretationIntervalTypeReassignmentResult:
        source_id = _clean_id(source_type_id)
        target_id = _clean_id(target_type_id)
        if source_id == target_id:
            raise ValueError("Исходный и целевой типы должны отличаться.")
        if self.get(source_id) is None:
            raise KeyError(f"Тип интервала не найден: {source_id}")
        target = self.get(target_id)
        if target is None:
            raise KeyError(f"Тип интервала не найден: {target_id}")
        if expected_confirmation_token is not None:
            current_preview = self.preview_reassignment(
                source_id,
                target_id,
                apply_target_color=apply_target_color,
            )
            if current_preview.confirmation_token != str(expected_confirmation_token):
                raise ValueError(
                    "Данные проекта изменились после предварительного просмотра. "
                    "Обновите preview и подтвердите операцию повторно."
                )

        project_root = self.root / self.project_id / "wells"
        paths = sorted(project_root.glob("*/interpretations/*/intervals.json")) if project_root.exists() else []
        originals: dict[Path, bytes] = {}
        changed_paths: list[Path] = []
        interval_count = 0
        wells: set[str] = set()
        interpretations: set[tuple[str, str]] = set()
        now = _utc_now()

        try:
            for path in paths:
                well_id = path.parents[2].name
                interpretation_id = path.parent.name
                interval_set = load_interpretation_intervals(
                    self.root, self.project_id, well_id, interpretation_id
                )
                matching = [item for item in interval_set.intervals if item.interval_type == source_id]
                if not matching:
                    continue
                originals[path] = path.read_bytes()
                updated_intervals = tuple(
                    replace(
                        item,
                        interval_type=target_id,
                        color=target.color if apply_target_color else item.color,
                        updated_at=now,
                    )
                    if item.interval_type == source_id
                    else item
                    for item in interval_set.intervals
                )
                save_interpretation_intervals(
                    replace(interval_set, intervals=updated_intervals),
                    self.root,
                )
                changed_paths.append(path)
                interval_count += len(matching)
                wells.add(well_id)
                interpretations.add((well_id, interpretation_id))
        except Exception:
            for changed_path in reversed(changed_paths):
                original = originals.get(changed_path)
                if original is not None:
                    _write_bytes_atomic(changed_path, original)
            raise

        return InterpretationIntervalTypeReassignmentResult(
            source_type_id=source_id,
            target_type_id=target_id,
            interval_count=interval_count,
            well_count=len(wells),
            interpretation_count=len(interpretations),
            target_color_applied=bool(apply_target_color),
        )

    def reassign_and_delete(
        self,
        source_type_id: str,
        target_type_id: str,
        *,
        apply_target_color: bool = True,
        expected_confirmation_token: str | None = None,
    ) -> InterpretationIntervalTypeReassignmentResult:
        source_id = _clean_id(source_type_id)
        target_id = _clean_id(target_type_id)
        preview = self.preview_reassignment(
            source_id, target_id, apply_target_color=apply_target_color
        )
        if expected_confirmation_token is not None and preview.confirmation_token != str(expected_confirmation_token):
            raise ValueError(
                "Данные проекта изменились после предварительного просмотра. "
                "Обновите preview и подтвердите операцию повторно."
            )
        operation_id = str(uuid4())
        project_root = self.root / self.project_id
        interval_paths = sorted({
            project_root / "wells" / item.well_id / "interpretations" / item.interpretation_id / "intervals.json"
            for item in preview.items
        })
        catalog_path = _storage_path(self.root, self.project_id)
        _save_type_operation_backup(
            self.root, self.project_id, operation_id,
            catalog_path=catalog_path, interval_paths=interval_paths,
        )
        try:
            result = self.reassign(
                source_id,
                target_id,
                apply_target_color=apply_target_color,
                expected_confirmation_token=preview.confirmation_token,
            )
            self.delete(source_id)
            _seal_type_operation_backup(self.root, self.project_id, operation_id)
            _append_type_operation(
                self.root,
                self.project_id,
                InterpretationIntervalTypeOperation(
                    id=operation_id,
                    operation="reassign_and_delete",
                    source_type_id=result.source_type_id,
                    target_type_id=result.target_type_id,
                    interval_count=result.interval_count,
                    well_count=result.well_count,
                    interpretation_count=result.interpretation_count,
                    target_color_applied=result.target_color_applied,
                    created_at=_utc_now(),
                    undo_available=True,
                ),
            )
        except Exception:
            backup_path = _operation_backup_path(self.root, self.project_id, operation_id)
            if backup_path.exists():
                try:
                    payload = json.loads(backup_path.read_text(encoding="utf-8"))
                    project_root = self.root / self.project_id
                    catalog = payload.get("catalog", {})
                    restore_entries = [
                        (project_root / catalog["path"], catalog.get("content"))
                    ] + [
                        (project_root / item["path"], item.get("content"))
                        for item in payload.get("intervals", ())
                    ]
                    for path, content in restore_entries:
                        if content is None:
                            path.unlink(missing_ok=True)
                        else:
                            _write_bytes_atomic(path, str(content).encode("utf-8"))
                finally:
                    backup_path.unlink(missing_ok=True)
            raise
        return result

    def undo_last_reassignment(self) -> InterpretationIntervalTypeOperation:
        operations = list(_load_type_operations(self.root, self.project_id))
        if not operations:
            raise ValueError("В журнале нет операций для отмены.")
        operation = operations[-1]
        if operation.operation != "reassign_and_delete" or not operation.undo_available or operation.undone_at:
            raise ValueError("Последнюю операцию нельзя отменить.")
        backup_path = _operation_backup_path(self.root, self.project_id, operation.id)
        if not backup_path.exists():
            raise ValueError("Резервная копия операции не найдена.")
        try:
            payload = json.loads(backup_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise ValueError("Резервная копия операции повреждена.") from exc
        if payload.get("schema") != "gas-ratio-pro/interpretation-interval-type-operation-backup/v1":
            raise ValueError("Неподдерживаемая схема резервной копии операции.")
        project_root = self.root / self.project_id
        post_state = payload.get("post_state", {})
        for relative, expected_hash in post_state.items():
            if _file_state_hash(project_root / relative) != expected_hash:
                raise ValueError(
                    "Данные проекта изменились после пакетной операции. "
                    "Автоматическая отмена заблокирована."
                )
        catalog = payload["catalog"]
        catalog_path = project_root / catalog["path"]
        interval_entries = payload.get("intervals", ())
        current: dict[Path, bytes | None] = {}
        restore_entries = [(catalog_path, catalog.get("content"))] + [
            (project_root / item["path"], item.get("content")) for item in interval_entries
        ]
        try:
            for path, _ in restore_entries:
                current[path] = path.read_bytes() if path.exists() else None
            for path, content in restore_entries:
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    _write_bytes_atomic(path, str(content).encode("utf-8"))
        except Exception:
            for path, content in current.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    _write_bytes_atomic(path, content)
            raise
        restored_operation = replace(
            operation, undo_available=False, undone_at=_utc_now()
        )
        operations[-1] = restored_operation
        _replace_type_operations(self.root, self.project_id, operations)
        backup_path.unlink(missing_ok=True)
        return restored_operation

    def delete(self, type_id: str) -> bool:
        clean_id = _clean_id(type_id)
        usage = self.usage(clean_id)
        if usage.in_use:
            raise ValueError(
                f"Тип «{clean_id}» используется в {usage.interval_count} интервалах "
                f"({usage.well_count} скважин). Сначала переназначьте интервалы."
            )
        current = list(self.list())
        updated = [item for item in current if item.id != clean_id]
        if len(updated) == len(current):
            return False
        save_interval_types(updated, self.root, self.project_id)
        return True

    def reset_defaults(self) -> tuple[InterpretationIntervalType, ...]:
        defaults = _defaults()
        return save_interval_types(defaults, self.root, self.project_id)

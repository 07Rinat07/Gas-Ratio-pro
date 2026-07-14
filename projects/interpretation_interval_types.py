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

from projects.interpretation_intervals import load_interpretation_intervals, save_interpretation_intervals
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

INTERVAL_TYPES_SCHEMA = "gas-ratio-pro/interpretation-interval-types/v1"
INTERVAL_TYPES_FILE_NAME = "interpretation_interval_types.json"


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
        result = self.reassign(
            source_type_id,
            target_type_id,
            apply_target_color=apply_target_color,
            expected_confirmation_token=expected_confirmation_token,
        )
        self.delete(source_type_id)
        return result

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

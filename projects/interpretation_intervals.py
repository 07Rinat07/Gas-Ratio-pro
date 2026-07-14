from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID, uuid4

from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

INTERPRETATION_INTERVALS_SCHEMA = "gas-ratio-pro/interpretation-intervals/v1"
INTERPRETATION_INTERVALS_FILE_NAME = "intervals.json"
DEFAULT_INTERPRETATION_ID = "default"


@dataclass(frozen=True)
class InterpretationInterval:
    """Serializable manually managed depth interval.

    Runtime/UI objects must never be attached to this model.  It is intentionally
    composed only of JSON-compatible scalar values so it can be persisted safely.
    """

    id: str
    label: str
    top: float
    base: float
    interval_type: str = "undefined"
    color: str = "#4C78A8"
    comment: str = ""
    source: str = "manual"
    created_at: str = ""
    updated_at: str = ""

    @property
    def thickness(self) -> float:
        return round(self.base - self.top, 6)

    @property
    def middle_depth(self) -> float:
        return round((self.top + self.base) / 2.0, 6)


@dataclass(frozen=True)
class InterpretationIntervalSet:
    schema: str
    project_id: str
    well_id: str
    interpretation_id: str
    intervals: tuple[InterpretationInterval, ...]
    updated_at: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_interpretation_id(value: str) -> str:
    clean = str(value or DEFAULT_INTERPRETATION_ID).strip()
    if not clean or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in clean):
        raise ValueError("Некорректный идентификатор интерпретации.")
    return clean


def _storage_path(root: Path | str, project_id: str, well_id: str, interpretation_id: str) -> Path:
    return (
        Path(root)
        / safe_project_id(project_id)
        / "wells"
        / safe_well_id(well_id)
        / "interpretations"
        / _safe_interpretation_id(interpretation_id)
        / INTERPRETATION_INTERVALS_FILE_NAME
    )


def _normalize_uuid(value: str | None) -> str:
    if value is None or not str(value).strip():
        return str(uuid4())
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Некорректный UUID интервала.") from exc


def _clean_text(value: str, field_name: str, *, max_length: int, fallback: str = "") -> str:
    clean = str(value or "").strip()
    if len(clean) > max_length:
        raise ValueError(f"Поле «{field_name}» длиннее {max_length} символов.")
    return clean or fallback


def _normalize_color(value: str) -> str:
    clean = _clean_text(value, "Цвет", max_length=32, fallback="#4C78A8")
    if clean.startswith("#") and len(clean) in {4, 7, 9}:
        try:
            int(clean[1:], 16)
        except ValueError as exc:
            raise ValueError("Цвет должен быть корректным HEX-значением.") from exc
    return clean


def _validate_depths(top: float, base: float) -> tuple[float, float]:
    try:
        clean_top = float(top)
        clean_base = float(base)
    except (TypeError, ValueError) as exc:
        raise ValueError("Верх и низ интервала должны быть числовыми.") from exc
    if not clean_top < clean_base:
        raise ValueError("Верх интервала должен быть меньше низа.")
    return clean_top, clean_base


def build_interpretation_interval(
    *,
    label: str,
    top: float,
    base: float,
    interval_type: str = "undefined",
    color: str = "#4C78A8",
    comment: str = "",
    source: str = "manual",
    interval_id: str | None = None,
    created_at: str | None = None,
) -> InterpretationInterval:
    """Validate and construct one immutable interval with a stable UUID."""

    clean_top, clean_base = _validate_depths(top, base)
    now = _utc_now()
    return InterpretationInterval(
        id=_normalize_uuid(interval_id),
        label=_clean_text(label, "Подпись", max_length=160, fallback="Интервал"),
        top=clean_top,
        base=clean_base,
        interval_type=_clean_text(interval_type, "Тип", max_length=80, fallback="undefined"),
        color=_normalize_color(color),
        comment=_clean_text(comment, "Комментарий", max_length=2000),
        source=_clean_text(source, "Источник", max_length=80, fallback="manual"),
        created_at=created_at or now,
        updated_at=now,
    )


def _interval_from_dict(raw: dict[str, Any]) -> InterpretationInterval:
    return build_interpretation_interval(
        interval_id=str(raw.get("id", "")),
        label=str(raw.get("label", "")),
        top=raw.get("top"),
        base=raw.get("base"),
        interval_type=str(raw.get("interval_type", "undefined")),
        color=str(raw.get("color", "#4C78A8")),
        comment=str(raw.get("comment", "")),
        source=str(raw.get("source", "manual")),
        created_at=str(raw.get("created_at", "")) or None,
    )


def _empty_set(project_id: str, well_id: str, interpretation_id: str) -> InterpretationIntervalSet:
    return InterpretationIntervalSet(
        schema=INTERPRETATION_INTERVALS_SCHEMA,
        project_id=safe_project_id(project_id),
        well_id=safe_well_id(well_id),
        interpretation_id=_safe_interpretation_id(interpretation_id),
        intervals=(),
        updated_at="",
    )


def load_interpretation_intervals(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str = "",
    interpretation_id: str = DEFAULT_INTERPRETATION_ID,
) -> InterpretationIntervalSet:
    path = _storage_path(root, project_id, well_id, interpretation_id)
    if not path.exists():
        return _empty_set(project_id, well_id, interpretation_id)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Не удалось прочитать интервалы интерпретации: {path}") from exc
    if raw.get("schema") != INTERPRETATION_INTERVALS_SCHEMA:
        raise ValueError("Неподдерживаемая схема хранилища интервалов.")
    intervals = tuple(_interval_from_dict(item) for item in raw.get("intervals", ()))
    return InterpretationIntervalSet(
        schema=INTERPRETATION_INTERVALS_SCHEMA,
        project_id=safe_project_id(project_id),
        well_id=safe_well_id(well_id),
        interpretation_id=_safe_interpretation_id(interpretation_id),
        intervals=tuple(sorted(intervals, key=lambda item: (item.top, item.base, item.label.lower()))),
        updated_at=str(raw.get("updated_at", "")),
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
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


def save_interpretation_intervals(
    interval_set: InterpretationIntervalSet,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
) -> InterpretationIntervalSet:
    ids = [item.id for item in interval_set.intervals]
    if len(ids) != len(set(ids)):
        raise ValueError("UUID интервалов должны быть уникальными.")
    normalized = replace(
        interval_set,
        schema=INTERPRETATION_INTERVALS_SCHEMA,
        project_id=safe_project_id(interval_set.project_id),
        well_id=safe_well_id(interval_set.well_id),
        interpretation_id=_safe_interpretation_id(interval_set.interpretation_id),
        intervals=tuple(sorted(interval_set.intervals, key=lambda item: (item.top, item.base, item.label.lower()))),
        updated_at=_utc_now(),
    )
    payload = {
        "schema": normalized.schema,
        "project_id": normalized.project_id,
        "well_id": normalized.well_id,
        "interpretation_id": normalized.interpretation_id,
        "updated_at": normalized.updated_at,
        "intervals": [asdict(item) for item in normalized.intervals],
    }
    _atomic_write_json(
        _storage_path(root, normalized.project_id, normalized.well_id, normalized.interpretation_id),
        payload,
    )
    return normalized


def create_interpretation_interval(
    *,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str,
    interpretation_id: str = DEFAULT_INTERPRETATION_ID,
    label: str,
    top: float,
    base: float,
    interval_type: str = "undefined",
    color: str = "#4C78A8",
    comment: str = "",
    source: str = "manual",
) -> InterpretationInterval:
    current = load_interpretation_intervals(root, project_id, well_id, interpretation_id)
    interval = build_interpretation_interval(
        label=label,
        top=top,
        base=base,
        interval_type=interval_type,
        color=color,
        comment=comment,
        source=source,
    )
    save_interpretation_intervals(replace(current, intervals=(*current.intervals, interval)), root)
    return interval


def update_interpretation_interval(
    interval_id: str,
    *,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str,
    interpretation_id: str = DEFAULT_INTERPRETATION_ID,
    label: str,
    top: float,
    base: float,
    interval_type: str = "undefined",
    color: str = "#4C78A8",
    comment: str = "",
) -> InterpretationInterval:
    clean_id = _normalize_uuid(interval_id)
    current = load_interpretation_intervals(root, project_id, well_id, interpretation_id)
    existing = next((item for item in current.intervals if item.id == clean_id), None)
    if existing is None:
        raise KeyError(f"Интервал не найден: {clean_id}")
    updated = build_interpretation_interval(
        interval_id=existing.id,
        label=label,
        top=top,
        base=base,
        interval_type=interval_type,
        color=color,
        comment=comment,
        source=existing.source,
        created_at=existing.created_at,
    )
    save_interpretation_intervals(
        replace(current, intervals=tuple(updated if item.id == clean_id else item for item in current.intervals)),
        root,
    )
    return updated


def delete_interpretation_interval(
    interval_id: str,
    *,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str,
    interpretation_id: str = DEFAULT_INTERPRETATION_ID,
) -> bool:
    clean_id = _normalize_uuid(interval_id)
    current = load_interpretation_intervals(root, project_id, well_id, interpretation_id)
    remaining = tuple(item for item in current.intervals if item.id != clean_id)
    if len(remaining) == len(current.intervals):
        return False
    save_interpretation_intervals(replace(current, intervals=remaining), root)
    return True


def interpretation_interval_table_rows(intervals: Iterable[InterpretationInterval]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "label": item.label,
            "top": item.top,
            "base": item.base,
            "thickness": item.thickness,
            "middle_depth": item.middle_depth,
            "interval_type": item.interval_type,
            "color": item.color,
            "comment": item.comment,
            "source": item.source,
        }
        for item in intervals
    ]

from __future__ import annotations

"""Persistent saved views for manual interpretation interval filters."""

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from projects.interpretation_interval_analysis import InterpretationIntervalFilter
from projects.interpretation_intervals import DEFAULT_INTERPRETATION_ID, _safe_interpretation_id
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

FILTER_PRESET_SCHEMA = "gas-ratio-pro/interpretation-interval-filter-presets/v1"
FILTER_PRESET_EXCHANGE_SCHEMA = "gas-ratio-pro/interpretation-interval-filter-preset-exchange/v1"
FILTER_PRESET_FILE_NAME = "filter_presets.json"
MAX_PRESETS = 100


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean_name(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        raise ValueError("Название представления обязательно.")
    if len(name) > 120:
        raise ValueError("Название представления не должно превышать 120 символов.")
    return name


def _clean_string_tuple(values: Iterable[object] | None) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in (values or ()) if str(value).strip()))


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


@dataclass(frozen=True)
class InterpretationIntervalFilterPreset:
    id: str
    name: str
    criteria: InterpretationIntervalFilter
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "criteria": asdict(self.criteria),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def build_filter_preset(
    *,
    name: object,
    criteria: InterpretationIntervalFilter,
    preset_id: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> InterpretationIntervalFilterPreset:
    clean_id = str(preset_id or uuid.uuid4()).strip()
    try:
        uuid.UUID(clean_id)
    except (ValueError, AttributeError) as exc:
        raise ValueError("Некорректный UUID представления.") from exc
    now = _utc_now()
    normalized = InterpretationIntervalFilter(
        query=str(criteria.query or "").strip(),
        interval_types=_clean_string_tuple(criteria.interval_types),
        sources=_clean_string_tuple(criteria.sources),
        depth_top=_optional_float(criteria.depth_top),
        depth_base=_optional_float(criteria.depth_base),
        min_thickness=_optional_float(criteria.min_thickness),
        max_thickness=_optional_float(criteria.max_thickness),
    )
    return InterpretationIntervalFilterPreset(
        id=clean_id,
        name=_clean_name(name),
        criteria=normalized,
        created_at=str(created_at or now),
        updated_at=str(updated_at or now),
    )


def preset_from_mapping(payload: Mapping[str, Any]) -> InterpretationIntervalFilterPreset:
    raw_criteria = payload.get("criteria", {})
    if not isinstance(raw_criteria, Mapping):
        raise ValueError("Некорректные параметры представления.")
    return build_filter_preset(
        preset_id=str(payload.get("id", "")),
        name=payload.get("name", ""),
        criteria=InterpretationIntervalFilter(
            query=str(raw_criteria.get("query", "") or ""),
            interval_types=_clean_string_tuple(raw_criteria.get("interval_types", ())),
            sources=_clean_string_tuple(raw_criteria.get("sources", ())),
            depth_top=_optional_float(raw_criteria.get("depth_top")),
            depth_base=_optional_float(raw_criteria.get("depth_base")),
            min_thickness=_optional_float(raw_criteria.get("min_thickness")),
            max_thickness=_optional_float(raw_criteria.get("max_thickness")),
        ),
        created_at=str(payload.get("created_at", "") or _utc_now()),
        updated_at=str(payload.get("updated_at", "") or _utc_now()),
    )


class InterpretationIntervalFilterPresetRepository:
    def __init__(
        self,
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str = DEFAULT_PROJECT_ID,
        well_id: str = "",
        interpretation_id: str = DEFAULT_INTERPRETATION_ID,
    ) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)
        self.well_id = safe_well_id(well_id)
        self.interpretation_id = _safe_interpretation_id(interpretation_id)

    @property
    def path(self) -> Path:
        return (
            self.root
            / self.project_id
            / "wells"
            / self.well_id
            / "interpretations"
            / self.interpretation_id
            / FILTER_PRESET_FILE_NAME
        )

    def list(self) -> tuple[InterpretationIntervalFilterPreset, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"Не удалось прочитать сохранённые представления: {self.path}") from exc
        if payload.get("schema") != FILTER_PRESET_SCHEMA:
            raise ValueError("Неподдерживаемая схема сохранённых представлений.")
        rows = payload.get("presets", [])
        if not isinstance(rows, list):
            raise ValueError("Некорректный список сохранённых представлений.")
        presets = tuple(preset_from_mapping(row) for row in rows if isinstance(row, Mapping))
        return tuple(sorted(presets, key=lambda item: (item.name.casefold(), item.id)))

    def get(self, preset_id: str) -> InterpretationIntervalFilterPreset:
        for preset in self.list():
            if preset.id == preset_id:
                return preset
        raise KeyError(f"Представление не найдено: {preset_id}")

    def save(
        self,
        *,
        name: object,
        criteria: InterpretationIntervalFilter,
        preset_id: str | None = None,
    ) -> InterpretationIntervalFilterPreset:
        existing = {item.id: item for item in self.list()}
        prior = existing.get(str(preset_id or ""))
        preset = build_filter_preset(
            preset_id=prior.id if prior else preset_id,
            name=name,
            criteria=criteria,
            created_at=prior.created_at if prior else None,
        )
        existing[preset.id] = preset
        if len(existing) > MAX_PRESETS:
            raise ValueError(f"Допускается не более {MAX_PRESETS} сохранённых представлений.")
        self._write(existing.values())
        return preset

    def delete(self, preset_id: str) -> bool:
        presets = {item.id: item for item in self.list()}
        removed = presets.pop(str(preset_id), None) is not None
        if removed:
            self._write(presets.values())
        return removed

    def replace_all(self, presets: Iterable[InterpretationIntervalFilterPreset]) -> None:
        unique: dict[str, InterpretationIntervalFilterPreset] = {}
        for preset in presets:
            if preset.id in unique:
                raise ValueError(f"Повторяющийся UUID представления: {preset.id}")
            unique[preset.id] = preset
        if len(unique) > MAX_PRESETS:
            raise ValueError(f"Допускается не более {MAX_PRESETS} сохранённых представлений.")
        self._write(unique.values())

    def _write(self, presets: Iterable[InterpretationIntervalFilterPreset]) -> None:
        rows = sorted((item.to_dict() for item in presets), key=lambda row: (row["name"].casefold(), row["id"]))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": FILTER_PRESET_SCHEMA,
            "project_id": self.project_id,
            "well_id": self.well_id,
            "interpretation_id": self.interpretation_id,
            "updated_at": _utc_now(),
            "presets": rows,
        }
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.path)
        finally:
            temporary_path.unlink(missing_ok=True)


def export_filter_presets_json(
    presets: Iterable[InterpretationIntervalFilterPreset],
    *,
    project_id: str,
    well_id: str,
    interpretation_id: str,
) -> bytes:
    payload = {
        "schema": FILTER_PRESET_EXCHANGE_SCHEMA,
        "project_id": safe_project_id(project_id),
        "well_id": safe_well_id(well_id),
        "interpretation_id": _safe_interpretation_id(interpretation_id),
        "exported_at": _utc_now(),
        "presets": [item.to_dict() for item in presets],
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def import_filter_presets_json(data: bytes | str) -> tuple[InterpretationIntervalFilterPreset, ...]:
    try:
        text = data.decode("utf-8-sig") if isinstance(data, bytes) else str(data)
        payload = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Не удалось прочитать JSON представлений.") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != FILTER_PRESET_EXCHANGE_SCHEMA:
        raise ValueError("Неподдерживаемая схема импорта представлений.")
    rows = payload.get("presets", [])
    if not isinstance(rows, list):
        raise ValueError("Некорректный список представлений.")
    presets = tuple(preset_from_mapping(row) for row in rows if isinstance(row, Mapping))
    if len({item.id for item in presets}) != len(presets):
        raise ValueError("Импорт содержит повторяющиеся UUID представлений.")
    if len(presets) > MAX_PRESETS:
        raise ValueError(f"Допускается не более {MAX_PRESETS} сохранённых представлений.")
    return presets

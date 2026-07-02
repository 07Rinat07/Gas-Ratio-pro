from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from las_correlation.core import DEFAULT_GAS_GROUPS, DEFAULT_GIS_GROUPS


RangeValue = tuple[float, float] | None


@dataclass(frozen=True)
class LasCorrelationSettings:
    selected_well_names: tuple[str, ...] = ()
    curve_group_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    gis_groups: tuple[str, ...] = DEFAULT_GIS_GROUPS
    gas_groups: tuple[str, ...] = DEFAULT_GAS_GROUPS
    depth_range: RangeValue = None
    gis_x_range: RangeValue = None
    gas_x_range: RangeValue = None
    height_per_well: int = 430


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(str(item) for item in value if str(item))
    except TypeError:
        return ()


def _range_tuple(value: Any) -> RangeValue:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        left = float(value[0])
        right = float(value[1])
    except (TypeError, ValueError):
        return None
    if left == right:
        return None
    return (min(left, right), max(left, right))


def _overrides_dict(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, Mapping):
        return {}

    result: dict[str, dict[str, str]] = {}
    for well_name, overrides in value.items():
        if not isinstance(overrides, Mapping):
            continue
        clean_overrides = {
            str(curve): str(group)
            for curve, group in overrides.items()
            if str(curve) and str(group)
        }
        if clean_overrides:
            result[str(well_name)] = clean_overrides
    return result


def settings_to_dict(settings: LasCorrelationSettings) -> dict[str, Any]:
    return {
        "selected_well_names": list(settings.selected_well_names),
        "curve_group_overrides": {
            well_name: dict(overrides)
            for well_name, overrides in settings.curve_group_overrides.items()
            if overrides
        },
        "gis_groups": list(settings.gis_groups),
        "gas_groups": list(settings.gas_groups),
        "depth_range": list(settings.depth_range) if settings.depth_range is not None else None,
        "gis_x_range": list(settings.gis_x_range) if settings.gis_x_range is not None else None,
        "gas_x_range": list(settings.gas_x_range) if settings.gas_x_range is not None else None,
        "height_per_well": int(settings.height_per_well),
    }


def settings_from_dict(payload: Mapping[str, Any] | None) -> LasCorrelationSettings:
    payload = payload or {}
    try:
        height_per_well = int(payload.get("height_per_well", 430))
    except (TypeError, ValueError):
        height_per_well = 430

    return LasCorrelationSettings(
        selected_well_names=_string_tuple(payload.get("selected_well_names")),
        curve_group_overrides=_overrides_dict(payload.get("curve_group_overrides")),
        gis_groups=_string_tuple(payload.get("gis_groups")) or DEFAULT_GIS_GROUPS,
        gas_groups=_string_tuple(payload.get("gas_groups")) or DEFAULT_GAS_GROUPS,
        depth_range=_range_tuple(payload.get("depth_range")),
        gis_x_range=_range_tuple(payload.get("gis_x_range")),
        gas_x_range=_range_tuple(payload.get("gas_x_range")),
        height_per_well=max(320, min(750, height_per_well)),
    )


def settings_summary(settings: LasCorrelationSettings) -> tuple[str, ...]:
    selected_wells = ", ".join(settings.selected_well_names) if settings.selected_well_names else "все доступные"
    manual_override_count = sum(len(overrides) for overrides in settings.curve_group_overrides.values())
    summary = [
        f"Скважины: {selected_wells}.",
        f"ГИС слева: {', '.join(settings.gis_groups) if settings.gis_groups else 'не выбрано'}.",
        f"Газы справа: {', '.join(settings.gas_groups) if settings.gas_groups else 'не выбрано'}.",
        f"Ручные группы кривых: {manual_override_count}.",
        f"Диапазон глубины: {settings.depth_range if settings.depth_range is not None else 'весь интервал'}.",
        f"X-scale ГИС: {settings.gis_x_range if settings.gis_x_range is not None else 'авто'}.",
        f"X-scale газы: {settings.gas_x_range if settings.gas_x_range is not None else 'авто'}.",
        f"Высота на скважину: {settings.height_per_well}.",
    ]
    return tuple(summary)

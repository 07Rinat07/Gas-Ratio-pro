from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

import pandas as pd

from importers.header_detector import detect_header_row, prepare_dataframe_with_header
from importers.las_importer import load_las_raw
from mapping.curve_aliases import normalize_curve_name


CURVE_GROUP_LABELS: dict[str, str] = {
    "depth": "Глубина",
    "gamma": "Gamma ray / GR",
    "total_gas": "Total gas",
    "gas_component": "C1-C5",
    "gas_ratio": "Газовые коэффициенты",
    "resistivity": "Resistivity",
    "density_neutron": "Density / neutron",
    "drilling": "Буровые параметры",
    "lithology": "Литология",
    "other": "Прочие",
}

DEFAULT_GIS_GROUPS: tuple[str, ...] = ("gamma", "resistivity", "density_neutron")
DEFAULT_GAS_GROUPS: tuple[str, ...] = ("total_gas", "gas_component", "gas_ratio")

_GROUP_ALIASES: dict[str, tuple[str, ...]] = {
    "depth": ("dept", "depth", "md", "measureddepth", "tvd", "tvdss"),
    "gamma": ("gr", "gk", "gamma", "gammaray", "grc", "sgr", "cgr"),
    "total_gas": ("tgas", "totalgas", "total_gas", "tg", "gas", "gas_total"),
    "gas_component": (
        "c1",
        "c2",
        "c3",
        "ic4",
        "nc4",
        "ic5",
        "nc5",
        "ch4",
        "methane",
        "ethane",
        "propane",
        "isobutane",
        "nbutane",
        "isopentane",
        "npentane",
    ),
    "gas_ratio": (
        "wh",
        "wetness",
        "bh",
        "balance",
        "ch",
        "character",
        "bar2",
        "c1c2",
        "c1c3",
        "c1c4",
        "c1c5",
        "ioi",
        "inverseoilindicator",
    ),
    "resistivity": (
        "rt",
        "rd",
        "rs",
        "rdeep",
        "rshal",
        "rshallow",
        "p22h",
        "a40h",
        "rpd",
        "rat",
        "at90",
        "ph90",
    ),
    "density_neutron": ("rhob", "rhoz", "den", "density", "nphi", "tnph", "neutron", "dphi"),
    "drilling": ("rop", "wob", "rpm", "flow", "hookload", "torque"),
    "lithology": ("lith", "lithology", "lito", "литология"),
}

_ALIAS_LOOKUP = {
    normalize_curve_name(alias): group
    for group, aliases in _GROUP_ALIASES.items()
    for alias in aliases
}


@dataclass(frozen=True)
class LasCorrelationWell:
    name: str
    data: pd.DataFrame
    depth_column: str
    curve_groups: dict[str, tuple[str, ...]]
    row_count: int
    min_depth: float | None
    max_depth: float | None
    warnings: tuple[str, ...] = ()


def classify_curve_name(name: object) -> str:
    normalized = normalize_curve_name(name)
    if not normalized:
        return "other"

    exact_group = _ALIAS_LOOKUP.get(normalized)
    if exact_group is not None:
        return exact_group

    if normalized.startswith("c1") or normalized.startswith("c2") or normalized.startswith("c3"):
        return "gas_component"
    if normalized.startswith("ic4") or normalized.startswith("nc4"):
        return "gas_component"
    if normalized.startswith("ic5") or normalized.startswith("nc5"):
        return "gas_component"
    if normalized.startswith("gr") and len(normalized) <= 6:
        return "gamma"
    if normalized.startswith("r") and any(token in normalized for token in ("deep", "shal", "res", "t")):
        return "resistivity"
    return "other"


def group_curve_columns(columns: Iterable[object]) -> dict[str, tuple[str, ...]]:
    groups: dict[str, list[str]] = {group: [] for group in CURVE_GROUP_LABELS}
    for column in columns:
        column_name = str(column)
        groups[classify_curve_name(column_name)].append(column_name)
    return {group: tuple(values) for group, values in groups.items() if values}


def apply_curve_group_overrides(
    well: LasCorrelationWell,
    overrides: dict[str, str],
) -> LasCorrelationWell:
    groups: dict[str, list[str]] = {group: [] for group in CURVE_GROUP_LABELS}
    normalized_overrides = {str(column): group for column, group in overrides.items()}
    current_group_by_column = {
        column: group
        for group, columns in well.curve_groups.items()
        for column in columns
    }
    warnings = list(well.warnings)

    for column in well.data.columns:
        column_name = str(column)
        current_group = current_group_by_column.get(column_name, classify_curve_name(column_name))
        target_group = normalized_overrides.get(column_name, current_group)
        if target_group not in CURVE_GROUP_LABELS:
            warnings.append(
                f"Кривая {column_name}: группа {target_group} не поддерживается, использована `Прочие`."
            )
            target_group = "other"
        groups[target_group].append(column_name)

    return replace(
        well,
        curve_groups={group: tuple(values) for group, values in groups.items() if values},
        warnings=tuple(dict.fromkeys(warnings)),
    )


def curve_group_rows(well: LasCorrelationWell) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    group_by_column = {
        column: group
        for group, columns in well.curve_groups.items()
        for column in columns
    }
    for column in well.data.columns:
        column_name = str(column)
        group = group_by_column.get(column_name, "other")
        rows.append(
            {
                "curve": column_name,
                "group": group,
                "group_label": CURVE_GROUP_LABELS.get(group, group),
                "is_depth": "yes" if column_name == well.depth_column else "no",
            }
        )
    return tuple(rows)


def _source_name(file_or_path, fallback_index: int | None = None) -> str:
    raw_name = getattr(file_or_path, "name", None)
    if raw_name:
        return Path(str(raw_name)).stem
    if isinstance(file_or_path, (str, Path)):
        return Path(file_or_path).stem
    return f"LAS {fallback_index}" if fallback_index is not None else "LAS"


def _find_depth_column(groups: dict[str, tuple[str, ...]], columns: Iterable[object]) -> str:
    depth_columns = groups.get("depth", ())
    if depth_columns:
        return depth_columns[0]
    column_names = [str(column) for column in columns]
    return column_names[0] if column_names else ""


def _numeric_depth(data: pd.DataFrame, depth_column: str) -> pd.Series:
    if depth_column not in data.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(data[depth_column], errors="coerce")


def prepare_las_correlation_well(file_or_path, name: str | None = None) -> LasCorrelationWell:
    raw_df = load_las_raw(file_or_path)
    header = detect_header_row(raw_df)
    data = prepare_dataframe_with_header(raw_df, header.header_row)
    curve_groups = group_curve_columns(data.columns)
    depth_column = _find_depth_column(curve_groups, data.columns)
    warnings: list[str] = []

    if data.empty:
        warnings.append("LAS прочитан, но таблица кривых пустая.")

    depth = _numeric_depth(data, depth_column)
    if depth.empty or depth.isna().all():
        min_depth = None
        max_depth = None
        warnings.append("Не найдена числовая кривая глубины для корреляции.")
    else:
        data = data.copy()
        data[depth_column] = depth
        data = data.dropna(subset=[depth_column]).sort_values(depth_column).reset_index(drop=True)
        min_depth = float(data[depth_column].min())
        max_depth = float(data[depth_column].max())

    return LasCorrelationWell(
        name=name or _source_name(file_or_path),
        data=data,
        depth_column=depth_column,
        curve_groups=curve_groups,
        row_count=len(data),
        min_depth=min_depth,
        max_depth=max_depth,
        warnings=tuple(warnings),
    )


def prepare_las_correlation_wells(files: Iterable[object]) -> tuple[LasCorrelationWell, ...]:
    wells: list[LasCorrelationWell] = []
    used_names: set[str] = set()
    for index, file_or_path in enumerate(files, start=1):
        base_name = _source_name(file_or_path, index)
        name = base_name
        duplicate_index = 2
        while name in used_names:
            name = f"{base_name} ({duplicate_index})"
            duplicate_index += 1
        used_names.add(name)
        wells.append(prepare_las_correlation_well(file_or_path, name=name))
    return tuple(wells)

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


def curve_columns_for_groups(well: LasCorrelationWell, groups: Iterable[str]) -> tuple[str, ...]:
    columns: list[str] = []
    for group in groups:
        columns.extend(well.curve_groups.get(group, ()))
    return tuple(dict.fromkeys(columns))


def curve_names_for_comparison(
    wells: Iterable[LasCorrelationWell],
    *,
    groups: Iterable[str] | None = None,
) -> tuple[str, ...]:
    selected_groups = tuple(groups) if groups is not None else None
    curve_names: list[str] = []

    for well in wells:
        if well.data.empty:
            continue
        if selected_groups is None:
            candidate_columns = tuple(str(column) for column in well.data.columns)
        else:
            candidate_columns = curve_columns_for_groups(well, selected_groups)

        for column in candidate_columns:
            if column == well.depth_column or column not in well.data.columns:
                continue
            values = pd.to_numeric(well.data[column], errors="coerce")
            if values.empty or values.isna().all():
                continue
            curve_names.append(column)

    return tuple(dict.fromkeys(curve_names))


def build_las_correlation_interval_table(
    wells: Iterable[LasCorrelationWell],
    *,
    groups: Iterable[str] | None = None,
    depth_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    selected_groups = tuple(groups) if groups is not None else None
    frames: list[pd.DataFrame] = []

    for well in wells:
        if well.data.empty or not well.depth_column or well.depth_column not in well.data.columns:
            continue

        depth = _numeric_depth(well.data, well.depth_column)
        mask = depth.notna()
        if depth_range is not None:
            top_depth, bottom_depth = sorted((float(depth_range[0]), float(depth_range[1])))
            mask &= depth.between(top_depth, bottom_depth, inclusive="both")

        if selected_groups is None:
            selected_columns = tuple(str(column) for column in well.data.columns)
        else:
            selected_columns = (well.depth_column, *curve_columns_for_groups(well, selected_groups))
        existing_columns = [column for column in dict.fromkeys(selected_columns) if column in well.data.columns]
        if well.depth_column not in existing_columns:
            existing_columns.insert(0, well.depth_column)

        interval_data = well.data.loc[mask, existing_columns].copy()
        if interval_data.empty:
            continue
        interval_data.loc[:, well.depth_column] = depth.loc[interval_data.index]
        interval_data = interval_data.rename(columns={well.depth_column: "depth"})
        interval_data.insert(0, "well", well.name)
        frames.append(interval_data)

    if not frames:
        return pd.DataFrame(columns=["well", "depth"])
    return pd.concat(frames, ignore_index=True)


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


@dataclass(frozen=True)
class CorrelationMarker:
    well: str
    name: str
    depth: float
    kind: str = "marker"
    color: str = "#FBBF24"
    note: str = ""


@dataclass(frozen=True)
class CorrelationPanel:
    wells: tuple[LasCorrelationWell, ...]
    markers: tuple[CorrelationMarker, ...]
    depth_range: tuple[float, float] | None
    common_curves: tuple[str, ...]
    shared_depth_grid: tuple[float, ...]
    warnings: tuple[str, ...] = ()


def normalize_correlation_markers(rows: Iterable[dict[str, object]]) -> tuple[CorrelationMarker, ...]:
    markers: list[CorrelationMarker] = []
    for row in rows:
        try:
            depth = float(row.get("depth", ""))
        except (TypeError, ValueError):
            continue
        if pd.isna(depth):
            continue
        name = str(row.get("name") or row.get("marker") or row.get("top") or "Marker").strip()
        well = str(row.get("well") or "").strip()
        kind = str(row.get("kind") or row.get("type") or "marker").strip() or "marker"
        color = str(row.get("color") or "#FBBF24").strip() or "#FBBF24"
        note = str(row.get("note") or "").strip()
        markers.append(CorrelationMarker(well=well, name=name, depth=depth, kind=kind, color=color, note=note))
    return tuple(sorted(markers, key=lambda marker: (marker.well, marker.depth, marker.name)))


def shared_depth_range(wells: Iterable[LasCorrelationWell]) -> tuple[float, float] | None:
    valid_ranges = [
        (well.min_depth, well.max_depth)
        for well in wells
        if well.min_depth is not None and well.max_depth is not None
    ]
    if not valid_ranges:
        return None
    top = min(float(start) for start, _ in valid_ranges)
    bottom = max(float(stop) for _, stop in valid_ranges)
    return (top, bottom)


def overlapping_depth_range(wells: Iterable[LasCorrelationWell]) -> tuple[float, float] | None:
    valid_ranges = [
        (well.min_depth, well.max_depth)
        for well in wells
        if well.min_depth is not None and well.max_depth is not None
    ]
    if not valid_ranges:
        return None
    top = max(float(start) for start, _ in valid_ranges)
    bottom = min(float(stop) for _, stop in valid_ranges)
    if top > bottom:
        return None
    return (top, bottom)


def build_shared_depth_grid(
    wells: Iterable[LasCorrelationWell],
    *,
    step: float | None = None,
    depth_range: tuple[float, float] | None = None,
    mode: str = "union",
) -> tuple[float, ...]:
    selected_wells = tuple(wells)
    if depth_range is None:
        depth_range = overlapping_depth_range(selected_wells) if mode == "overlap" else shared_depth_range(selected_wells)
    if depth_range is None:
        return ()

    top, bottom = sorted((float(depth_range[0]), float(depth_range[1])))
    if step is None or step <= 0:
        deltas: list[float] = []
        for well in selected_wells:
            if well.data.empty or well.depth_column not in well.data.columns:
                continue
            depth = _numeric_depth(well.data, well.depth_column).dropna().sort_values()
            diff = depth.diff().dropna()
            diff = diff[diff > 0]
            if not diff.empty:
                deltas.append(float(diff.median()))
        step = min(deltas) if deltas else max((bottom - top), 1.0)
    if step <= 0:
        return ()

    values: list[float] = []
    current = top
    guard = 0
    while current <= bottom + step / 2 and guard < 1_000_000:
        values.append(round(current, 6))
        current += step
        guard += 1
    return tuple(values)


def common_curve_names(
    wells: Iterable[LasCorrelationWell],
    *,
    groups: Iterable[str] | None = None,
    require_all_wells: bool = False,
) -> tuple[str, ...]:
    selected_wells = [well for well in wells if not well.data.empty]
    if not selected_wells:
        return ()

    curve_sets: list[set[str]] = []
    for well in selected_wells:
        curves = set(curve_names_for_comparison([well], groups=groups))
        curve_sets.append(curves)
    if not curve_sets:
        return ()
    if require_all_wells:
        selected = set.intersection(*curve_sets) if curve_sets else set()
    else:
        selected = set.union(*curve_sets) if curve_sets else set()
    ordered: list[str] = []
    for well in selected_wells:
        for curve in curve_names_for_comparison([well], groups=groups):
            if curve in selected and curve not in ordered:
                ordered.append(curve)
    return tuple(ordered)


def build_correlation_panel(
    wells: Iterable[LasCorrelationWell],
    *,
    markers: Iterable[dict[str, object]] | Iterable[CorrelationMarker] = (),
    depth_range: tuple[float, float] | None = None,
    depth_step: float | None = None,
    groups: Iterable[str] | None = None,
    require_common_curves: bool = False,
    grid_mode: str = "union",
) -> CorrelationPanel:
    selected_wells = tuple(wells)
    warnings: list[str] = []
    if depth_range is None:
        depth_range = overlapping_depth_range(selected_wells) if grid_mode == "overlap" else shared_depth_range(selected_wells)
    if depth_range is None:
        warnings.append("Нет общего диапазона глубин для корреляционной панели.")

    normalized_markers: list[CorrelationMarker] = []
    for marker in markers:
        if isinstance(marker, CorrelationMarker):
            normalized_markers.append(marker)
        else:
            normalized_markers.extend(normalize_correlation_markers([marker]))

    common_curves = common_curve_names(selected_wells, groups=groups, require_all_wells=require_common_curves)
    if not common_curves:
        warnings.append("Нет числовых кривых для межскважинного сравнения.")

    grid = build_shared_depth_grid(selected_wells, step=depth_step, depth_range=depth_range, mode=grid_mode)
    if not grid:
        warnings.append("Не удалось построить общую глубинную сетку.")

    return CorrelationPanel(
        wells=selected_wells,
        markers=tuple(sorted(normalized_markers, key=lambda item: (item.depth, item.well, item.name))),
        depth_range=depth_range,
        common_curves=common_curves,
        shared_depth_grid=grid,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def correlation_marker_rows(panel: CorrelationPanel) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for marker in panel.markers:
        rows.append(
            {
                "well": marker.well or "Все скважины",
                "name": marker.name,
                "depth": marker.depth,
                "kind": marker.kind,
                "color": marker.color,
                "note": marker.note,
            }
        )
    return tuple(rows)


def correlation_panel_summary(panel: CorrelationPanel) -> dict[str, object]:
    return {
        "wells": len(panel.wells),
        "markers": len(panel.markers),
        "depth_range": panel.depth_range,
        "common_curves": panel.common_curves,
        "grid_points": len(panel.shared_depth_grid),
        "warnings": panel.warnings,
    }

@dataclass(frozen=True)
class CorrelationLine:
    """Manual or generated correlation tie between two wells at marker depths."""

    source_well: str
    target_well: str
    name: str
    source_depth: float
    target_depth: float
    kind: str = "correlation"
    color: str = "#38BDF8"
    style: str = "solid"
    confidence: float = 1.0
    note: str = ""


@dataclass(frozen=True)
class DepthAlignment:
    """Depth shift definition used to align a well to a reference horizon."""

    well: str
    shift: float = 0.0
    reference: str = "manual"
    note: str = ""


def normalize_correlation_lines(rows: Iterable[dict[str, object]]) -> tuple[CorrelationLine, ...]:
    """Normalize editable correlation line rows from UI/import tables."""

    lines: list[CorrelationLine] = []
    for row in rows:
        try:
            source_depth = float(row.get("source_depth", row.get("from_depth", "")))
            target_depth = float(row.get("target_depth", row.get("to_depth", "")))
        except (TypeError, ValueError):
            continue
        if pd.isna(source_depth) or pd.isna(target_depth):
            continue

        source_well = str(row.get("source_well") or row.get("from_well") or "").strip()
        target_well = str(row.get("target_well") or row.get("to_well") or "").strip()
        if not source_well or not target_well or source_well == target_well:
            continue

        try:
            confidence = float(row.get("confidence", 1.0))
        except (TypeError, ValueError):
            confidence = 1.0
        confidence = max(0.0, min(1.0, confidence))

        lines.append(
            CorrelationLine(
                source_well=source_well,
                target_well=target_well,
                name=str(row.get("name") or row.get("marker") or "Correlation").strip() or "Correlation",
                source_depth=source_depth,
                target_depth=target_depth,
                kind=str(row.get("kind") or row.get("type") or "correlation").strip() or "correlation",
                color=str(row.get("color") or "#38BDF8").strip() or "#38BDF8",
                style=str(row.get("style") or "solid").strip() or "solid",
                confidence=confidence,
                note=str(row.get("note") or "").strip(),
            )
        )
    return tuple(sorted(lines, key=lambda line: (line.source_well, line.target_well, line.source_depth, line.name)))


def normalize_depth_alignments(rows: Iterable[dict[str, object]]) -> tuple[DepthAlignment, ...]:
    """Normalize manual depth alignment rows from UI/import tables."""

    alignments: list[DepthAlignment] = []
    for row in rows:
        well = str(row.get("well") or row.get("name") or "").strip()
        if not well:
            continue
        try:
            shift = float(row.get("shift", row.get("depth_shift", 0.0)))
        except (TypeError, ValueError):
            shift = 0.0
        if pd.isna(shift):
            shift = 0.0
        alignments.append(
            DepthAlignment(
                well=well,
                shift=shift,
                reference=str(row.get("reference") or "manual").strip() or "manual",
                note=str(row.get("note") or "").strip(),
            )
        )
    return tuple(alignments)


def apply_depth_alignment(well: LasCorrelationWell, alignment: DepthAlignment | float) -> LasCorrelationWell:
    """Return a copy of the well with its depth curve shifted by alignment.shift."""

    shift = float(alignment.shift if isinstance(alignment, DepthAlignment) else alignment)
    if well.data.empty or not well.depth_column or well.depth_column not in well.data.columns:
        return well
    data = well.data.copy()
    depth = _numeric_depth(data, well.depth_column) + shift
    data[well.depth_column] = depth
    data = data.dropna(subset=[well.depth_column]).sort_values(well.depth_column).reset_index(drop=True)
    min_depth = float(data[well.depth_column].min()) if not data.empty else None
    max_depth = float(data[well.depth_column].max()) if not data.empty else None
    warning = f"Скважина {well.name}: применено смещение глубины {shift:+.3f} м."
    return replace(
        well,
        data=data,
        min_depth=min_depth,
        max_depth=max_depth,
        warnings=tuple(dict.fromkeys((*well.warnings, warning))),
    )


def apply_depth_alignments(
    wells: Iterable[LasCorrelationWell],
    alignments: Iterable[DepthAlignment] | dict[str, float],
) -> tuple[LasCorrelationWell, ...]:
    """Apply per-well depth shifts and preserve wells without configured shifts."""

    if isinstance(alignments, dict):
        alignment_map = {str(well): DepthAlignment(well=str(well), shift=float(shift)) for well, shift in alignments.items()}
    else:
        alignment_map = {alignment.well: alignment for alignment in alignments}

    aligned_wells: list[LasCorrelationWell] = []
    for well in wells:
        alignment = alignment_map.get(well.name)
        aligned_wells.append(apply_depth_alignment(well, alignment) if alignment is not None else well)
    return tuple(aligned_wells)


def build_correlation_lines_from_markers(
    markers: Iterable[CorrelationMarker],
    *,
    well_order: Iterable[str] = (),
) -> tuple[CorrelationLine, ...]:
    """Create adjacent-well correlation lines from markers with matching names."""

    order = {well: index for index, well in enumerate(well_order)}
    grouped: dict[tuple[str, str], list[CorrelationMarker]] = {}
    for marker in markers:
        if not marker.well:
            continue
        grouped.setdefault((marker.kind, marker.name), []).append(marker)

    lines: list[CorrelationLine] = []
    for (kind, name), marker_group in grouped.items():
        sorted_group = sorted(marker_group, key=lambda item: (order.get(item.well, 10_000), item.well, item.depth))
        for left, right in zip(sorted_group, sorted_group[1:]):
            lines.append(
                CorrelationLine(
                    source_well=left.well,
                    target_well=right.well,
                    name=name,
                    kind=kind,
                    source_depth=left.depth,
                    target_depth=right.depth,
                    color=left.color or right.color,
                    confidence=1.0,
                )
            )
    return tuple(lines)


def correlation_line_rows(lines: Iterable[CorrelationLine]) -> tuple[dict[str, object], ...]:
    """Return tabular rows suitable for Streamlit/CSV export."""

    return tuple(
        {
            "source_well": line.source_well,
            "target_well": line.target_well,
            "name": line.name,
            "source_depth": line.source_depth,
            "target_depth": line.target_depth,
            "kind": line.kind,
            "color": line.color,
            "style": line.style,
            "confidence": line.confidence,
            "note": line.note,
        }
        for line in lines
    )


def validate_correlation_lines(
    lines: Iterable[CorrelationLine],
    wells: Iterable[LasCorrelationWell],
) -> dict[str, tuple[str, ...]]:
    """Validate well names, depth intervals and line crossing within pair groups."""

    well_ranges = {
        well.name: (well.min_depth, well.max_depth)
        for well in wells
        if well.min_depth is not None and well.max_depth is not None
    }
    errors: list[str] = []
    warnings: list[str] = []
    by_pair: dict[tuple[str, str], list[CorrelationLine]] = {}

    for line in lines:
        if line.source_well not in well_ranges:
            errors.append(f"Линия {line.name}: исходная скважина {line.source_well} отсутствует.")
            continue
        if line.target_well not in well_ranges:
            errors.append(f"Линия {line.name}: целевая скважина {line.target_well} отсутствует.")
            continue
        source_top, source_bottom = well_ranges[line.source_well]
        target_top, target_bottom = well_ranges[line.target_well]
        if not (float(source_top) <= line.source_depth <= float(source_bottom)):
            warnings.append(f"Линия {line.name}: глубина {line.source_depth:g} вне интервала {line.source_well}.")
        if not (float(target_top) <= line.target_depth <= float(target_bottom)):
            warnings.append(f"Линия {line.name}: глубина {line.target_depth:g} вне интервала {line.target_well}.")
        if line.confidence < 0.5:
            warnings.append(f"Линия {line.name}: низкая уверенность {line.confidence:.2f}.")
        by_pair.setdefault((line.source_well, line.target_well), []).append(line)

    for (source_well, target_well), pair_lines in by_pair.items():
        ordered = sorted(pair_lines, key=lambda item: item.source_depth)
        previous_target = None
        previous_name = ""
        for line in ordered:
            if previous_target is not None and line.target_depth < previous_target:
                warnings.append(
                    f"Пара {source_well}→{target_well}: возможное пересечение линий {previous_name} и {line.name}."
                )
            previous_target = line.target_depth
            previous_name = line.name

    return {"errors": tuple(dict.fromkeys(errors)), "warnings": tuple(dict.fromkeys(warnings))}


def build_correlation_studio_state(
    wells: Iterable[LasCorrelationWell],
    *,
    marker_rows: Iterable[dict[str, object]] = (),
    line_rows: Iterable[dict[str, object]] = (),
    alignment_rows: Iterable[dict[str, object]] = (),
    depth_step: float | None = None,
    groups: Iterable[str] | None = None,
    grid_mode: str = "union",
) -> dict[str, object]:
    """Build a single serializable state object for Correlation Studio Professional."""

    alignments = normalize_depth_alignments(alignment_rows)
    aligned_wells = apply_depth_alignments(tuple(wells), alignments)
    markers = normalize_correlation_markers(marker_rows)
    manual_lines = normalize_correlation_lines(line_rows)
    generated_lines = build_correlation_lines_from_markers(markers, well_order=[well.name for well in aligned_wells])
    panel = build_correlation_panel(
        aligned_wells,
        markers=markers,
        depth_step=depth_step,
        groups=groups,
        grid_mode=grid_mode,
    )
    lines = tuple(dict.fromkeys((*manual_lines, *generated_lines)))
    validation = validate_correlation_lines(lines, aligned_wells)
    return {
        "wells": aligned_wells,
        "panel": panel,
        "markers": markers,
        "lines": lines,
        "alignments": alignments,
        "validation": validation,
        "summary": {
            **correlation_panel_summary(panel),
            "lines": len(lines),
            "aligned_wells": len(alignments),
            "errors": len(validation["errors"]),
            "warnings": len(validation["warnings"]),
        },
    }

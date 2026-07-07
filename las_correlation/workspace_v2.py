from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import pandas as pd

from las_correlation.core import (
    CorrelationLine,
    LasCorrelationWell,
    build_correlation_lines_from_markers,
    build_correlation_panel,
    correlation_line_rows,
    normalize_correlation_lines,
    validate_correlation_lines,
    CorrelationMarker,
)

SUPPORTED_BOUNDARY_TYPES: tuple[str, ...] = ("top", "base")
SUPPORTED_FLUID_CONTACT_TYPES: tuple[str, ...] = (
    "OWC",  # oil-water contact / ВНК
    "GOC",  # gas-oil contact / ГНК
    "GWC",  # gas-water contact / ГВК
    "oil",
    "gas",
    "water",
    "gas_condensate",
)

_DEFAULT_FLUID_COLORS: dict[str, str] = {
    "OWC": "#2563EB",
    "GOC": "#F97316",
    "GWC": "#06B6D4",
    "oil": "#16A34A",
    "gas": "#FBBF24",
    "water": "#3B82F6",
    "gas_condensate": "#A855F7",
}


@dataclass(frozen=True)
class StratigraphicBoundary:
    """Top/base marker used for manual and automatic interwell correlation."""

    well: str
    name: str
    depth: float
    boundary_type: str = "top"
    color: str = "#FBBF24"
    note: str = ""


@dataclass(frozen=True)
class LithologyInterval:
    """Lithology interval displayed as a colored fill on correlation tablets."""

    well: str
    top_depth: float
    base_depth: float
    lithology: str
    color: str = "#D6D3D1"
    note: str = ""


@dataclass(frozen=True)
class FluidContact:
    """Reservoir fluid/contact marker: OWC, GOC, GWC, oil, gas, water or gas-condensate."""

    well: str
    name: str
    depth: float
    contact_type: str
    color: str
    note: str = ""


@dataclass(frozen=True)
class CorrelationWorkspaceV2State:
    """Serializable backend state for Correlation Workspace 2.0."""

    wells: tuple[LasCorrelationWell, ...]
    boundaries: tuple[StratigraphicBoundary, ...]
    lithology_intervals: tuple[LithologyInterval, ...]
    fluid_contacts: tuple[FluidContact, ...]
    lines: tuple[CorrelationLine, ...]
    result_rows: tuple[dict[str, object], ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]


def _string_value(row: Mapping[str, object], *keys: str, default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _float_value(row: Mapping[str, object], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None or str(value).strip() == "":
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if not pd.isna(numeric):
            return numeric
    return None


def normalize_stratigraphic_boundaries(rows: Iterable[Mapping[str, object]]) -> tuple[StratigraphicBoundary, ...]:
    """Normalize top/base rows from UI tables, CSV import or persisted JSON."""

    boundaries: list[StratigraphicBoundary] = []
    for row in rows:
        well = _string_value(row, "well", "well_name")
        name = _string_value(row, "name", "horizon", "layer", "formation", default="Boundary")
        depth = _float_value(row, "depth", "md", "top_depth")
        if not well or depth is None:
            continue
        boundary_type = _string_value(row, "boundary_type", "type", "kind", default="top").lower()
        if boundary_type not in SUPPORTED_BOUNDARY_TYPES:
            boundary_type = "top"
        boundaries.append(
            StratigraphicBoundary(
                well=well,
                name=name,
                depth=depth,
                boundary_type=boundary_type,
                color=_string_value(row, "color", default="#FBBF24"),
                note=_string_value(row, "note", "comment"),
            )
        )
    return tuple(sorted(boundaries, key=lambda item: (item.name, item.boundary_type, item.well, item.depth)))


def normalize_lithology_intervals(rows: Iterable[Mapping[str, object]]) -> tuple[LithologyInterval, ...]:
    """Normalize lithology intervals and ensure top_depth <= base_depth."""

    intervals: list[LithologyInterval] = []
    for row in rows:
        well = _string_value(row, "well", "well_name")
        top = _float_value(row, "top_depth", "top", "from_depth")
        base = _float_value(row, "base_depth", "base", "bottom", "to_depth")
        lithology = _string_value(row, "lithology", "rock", "facies", default="Lithology")
        if not well or top is None or base is None or top == base:
            continue
        top_depth, base_depth = sorted((top, base))
        intervals.append(
            LithologyInterval(
                well=well,
                top_depth=top_depth,
                base_depth=base_depth,
                lithology=lithology,
                color=_string_value(row, "color", default="#D6D3D1"),
                note=_string_value(row, "note", "comment"),
            )
        )
    return tuple(sorted(intervals, key=lambda item: (item.well, item.top_depth, item.base_depth, item.lithology)))


def normalize_fluid_contacts(rows: Iterable[Mapping[str, object]]) -> tuple[FluidContact, ...]:
    """Normalize fluid contact rows for OWC/GOC/GWC and reservoir fluid annotations."""

    contacts: list[FluidContact] = []
    for row in rows:
        well = _string_value(row, "well", "well_name")
        depth = _float_value(row, "depth", "md")
        contact_type = _string_value(row, "contact_type", "type", "kind", default="OWC")
        if contact_type.lower() in {"owc", "внк"}:
            contact_type = "OWC"
        elif contact_type.lower() in {"goc", "гнк"}:
            contact_type = "GOC"
        elif contact_type.lower() in {"gwc", "гвк"}:
            contact_type = "GWC"
        elif contact_type not in SUPPORTED_FLUID_CONTACT_TYPES:
            contact_type = "OWC"
        if not well or depth is None:
            continue
        contacts.append(
            FluidContact(
                well=well,
                name=_string_value(row, "name", default=contact_type),
                depth=depth,
                contact_type=contact_type,
                color=_string_value(row, "color", default=_DEFAULT_FLUID_COLORS.get(contact_type, "#2563EB")),
                note=_string_value(row, "note", "comment"),
            )
        )
    return tuple(sorted(contacts, key=lambda item: (item.well, item.depth, item.contact_type, item.name)))


def boundaries_to_markers(boundaries: Iterable[StratigraphicBoundary]) -> tuple[CorrelationMarker, ...]:
    """Convert stratigraphic top/base definitions to existing correlation markers."""

    return tuple(
        CorrelationMarker(
            well=item.well,
            name=item.name,
            depth=item.depth,
            kind=item.boundary_type,
            color=item.color,
            note=item.note,
        )
        for item in boundaries
    )


def _well_ranges(wells: Iterable[LasCorrelationWell]) -> dict[str, tuple[float, float]]:
    return {
        well.name: (float(well.min_depth), float(well.max_depth))
        for well in wells
        if well.min_depth is not None and well.max_depth is not None
    }


def validate_correlation_workspace_v2(
    wells: Iterable[LasCorrelationWell],
    *,
    boundaries: Iterable[StratigraphicBoundary] = (),
    lithology_intervals: Iterable[LithologyInterval] = (),
    fluid_contacts: Iterable[FluidContact] = (),
    lines: Iterable[CorrelationLine] = (),
) -> dict[str, tuple[str, ...]]:
    """Validate V2 correlation objects against known wells and depth intervals."""

    ranges = _well_ranges(wells)
    errors: list[str] = []
    warnings: list[str] = []

    def check_depth(well: str, depth: float, label: str) -> None:
        if well not in ranges:
            errors.append(f"{label}: скважина {well} отсутствует.")
            return
        top, base = ranges[well]
        if not (top <= depth <= base):
            warnings.append(f"{label}: глубина {depth:g} вне интервала скважины {well}.")

    for boundary in boundaries:
        check_depth(boundary.well, boundary.depth, f"Граница {boundary.name}")
    for contact in fluid_contacts:
        check_depth(contact.well, contact.depth, f"Контакт {contact.name}")
    for interval in lithology_intervals:
        if interval.well not in ranges:
            errors.append(f"Литология {interval.lithology}: скважина {interval.well} отсутствует.")
            continue
        top, base = ranges[interval.well]
        if interval.top_depth < top or interval.base_depth > base:
            warnings.append(
                f"Литология {interval.lithology}: интервал {interval.top_depth:g}-{interval.base_depth:g} "
                f"выходит за диапазон {interval.well}."
            )

    line_validation = validate_correlation_lines(lines, tuple(wells))
    errors.extend(line_validation["errors"])
    warnings.extend(line_validation["warnings"])
    return {"errors": tuple(dict.fromkeys(errors)), "warnings": tuple(dict.fromkeys(warnings))}


def build_correlation_result_table(
    *,
    boundaries: Iterable[StratigraphicBoundary] = (),
    lithology_intervals: Iterable[LithologyInterval] = (),
    fluid_contacts: Iterable[FluidContact] = (),
    lines: Iterable[CorrelationLine] = (),
) -> tuple[dict[str, object], ...]:
    """Build a single result table for UI, export and professional printing."""

    rows: list[dict[str, object]] = []
    for boundary in boundaries:
        rows.append(
            {
                "object_type": "boundary",
                "well": boundary.well,
                "name": boundary.name,
                "top_depth": boundary.depth,
                "base_depth": boundary.depth,
                "category": boundary.boundary_type,
                "color": boundary.color,
                "note": boundary.note,
            }
        )
    for interval in lithology_intervals:
        rows.append(
            {
                "object_type": "lithology",
                "well": interval.well,
                "name": interval.lithology,
                "top_depth": interval.top_depth,
                "base_depth": interval.base_depth,
                "category": "lithology",
                "color": interval.color,
                "note": interval.note,
            }
        )
    for contact in fluid_contacts:
        rows.append(
            {
                "object_type": "fluid_contact",
                "well": contact.well,
                "name": contact.name,
                "top_depth": contact.depth,
                "base_depth": contact.depth,
                "category": contact.contact_type,
                "color": contact.color,
                "note": contact.note,
            }
        )
    for line_row in correlation_line_rows(lines):
        rows.append({"object_type": "correlation_line", **line_row})
    return tuple(rows)


def build_correlation_workspace_v2(
    wells: Iterable[LasCorrelationWell],
    *,
    boundary_rows: Iterable[Mapping[str, object]] = (),
    lithology_rows: Iterable[Mapping[str, object]] = (),
    fluid_contact_rows: Iterable[Mapping[str, object]] = (),
    line_rows: Iterable[Mapping[str, object]] = (),
    depth_step: float | None = None,
    grid_mode: str = "union",
) -> CorrelationWorkspaceV2State:
    """Build Correlation Workspace 2.0 backend state without mutating source LAS data."""

    selected_wells = tuple(wells)
    boundaries = normalize_stratigraphic_boundaries(boundary_rows)
    lithology_intervals = normalize_lithology_intervals(lithology_rows)
    fluid_contacts = normalize_fluid_contacts(fluid_contact_rows)
    manual_lines = normalize_correlation_lines(line_rows)
    generated_lines = build_correlation_lines_from_markers(
        boundaries_to_markers(boundaries),
        well_order=[well.name for well in selected_wells],
    )
    lines = tuple(dict.fromkeys((*manual_lines, *generated_lines)))
    panel = build_correlation_panel(
        selected_wells,
        markers=boundaries_to_markers(boundaries),
        depth_step=depth_step,
        grid_mode=grid_mode,
    )
    validation = validate_correlation_workspace_v2(
        selected_wells,
        boundaries=boundaries,
        lithology_intervals=lithology_intervals,
        fluid_contacts=fluid_contacts,
        lines=lines,
    )
    result_rows = build_correlation_result_table(
        boundaries=boundaries,
        lithology_intervals=lithology_intervals,
        fluid_contacts=fluid_contacts,
        lines=lines,
    )
    warnings = tuple(dict.fromkeys((*panel.warnings, *validation["warnings"])))
    return CorrelationWorkspaceV2State(
        wells=selected_wells,
        boundaries=boundaries,
        lithology_intervals=lithology_intervals,
        fluid_contacts=fluid_contacts,
        lines=lines,
        result_rows=result_rows,
        warnings=warnings,
        errors=validation["errors"],
    )

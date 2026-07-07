from __future__ import annotations

import pandas as pd

from las_correlation.core import LasCorrelationWell, group_curve_columns
from las_correlation.workspace_v2 import (
    FluidContact,
    LithologyInterval,
    StratigraphicBoundary,
    boundaries_to_markers,
    build_correlation_result_table,
    build_correlation_workspace_v2,
    normalize_fluid_contacts,
    normalize_lithology_intervals,
    normalize_stratigraphic_boundaries,
    validate_correlation_workspace_v2,
)


def _well(name: str, top: float = 1000.0, base: float = 1010.0) -> LasCorrelationWell:
    data = pd.DataFrame(
        {
            "DEPT": [top, (top + base) / 2, base],
            "GR": [80.0, 95.0, 70.0],
            "C1": [0.2, 0.5, 0.3],
        }
    )
    return LasCorrelationWell(
        name=name,
        data=data,
        depth_column="DEPT",
        curve_groups=group_curve_columns(data.columns),
        row_count=len(data),
        min_depth=top,
        max_depth=base,
    )


def test_normalize_stratigraphic_boundaries_supports_top_and_base_rows():
    boundaries = normalize_stratigraphic_boundaries(
        [
            {"well": "W-1", "horizon": "A", "depth": "1001.5", "type": "top"},
            {"well": "W-1", "horizon": "A", "depth": 1004.5, "type": "base"},
            {"well": "", "horizon": "ignored", "depth": 1},
        ]
    )

    assert boundaries == (
        StratigraphicBoundary(well="W-1", name="A", depth=1004.5, boundary_type="base"),
        StratigraphicBoundary(well="W-1", name="A", depth=1001.5, boundary_type="top"),
    )


def test_normalize_lithology_intervals_orders_top_and_base_depths():
    intervals = normalize_lithology_intervals(
        [{"well": "W-1", "top": 1010, "base": 1000, "lithology": "Sand", "color": "#FFE08A"}]
    )

    assert intervals == (
        LithologyInterval(well="W-1", top_depth=1000.0, base_depth=1010.0, lithology="Sand", color="#FFE08A"),
    )


def test_normalize_fluid_contacts_maps_russian_contact_aliases():
    contacts = normalize_fluid_contacts(
        [
            {"well": "W-1", "name": "ВНК", "depth": 1008, "type": "внк"},
            {"well": "W-1", "name": "ГНК", "depth": 1003, "type": "гнк"},
        ]
    )

    assert contacts[0].contact_type == "GOC"
    assert contacts[1].contact_type == "OWC"
    assert all(isinstance(contact, FluidContact) for contact in contacts)


def test_boundaries_to_markers_preserves_correlation_marker_fields():
    boundary = StratigraphicBoundary(well="W-1", name="Layer A", depth=1002, boundary_type="top")

    markers = boundaries_to_markers([boundary])

    assert markers[0].well == "W-1"
    assert markers[0].name == "Layer A"
    assert markers[0].kind == "top"
    assert markers[0].depth == 1002


def test_validate_correlation_workspace_v2_reports_missing_wells_and_out_of_range_depths():
    result = validate_correlation_workspace_v2(
        [_well("W-1")],
        boundaries=[StratigraphicBoundary(well="W-X", name="A", depth=1001)],
        fluid_contacts=[FluidContact(well="W-1", name="OWC", depth=1200, contact_type="OWC", color="#2563EB")],
        lithology_intervals=[LithologyInterval(well="W-1", top_depth=999, base_depth=1002, lithology="Sand")],
    )

    assert result["errors"] == ("Граница A: скважина W-X отсутствует.",)
    assert "Контакт OWC: глубина 1200 вне интервала скважины W-1." in result["warnings"]
    assert "Литология Sand: интервал 999-1002 выходит за диапазон W-1." in result["warnings"]


def test_build_correlation_result_table_contains_boundaries_lithology_contacts_and_lines():
    state = build_correlation_workspace_v2(
        [_well("W-1"), _well("W-2")],
        boundary_rows=[
            {"well": "W-1", "name": "A", "depth": 1002, "type": "top"},
            {"well": "W-2", "name": "A", "depth": 1003, "type": "top"},
        ],
        lithology_rows=[{"well": "W-1", "top": 1002, "base": 1006, "lithology": "Sand"}],
        fluid_contact_rows=[{"well": "W-1", "name": "OWC", "depth": 1008, "type": "OWC"}],
    )

    object_types = {row["object_type"] for row in state.result_rows}
    assert object_types == {"boundary", "lithology", "fluid_contact", "correlation_line"}
    assert len(state.lines) == 1
    assert state.lines[0].source_well == "W-1"
    assert state.lines[0].target_well == "W-2"
    assert not state.errors


def test_build_correlation_result_table_can_be_used_without_full_workspace_state():
    rows = build_correlation_result_table(
        boundaries=[StratigraphicBoundary(well="W-1", name="A", depth=1001)],
        lithology_intervals=[LithologyInterval(well="W-1", top_depth=1001, base_depth=1005, lithology="Clay")],
        fluid_contacts=[FluidContact(well="W-1", name="Gas", depth=1002, contact_type="gas", color="#FBBF24")],
    )

    assert [row["object_type"] for row in rows] == ["boundary", "lithology", "fluid_contact"]

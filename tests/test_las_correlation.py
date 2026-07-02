from __future__ import annotations

from io import BytesIO

import pytest

from las_correlation import (
    apply_curve_group_overrides,
    build_las_correlation_figure,
    classify_curve_name,
    curve_group_rows,
    group_curve_columns,
    prepare_las_correlation_well,
    prepare_las_correlation_wells,
)


class UploadedLasStub:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def _sample_las_bytes() -> bytes:
    return b"""
~Well
NULL. -999.25
~Curve
DEPT.M : measured depth
GR.API : gamma ray
RDEEP.OHMM : deep resistivity
RHOB.G/C3 : density
TGAS.% : total gas
C1.% : methane
C2.% : ethane
~ASCII
1001 75 20 2.30 3.1 80 10
1000 70 18 2.25 2.4 70 9
"""


@pytest.mark.parametrize(
    ("curve_name", "expected_group"),
    [
        ("DEPT", "depth"),
        ("GR", "gamma"),
        ("TGAS", "total_gas"),
        ("C1", "gas_component"),
        ("RDEEP", "resistivity"),
        ("RHOB", "density_neutron"),
        ("ROP", "drilling"),
        ("UNKNOWN", "other"),
    ],
)
def test_classify_curve_name_groups_las_mnemonics(curve_name, expected_group):
    assert classify_curve_name(curve_name) == expected_group


def test_group_curve_columns_preserves_columns_by_group():
    groups = group_curve_columns(["DEPT", "GR", "RDEEP", "RHOB", "TGAS", "C1", "COMMENT"])

    assert groups["depth"] == ("DEPT",)
    assert groups["gamma"] == ("GR",)
    assert groups["resistivity"] == ("RDEEP",)
    assert groups["density_neutron"] == ("RHOB",)
    assert groups["total_gas"] == ("TGAS",)
    assert groups["gas_component"] == ("C1",)
    assert groups["other"] == ("COMMENT",)


def test_apply_curve_group_overrides_moves_curve_to_selected_group():
    well = prepare_las_correlation_well(BytesIO(_sample_las_bytes()), name="Well A")

    overridden = apply_curve_group_overrides(well, {"TGAS": "gamma", "GR": "other"})

    assert overridden.curve_groups["gamma"] == ("TGAS",)
    assert "GR" not in overridden.curve_groups.get("gamma", ())
    assert "GR" in overridden.curve_groups["other"]


def test_curve_group_rows_show_current_group_and_depth_flag():
    well = prepare_las_correlation_well(BytesIO(_sample_las_bytes()), name="Well A")

    rows = curve_group_rows(well)
    rows_by_curve = {row["curve"]: row for row in rows}

    assert rows_by_curve["DEPT"]["group"] == "depth"
    assert rows_by_curve["DEPT"]["is_depth"] == "yes"
    assert rows_by_curve["GR"]["group_label"] == "Gamma ray / GR"


def test_prepare_las_correlation_well_sorts_depth_and_keeps_gis_curves():
    stream = BytesIO(_sample_las_bytes())

    well = prepare_las_correlation_well(stream, name="Well A")

    assert well.name == "Well A"
    assert well.depth_column == "DEPT"
    assert well.min_depth == 1000.0
    assert well.max_depth == 1001.0
    assert list(well.data["DEPT"]) == [1000.0, 1001.0]
    assert well.curve_groups["gamma"] == ("GR",)
    assert well.curve_groups["resistivity"] == ("RDEEP",)
    assert well.curve_groups["density_neutron"] == ("RHOB",)
    assert well.curve_groups["total_gas"] == ("TGAS",)
    assert well.curve_groups["gas_component"] == ("C1", "C2")


def test_prepare_las_correlation_wells_uses_unique_uploaded_names():
    wells = prepare_las_correlation_wells(
        [
            UploadedLasStub("well.las", _sample_las_bytes()),
            UploadedLasStub("well.las", _sample_las_bytes()),
        ]
    )

    assert [well.name for well in wells] == ["well", "well (2)"]


def test_build_las_correlation_figure_puts_gis_and_gas_tracks_side_by_side():
    well = prepare_las_correlation_well(BytesIO(_sample_las_bytes()), name="Well A")

    fig = build_las_correlation_figure(
        [well],
        gis_groups=("gamma", "resistivity"),
        gas_groups=("total_gas", "gas_component"),
        depth_range=(1000.0, 1001.0),
        height_per_well=500,
    )

    trace_names = {trace.name for trace in fig.data}
    assert "Well A: GR" in trace_names
    assert "Well A: RDEEP" in trace_names
    assert "Well A: TGAS" in trace_names
    assert "Well A: C1" in trace_names
    assert tuple(fig.layout.yaxis.range) == (1001.0, 1000.0)
    assert fig.layout.height == 500

def test_las_correlation_figure_uses_overridden_groups():
    well = prepare_las_correlation_well(BytesIO(_sample_las_bytes()), name="Well A")
    overridden = apply_curve_group_overrides(well, {"TGAS": "gamma"})

    fig = build_las_correlation_figure(
        [overridden],
        gis_groups=("gamma",),
        gas_groups=("total_gas",),
    )

    trace_names = {trace.name for trace in fig.data}
    assert "Well A: TGAS" in trace_names
    assert "Well A: GR" in trace_names

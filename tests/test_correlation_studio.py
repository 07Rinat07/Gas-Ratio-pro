from io import BytesIO

from las_correlation import (
    CorrelationMarker,
    build_correlation_panel,
    build_correlation_panel_figure,
    build_shared_depth_grid,
    common_curve_names,
    correlation_marker_rows,
    correlation_panel_summary,
    normalize_correlation_markers,
    overlapping_depth_range,
    prepare_las_correlation_well,
    prepare_las_correlation_wells,
    shared_depth_range,
)


def _las_bytes(start: int = 1000) -> bytes:
    return f"""
~Well
NULL. -999.25
~Curve
DEPT.M : measured depth
GR.API : gamma ray
TGAS.% : total gas
~ASCII
{start} 70 2.1
{start + 1} 75 2.8
{start + 2} 80 3.0
""".encode()


def test_correlation_depth_ranges_use_union_and_overlap():
    wells = prepare_las_correlation_wells([BytesIO(_las_bytes(1000)), BytesIO(_las_bytes(1001))])

    assert shared_depth_range(wells) == (1000.0, 1003.0)
    assert overlapping_depth_range(wells) == (1001.0, 1002.0)


def test_build_shared_depth_grid_uses_requested_step():
    wells = prepare_las_correlation_wells([BytesIO(_las_bytes(1000))])

    grid = build_shared_depth_grid(wells, step=0.5, depth_range=(1000.0, 1001.0))

    assert grid == (1000.0, 1000.5, 1001.0)


def test_common_curve_names_can_require_all_wells():
    well_a = prepare_las_correlation_well(BytesIO(_las_bytes(1000)), name="A")
    well_b = prepare_las_correlation_well(BytesIO(_las_bytes(1001)), name="B")
    well_b = well_b.__class__(
        name=well_b.name,
        data=well_b.data.drop(columns=["TGAS"]),
        depth_column=well_b.depth_column,
        curve_groups={"depth": ("DEPT",), "gamma": ("GR",)},
        row_count=well_b.row_count,
        min_depth=well_b.min_depth,
        max_depth=well_b.max_depth,
        warnings=well_b.warnings,
    )

    assert "TGAS" in common_curve_names([well_a, well_b], require_all_wells=False)
    assert common_curve_names([well_a, well_b], require_all_wells=True) == ("GR",)


def test_normalize_correlation_markers_skips_bad_depth_and_sorts():
    markers = normalize_correlation_markers(
        [
            {"well": "B", "name": "Top B", "depth": "1002", "kind": "top"},
            {"well": "A", "name": "bad", "depth": "not-number"},
            {"well": "A", "name": "Top A", "depth": 1001.0, "color": "#fff"},
        ]
    )

    assert [marker.name for marker in markers] == ["Top A", "Top B"]
    assert markers[0].color == "#fff"


def test_build_correlation_panel_returns_summary_markers_and_grid():
    wells = prepare_las_correlation_wells([BytesIO(_las_bytes(1000)), BytesIO(_las_bytes(1001))])
    panel = build_correlation_panel(
        wells,
        markers=[CorrelationMarker(well="", name="Regional Top", depth=1001.5, kind="top")],
        depth_step=0.5,
        groups=("gamma", "total_gas"),
        grid_mode="overlap",
    )

    summary = correlation_panel_summary(panel)
    assert summary["wells"] == 2
    assert summary["markers"] == 1
    assert summary["depth_range"] == (1001.0, 1002.0)
    assert summary["grid_points"] == 3
    assert panel.common_curves == ("GR", "TGAS")
    assert correlation_marker_rows(panel)[0]["well"] == "Все скважины"


def test_build_correlation_panel_figure_draws_one_track_per_well_and_markers():
    wells = prepare_las_correlation_wells([BytesIO(_las_bytes(1000)), BytesIO(_las_bytes(1001))])
    panel = build_correlation_panel(
        wells,
        markers=[{"well": "LAS 1", "name": "Top", "depth": 1001.0, "color": "#f59e0b"}],
        depth_range=(1000.0, 1003.0),
    )

    fig = build_correlation_panel_figure(panel, "GR", height_per_well=520)

    assert len(fig.data) == 2
    assert fig.layout.height == 520
    assert tuple(fig.layout.yaxis.range) == (1003.0, 1000.0)
    assert "Correlation Studio" in fig.layout.title.text

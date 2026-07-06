from io import BytesIO

from las_correlation import (
    CorrelationMarker,
    apply_depth_alignments,
    build_correlation_lines_from_markers,
    build_correlation_studio_state,
    normalize_correlation_lines,
    normalize_depth_alignments,
    prepare_las_correlation_wells,
    validate_correlation_lines,
)


def _las_bytes(start: int = 1000) -> bytes:
    return f"""
~Well
NULL. -999.25
~Curve
DEPT.M : measured depth
GR.API : gamma ray
RT.OHMM : resistivity
~ASCII
{start} 70 10
{start + 1} 75 12
{start + 2} 80 15
""".encode()


def test_depth_alignments_shift_selected_well_only():
    wells = prepare_las_correlation_wells([BytesIO(_las_bytes(1000)), BytesIO(_las_bytes(1100))])
    alignments = normalize_depth_alignments([{"well": "LAS 2", "shift": -100.0, "reference": "Top A"}])

    aligned = apply_depth_alignments(wells, alignments)

    assert aligned[0].min_depth == 1000.0
    assert aligned[1].min_depth == 1000.0
    assert "смещение глубины -100.000 м" in aligned[1].warnings[-1]


def test_correlation_lines_from_matching_markers_follow_well_order():
    markers = [
        CorrelationMarker(well="B", name="Top A", depth=1010.0),
        CorrelationMarker(well="A", name="Top A", depth=1000.0),
        CorrelationMarker(well="C", name="Top A", depth=1020.0),
    ]

    lines = build_correlation_lines_from_markers(markers, well_order=("A", "B", "C"))

    assert [(line.source_well, line.target_well) for line in lines] == [("A", "B"), ("B", "C")]
    assert lines[0].source_depth == 1000.0
    assert lines[0].target_depth == 1010.0


def test_normalize_manual_correlation_lines_clamps_confidence():
    lines = normalize_correlation_lines(
        [
            {
                "source_well": "A",
                "target_well": "B",
                "name": "Top A",
                "source_depth": "1000",
                "target_depth": "1002",
                "confidence": 2.5,
            },
            {"source_well": "A", "target_well": "A", "source_depth": 1, "target_depth": 2},
        ]
    )

    assert len(lines) == 1
    assert lines[0].confidence == 1.0


def test_validate_correlation_lines_detects_crossing_and_missing_wells():
    wells = prepare_las_correlation_wells([BytesIO(_las_bytes(1000)), BytesIO(_las_bytes(1000))])
    lines = normalize_correlation_lines(
        [
            {"source_well": "LAS 1", "target_well": "LAS 2", "name": "Top A", "source_depth": 1000, "target_depth": 1002},
            {"source_well": "LAS 1", "target_well": "LAS 2", "name": "Top B", "source_depth": 1001, "target_depth": 1000},
            {"source_well": "LAS 1", "target_well": "Missing", "name": "Bad", "source_depth": 1000, "target_depth": 1000},
        ]
    )

    validation = validate_correlation_lines(lines, wells)

    assert any("Missing" in item for item in validation["errors"])
    assert any("пересечение" in item for item in validation["warnings"])


def test_build_correlation_studio_state_returns_panel_lines_and_validation():
    wells = prepare_las_correlation_wells([BytesIO(_las_bytes(1000)), BytesIO(_las_bytes(1000))])
    state = build_correlation_studio_state(
        wells,
        marker_rows=[
            {"well": "LAS 1", "name": "Top A", "depth": 1000.0},
            {"well": "LAS 2", "name": "Top A", "depth": 1001.0},
        ],
        alignment_rows=[{"well": "LAS 2", "shift": -1.0}],
        depth_step=0.5,
        groups=("gamma", "resistivity"),
    )

    assert state["summary"]["wells"] == 2
    assert state["summary"]["lines"] == 1
    assert state["summary"]["aligned_wells"] == 1
    assert state["summary"]["grid_points"] >= 5

from __future__ import annotations

from pathlib import Path

import pytest

from projects import create_project
from projects.plot_studio import add_plot_curve, add_plot_track, save_plot_template
from projects.plot_studio_annotation_layer import (
    PlotAnnotation,
    PlotAnnotationLayerConfig,
    build_plot_annotation_layer,
    build_plot_annotation_manifest,
    build_plot_annotation_table,
    validate_annotation_layer_config,
    validate_plot_annotations,
)
from projects.plot_studio_core import build_plot_workspace
from projects.plot_studio_track_layout import PlotTrackLayoutConfig, build_plot_track_layout


def _workspace(tmp_path: Path):
    project = create_project(tmp_path, name="Annotation Layer")
    template = save_plot_template(tmp_path, project.id, "Annotation Tablet", template_id="annotation-tablet", well_id="well-01")
    template = add_plot_track(tmp_path, project.id, template.id, "Gamma", track_id="track-gamma", width=1.0)
    template = add_plot_track(tmp_path, project.id, template.id, "Density", track_id="track-density", width=2.0)
    template = add_plot_curve(tmp_path, project.id, template.id, "GR", "track-gamma", curve_id="curve-gr")
    template = add_plot_curve(tmp_path, project.id, template.id, "RHOB", "track-density", curve_id="curve-rhob")
    return build_plot_workspace(template, depth_from=1000, depth_to=1600)


def test_annotation_layer_config_validates_canvas_and_margins():
    cfg = validate_annotation_layer_config(PlotAnnotationLayerConfig(canvas_height_px="1800", top_margin_px="90"))  # type: ignore[arg-type]

    assert cfg.canvas_height_px == 1800
    assert cfg.top_margin_px == 90

    with pytest.raises(ValueError, match="меньше высоты canvas"):
        validate_annotation_layer_config(PlotAnnotationLayerConfig(canvas_height_px=100, top_margin_px=60, bottom_margin_px=60))

    with pytest.raises(ValueError, match="больше нуля"):
        validate_annotation_layer_config(PlotAnnotationLayerConfig(canvas_height_px=0))


def test_validate_plot_annotations_normalizes_and_rejects_invalid_values():
    annotations = validate_plot_annotations(
        [
            PlotAnnotation(id=" m1 ", type="marker", depth_from="1200,5", label="Top A"),  # type: ignore[arg-type]
            PlotAnnotation(id="i1", type="interval", depth_from=1250, depth_to=1300, label="Layer A"),
        ]
    )

    assert annotations[0].id == "m1"
    assert annotations[0].depth_from == 1200.5
    assert annotations[1].depth_to == 1300

    with pytest.raises(ValueError, match="повторяющийся"):
        validate_plot_annotations([
            PlotAnnotation(id="dup", type="marker", depth_from=1000, label="A"),
            PlotAnnotation(id="dup", type="marker", depth_from=1001, label="B"),
        ])

    with pytest.raises(ValueError, match="требуется depth_to"):
        validate_plot_annotations([PlotAnnotation(id="bad", type="zone", depth_from=1000, label="Zone")])

    with pytest.raises(ValueError, match="label или text"):
        validate_plot_annotations([PlotAnnotation(id="bad-text", type="text", depth_from=1000)])


def test_annotation_layer_places_marker_interval_zone_and_text(tmp_path):
    workspace = _workspace(tmp_path)
    layout = build_plot_track_layout(workspace, config=PlotTrackLayoutConfig(canvas_width_px=1200))

    result = build_plot_annotation_layer(
        workspace,
        [
            PlotAnnotation(id="top-a", type="marker", depth_from=1100, track_id="track-gamma", label="Top A"),
            PlotAnnotation(id="pay-a", type="interval", depth_from=1200, depth_to=1300, track_id="track-density", label="Pay A"),
            PlotAnnotation(id="gas-zone", type="zone", depth_from=1320, depth_to=1400, label="Gas"),
            PlotAnnotation(id="comment", type="text", depth_from=1500, text="Check density response"),
        ],
        layout=layout,
        config=PlotAnnotationLayerConfig(canvas_height_px=1600, top_margin_px=100, bottom_margin_px=100),
    )

    assert result.workspace_id == "annotation-tablet"
    assert len(result.placements) == 4
    assert all(100 <= placement.y_from_px <= 1500 for placement in result.placements)
    assert result.placements[0].track_id == "track-gamma"
    assert result.placements[2].track_id == ""
    assert result.placements[2].left_px < result.placements[2].right_px


def test_annotation_layer_clips_to_current_viewport_and_skips_outside(tmp_path):
    workspace = _workspace(tmp_path)

    result = build_plot_annotation_layer(
        workspace,
        [
            PlotAnnotation(id="partly-visible", type="interval", depth_from=950, depth_to=1050, label="Clip"),
            PlotAnnotation(id="outside", type="marker", depth_from=1800, label="Outside"),
        ],
    )

    assert len(result.placements) == 1
    placement = result.placements[0]
    assert placement.annotation.id == "partly-visible"
    assert placement.clipped is True
    assert placement.clipped_depth_from == 1000
    assert any("outside viewport" in message for message in result.messages)


def test_annotation_layer_respects_visibility_lock_and_track_rules(tmp_path):
    workspace = _workspace(tmp_path)

    result = build_plot_annotation_layer(
        workspace,
        [
            PlotAnnotation(id="hidden", type="marker", depth_from=1100, label="Hidden", visible=False),
            PlotAnnotation(id="locked", type="marker", depth_from=1150, label="Locked", locked=True),
            PlotAnnotation(id="unknown", type="marker", depth_from=1200, track_id="missing", label="Missing Track"),
            PlotAnnotation(id="global", type="marker", depth_from=1250, label="Global"),
        ],
        config=PlotAnnotationLayerConfig(include_locked=False, allow_global_annotations=False),
    )

    assert result.placements == ()
    assert any("hidden" in message for message in result.messages)
    assert any("locked" in message for message in result.messages)
    assert any("unknown track" in message for message in result.messages)
    assert any("global annotations disabled" in message for message in result.messages)


def test_annotation_manifest_and_table_are_serializable(tmp_path):
    workspace = _workspace(tmp_path)
    result = build_plot_annotation_layer(
        workspace,
        [PlotAnnotation(id="m1", type="marker", depth_from=1200, track_id="track-gamma", label="Marker 1")],
    )

    manifest = build_plot_annotation_manifest(result)
    table = build_plot_annotation_table(result)

    assert manifest["workspace_id"] == "annotation-tablet"
    assert manifest["placements"][0]["id"] == "m1"
    assert table[0]["track"] == "track-gamma"
    assert table[0]["label"] == "Marker 1"

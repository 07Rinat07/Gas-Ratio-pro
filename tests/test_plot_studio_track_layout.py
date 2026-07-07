from __future__ import annotations

import pytest

from projects import create_project
from projects.plot_studio import add_plot_curve, add_plot_track, save_plot_template
from projects.plot_studio_core import build_plot_workspace
from projects.plot_studio_track_layout import (
    PlotTrackLayoutConfig,
    build_plot_track_layout,
    build_plot_track_layout_manifest,
    build_plot_track_layout_table,
    validate_track_layout_config,
)


def _workspace(tmp_path):
    project = create_project(tmp_path, name="Track Layout")
    template = save_plot_template(tmp_path, project.id, "Layout", template_id="layout", well_id="well-01")
    template = add_plot_track(tmp_path, project.id, template.id, "Density", track_id="track-density", width=2.0)
    template = add_plot_track(tmp_path, project.id, template.id, "Resistivity", track_id="track-resistivity", width=1.5)
    template = add_plot_curve(tmp_path, project.id, template.id, "GR", "track-gamma", curve_id="curve-gr")
    template = add_plot_curve(tmp_path, project.id, template.id, "RHOB", "track-density", curve_id="curve-rhob")
    return build_plot_workspace(template, depth_from=1000, depth_to=1600)


def test_track_layout_builds_depth_track_and_visible_tracks(tmp_path):
    workspace = _workspace(tmp_path)

    layout = build_plot_track_layout(workspace, config=PlotTrackLayoutConfig(canvas_width_px=1000))
    manifest = build_plot_track_layout_manifest(layout)

    assert layout.items[0].track_id == "__depth__"
    assert layout.items[0].frozen is True
    assert len(layout.track_items) == len(workspace.tracks)
    assert manifest["items"][1]["track_id"] == workspace.tracks[0].id
    assert layout.total_width_px <= layout.canvas_width_px


def test_track_layout_supports_custom_track_order_without_mutating_workspace(tmp_path):
    workspace = _workspace(tmp_path)

    layout = build_plot_track_layout(workspace, track_order=("track-resistivity", "track-gamma"))

    assert workspace.track_ids[0] == "track-depth"
    assert layout.track_items[0].track_id == "track-resistivity"
    assert layout.track_items[1].track_id == "track-gamma"


def test_track_layout_can_place_depth_track_on_right_or_hide_it(tmp_path):
    workspace = _workspace(tmp_path)

    right = build_plot_track_layout(workspace, config=PlotTrackLayoutConfig(depth_track_position="right"))
    hidden = build_plot_track_layout(workspace, config=PlotTrackLayoutConfig(depth_track_position="hidden"))

    assert right.items[-1].is_depth_track is True
    assert all(not item.is_depth_track for item in hidden.items)
    assert len(hidden.items) == len(workspace.tracks)


def test_track_layout_respects_minimum_width_when_canvas_is_tight(tmp_path):
    workspace = _workspace(tmp_path)

    layout = build_plot_track_layout(workspace, config=PlotTrackLayoutConfig(canvas_width_px=200, min_track_width_px=120))

    assert all(item.width_px >= 120 for item in layout.track_items)
    assert layout.canvas_width_px >= layout.total_width_px


def test_track_layout_validation_rejects_invalid_config():
    with pytest.raises(ValueError, match="Canvas width"):
        validate_track_layout_config(PlotTrackLayoutConfig(canvas_width_px=0))

    with pytest.raises(ValueError, match="Depth track position"):
        validate_track_layout_config(PlotTrackLayoutConfig(depth_track_position="center"))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="минимальной ширины"):
        validate_track_layout_config(PlotTrackLayoutConfig(canvas_width_px=80, min_track_width_px=120))


def test_track_layout_table_is_ready_for_ui(tmp_path):
    workspace = _workspace(tmp_path)
    layout = build_plot_track_layout(workspace)

    table = build_plot_track_layout_table(layout)

    assert table[0]["Depth track"] == "да"
    assert {row["Закреплен"] for row in table} >= {"да", "нет"}


def test_track_layout_reports_empty_workspace():
    from projects.plot_studio_core import PlotWorkspace, PlotViewportState, build_plot_depth_range

    workspace = PlotWorkspace(
        template_id="empty",
        name="Empty",
        well_id="",
        viewport=PlotViewportState(depth_range=build_plot_depth_range(0, 100)),
        tracks=(),
    )

    layout = build_plot_track_layout(workspace)

    assert layout.items == () or all(item.is_depth_track for item in layout.items)
    assert any("Нет видимых треков" in message for message in layout.messages)

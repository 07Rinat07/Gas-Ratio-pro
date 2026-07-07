from __future__ import annotations

import pytest

from projects.plot_studio import PlotAxisConfig, PlotTemplate, add_plot_curve, save_plot_template
from projects.plot_studio_core import (
    PlotLayerState,
    build_crosshair_state,
    build_plot_depth_range,
    build_plot_workspace,
    build_plot_workspace_manifest,
    build_plot_workspace_track_table,
    set_plot_workspace_depth_interval,
    synchronize_plot_tracks,
)
from projects import create_project


def test_plot_studio_core_builds_workspace_from_template(tmp_path):
    project = create_project(tmp_path, name="Plot Core")
    template = save_plot_template(tmp_path, project.id, "Core", template_id="core", well_id="well-01")
    template = add_plot_curve(
        tmp_path,
        project.id,
        template.id,
        "GR",
        "track-gamma",
        curve_id="curve-gr",
        axis=PlotAxisConfig(min_value=0, max_value=150),
    )

    workspace = build_plot_workspace(template, depth_from=1200, depth_to=1600, active_track_id="track-gamma", crosshair_md=1305.5)
    manifest = build_plot_workspace_manifest(workspace)

    assert workspace.template_id == "core"
    assert workspace.viewport.depth_range.height_m == 400
    assert workspace.viewport.active_track_id == "track-gamma"
    assert workspace.crosshair.label == "MD 1305.50 m"
    assert workspace.curve_count == 1
    assert manifest["tracks"][1]["curves"][0]["mnemonic"] == "GR"


def test_plot_studio_core_validates_depth_interval():
    with pytest.raises(ValueError, match="Depth From"):
        build_plot_depth_range(1000, 900)

    with pytest.raises(ValueError, match="глубина не может быть отрицательной"):
        build_plot_depth_range(-1, 900)

    with pytest.raises(ValueError, match="шаг сетки"):
        build_plot_depth_range(0, 900, major_step=0)


def test_plot_studio_core_synchronizes_visible_tracks(tmp_path):
    project = create_project(tmp_path, name="Plot Sync")
    template = save_plot_template(tmp_path, project.id, "Sync", template_id="sync")
    workspace = build_plot_workspace(template, depth_from=0, depth_to=500)

    sync = synchronize_plot_tracks(workspace)
    table = build_plot_workspace_track_table(workspace)

    assert set(sync) == set(workspace.track_ids)
    assert all(row["Depth To"] == 500 for row in table)
    assert all(row["Синхронно"] == "да" for row in table)


def test_plot_studio_core_changes_depth_interval_without_mutating_workspace(tmp_path):
    project = create_project(tmp_path, name="Plot Interval")
    template = save_plot_template(tmp_path, project.id, "Interval", template_id="interval")
    workspace = build_plot_workspace(template, depth_from=100, depth_to=900, crosshair_md=850)

    changed = set_plot_workspace_depth_interval(workspace, 200, 700)

    assert workspace.viewport.depth_range.from_md == 100
    assert changed.viewport.depth_range.from_md == 200
    assert changed.viewport.depth_range.to_md == 700
    assert changed.crosshair.md_m == 700


def test_plot_studio_core_crosshair_clamps_to_depth_range():
    depth_range = build_plot_depth_range(1000, 1200)

    below = build_crosshair_state(depth_range, md_m=900, track_id="track-gamma")
    above = build_crosshair_state(depth_range, md_m=1300, x_value=42)

    assert below.md_m == 1000
    assert above.md_m == 1200
    assert above.label == "MD 1200.00 m, X 42"


def test_plot_studio_core_reports_hidden_or_empty_tracks():
    template = PlotTemplate(id="hidden", name="Hidden", tracks=())

    workspace = build_plot_workspace(template, depth_from=0, depth_to=100)

    assert workspace.tracks == ()
    assert any("Нет видимых треков" in issue for issue in workspace.issues)


def test_plot_studio_core_layer_state_controls_manifest(tmp_path):
    project = create_project(tmp_path, name="Plot Layers")
    template = save_plot_template(tmp_path, project.id, "Layers", template_id="layers")

    workspace = build_plot_workspace(template, depth_from=0, depth_to=100, layers=PlotLayerState(grid=False, annotations=False))
    manifest = build_plot_workspace_manifest(workspace)

    assert manifest["layers"]["grid"] is False
    assert manifest["layers"]["annotations"] is False
    assert all(track["layers"]["grid"] is False for track in manifest["tracks"])

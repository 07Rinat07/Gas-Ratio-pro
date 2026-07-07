from __future__ import annotations

import pytest

from projects import create_project
from projects.plot_studio import PlotAxisConfig, add_plot_curve, add_plot_track, save_plot_template
from projects.plot_studio_core import build_plot_workspace
from projects.plot_studio_manual_scale import (
    PlotManualCurveScaleRequest,
    PlotManualDepthScaleRequest,
    PlotManualScaleConfig,
    apply_manual_curve_scale,
    apply_manual_depth_scale,
    build_manual_scale_manifest,
    reset_curve_auto_scale,
)


def _workspace(tmp_path):
    project = create_project(tmp_path, name="Manual Scale")
    template = save_plot_template(tmp_path, project.id, "Manual", template_id="manual", well_id="well-01")
    template = add_plot_curve(
        tmp_path,
        project.id,
        template.id,
        "GR",
        "track-gamma",
        curve_id="curve-gr",
        axis=PlotAxisConfig(min_value=0, max_value=150),
    )
    template = add_plot_track(tmp_path, project.id, template.id, "Density", track_id="track-density")
    template = add_plot_curve(
        tmp_path,
        project.id,
        template.id,
        "RHOB",
        "track-density",
        curve_id="curve-rhob",
        axis=PlotAxisConfig(min_value=1.95, max_value=2.95),
    )
    return build_plot_workspace(template, depth_from=1000, depth_to=2000, active_track_id="track-gamma", crosshair_md=1900)


def test_manual_depth_scale_changes_shared_y_interval_without_mutating_source(tmp_path):
    workspace = _workspace(tmp_path)

    result = apply_manual_depth_scale(workspace, PlotManualDepthScaleRequest(1200, 1800, major_step=50, minor_step=10))

    assert result.changed is True
    assert workspace.viewport.depth_range.from_md == 1000
    assert result.workspace.viewport.depth_range.from_md == 1200
    assert result.workspace.viewport.depth_range.to_md == 1800
    assert result.workspace.viewport.depth_range.major_step == 50
    assert result.workspace.crosshair.md_m == 1800


def test_manual_depth_scale_validates_limits(tmp_path):
    workspace = _workspace(tmp_path)

    with pytest.raises(ValueError, match="пределах"):
        apply_manual_depth_scale(workspace, PlotManualDepthScaleRequest(1000, 16000))

    with pytest.raises(ValueError, match="слишком маленькое"):
        apply_manual_depth_scale(workspace, PlotManualDepthScaleRequest(1000, 1000.01), config=PlotManualScaleConfig(min_depth_window_m=1))


def test_manual_curve_scale_updates_single_curve_axis(tmp_path):
    workspace = _workspace(tmp_path)

    result = apply_manual_curve_scale(
        workspace,
        PlotManualCurveScaleRequest(curve_id="curve-gr", min_value=10, max_value=120, inverted=True),
    )
    manifest = build_manual_scale_manifest(result)
    gr = next(item for item in manifest["curve_scales"] if item["curve_id"] == "curve-gr")
    rhob = next(item for item in manifest["curve_scales"] if item["curve_id"] == "curve-rhob")

    assert result.changed is True
    assert result.affected_curves == ("curve-gr",)
    assert gr["min_value"] == 10
    assert gr["max_value"] == 120
    assert gr["auto_range"] is False
    assert gr["inverted"] is True
    assert rhob["min_value"] == 1.95
    assert workspace.tracks[1].curves[0].axis["min_value"] == 0


def test_manual_curve_scale_can_target_track_curves(tmp_path):
    workspace = _workspace(tmp_path)

    result = apply_manual_curve_scale(workspace, PlotManualCurveScaleRequest(track_id="track-density", min_value=2.0, max_value=2.8))

    assert result.affected_curves == ("curve-rhob",)
    curve = next(curve for track in result.workspace.tracks for curve in track.curves if curve.id == "curve-rhob")
    assert curve.mnemonic == "RHOB"
    assert curve.axis["min_value"] == 2.0
    assert curve.axis["max_value"] == 2.8


def test_manual_curve_scale_validates_log_and_range(tmp_path):
    workspace = _workspace(tmp_path)

    with pytest.raises(ValueError, match="минимум должен быть меньше"):
        apply_manual_curve_scale(workspace, PlotManualCurveScaleRequest(curve_id="curve-gr", min_value=100, max_value=100))

    with pytest.raises(ValueError, match="log"):
        apply_manual_curve_scale(workspace, PlotManualCurveScaleRequest(curve_id="curve-gr", min_value=0, max_value=100, scale="log"))


def test_manual_curve_scale_reports_missing_curve(tmp_path):
    workspace = _workspace(tmp_path)

    result = apply_manual_curve_scale(workspace, PlotManualCurveScaleRequest(curve_id="missing", min_value=0, max_value=1))

    assert result.changed is False
    assert "не найдены" in result.messages[0]


def test_reset_curve_auto_scale_restores_auto_range(tmp_path):
    workspace = _workspace(tmp_path)
    manual = apply_manual_curve_scale(workspace, PlotManualCurveScaleRequest(curve_id="curve-gr", min_value=10, max_value=120)).workspace

    result = reset_curve_auto_scale(manual, curve_id="curve-gr")
    manifest = build_manual_scale_manifest(result)
    gr = next(item for item in manifest["curve_scales"] if item["curve_id"] == "curve-gr")

    assert result.changed is True
    assert gr["min_value"] is None
    assert gr["max_value"] is None
    assert gr["auto_range"] is True

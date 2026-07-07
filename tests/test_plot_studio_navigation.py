from __future__ import annotations

import pytest

from projects import create_project
from projects.plot_studio import save_plot_template
from projects.plot_studio_core import build_plot_workspace
from projects.plot_studio_navigation import (
    PlotBoxZoomRequest,
    PlotNavigationConfig,
    PlotPanRequest,
    box_zoom,
    build_plot_navigation_bounds,
    build_plot_navigation_manifest,
    initialize_plot_navigation,
    mouse_wheel_zoom,
    pan_plot,
    redo_plot_navigation,
    reset_plot_zoom,
    undo_plot_navigation,
)


def _workspace(tmp_path):
    project = create_project(tmp_path, name="Navigation")
    template = save_plot_template(tmp_path, project.id, "Navigation", template_id="nav", well_id="well-01")
    return build_plot_workspace(template, depth_from=1000, depth_to=2000, active_track_id="track-gamma", crosshair_md=1500)


def test_navigation_initializes_from_workspace_depth_range(tmp_path):
    workspace = _workspace(tmp_path)

    state = initialize_plot_navigation(workspace)
    manifest = build_plot_navigation_manifest(state)

    assert state.bounds.depth_from == 1000
    assert state.bounds.depth_to == 2000
    assert manifest["viewport"]["height_m"] == 1000
    assert manifest["history"]["can_undo"] is False


def test_navigation_validates_bounds():
    with pytest.raises(ValueError, match="верхняя граница"):
        build_plot_navigation_bounds(2000, 1000)

    with pytest.raises(ValueError, match="минимальное окно"):
        build_plot_navigation_bounds(1000, 2000, min_window_m=2000)


def test_mouse_wheel_zoom_in_around_anchor_keeps_anchor_ratio(tmp_path):
    state = initialize_plot_navigation(_workspace(tmp_path), config=PlotNavigationConfig(wheel_zoom_factor=0.2))

    zoomed = mouse_wheel_zoom(state, direction="in", anchor_md=1500, config=PlotNavigationConfig(wheel_zoom_factor=0.2))

    assert zoomed.workspace.viewport.depth_range.from_md == 1100
    assert zoomed.workspace.viewport.depth_range.to_md == 1900
    assert zoomed.workspace.viewport.zoom_level == 1.25
    assert zoomed.history.can_undo is True
    assert zoomed.workspace.crosshair.md_m == 1500


def test_mouse_wheel_zoom_out_is_clamped_to_full_bounds(tmp_path):
    state = initialize_plot_navigation(_workspace(tmp_path))

    zoomed = mouse_wheel_zoom(state, direction="out", anchor_md=1500)

    assert zoomed.workspace.viewport.depth_range.from_md == 1000
    assert zoomed.workspace.viewport.depth_range.to_md == 2000
    assert zoomed.workspace.viewport.zoom_level == 1.0


def test_box_zoom_accepts_reversed_depth_selection(tmp_path):
    state = initialize_plot_navigation(_workspace(tmp_path))

    zoomed = box_zoom(state, PlotBoxZoomRequest(depth_from=1800, depth_to=1200, track_id="track-gamma"))

    assert zoomed.workspace.viewport.depth_range.from_md == 1200
    assert zoomed.workspace.viewport.depth_range.to_md == 1800
    assert zoomed.workspace.viewport.zoom_level == pytest.approx(1.666667)


def test_box_zoom_expands_too_small_window_to_minimum(tmp_path):
    workspace = _workspace(tmp_path)
    bounds = build_plot_navigation_bounds(1000, 2000, min_window_m=50)
    state = initialize_plot_navigation(workspace, bounds=bounds)

    zoomed = box_zoom(state, PlotBoxZoomRequest(depth_from=1490, depth_to=1495))

    assert zoomed.workspace.viewport.depth_range.height_m == 50
    assert zoomed.workspace.viewport.depth_range.from_md == 1467.5
    assert zoomed.workspace.viewport.depth_range.to_md == 1517.5


def test_pan_moves_viewport_without_changing_zoom_height(tmp_path):
    state = initialize_plot_navigation(_workspace(tmp_path))
    state = box_zoom(state, PlotBoxZoomRequest(depth_from=1200, depth_to=1600))

    panned = pan_plot(state, PlotPanRequest(delta_m=100))

    assert panned.workspace.viewport.depth_range.from_md == 1300
    assert panned.workspace.viewport.depth_range.to_md == 1700
    assert panned.workspace.viewport.depth_range.height_m == 400


def test_pan_is_clamped_to_navigation_bounds(tmp_path):
    state = initialize_plot_navigation(_workspace(tmp_path))
    state = box_zoom(state, PlotBoxZoomRequest(depth_from=1200, depth_to=1600))

    panned = pan_plot(state, PlotPanRequest(delta_m=1000))

    assert panned.workspace.viewport.depth_range.from_md == 1600
    assert panned.workspace.viewport.depth_range.to_md == 2000


def test_reset_zoom_restores_full_depth_range(tmp_path):
    state = initialize_plot_navigation(_workspace(tmp_path))
    state = box_zoom(state, PlotBoxZoomRequest(depth_from=1200, depth_to=1600))

    reset = reset_plot_zoom(state)

    assert reset.workspace.viewport.depth_range.from_md == 1000
    assert reset.workspace.viewport.depth_range.to_md == 2000
    assert reset.workspace.viewport.zoom_level == 1.0


def test_navigation_undo_and_redo_restore_viewports(tmp_path):
    state = initialize_plot_navigation(_workspace(tmp_path))
    zoomed = box_zoom(state, PlotBoxZoomRequest(depth_from=1200, depth_to=1600))
    panned = pan_plot(zoomed, PlotPanRequest(delta_m=100))

    undone = undo_plot_navigation(panned)
    redone = redo_plot_navigation(undone)

    assert undone.workspace.viewport.depth_range.from_md == 1200
    assert undone.workspace.viewport.depth_range.to_md == 1600
    assert redone.workspace.viewport.depth_range.from_md == 1300
    assert redone.workspace.viewport.depth_range.to_md == 1700


def test_navigation_history_is_limited(tmp_path):
    state = initialize_plot_navigation(_workspace(tmp_path), config=PlotNavigationConfig(max_history=2))
    state = box_zoom(state, PlotBoxZoomRequest(depth_from=1100, depth_to=1900))
    state = box_zoom(state, PlotBoxZoomRequest(depth_from=1200, depth_to=1800))
    state = box_zoom(state, PlotBoxZoomRequest(depth_from=1300, depth_to=1700))

    assert len(state.history.undo_stack) == 2

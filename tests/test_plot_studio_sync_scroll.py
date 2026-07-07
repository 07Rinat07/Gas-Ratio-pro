from __future__ import annotations

import pytest

from projects import create_project
from projects.plot_studio import add_plot_track, save_plot_template
from projects.plot_studio_core import build_plot_workspace
from projects.plot_studio_navigation import build_plot_navigation_bounds
from projects.plot_studio_sync_scroll import (
    PlotScrollConfig,
    PlotScrollRequest,
    align_workspace_to_bounds,
    build_synchronized_scroll_manifest,
    build_synchronized_track_states,
    initialize_synchronized_scrolling,
    scroll_synchronized_tracks,
    scroll_to_depth,
)


def _workspace(tmp_path):
    project = create_project(tmp_path, name="Sync Scroll")
    template = save_plot_template(tmp_path, project.id, "Sync Scroll", template_id="sync-scroll", well_id="well-01")
    template = add_plot_track(tmp_path, project.id, template.id, "Density", track_id="track-density")
    return build_plot_workspace(template, depth_from=1000, depth_to=1400, active_track_id="track-gamma", crosshair_md=1380)


def test_synchronized_scrolling_initializes_track_states(tmp_path):
    workspace = _workspace(tmp_path)
    bounds = build_plot_navigation_bounds(1000, 2000)

    result = initialize_synchronized_scrolling(workspace, bounds=bounds)
    manifest = build_synchronized_scroll_manifest(result)

    assert result.action == "init_synchronized_scrolling"
    assert result.workspace.viewport.synchronized is True
    assert len(result.track_states) == len(workspace.tracks)
    assert manifest["tracks"][0]["depth_from"] == 1000
    assert all(track.synchronized for track in result.track_states)


def test_scroll_down_moves_all_tracks_by_delta_without_mutating_source(tmp_path):
    workspace = _workspace(tmp_path)
    bounds = build_plot_navigation_bounds(1000, 2000)

    result = scroll_synchronized_tracks(workspace, PlotScrollRequest(direction="down", delta_m=150), bounds=bounds)

    assert result.changed is True
    assert workspace.viewport.depth_range.from_md == 1000
    assert result.workspace.viewport.depth_range.from_md == 1150
    assert result.workspace.viewport.depth_range.to_md == 1550
    assert {state.depth_from for state in result.track_states} == {1150}
    assert result.workspace.crosshair.md_m == 1380


def test_scroll_up_is_clamped_to_top_boundary(tmp_path):
    workspace = _workspace(tmp_path)
    bounds = build_plot_navigation_bounds(1000, 2000)

    result = scroll_synchronized_tracks(workspace, PlotScrollRequest(direction="up", delta_m=500), bounds=bounds)

    assert result.changed is False
    assert result.workspace.viewport.depth_range.from_md == 1000
    assert result.workspace.viewport.depth_range.to_md == 1400
    assert "boundary" in result.messages[0]


def test_scroll_down_is_clamped_to_bottom_boundary(tmp_path):
    workspace = _workspace(tmp_path)
    bounds = build_plot_navigation_bounds(1000, 1500)

    result = scroll_synchronized_tracks(workspace, PlotScrollRequest(direction="down", delta_m=800), bounds=bounds)

    assert result.workspace.viewport.depth_range.from_md == 1100
    assert result.workspace.viewport.depth_range.to_md == 1500
    assert result.workspace.crosshair.md_m == 1380


def test_scroll_fraction_uses_source_specific_config(tmp_path):
    workspace = _workspace(tmp_path)
    bounds = build_plot_navigation_bounds(1000, 2000)

    result = scroll_synchronized_tracks(
        workspace,
        PlotScrollRequest(direction="down", source="keyboard"),
        bounds=bounds,
        config=PlotScrollConfig(keyboard_step_fraction=0.5),
    )

    assert result.workspace.viewport.depth_range.from_md == 1200
    assert result.workspace.viewport.depth_range.to_md == 1600


def test_scroll_to_depth_centers_viewport_and_clamps_edges(tmp_path):
    workspace = _workspace(tmp_path)
    bounds = build_plot_navigation_bounds(1000, 2000)

    centered = scroll_to_depth(workspace, 1700, bounds=bounds)
    clamped = scroll_to_depth(workspace, 1950, bounds=bounds)

    assert centered.workspace.viewport.depth_range.from_md == 1500
    assert centered.workspace.viewport.depth_range.to_md == 1900
    assert clamped.workspace.viewport.depth_range.from_md == 1600
    assert clamped.workspace.viewport.depth_range.to_md == 2000


def test_align_workspace_to_bounds_clamps_current_viewport(tmp_path):
    workspace = _workspace(tmp_path)
    bounds = build_plot_navigation_bounds(900, 1300)

    result = align_workspace_to_bounds(workspace, bounds)

    assert result.workspace.viewport.depth_range.from_md == 900
    assert result.workspace.viewport.depth_range.to_md == 1300
    assert result.workspace.crosshair.md_m == 1300


def test_synchronized_scroll_validates_direction_and_fraction(tmp_path):
    workspace = _workspace(tmp_path)
    bounds = build_plot_navigation_bounds(1000, 2000)

    with pytest.raises(ValueError, match="direction"):
        scroll_synchronized_tracks(workspace, PlotScrollRequest(direction="left"), bounds=bounds)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="доля"):
        scroll_synchronized_tracks(workspace, PlotScrollRequest(direction="down", fraction=0), bounds=bounds)


def test_build_synchronized_track_states_matches_workspace_tracks(tmp_path):
    workspace = _workspace(tmp_path)

    states = build_synchronized_track_states(workspace)

    assert tuple(state.track_id for state in states) == workspace.track_ids
    assert all(state.depth_to == 1400 for state in states)

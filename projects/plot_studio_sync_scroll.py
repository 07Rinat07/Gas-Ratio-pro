from __future__ import annotations

"""Synchronized scrolling backend for Plot Studio 2.0.

This module keeps vertical scrolling independent from the renderer and UI
framework.  It moves the shared measured-depth viewport for all visible tracks,
clamps it to the full data bounds and returns new immutable ``PlotWorkspace``
instances.  LAS source data and saved plot templates are never mutated.
"""

from dataclasses import dataclass
from typing import Any, Literal

from projects.plot_studio_core import (
    PlotViewportState,
    PlotWorkspace,
    build_crosshair_state,
    build_plot_depth_range,
    synchronize_plot_tracks,
)
from projects.plot_studio_navigation import PlotNavigationBounds, build_plot_navigation_bounds

ScrollDirection = Literal["up", "down"]


@dataclass(frozen=True)
class PlotScrollConfig:
    """Engineering limits and UI sensitivity for synchronized scrolling."""

    wheel_step_fraction: float = 0.10
    keyboard_step_fraction: float = 0.25
    page_step_fraction: float = 0.90
    min_window_m: float = 1.0


@dataclass(frozen=True)
class PlotScrollRequest:
    """Normalized vertical scroll request from mouse wheel, keyboard or UI button."""

    direction: ScrollDirection = "down"
    delta_m: Any | None = None
    fraction: Any | None = None
    source: str = "wheel"


@dataclass(frozen=True)
class PlotSynchronizedTrackState:
    """Per-track synchronized viewport state prepared for renderer manifests."""

    track_id: str
    depth_from: float
    depth_to: float
    height_m: float
    synchronized: bool = True


@dataclass(frozen=True)
class PlotScrollResult:
    """Result object for UI status panels, Session State and Operation Journal."""

    workspace: PlotWorkspace
    changed: bool
    action: str
    messages: tuple[str, ...] = ()
    track_states: tuple[PlotSynchronizedTrackState, ...] = ()


def _finite_float(value: Any, field_label: str) -> float:
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{field_label}: значение должно быть конечным числом.")
    return number


def _config_step_fraction(config: PlotScrollConfig, source: str) -> float:
    clean_source = str(source or "wheel").strip().lower()
    if clean_source in {"keyboard", "key", "arrow"}:
        return config.keyboard_step_fraction
    if clean_source in {"page", "pageup", "pagedown"}:
        return config.page_step_fraction
    return config.wheel_step_fraction


def _validate_fraction(value: float, field_label: str) -> float:
    if value <= 0:
        raise ValueError(f"{field_label}: доля прокрутки должна быть больше нуля.")
    return value


def _clamp_depth_window(start: float, height: float, bounds: PlotNavigationBounds) -> tuple[float, float]:
    height = min(max(height, bounds.min_window_m), bounds.height_m)
    end = start + height
    if start < bounds.depth_from:
        start = bounds.depth_from
        end = start + height
    if end > bounds.depth_to:
        end = bounds.depth_to
        start = end - height
    return round(start, 6), round(end, 6)


def _workspace_with_depth_interval(workspace: PlotWorkspace, depth_from: float, depth_to: float, bounds: PlotNavigationBounds) -> PlotWorkspace:
    current_depth = workspace.viewport.depth_range
    depth_range = build_plot_depth_range(
        depth_from,
        depth_to,
        major_step=current_depth.major_step,
        minor_step=current_depth.minor_step,
    )
    crosshair = workspace.crosshair
    if crosshair.md_m is not None:
        crosshair = build_crosshair_state(depth_range, md_m=crosshair.md_m, track_id=crosshair.track_id, x_value=crosshair.x_value)
    viewport = PlotViewportState(
        depth_range=depth_range,
        synchronized=True,
        active_track_id=workspace.viewport.active_track_id,
        zoom_level=round(bounds.height_m / depth_range.height_m, 6),
        pan_offset_m=round(depth_range.from_md - bounds.depth_from, 6),
    )
    return PlotWorkspace(
        template_id=workspace.template_id,
        name=workspace.name,
        well_id=workspace.well_id,
        viewport=viewport,
        tracks=workspace.tracks,
        crosshair=crosshair,
        layers=workspace.layers,
        issues=workspace.issues,
    )


def build_synchronized_track_states(workspace: PlotWorkspace) -> tuple[PlotSynchronizedTrackState, ...]:
    """Return one synchronized vertical interval for every visible track."""

    synced = synchronize_plot_tracks(workspace)
    return tuple(
        PlotSynchronizedTrackState(
            track_id=track_id,
            depth_from=state["depth_from"],
            depth_to=state["depth_to"],
            height_m=round(state["depth_to"] - state["depth_from"], 6),
            synchronized=True,
        )
        for track_id, state in synced.items()
    )


def initialize_synchronized_scrolling(
    workspace: PlotWorkspace,
    *,
    bounds: PlotNavigationBounds | None = None,
    config: PlotScrollConfig | None = None,
) -> PlotScrollResult:
    """Prepare synchronized scrolling state from the current Plot Workspace."""

    cfg = config or PlotScrollConfig()
    depth = workspace.viewport.depth_range
    actual_bounds = bounds or build_plot_navigation_bounds(depth.from_md, depth.to_md, min_window_m=cfg.min_window_m)
    normalized_from, normalized_to = _clamp_depth_window(depth.from_md, depth.height_m, actual_bounds)
    normalized_workspace = _workspace_with_depth_interval(workspace, normalized_from, normalized_to, actual_bounds)
    changed = normalized_workspace.viewport != workspace.viewport
    return PlotScrollResult(
        workspace=normalized_workspace,
        changed=changed,
        action="init_synchronized_scrolling",
        messages=("Synchronized scrolling initialized.",),
        track_states=build_synchronized_track_states(normalized_workspace),
    )


def scroll_synchronized_tracks(
    workspace: PlotWorkspace,
    request: PlotScrollRequest | None = None,
    *,
    bounds: PlotNavigationBounds | None = None,
    config: PlotScrollConfig | None = None,
) -> PlotScrollResult:
    """Scroll the shared depth viewport and apply it to all visible tracks."""

    cfg = config or PlotScrollConfig()
    req = request or PlotScrollRequest()
    depth = workspace.viewport.depth_range
    actual_bounds = bounds or build_plot_navigation_bounds(depth.from_md, depth.to_md, min_window_m=cfg.min_window_m)

    if req.delta_m is not None:
        delta = abs(_finite_float(req.delta_m, "Scroll delta"))
    else:
        fraction = _finite_float(req.fraction, "Scroll fraction") if req.fraction is not None else _config_step_fraction(cfg, req.source)
        delta = depth.height_m * _validate_fraction(fraction, "Scroll fraction")

    direction = str(req.direction or "down").strip().lower()
    if direction not in {"up", "down"}:
        raise ValueError("Scroll direction: поддерживаются только 'up' и 'down'.")
    signed_delta = -delta if direction == "up" else delta
    new_from, new_to = _clamp_depth_window(depth.from_md + signed_delta, depth.height_m, actual_bounds)
    changed_workspace = _workspace_with_depth_interval(workspace, new_from, new_to, actual_bounds)
    changed = changed_workspace.viewport.depth_range != workspace.viewport.depth_range
    return PlotScrollResult(
        workspace=changed_workspace,
        changed=changed,
        action=f"scroll_{direction}",
        messages=("Synchronized scroll applied." if changed else "Synchronized scroll unchanged at data boundary.",),
        track_states=build_synchronized_track_states(changed_workspace),
    )


def scroll_to_depth(
    workspace: PlotWorkspace,
    center_md: Any,
    *,
    bounds: PlotNavigationBounds | None = None,
    config: PlotScrollConfig | None = None,
) -> PlotScrollResult:
    """Center the synchronized viewport around a measured depth where possible."""

    cfg = config or PlotScrollConfig()
    depth = workspace.viewport.depth_range
    actual_bounds = bounds or build_plot_navigation_bounds(depth.from_md, depth.to_md, min_window_m=cfg.min_window_m)
    center = _finite_float(center_md, "Scroll center MD")
    height = depth.height_m
    new_from, new_to = _clamp_depth_window(center - height / 2, height, actual_bounds)
    changed_workspace = _workspace_with_depth_interval(workspace, new_from, new_to, actual_bounds)
    changed = changed_workspace.viewport.depth_range != workspace.viewport.depth_range
    return PlotScrollResult(
        workspace=changed_workspace,
        changed=changed,
        action="scroll_to_depth",
        messages=("Synchronized viewport centered on depth." if changed else "Synchronized viewport unchanged.",),
        track_states=build_synchronized_track_states(changed_workspace),
    )


def align_workspace_to_bounds(
    workspace: PlotWorkspace,
    bounds: PlotNavigationBounds,
) -> PlotScrollResult:
    """Clamp current shared viewport to full data bounds without changing window height."""

    depth = workspace.viewport.depth_range
    new_from, new_to = _clamp_depth_window(depth.from_md, depth.height_m, bounds)
    changed_workspace = _workspace_with_depth_interval(workspace, new_from, new_to, bounds)
    changed = changed_workspace.viewport.depth_range != workspace.viewport.depth_range
    return PlotScrollResult(
        workspace=changed_workspace,
        changed=changed,
        action="align_workspace_to_bounds",
        messages=("Viewport aligned to data bounds." if changed else "Viewport already inside data bounds.",),
        track_states=build_synchronized_track_states(changed_workspace),
    )


def build_synchronized_scroll_manifest(result: PlotScrollResult) -> dict[str, Any]:
    """Build serializable manifest for UI, debug panels and tests."""

    depth = result.workspace.viewport.depth_range
    return {
        "action": result.action,
        "changed": result.changed,
        "messages": list(result.messages),
        "viewport": {
            "depth_from": depth.from_md,
            "depth_to": depth.to_md,
            "height_m": depth.height_m,
            "zoom_level": result.workspace.viewport.zoom_level,
            "pan_offset_m": result.workspace.viewport.pan_offset_m,
            "synchronized": result.workspace.viewport.synchronized,
        },
        "tracks": [track.__dict__ for track in result.track_states],
    }

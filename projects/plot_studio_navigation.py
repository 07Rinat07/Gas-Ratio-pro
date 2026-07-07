from __future__ import annotations

"""Renderer-independent mouse zoom and navigation backend for Plot Studio 2.0.

The module intentionally works only with :class:`projects.plot_studio_core.PlotWorkspace`
objects.  It does not render figures, does not read/write LAS files and always returns
new immutable workspace states.  UI layers can convert wheel events, drag events and
box-selection events into the functions below.
"""

from dataclasses import dataclass
from typing import Any, Literal

from projects.plot_studio_core import (
    PlotViewportState,
    PlotWorkspace,
    build_crosshair_state,
    build_plot_depth_range,
)

ZoomDirection = Literal["in", "out"]


@dataclass(frozen=True)
class PlotNavigationBounds:
    """Allowed full depth interval for zoom and pan operations."""

    depth_from: float
    depth_to: float
    min_window_m: float = 1.0

    @property
    def height_m(self) -> float:
        return round(self.depth_to - self.depth_from, 6)


@dataclass(frozen=True)
class PlotNavigationConfig:
    """Interaction tuning for mouse wheel, box zoom and pan operations."""

    wheel_zoom_factor: float = 0.20
    zoom_out_factor: float = 0.25
    pan_fraction: float = 0.15
    min_window_m: float = 1.0
    max_history: int = 25


@dataclass(frozen=True)
class PlotNavigationHistory:
    """Undo/redo history of Plot Studio viewport states."""

    undo_stack: tuple[PlotViewportState, ...] = ()
    redo_stack: tuple[PlotViewportState, ...] = ()
    max_history: int = 25

    @property
    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self.redo_stack)


@dataclass(frozen=True)
class PlotNavigationState:
    """Workspace plus viewport history prepared for UI Session State."""

    workspace: PlotWorkspace
    bounds: PlotNavigationBounds
    history: PlotNavigationHistory
    action: str = ""


@dataclass(frozen=True)
class PlotBoxZoomRequest:
    """Normalized rectangle selection from UI."""

    depth_from: float
    depth_to: float
    track_id: str = ""
    x_min: float | None = None
    x_max: float | None = None


@dataclass(frozen=True)
class PlotPanRequest:
    """Normalized vertical pan request."""

    delta_m: float | None = None
    fraction: float | None = None


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


def build_plot_navigation_bounds(depth_from: Any, depth_to: Any, *, min_window_m: Any = 1.0) -> PlotNavigationBounds:
    """Validate and build full data bounds used by zoom/pan clamping."""

    left = _finite_float(depth_from, "Navigation bounds from")
    right = _finite_float(depth_to, "Navigation bounds to")
    minimum = _finite_float(min_window_m, "Minimum zoom window")
    if left < 0 or right < 0:
        raise ValueError("Navigation bounds: глубина не может быть отрицательной.")
    if left >= right:
        raise ValueError("Navigation bounds: верхняя граница должна быть меньше нижней.")
    if minimum <= 0:
        raise ValueError("Navigation bounds: минимальное окно должно быть больше нуля.")
    if minimum > right - left:
        raise ValueError("Navigation bounds: минимальное окно не может быть больше полного диапазона.")
    return PlotNavigationBounds(depth_from=left, depth_to=right, min_window_m=minimum)


def _clamp_interval(start: float, end: float, bounds: PlotNavigationBounds) -> tuple[float, float]:
    """Clamp interval to full data bounds while preserving requested height when possible."""

    height = max(end - start, bounds.min_window_m)
    height = min(height, bounds.height_m)
    if start < bounds.depth_from:
        start = bounds.depth_from
        end = start + height
    if end > bounds.depth_to:
        end = bounds.depth_to
        start = end - height
    return round(start, 6), round(end, 6)


def _workspace_with_viewport(workspace: PlotWorkspace, viewport: PlotViewportState) -> PlotWorkspace:
    crosshair = workspace.crosshair
    if crosshair.md_m is not None:
        crosshair = build_crosshair_state(
            viewport.depth_range,
            md_m=crosshair.md_m,
            track_id=crosshair.track_id,
            x_value=crosshair.x_value,
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


def _replace_depth_interval(
    workspace: PlotWorkspace,
    bounds: PlotNavigationBounds,
    depth_from: float,
    depth_to: float,
    *,
    action: str,
    zoom_level: float | None = None,
) -> PlotWorkspace:
    start, end = _clamp_interval(depth_from, depth_to, bounds)
    depth_range = build_plot_depth_range(
        start,
        end,
        major_step=workspace.viewport.depth_range.major_step,
        minor_step=workspace.viewport.depth_range.minor_step,
    )
    full_height = bounds.height_m or depth_range.height_m
    calculated_zoom = round(full_height / depth_range.height_m, 6)
    viewport = PlotViewportState(
        depth_range=depth_range,
        synchronized=workspace.viewport.synchronized,
        active_track_id=workspace.viewport.active_track_id,
        zoom_level=round(zoom_level if zoom_level is not None else calculated_zoom, 6),
        pan_offset_m=round(depth_range.from_md - bounds.depth_from, 6),
    )
    return _workspace_with_viewport(workspace, viewport)


def initialize_plot_navigation(
    workspace: PlotWorkspace,
    *,
    bounds: PlotNavigationBounds | None = None,
    config: PlotNavigationConfig | None = None,
) -> PlotNavigationState:
    """Create initial navigation state for UI Session State."""

    cfg = config or PlotNavigationConfig()
    depth = workspace.viewport.depth_range
    actual_bounds = bounds or build_plot_navigation_bounds(depth.from_md, depth.to_md, min_window_m=cfg.min_window_m)
    history = PlotNavigationHistory(max_history=cfg.max_history)
    return PlotNavigationState(workspace=workspace, bounds=actual_bounds, history=history, action="init")


def _push_history(history: PlotNavigationHistory, viewport: PlotViewportState) -> PlotNavigationHistory:
    stack = (history.undo_stack + (viewport,))[-history.max_history :]
    return PlotNavigationHistory(undo_stack=stack, redo_stack=(), max_history=history.max_history)


def _with_history(state: PlotNavigationState, workspace: PlotWorkspace, action: str) -> PlotNavigationState:
    if workspace.viewport == state.workspace.viewport:
        return PlotNavigationState(workspace=workspace, bounds=state.bounds, history=state.history, action=action)
    return PlotNavigationState(
        workspace=workspace,
        bounds=state.bounds,
        history=_push_history(state.history, state.workspace.viewport),
        action=action,
    )


def mouse_wheel_zoom(
    state: PlotNavigationState,
    *,
    direction: ZoomDirection,
    anchor_md: Any | None = None,
    config: PlotNavigationConfig | None = None,
) -> PlotNavigationState:
    """Zoom viewport around a depth anchor using a normalized mouse wheel event."""

    cfg = config or PlotNavigationConfig(max_history=state.history.max_history)
    depth = state.workspace.viewport.depth_range
    anchor = (depth.from_md + depth.to_md) / 2 if anchor_md is None else _finite_float(anchor_md, "Zoom anchor MD")
    anchor = min(max(anchor, depth.from_md), depth.to_md)
    current_height = depth.height_m
    if direction == "in":
        new_height = current_height * (1.0 - cfg.wheel_zoom_factor)
    elif direction == "out":
        new_height = current_height * (1.0 + cfg.zoom_out_factor)
    else:
        raise ValueError("Zoom direction: поддерживаются только 'in' и 'out'.")
    new_height = min(max(new_height, state.bounds.min_window_m), state.bounds.height_m)
    ratio = 0.5 if current_height <= 0 else (anchor - depth.from_md) / current_height
    new_start = anchor - new_height * ratio
    new_end = new_start + new_height
    workspace = _replace_depth_interval(state.workspace, state.bounds, new_start, new_end, action=f"wheel_zoom_{direction}")
    return _with_history(state, workspace, f"wheel_zoom_{direction}")


def box_zoom(state: PlotNavigationState, request: PlotBoxZoomRequest) -> PlotNavigationState:
    """Apply depth interval selected by a UI zoom rectangle."""

    start = _finite_float(request.depth_from, "Box Zoom depth from")
    end = _finite_float(request.depth_to, "Box Zoom depth to")
    if start > end:
        start, end = end, start
    if end - start < state.bounds.min_window_m:
        center = (start + end) / 2
        half = state.bounds.min_window_m / 2
        start, end = center - half, center + half
    workspace = _replace_depth_interval(state.workspace, state.bounds, start, end, action="box_zoom")
    return _with_history(state, workspace, "box_zoom")


def pan_plot(state: PlotNavigationState, request: PlotPanRequest | None = None, *, direction: Literal["up", "down"] | None = None) -> PlotNavigationState:
    """Move the current viewport vertically without changing zoom height."""

    depth = state.workspace.viewport.depth_range
    if request and request.delta_m is not None:
        delta = _finite_float(request.delta_m, "Pan delta")
    elif request and request.fraction is not None:
        delta = depth.height_m * _finite_float(request.fraction, "Pan fraction")
    elif direction == "up":
        delta = -depth.height_m * PlotNavigationConfig().pan_fraction
    elif direction == "down":
        delta = depth.height_m * PlotNavigationConfig().pan_fraction
    else:
        raise ValueError("Pan request: задайте delta_m, fraction или direction.")
    workspace = _replace_depth_interval(state.workspace, state.bounds, depth.from_md + delta, depth.to_md + delta, action="pan")
    return _with_history(state, workspace, "pan")


def reset_plot_zoom(state: PlotNavigationState) -> PlotNavigationState:
    """Reset viewport to full navigation bounds."""

    workspace = _replace_depth_interval(
        state.workspace,
        state.bounds,
        state.bounds.depth_from,
        state.bounds.depth_to,
        action="reset_zoom",
        zoom_level=1.0,
    )
    return _with_history(state, workspace, "reset_zoom")


def undo_plot_navigation(state: PlotNavigationState) -> PlotNavigationState:
    """Restore previous viewport from history."""

    if not state.history.undo_stack:
        return PlotNavigationState(workspace=state.workspace, bounds=state.bounds, history=state.history, action="undo_empty")
    previous = state.history.undo_stack[-1]
    undo_stack = state.history.undo_stack[:-1]
    redo_stack = (state.history.redo_stack + (state.workspace.viewport,))[-state.history.max_history :]
    workspace = _workspace_with_viewport(state.workspace, previous)
    history = PlotNavigationHistory(undo_stack=undo_stack, redo_stack=redo_stack, max_history=state.history.max_history)
    return PlotNavigationState(workspace=workspace, bounds=state.bounds, history=history, action="undo")


def redo_plot_navigation(state: PlotNavigationState) -> PlotNavigationState:
    """Restore next viewport from history."""

    if not state.history.redo_stack:
        return PlotNavigationState(workspace=state.workspace, bounds=state.bounds, history=state.history, action="redo_empty")
    next_viewport = state.history.redo_stack[-1]
    redo_stack = state.history.redo_stack[:-1]
    undo_stack = (state.history.undo_stack + (state.workspace.viewport,))[-state.history.max_history :]
    workspace = _workspace_with_viewport(state.workspace, next_viewport)
    history = PlotNavigationHistory(undo_stack=undo_stack, redo_stack=redo_stack, max_history=state.history.max_history)
    return PlotNavigationState(workspace=workspace, bounds=state.bounds, history=history, action="redo")


def build_plot_navigation_manifest(state: PlotNavigationState) -> dict[str, Any]:
    """Build serializable navigation state for Streamlit Session State/debug panels."""

    depth = state.workspace.viewport.depth_range
    return {
        "action": state.action,
        "bounds": {
            "depth_from": state.bounds.depth_from,
            "depth_to": state.bounds.depth_to,
            "height_m": state.bounds.height_m,
            "min_window_m": state.bounds.min_window_m,
        },
        "viewport": {
            "depth_from": depth.from_md,
            "depth_to": depth.to_md,
            "height_m": depth.height_m,
            "zoom_level": state.workspace.viewport.zoom_level,
            "pan_offset_m": state.workspace.viewport.pan_offset_m,
            "synchronized": state.workspace.viewport.synchronized,
            "active_track_id": state.workspace.viewport.active_track_id,
        },
        "history": {
            "undo_count": len(state.history.undo_stack),
            "redo_count": len(state.history.redo_stack),
            "can_undo": state.history.can_undo,
            "can_redo": state.history.can_redo,
            "max_history": state.history.max_history,
        },
    }

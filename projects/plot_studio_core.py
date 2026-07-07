from __future__ import annotations

"""Renderer-independent Plot Studio Core.

This module is the first backend layer of Plot Studio 2.0.  It does not draw
Plotly/Matplotlib figures and does not touch LAS source data.  Its job is to
convert a saved :class:`projects.plot_studio.PlotTemplate` into a stable
workspace model that UI renderers, export engines and future mouse-interaction
handlers can consume.
"""

from dataclasses import dataclass, field
from typing import Any, Iterable

from projects.plot_studio import PlotCurveConfig, PlotTemplate, PlotTrackConfig, validate_plot_template


DEFAULT_DEPTH_STEP_M = 100.0


@dataclass(frozen=True)
class PlotDepthRange:
    """Shared vertical depth interval for all Plot Studio tracks."""

    from_md: float
    to_md: float
    major_step: float = DEFAULT_DEPTH_STEP_M
    minor_step: float = 20.0

    @property
    def height_m(self) -> float:
        """Return interval height in measured-depth metres."""

        return round(self.to_md - self.from_md, 6)


@dataclass(frozen=True)
class PlotViewportState:
    """Current viewport state prepared for UI zoom/pan implementation."""

    depth_range: PlotDepthRange
    synchronized: bool = True
    active_track_id: str = ""
    zoom_level: float = 1.0
    pan_offset_m: float = 0.0


@dataclass(frozen=True)
class PlotCrosshairState:
    """Shared crosshair/cursor state for synchronized tracks."""

    enabled: bool = True
    md_m: float | None = None
    track_id: str = ""
    x_value: float | None = None
    label: str = ""


@dataclass(frozen=True)
class PlotLayerState:
    """Visibility state for core Plot Studio layers."""

    curves: bool = True
    grid: bool = True
    annotations: bool = True
    markers: bool = True
    crosshair: bool = True


@dataclass(frozen=True)
class PlotRenderCurve:
    """Curve description normalized for a renderer."""

    id: str
    mnemonic: str
    track_id: str
    color: str
    line_width: float
    line_style: str
    axis: dict[str, Any]


@dataclass(frozen=True)
class PlotRenderTrack:
    """Track description normalized for a renderer."""

    id: str
    title: str
    width: float
    width_percent: float
    curves: tuple[PlotRenderCurve, ...] = ()
    layers: PlotLayerState = field(default_factory=PlotLayerState)


@dataclass(frozen=True)
class PlotWorkspace:
    """Complete renderer-independent Plot Studio workspace."""

    template_id: str
    name: str
    well_id: str
    viewport: PlotViewportState
    tracks: tuple[PlotRenderTrack, ...]
    crosshair: PlotCrosshairState = field(default_factory=PlotCrosshairState)
    layers: PlotLayerState = field(default_factory=PlotLayerState)
    issues: tuple[str, ...] = ()

    @property
    def track_ids(self) -> tuple[str, ...]:
        return tuple(track.id for track in self.tracks)

    @property
    def curve_count(self) -> int:
        return sum(len(track.curves) for track in self.tracks)


def _finite_float(value: Any, field_label: str) -> float:
    """Convert value to finite float with a clear engineering error message."""

    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{field_label}: значение должно быть конечным числом.")
    return number


def build_plot_depth_range(depth_from: Any, depth_to: Any, *, major_step: Any = DEFAULT_DEPTH_STEP_M, minor_step: Any = 20.0) -> PlotDepthRange:
    """Build and validate the shared depth interval for Plot Studio.

    The interval is intentionally explicit: Plot Studio 2.0 must allow manual
    depth-from/depth-to control and synchronized display of all visible tracks.
    """

    from_md = _finite_float(depth_from, "Depth From")
    to_md = _finite_float(depth_to, "Depth To")
    major = _finite_float(major_step, "Depth major step")
    minor = _finite_float(minor_step, "Depth minor step")
    if from_md < 0 or to_md < 0:
        raise ValueError("Depth interval: глубина не может быть отрицательной.")
    if from_md >= to_md:
        raise ValueError("Depth interval: Depth From должен быть меньше Depth To.")
    if major <= 0 or minor <= 0:
        raise ValueError("Depth interval: шаг сетки должен быть больше нуля.")
    return PlotDepthRange(from_md=from_md, to_md=to_md, major_step=major, minor_step=minor)


def _curve_to_render(curve: PlotCurveConfig) -> PlotRenderCurve:
    return PlotRenderCurve(
        id=curve.id,
        mnemonic=curve.mnemonic,
        track_id=curve.track_id,
        color=curve.color,
        line_width=curve.line_width,
        line_style=curve.line_style,
        axis={
            "scale": curve.axis.scale,
            "min_value": curve.axis.min_value,
            "max_value": curve.axis.max_value,
            "inverted": curve.axis.inverted,
            "auto_range": curve.axis.auto_range,
        },
    )


def _tracks_to_render(template: PlotTemplate, layers: PlotLayerState) -> tuple[PlotRenderTrack, ...]:
    visible_tracks = tuple(track for track in template.tracks if track.visible)
    total_width = sum(track.width for track in visible_tracks) or 1.0
    curves_by_track: dict[str, list[PlotRenderCurve]] = {track.id: [] for track in visible_tracks}
    for curve in template.curves:
        if curve.track_id in curves_by_track:
            curves_by_track[curve.track_id].append(_curve_to_render(curve))
    return tuple(
        PlotRenderTrack(
            id=track.id,
            title=track.title,
            width=track.width,
            width_percent=round(track.width / total_width * 100, 2),
            curves=tuple(curves_by_track.get(track.id, ())),
            layers=layers,
        )
        for track in visible_tracks
    )


def build_plot_workspace(
    template: PlotTemplate,
    *,
    depth_from: Any = 0.0,
    depth_to: Any = 1000.0,
    depth_major_step: Any | None = None,
    depth_minor_step: Any | None = None,
    active_track_id: str = "",
    crosshair_md: Any | None = None,
    layers: PlotLayerState | None = None,
) -> PlotWorkspace:
    """Create a Plot Studio workspace from a saved template.

    The returned object is immutable and renderer-independent.  It is safe to
    pass to Streamlit, Plotly builders, export services and future interaction
    handlers without giving those layers write access to project metadata.
    """

    template_issues = validate_plot_template(template)
    issue_messages = tuple(issue.message for issue in template_issues)
    layer_state = layers or PlotLayerState(grid=template.show_grid)
    depth_range = build_plot_depth_range(
        depth_from,
        depth_to,
        major_step=template.grid_major_step if depth_major_step is None else depth_major_step,
        minor_step=template.grid_minor_step if depth_minor_step is None else depth_minor_step,
    )
    tracks = _tracks_to_render(template, layer_state)
    if not tracks:
        issue_messages = issue_messages + ("Нет видимых треков для построения Plot Studio.",)
    track_ids = {track.id for track in tracks}
    clean_active_track_id = active_track_id if active_track_id in track_ids else (tracks[0].id if tracks else "")
    crosshair = build_crosshair_state(depth_range, md_m=crosshair_md, track_id=clean_active_track_id) if crosshair_md is not None else PlotCrosshairState(track_id=clean_active_track_id)
    return PlotWorkspace(
        template_id=template.id,
        name=template.name,
        well_id=template.well_id,
        viewport=PlotViewportState(depth_range=depth_range, synchronized=True, active_track_id=clean_active_track_id),
        tracks=tracks,
        crosshair=crosshair,
        layers=layer_state,
        issues=issue_messages,
    )


def build_crosshair_state(depth_range: PlotDepthRange, *, md_m: Any, track_id: str = "", x_value: Any | None = None) -> PlotCrosshairState:
    """Build shared crosshair state and clamp it to the current depth interval."""

    md = _finite_float(md_m, "Crosshair MD")
    if md < depth_range.from_md:
        md = depth_range.from_md
    if md > depth_range.to_md:
        md = depth_range.to_md
    x = None if x_value is None else _finite_float(x_value, "Crosshair X")
    label = f"MD {md:.2f} m"
    if x is not None:
        label = f"{label}, X {x:.4g}"
    return PlotCrosshairState(enabled=True, md_m=md, track_id=track_id, x_value=x, label=label)


def set_plot_workspace_depth_interval(workspace: PlotWorkspace, depth_from: Any, depth_to: Any) -> PlotWorkspace:
    """Return a new workspace with the same tracks and a different depth interval."""

    depth_range = build_plot_depth_range(
        depth_from,
        depth_to,
        major_step=workspace.viewport.depth_range.major_step,
        minor_step=workspace.viewport.depth_range.minor_step,
    )
    crosshair = workspace.crosshair
    if crosshair.md_m is not None:
        crosshair = build_crosshair_state(depth_range, md_m=crosshair.md_m, track_id=crosshair.track_id, x_value=crosshair.x_value)
    return PlotWorkspace(
        template_id=workspace.template_id,
        name=workspace.name,
        well_id=workspace.well_id,
        viewport=PlotViewportState(
            depth_range=depth_range,
            synchronized=workspace.viewport.synchronized,
            active_track_id=workspace.viewport.active_track_id,
            zoom_level=workspace.viewport.zoom_level,
            pan_offset_m=workspace.viewport.pan_offset_m,
        ),
        tracks=workspace.tracks,
        crosshair=crosshair,
        layers=workspace.layers,
        issues=workspace.issues,
    )


def synchronize_plot_tracks(workspace: PlotWorkspace) -> dict[str, dict[str, float]]:
    """Return synchronized depth intervals for every visible track."""

    depth = workspace.viewport.depth_range
    return {
        track.id: {
            "depth_from": depth.from_md,
            "depth_to": depth.to_md,
            "major_step": depth.major_step,
            "minor_step": depth.minor_step,
        }
        for track in workspace.tracks
    }


def build_plot_workspace_manifest(workspace: PlotWorkspace) -> dict[str, Any]:
    """Build serializable manifest for UI, export and debugging."""

    return {
        "template_id": workspace.template_id,
        "name": workspace.name,
        "well_id": workspace.well_id,
        "viewport": {
            "depth_from": workspace.viewport.depth_range.from_md,
            "depth_to": workspace.viewport.depth_range.to_md,
            "height_m": workspace.viewport.depth_range.height_m,
            "major_step": workspace.viewport.depth_range.major_step,
            "minor_step": workspace.viewport.depth_range.minor_step,
            "synchronized": workspace.viewport.synchronized,
            "active_track_id": workspace.viewport.active_track_id,
            "zoom_level": workspace.viewport.zoom_level,
            "pan_offset_m": workspace.viewport.pan_offset_m,
        },
        "layers": workspace.layers.__dict__,
        "crosshair": workspace.crosshair.__dict__,
        "tracks": [
            {
                "id": track.id,
                "title": track.title,
                "width": track.width,
                "width_percent": track.width_percent,
                "layers": track.layers.__dict__,
                "curves": [curve.__dict__ for curve in track.curves],
            }
            for track in workspace.tracks
        ],
        "issues": list(workspace.issues),
    }


def build_plot_workspace_track_table(workspace: PlotWorkspace) -> tuple[dict[str, Any], ...]:
    """Build a compact table for Streamlit/sidebar diagnostics."""

    return tuple(
        {
            "Трек": track.title,
            "ID": track.id,
            "Ширина, %": track.width_percent,
            "Кривые": len(track.curves),
            "Depth From": workspace.viewport.depth_range.from_md,
            "Depth To": workspace.viewport.depth_range.to_md,
            "Синхронно": "да" if workspace.viewport.synchronized else "нет",
        }
        for track in workspace.tracks
    )

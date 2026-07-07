from __future__ import annotations

"""Manual X/Y scale backend for Plot Studio 2.0.

The module keeps Plot Studio scale editing renderer-independent.  It returns new
immutable workspace objects and never mutates LAS data, templates on disk or the
incoming workspace instance.  UI layers can bind these functions to sidebar
controls, keyboard shortcuts or tablet settings dialogs.
"""

from dataclasses import dataclass, replace
from typing import Any, Literal

from projects.plot_studio_core import (
    PlotDepthRange,
    PlotRenderCurve,
    PlotRenderTrack,
    PlotViewportState,
    PlotWorkspace,
    build_crosshair_state,
    build_plot_depth_range,
)

AxisScale = Literal["linear", "log"]


@dataclass(frozen=True)
class PlotManualScaleConfig:
    """Validation limits for manual Plot Studio scale controls."""

    min_depth_m: float = 0.0
    max_depth_m: float = 15000.0
    min_depth_window_m: float = 0.1
    min_x_window: float = 1e-9


@dataclass(frozen=True)
class PlotManualDepthScaleRequest:
    """Manual Y/depth interval request shared by all synchronized tracks."""

    depth_from: Any
    depth_to: Any
    major_step: Any | None = None
    minor_step: Any | None = None


@dataclass(frozen=True)
class PlotManualCurveScaleRequest:
    """Manual X-axis request for one curve or a group of curves."""

    min_value: Any
    max_value: Any
    curve_id: str = ""
    mnemonic: str = ""
    track_id: str = ""
    scale: AxisScale = "linear"
    inverted: bool | None = None
    auto_range: bool = False


@dataclass(frozen=True)
class PlotManualScaleResult:
    """Result object prepared for UI status panels and operation journal."""

    workspace: PlotWorkspace
    changed: bool
    action: str
    messages: tuple[str, ...] = ()
    affected_curves: tuple[str, ...] = ()


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


def _clean_scale(value: str) -> AxisScale:
    clean = str(value or "linear").strip().lower()
    if clean not in {"linear", "log"}:
        raise ValueError("X scale: поддерживаются только linear и log.")
    return clean  # type: ignore[return-value]


def _workspace_with_depth_range(workspace: PlotWorkspace, depth_range: PlotDepthRange) -> PlotWorkspace:
    crosshair = workspace.crosshair
    if crosshair.md_m is not None:
        crosshair = build_crosshair_state(
            depth_range,
            md_m=crosshair.md_m,
            track_id=crosshair.track_id,
            x_value=crosshair.x_value,
        )
    viewport = PlotViewportState(
        depth_range=depth_range,
        synchronized=workspace.viewport.synchronized,
        active_track_id=workspace.viewport.active_track_id,
        zoom_level=workspace.viewport.zoom_level,
        pan_offset_m=workspace.viewport.pan_offset_m,
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


def apply_manual_depth_scale(
    workspace: PlotWorkspace,
    request: PlotManualDepthScaleRequest,
    *,
    config: PlotManualScaleConfig | None = None,
) -> PlotManualScaleResult:
    """Apply explicit manual Y/depth scale to all synchronized tracks."""

    cfg = config or PlotManualScaleConfig()
    depth_from = _finite_float(request.depth_from, "Manual Depth From")
    depth_to = _finite_float(request.depth_to, "Manual Depth To")
    if depth_from < cfg.min_depth_m or depth_to > cfg.max_depth_m:
        raise ValueError(f"Manual Depth: диапазон должен быть в пределах {cfg.min_depth_m:g}..{cfg.max_depth_m:g} м.")
    if depth_to - depth_from < cfg.min_depth_window_m:
        raise ValueError("Manual Depth: окно глубины слишком маленькое.")

    current = workspace.viewport.depth_range
    major = current.major_step if request.major_step is None else request.major_step
    minor = current.minor_step if request.minor_step is None else request.minor_step
    depth_range = build_plot_depth_range(depth_from, depth_to, major_step=major, minor_step=minor)
    changed_workspace = _workspace_with_depth_range(workspace, depth_range)
    changed = changed_workspace.viewport.depth_range != workspace.viewport.depth_range
    return PlotManualScaleResult(
        workspace=changed_workspace,
        changed=changed,
        action="manual_depth_scale",
        messages=("Manual depth scale applied." if changed else "Manual depth scale unchanged.",),
    )


def _curve_matches(curve: PlotRenderCurve, request: PlotManualCurveScaleRequest) -> bool:
    if request.curve_id and curve.id != request.curve_id:
        return False
    if request.mnemonic and curve.mnemonic.upper() != request.mnemonic.upper():
        return False
    if request.track_id and curve.track_id != request.track_id:
        return False
    return bool(request.curve_id or request.mnemonic or request.track_id)


def _replace_curve_axis(curve: PlotRenderCurve, request: PlotManualCurveScaleRequest, cfg: PlotManualScaleConfig) -> PlotRenderCurve:
    x_min = _finite_float(request.min_value, "Manual X min")
    x_max = _finite_float(request.max_value, "Manual X max")
    if x_max - x_min < cfg.min_x_window:
        raise ValueError("Manual X scale: минимум должен быть меньше максимума.")
    scale = _clean_scale(request.scale)
    if scale == "log" and x_min <= 0:
        raise ValueError("Manual X scale: для log шкалы минимум должен быть больше нуля.")
    axis = dict(curve.axis)
    axis.update(
        {
            "scale": scale,
            "min_value": x_min,
            "max_value": x_max,
            "inverted": axis.get("inverted", False) if request.inverted is None else bool(request.inverted),
            "auto_range": bool(request.auto_range),
        }
    )
    return replace(curve, axis=axis)


def apply_manual_curve_scale(
    workspace: PlotWorkspace,
    request: PlotManualCurveScaleRequest,
    *,
    config: PlotManualScaleConfig | None = None,
) -> PlotManualScaleResult:
    """Apply explicit manual X scale to matching visible curves."""

    cfg = config or PlotManualScaleConfig()
    affected: list[str] = []
    new_tracks: list[PlotRenderTrack] = []
    for track in workspace.tracks:
        new_curves: list[PlotRenderCurve] = []
        for curve in track.curves:
            if _curve_matches(curve, request):
                curve = _replace_curve_axis(curve, request, cfg)
                affected.append(curve.id)
            new_curves.append(curve)
        new_tracks.append(replace(track, curves=tuple(new_curves)))

    if not affected:
        return PlotManualScaleResult(
            workspace=workspace,
            changed=False,
            action="manual_curve_scale",
            messages=("Manual X scale: подходящие кривые не найдены.",),
            affected_curves=(),
        )

    changed_workspace = PlotWorkspace(
        template_id=workspace.template_id,
        name=workspace.name,
        well_id=workspace.well_id,
        viewport=workspace.viewport,
        tracks=tuple(new_tracks),
        crosshair=workspace.crosshair,
        layers=workspace.layers,
        issues=workspace.issues,
    )
    return PlotManualScaleResult(
        workspace=changed_workspace,
        changed=True,
        action="manual_curve_scale",
        messages=(f"Manual X scale applied to {len(affected)} curve(s).",),
        affected_curves=tuple(affected),
    )


def reset_curve_auto_scale(workspace: PlotWorkspace, *, curve_id: str = "", mnemonic: str = "", track_id: str = "") -> PlotManualScaleResult:
    """Return matching curves to automatic X scale mode."""

    request = PlotManualCurveScaleRequest(min_value=0, max_value=1, curve_id=curve_id, mnemonic=mnemonic, track_id=track_id)
    affected: list[str] = []
    new_tracks: list[PlotRenderTrack] = []
    for track in workspace.tracks:
        new_curves: list[PlotRenderCurve] = []
        for curve in track.curves:
            if _curve_matches(curve, request):
                axis = dict(curve.axis)
                axis.update({"min_value": None, "max_value": None, "auto_range": True})
                curve = replace(curve, axis=axis)
                affected.append(curve.id)
            new_curves.append(curve)
        new_tracks.append(replace(track, curves=tuple(new_curves)))

    if not affected:
        return PlotManualScaleResult(workspace=workspace, changed=False, action="reset_curve_auto_scale", messages=("Auto scale: подходящие кривые не найдены.",))

    changed_workspace = PlotWorkspace(
        template_id=workspace.template_id,
        name=workspace.name,
        well_id=workspace.well_id,
        viewport=workspace.viewport,
        tracks=tuple(new_tracks),
        crosshair=workspace.crosshair,
        layers=workspace.layers,
        issues=workspace.issues,
    )
    return PlotManualScaleResult(
        workspace=changed_workspace,
        changed=True,
        action="reset_curve_auto_scale",
        messages=(f"Auto scale restored for {len(affected)} curve(s).",),
        affected_curves=tuple(affected),
    )


def build_manual_scale_manifest(result: PlotManualScaleResult) -> dict[str, Any]:
    """Build serializable manifest for UI, logs and tests."""

    depth = result.workspace.viewport.depth_range
    return {
        "action": result.action,
        "changed": result.changed,
        "messages": list(result.messages),
        "affected_curves": list(result.affected_curves),
        "depth_scale": {
            "from_md": depth.from_md,
            "to_md": depth.to_md,
            "major_step": depth.major_step,
            "minor_step": depth.minor_step,
        },
        "curve_scales": [
            {
                "track_id": track.id,
                "curve_id": curve.id,
                "mnemonic": curve.mnemonic,
                "scale": curve.axis.get("scale"),
                "min_value": curve.axis.get("min_value"),
                "max_value": curve.axis.get("max_value"),
                "auto_range": curve.axis.get("auto_range"),
                "inverted": curve.axis.get("inverted"),
            }
            for track in result.workspace.tracks
            for curve in track.curves
        ],
    }

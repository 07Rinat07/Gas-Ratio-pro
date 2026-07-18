"""Renderer-neutral LAS visualization payloads for Modern Workbench.

The service prepares lightweight plot-ready data from a selected LAS file without
importing Streamlit, matplotlib or plotly.  It returns a small serializable
contract: depth axis, track descriptors and decimated curve points.  Renderers can
choose any plotting backend while domain parsing stays inside the service layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from services.las_curve_metadata_service import DEPTH_MNEMONICS
from services.las_manager_service import LasManagerService
from services.visualization_engine_core import VisualizationEngineCore
from services.visualization_scene_pipeline import VisualizationScenePipeline
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer

DEFAULT_SAMPLE_LIMIT = 240
DEFAULT_CURVE_LIMIT = 8
DEFAULT_MAX_POINT_GAP_FACTOR = 3.0
GAS_MNEMONICS = {"C1", "C2", "C3", "IC4", "NC4", "IC5", "NC5", "TG", "GAS", "TOTALGAS"}
RESISTIVITY_HINTS = {"RT", "ILD", "ILM", "LLD", "LLS", "RES", "AT90"}
POROSITY_HINTS = {"NPHI", "DPHI", "RHOB", "DT", "PEF"}
GAMMA_HINTS = {"GR", "SGR", "CGR"}

TRACK_STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "track.gamma": {"palette_key": "gamma", "stroke": "#2f7d32", "fill": "#e8f5e9", "line_width": 1.3},
    "track.gas": {"palette_key": "gas", "stroke": "#ef6c00", "fill": "#fff3e0", "line_width": 1.4},
    "track.resistivity": {"palette_key": "resistivity", "stroke": "#1565c0", "fill": "#e3f2fd", "line_width": 1.2},
    "track.porosity": {"palette_key": "porosity", "stroke": "#6a1b9a", "fill": "#f3e5f5", "line_width": 1.2},
    "track.other": {"palette_key": "other", "stroke": "#455a64", "fill": "#eceff1", "line_width": 1.0},
}

FLUID_STYLE_PRESETS: dict[str, dict[str, str]] = {
    "oil": {"palette_key": "fluid.oil", "fill": "#d7a84f", "stroke": "#8d6e20"},
    "gas": {"palette_key": "fluid.gas", "fill": "#ef8f35", "stroke": "#a84c00"},
    "condensate": {"palette_key": "fluid.condensate", "fill": "#f6c96d", "stroke": "#ad7d00"},
    "water": {"palette_key": "fluid.water", "fill": "#64b5f6", "stroke": "#1565c0"},
    "unknown": {"palette_key": "fluid.unknown", "fill": "#b0bec5", "stroke": "#546e7a"},
}


@dataclass(frozen=True, slots=True)
class LasCurvePlotPayload:
    """Small sampled curve payload for renderers."""

    mnemonic: str
    unit: str = ""
    track_id: str = "track.other"
    axis: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)
    point_count: int = 0
    sampled_count: int = 0
    min_value: float | None = None
    max_value: float | None = None
    points: tuple[dict[str, float], ...] = field(default_factory=tuple)
    sampling: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mnemonic": self.mnemonic,
            "unit": self.unit,
            "track_id": self.track_id,
            "axis": dict(self.axis),
            "style": dict(self.style),
            "point_count": self.point_count,
            "sampled_count": self.sampled_count,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "points": [dict(point) for point in self.points],
            "sampling": dict(self.sampling),
            "quality": dict(self.quality),
        }


@dataclass(frozen=True, slots=True)
class LasTrackPlotPayload:
    """Track metadata used by UI-neutral LAS plot renderers."""

    id: str
    title: str
    curve_ids: tuple[str, ...] = field(default_factory=tuple)
    width: float = 1.0
    printable: bool = True
    axis: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "curve_ids": list(self.curve_ids),
            "width": self.width,
            "printable": self.printable,
            "axis": dict(self.axis),
            "style": dict(self.style),
        }


@dataclass(frozen=True, slots=True)
class LasIntervalOverlayPayload:
    """Renderer-neutral interval overlay for LAS plots.

    The overlay describes only printable depth bands and engineering labels. It
    intentionally avoids color objects, plotting callbacks and raw interval
    calculation rows so any renderer can draw the same interpretation zones.
    """

    id: str
    top: float
    base: float
    label: str = ""
    fluid_type: str = "unknown"
    confidence: str = ""
    selected: bool = False
    track_scope: tuple[str, ...] = field(default_factory=tuple)
    style: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "top": self.top,
            "base": self.base,
            "label": self.label,
            "fluid_type": self.fluid_type,
            "confidence": self.confidence,
            "selected": self.selected,
            "track_scope": list(self.track_scope),
            "style": dict(self.style),
        }


@dataclass(frozen=True, slots=True)
class LasVisualizationPayload:
    """Complete renderer-neutral LAS visualization contract."""

    project_id: str
    las_id: str
    depth_curve: str = ""
    depth_unit: str = ""
    depth_range: dict[str, float | None] = field(default_factory=dict)
    sample_limit: int = DEFAULT_SAMPLE_LIMIT
    truncated: bool = False
    tracks: tuple[LasTrackPlotPayload, ...] = field(default_factory=tuple)
    curves: tuple[LasCurvePlotPayload, ...] = field(default_factory=tuple)
    overlays: tuple[LasIntervalOverlayPayload, ...] = field(default_factory=tuple)
    quality_flags: tuple[str, ...] = field(default_factory=tuple)
    print_profile: dict[str, Any] = field(default_factory=dict)
    sampling_profile: dict[str, Any] = field(default_factory=dict)
    data_quality: dict[str, Any] = field(default_factory=dict)
    legend: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    visible_tracks: tuple[str, ...] = field(default_factory=tuple)
    plot_summary: dict[str, Any] = field(default_factory=dict)
    preview: dict[str, Any] = field(default_factory=dict)
    engine_scene: dict[str, Any] = field(default_factory=dict)
    scene_pipeline: dict[str, Any] = field(default_factory=dict)
    scene_renderers: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "las_id": self.las_id,
            "depth_curve": self.depth_curve,
            "depth_unit": self.depth_unit,
            "depth_range": dict(self.depth_range),
            "sample_limit": self.sample_limit,
            "truncated": self.truncated,
            "tracks": [track.to_dict() for track in self.tracks],
            "curves": [curve.to_dict() for curve in self.curves],
            "overlays": [overlay.to_dict() for overlay in self.overlays],
            "quality_flags": list(self.quality_flags),
            "print_profile": dict(self.print_profile),
            "sampling_profile": dict(self.sampling_profile),
            "data_quality": dict(self.data_quality),
            "legend": [dict(item) for item in self.legend],
            "visible_tracks": list(self.visible_tracks),
            "plot_summary": dict(self.plot_summary),
            "preview": dict(self.preview),
            "engine_scene": dict(self.engine_scene),
            "scene_pipeline": dict(self.scene_pipeline),
            "scene_renderers": dict(self.scene_renderers),
        }


def _units(frame: pd.DataFrame) -> dict[str, str]:
    return {str(k).strip(): str(v).strip() for k, v in dict(frame.attrs.get("las_units", {}) or {}).items()}


def _select_depth_curve(frame: pd.DataFrame) -> str:
    for column in frame.columns:
        if str(column).strip().upper() in DEPTH_MNEMONICS:
            return str(column).strip()
    for column in frame.columns:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.notna().any():
            return str(column).strip()
    return ""


def _depth_range(depth: pd.Series) -> dict[str, float | None]:
    clean = pd.to_numeric(depth, errors="coerce").dropna()
    if clean.empty:
        return {"start": None, "stop": None, "step": None}
    diffs = clean.diff().dropna()
    non_zero = diffs[diffs != 0]
    return {
        "start": float(clean.min()),
        "stop": float(clean.max()),
        "step": float(non_zero.median()) if not non_zero.empty else None,
    }




def _sampling_profile(sample_limit: int) -> dict[str, Any]:
    safe_limit = max(2, int(sample_limit or DEFAULT_SAMPLE_LIMIT))
    return {
        "strategy": "depth_preserving_even_decimation",
        "sample_limit": safe_limit,
        "preserve_first_last": True,
        "renderer_may_smooth": True,
        "raw_dataframe_included": False,
    }


def _curve_quality(valid: pd.DataFrame, *, depth_range: dict[str, float | None], original_count: int) -> dict[str, Any]:
    clean_depth = pd.to_numeric(valid["depth"], errors="coerce").dropna() if "depth" in valid else pd.Series(dtype="float64")
    gaps: list[float] = []
    has_depth_gaps = False
    if len(clean_depth) >= 3:
        diffs = clean_depth.sort_values().diff().dropna().abs()
        non_zero = diffs[diffs > 0]
        if not non_zero.empty:
            expected_step = _float_or_none(depth_range.get("step")) or float(non_zero.median())
            threshold = expected_step * DEFAULT_MAX_POINT_GAP_FACTOR
            gaps = [float(value) for value in non_zero[non_zero > threshold].head(10).tolist()]
            has_depth_gaps = bool(gaps)
    missing_values = max(0, int(original_count) - int(len(valid)))
    return {
        "valid_points": int(len(valid)),
        "missing_points": missing_values,
        "missing_ratio": round(missing_values / max(int(original_count), 1), 6),
        "has_depth_gaps": has_depth_gaps,
        "depth_gaps": gaps,
        "within_depth_range": {
            "start": depth_range.get("start"),
            "stop": depth_range.get("stop"),
        },
    }


def _payload_data_quality(curves: Sequence[LasCurvePlotPayload], frame_length: int) -> dict[str, Any]:
    missing_total = sum(int(curve.quality.get("missing_points", 0)) for curve in curves)
    gap_curves = [curve.mnemonic for curve in curves if curve.quality.get("has_depth_gaps")]
    return {
        "row_count": int(frame_length),
        "curve_count": len(curves),
        "total_missing_points": missing_total,
        "curves_with_depth_gaps": gap_curves,
        "raw_dataframe_included": False,
    }



def _legend(curves: Sequence[LasCurvePlotPayload], overlays: Sequence[LasIntervalOverlayPayload]) -> tuple[dict[str, Any], ...]:
    """Build a renderer-ready legend without requiring UI-side inspection.

    The legend is intentionally compact: curve entries describe printable line
    labels and overlay entries describe interpreted fluid bands.  Renderers can
    display this payload directly and should not recalculate colors or labels.
    """

    items: list[dict[str, Any]] = []
    for curve in curves:
        label = curve.mnemonic if not curve.unit else f"{curve.mnemonic} ({curve.unit})"
        items.append(
            {
                "id": f"curve.{curve.mnemonic}",
                "kind": "curve",
                "label": label,
                "track_id": curve.track_id,
                "style": dict(curve.style),
            }
        )
    seen_fluids: set[str] = set()
    for overlay in overlays:
        fluid = str(overlay.fluid_type or "unknown").lower()
        if fluid in seen_fluids:
            continue
        seen_fluids.add(fluid)
        items.append(
            {
                "id": f"overlay.{fluid}",
                "kind": "interval_overlay",
                "label": _fluid_label(fluid),
                "fluid_type": fluid,
                "style": dict(overlay.style),
            }
        )
    return tuple(items)


def _fluid_label(fluid_type: str) -> str:
    return {
        "oil": "Oil interval",
        "gas": "Gas interval",
        "condensate": "Condensate interval",
        "water": "Water interval",
        "unknown": "Interpreted interval",
    }.get(str(fluid_type or "unknown").lower(), "Interpreted interval")


def _visible_tracks(tracks: Sequence[LasTrackPlotPayload]) -> tuple[str, ...]:
    """Return track ids that renderers should show by default."""

    return tuple(track.id for track in tracks if track.curve_ids and track.printable)


def _plot_summary(
    *,
    depth_curve: str,
    depth_unit: str,
    depth_range: Mapping[str, float | None],
    tracks: Sequence[LasTrackPlotPayload],
    curves: Sequence[LasCurvePlotPayload],
    overlays: Sequence[LasIntervalOverlayPayload],
) -> dict[str, Any]:
    """Return a compact human-readable plot summary for Workbench cards."""

    return {
        "title": "LAS visualization",
        "depth_curve": depth_curve,
        "depth_unit": depth_unit,
        "depth_start": depth_range.get("start"),
        "depth_stop": depth_range.get("stop"),
        "track_count": len(tracks),
        "curve_count": len(curves),
        "overlay_count": len(overlays),
        "renderer_ready": bool(tracks and curves),
    }


def _svg_escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _mini_svg_preview(
    *,
    tracks: Sequence[LasTrackPlotPayload],
    curves: Sequence[LasCurvePlotPayload],
    overlays: Sequence[LasIntervalOverlayPayload],
    depth_range: Mapping[str, float | None],
) -> dict[str, Any]:
    """Return a tiny renderer-neutral SVG preview descriptor.

    The SVG is intentionally schematic.  It is not the final plotting backend and
    does not contain all curve points.  Its job is to give Workbench and reports a
    stable, lightweight preview artifact while preserving the rule that UI layers
    only consume prepared payloads.
    """

    width = max(360, 120 * max(len(tracks), 1))
    height = 240
    top_margin = 28
    bottom_margin = 18
    plot_height = height - top_margin - bottom_margin
    track_width = width / max(len(tracks), 1)
    depth_start = _float_or_none(depth_range.get("start"))
    depth_stop = _float_or_none(depth_range.get("stop"))
    depth_span = max((depth_stop or 0.0) - (depth_start or 0.0), 1e-9)

    curve_by_track: dict[str, list[LasCurvePlotPayload]] = {}
    for curve in curves:
        curve_by_track.setdefault(curve.track_id, []).append(curve)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        '<rect width="100%" height="100%" fill="white"/>',
    ]
    for index, track in enumerate(tracks):
        x = index * track_width
        parts.append(f'<g data-track="{_svg_escape(track.id)}">')
        parts.append(f'<rect x="{x:.1f}" y="{top_margin}" width="{track_width:.1f}" height="{plot_height}" fill="{track.style.get("fill", "#ffffff")}" stroke="#cfd8dc"/>')
        parts.append(f'<text x="{x + 6:.1f}" y="18" font-size="11" font-family="Arial, sans-serif">{_svg_escape(track.title)}</text>')
        for overlay in overlays:
            if track.id not in overlay.track_scope:
                continue
            y1 = top_margin + ((overlay.top - (depth_start or overlay.top)) / depth_span) * plot_height
            y2 = top_margin + ((overlay.base - (depth_start or overlay.top)) / depth_span) * plot_height
            oy = max(top_margin, min(y1, y2))
            oh = max(2.0, min(top_margin + plot_height, max(y1, y2)) - oy)
            parts.append(f'<rect x="{x + 2:.1f}" y="{oy:.1f}" width="{track_width - 4:.1f}" height="{oh:.1f}" fill="{overlay.style.get("fill", "#b0bec5")}" opacity="0.26"/>')
        for curve in curve_by_track.get(track.id, [])[:3]:
            if not curve.points:
                continue
            value_span = max(float(curve.max_value or 0.0) - float(curve.min_value or 0.0), 1e-9)
            poly_points: list[str] = []
            for point in curve.points[:80]:
                depth = float(point["depth"])
                value = float(point["value"])
                px = x + 8 + ((value - float(curve.min_value or 0.0)) / value_span) * max(track_width - 16, 1.0)
                py = top_margin + ((depth - (depth_start or depth)) / depth_span) * plot_height
                poly_points.append(f"{px:.1f},{py:.1f}")
            parts.append(f'<polyline points="{" ".join(poly_points)}" fill="none" stroke="{curve.style.get("stroke", "#455a64")}" stroke-width="1.4"/>')
        parts.append('</g>')
    parts.append('</svg>')
    svg = "".join(parts)
    return {
        "kind": "svg_preview",
        "format": "svg",
        "width": width,
        "height": height,
        "track_count": len(tracks),
        "curve_count": len(curves),
        "overlay_count": len(overlays),
        "export_ready": bool(tracks and curves),
        "contains_raw_dataframe": False,
        "svg": svg,
    }

def _track_style(track_id: str) -> dict[str, Any]:
    return dict(TRACK_STYLE_PRESETS.get(track_id, TRACK_STYLE_PRESETS["track.other"]))


def _fluid_style(fluid_type: str) -> dict[str, Any]:
    key = str(fluid_type or "unknown").strip().lower()
    return dict(FLUID_STYLE_PRESETS.get(key, FLUID_STYLE_PRESETS["unknown"]))


def _axis_scale(track_id: str, values: pd.Series) -> str:
    if track_id in {"track.resistivity", "track.gas"}:
        clean = pd.to_numeric(values, errors="coerce").dropna()
        if not clean.empty and float(clean.min()) > 0 and float(clean.max()) / max(float(clean.min()), 1e-12) >= 100:
            return "log"
    return "linear"


def _axis_payload(track_id: str, unit: str, values: pd.Series) -> dict[str, Any]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return {
        "unit": unit,
        "scale": _axis_scale(track_id, values),
        "min": float(clean.min()) if not clean.empty else None,
        "max": float(clean.max()) if not clean.empty else None,
        "grid": True,
        "printable": True,
    }


def _print_profile() -> dict[str, Any]:
    return {
        "quality": "print",
        "preferred_format": "svg_pdf",
        "depth_axis": "vertical",
        "min_curve_width_px": 2,
        "grid": True,
        "legend": True,
    }

def _track_id(mnemonic: str) -> str:
    key = mnemonic.strip().upper()
    if key in DEPTH_MNEMONICS:
        return "track.depth"
    if key in GAMMA_HINTS:
        return "track.gamma"
    if key in GAS_MNEMONICS:
        return "track.gas"
    if key in RESISTIVITY_HINTS:
        return "track.resistivity"
    if key in POROSITY_HINTS:
        return "track.porosity"
    return "track.other"


def _track_title(track_id: str) -> str:
    return {
        "track.depth": "Depth",
        "track.gamma": "Gamma Ray",
        "track.gas": "Gas",
        "track.resistivity": "Resistivity",
        "track.porosity": "Porosity",
        "track.other": "Other Curves",
    }.get(track_id, "Other Curves")


def _sample_indices(length: int, limit: int) -> list[int]:
    if length <= 0:
        return []
    safe_limit = max(2, int(limit or DEFAULT_SAMPLE_LIMIT))
    if length <= safe_limit:
        return list(range(length))
    step = (length - 1) / float(safe_limit - 1)
    return sorted({round(i * step) for i in range(safe_limit)})


def _curve_payload(
    frame: pd.DataFrame,
    *,
    depth_curve: str,
    curve: str,
    units: dict[str, str],
    sample_limit: int,
    depth_info: dict[str, float | None],
) -> LasCurvePlotPayload | None:
    if curve == depth_curve:
        return None
    values = pd.to_numeric(frame[curve], errors="coerce")
    depths = pd.to_numeric(frame[depth_curve], errors="coerce") if depth_curve in frame.columns else pd.Series(dtype="float64")
    original_count = int(len(values))
    valid = pd.DataFrame({"depth": depths, "value": values}).dropna()
    if valid.empty:
        return None
    indices = _sample_indices(len(valid), sample_limit)
    sampled = valid.iloc[indices]
    points = tuple({"depth": float(row.depth), "value": float(row.value)} for row in sampled.itertuples(index=False))
    track_id = _track_id(str(curve))
    return LasCurvePlotPayload(
        mnemonic=str(curve),
        unit=units.get(str(curve), ""),
        track_id=track_id,
        axis=_axis_payload(track_id, units.get(str(curve), ""), valid["value"]),
        style=_track_style(track_id),
        point_count=int(len(valid)),
        sampled_count=int(len(points)),
        min_value=float(valid["value"].min()),
        max_value=float(valid["value"].max()),
        points=points,
        sampling={
            "strategy": "depth_preserving_even_decimation",
            "sample_limit": max(2, int(sample_limit or DEFAULT_SAMPLE_LIMIT)),
            "decimated": len(points) < len(valid),
            "preserve_first_last": True,
        },
        quality=_curve_quality(valid, depth_range=depth_info, original_count=original_count),
    )


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_interval_id(interval_id: str) -> tuple[float | None, float | None]:
    clean = str(interval_id or "").strip()
    for sep in ("-", "..", ":"):
        if sep in clean:
            left, right = clean.split(sep, 1)
            return _float_or_none(left), _float_or_none(right)
    return None, None


def _interval_metadata(metadata: Mapping[str, Mapping[str, Any]] | None, interval_id: str) -> dict[str, Any]:
    if not metadata:
        return {}
    return dict(metadata.get(interval_id, {}) or {})


def _build_overlays(
    interval_ids: Sequence[str] | None,
    *,
    depth_start: float | None,
    depth_stop: float | None,
    metadata: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[LasIntervalOverlayPayload, ...]:
    overlays: list[LasIntervalOverlayPayload] = []
    for raw_id in tuple(interval_ids or ()): 
        interval_id = str(raw_id or "").strip()
        if not interval_id:
            continue
        item = _interval_metadata(metadata, interval_id)
        top = _float_or_none(item.get("top"))
        base = _float_or_none(item.get("base"))
        if top is None or base is None:
            top, base = _parse_interval_id(interval_id)
        if top is None or base is None:
            continue
        top, base = sorted((top, base))
        if depth_start is not None and base < depth_start:
            continue
        if depth_stop is not None and top > depth_stop:
            continue
        label = str(item.get("label") or item.get("title") or interval_id)
        fluid_type = str(item.get("fluid_type") or item.get("fluid") or "unknown")
        overlays.append(
            LasIntervalOverlayPayload(
                id=interval_id,
                top=float(top),
                base=float(base),
                label=label,
                fluid_type=fluid_type,
                confidence=str(item.get("confidence") or item.get("confidence_level") or ""),
                selected=True,
                track_scope=("track.gamma", "track.gas", "track.resistivity", "track.porosity"),
                style=_fluid_style(fluid_type),
            )
        )
    return tuple(overlays)


def _build_tracks(curves: Iterable[LasCurvePlotPayload]) -> tuple[LasTrackPlotPayload, ...]:
    grouped: dict[str, list[str]] = {}
    for curve in curves:
        grouped.setdefault(curve.track_id, []).append(curve.mnemonic)
    order = ("track.gamma", "track.gas", "track.resistivity", "track.porosity", "track.other")
    tracks: list[LasTrackPlotPayload] = []
    for track_id in order:
        if track_id in grouped:
            tracks.append(
                LasTrackPlotPayload(
                    track_id,
                    _track_title(track_id),
                    tuple(grouped[track_id]),
                    axis={"depth_unit": "", "orientation": "vertical", "grid": True},
                    style=_track_style(track_id),
                )
            )
    return tuple(tracks)


class LasVisualizationPayloadService:
    """Create printable renderer-neutral LAS plot payloads.

    Project-backed ``build`` and in-memory ``build_from_frame`` share one
    implementation so visible Print Center previews and stored LAS workspaces
    cannot drift into different visualization pipelines.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT, manager: LasManagerService | None = None) -> None:
        self.root = Path(root)
        self.manager = manager or LasManagerService(self.root)

    def build(
        self,
        project_id: str,
        las_id: str,
        *,
        curve_limit: int = DEFAULT_CURVE_LIMIT,
        sample_limit: int = DEFAULT_SAMPLE_LIMIT,
        interval_ids: Sequence[str] | None = None,
        interval_metadata: Mapping[str, Mapping[str, Any]] | None = None,
        print_options: Mapping[str, Any] | None = None,
    ) -> LasVisualizationPayload:
        clean_project_id = safe_project_id(project_id)
        clean_las_id = str(las_id or "").strip()
        if not clean_las_id:
            raise ValueError("LAS id must not be empty.")
        frame = self.manager.read_dataframe(clean_project_id, clean_las_id)
        return self.build_from_frame(
            frame,
            project_id=clean_project_id,
            las_id=clean_las_id,
            curve_limit=curve_limit,
            sample_limit=sample_limit,
            interval_ids=interval_ids,
            interval_metadata=interval_metadata,
            print_options=print_options,
        )

    def build_from_frame(
        self,
        frame: pd.DataFrame,
        *,
        project_id: str = "in-memory",
        las_id: str = "current-selection",
        curve_limit: int = DEFAULT_CURVE_LIMIT,
        sample_limit: int = DEFAULT_SAMPLE_LIMIT,
        interval_ids: Sequence[str] | None = None,
        interval_metadata: Mapping[str, Mapping[str, Any]] | None = None,
        print_options: Mapping[str, Any] | None = None,
    ) -> LasVisualizationPayload:
        """Build the same pipeline from an already prepared dataframe.

        This method is the application-layer bridge used by Professional Print
        Center. It accepts computed report data but returns only renderer-neutral
        contracts; raw dataframe content never enters the page-aware package.
        """

        clean_project_id = str(project_id or "in-memory").strip() or "in-memory"
        clean_las_id = str(las_id or "current-selection").strip() or "current-selection"
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame")
        unit_map = _units(frame)
        depth_curve = _select_depth_curve(frame)
        if not depth_curve or depth_curve not in frame.columns:
            return LasVisualizationPayload(
                project_id=clean_project_id,
                las_id=clean_las_id,
                sample_limit=sample_limit,
                quality_flags=("missing_depth_curve",),
            )
        depth_info = _depth_range(frame[depth_curve])
        candidate_curves = [str(column) for column in frame.columns if str(column) != depth_curve]
        limited_curves = candidate_curves[: max(1, int(curve_limit or DEFAULT_CURVE_LIMIT))]
        curve_payloads = tuple(
            payload
            for payload in (
                _curve_payload(
                    frame,
                    depth_curve=depth_curve,
                    curve=curve,
                    units=unit_map,
                    sample_limit=sample_limit,
                    depth_info=depth_info,
                )
                for curve in limited_curves
            )
            if payload is not None
        )
        flags: list[str] = []
        if len(candidate_curves) > len(limited_curves):
            flags.append("curves_truncated")
        if any(curve.sampled_count < curve.point_count for curve in curve_payloads):
            flags.append("curves_decimated")
        if not curve_payloads:
            flags.append("no_numeric_visualization_curves")
        overlays = _build_overlays(
            interval_ids,
            depth_start=depth_info.get("start"),
            depth_stop=depth_info.get("stop"),
            metadata=interval_metadata,
        )
        if interval_ids and not overlays:
            flags.append("interval_overlays_empty")
        tracks = _build_tracks(curve_payloads)
        mini_preview = _mini_svg_preview(
            tracks=tracks,
            curves=curve_payloads,
            overlays=overlays,
            depth_range=depth_info,
        )
        base_payload_for_engine = {
            "source_type": "las",
            "source_id": clean_las_id,
            "tracks": [track.to_dict() for track in tracks],
            "curves": [curve.to_dict() for curve in curve_payloads],
            "overlays": [overlay.to_dict() for overlay in overlays],
            "depth_curve": depth_curve,
            "depth_unit": unit_map.get(depth_curve, ""),
            "depth_range": dict(depth_info),
            "quality_flags": list(flags),
            "legend": [dict(item) for item in _legend(curve_payloads, overlays)],
            "visible_tracks": list(_visible_tracks(tracks)),
            "plot_summary": _plot_summary(
                depth_curve=depth_curve,
                depth_unit=unit_map.get(depth_curve, ""),
                depth_range=depth_info,
                tracks=tracks,
                curves=curve_payloads,
                overlays=overlays,
            ),
            "preview": dict(mini_preview),
        }
        if isinstance(print_options, Mapping):
            base_payload_for_engine["print_options"] = dict(print_options)
        pipeline_result = VisualizationScenePipeline().run(base_payload_for_engine).to_dict()
        engine_scene = dict(pipeline_result["scene"])
        svg_scene = VisualizationSvgSceneRenderer().render(pipeline_result).to_dict()
        return LasVisualizationPayload(
            project_id=clean_project_id,
            las_id=clean_las_id,
            depth_curve=depth_curve,
            depth_unit=unit_map.get(depth_curve, ""),
            depth_range=depth_info,
            sample_limit=max(2, int(sample_limit or DEFAULT_SAMPLE_LIMIT)),
            truncated=bool(flags),
            tracks=tracks,
            curves=curve_payloads,
            overlays=overlays,
            quality_flags=tuple(flags),
            print_profile=_print_profile(),
            sampling_profile=_sampling_profile(sample_limit),
            data_quality=_payload_data_quality(curve_payloads, len(frame)),
            legend=tuple(base_payload_for_engine["legend"]),
            visible_tracks=tuple(base_payload_for_engine["visible_tracks"]),
            plot_summary=dict(base_payload_for_engine["plot_summary"]),
            preview=mini_preview,
            engine_scene=engine_scene,
            scene_pipeline=pipeline_result,
            scene_renderers={"svg": svg_scene},
        )

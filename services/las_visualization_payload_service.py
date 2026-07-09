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

DEFAULT_SAMPLE_LIMIT = 240
DEFAULT_CURVE_LIMIT = 8
GAS_MNEMONICS = {"C1", "C2", "C3", "IC4", "NC4", "IC5", "NC5", "TG", "GAS", "TOTALGAS"}
RESISTIVITY_HINTS = {"RT", "ILD", "ILM", "LLD", "LLS", "RES", "AT90"}
POROSITY_HINTS = {"NPHI", "DPHI", "RHOB", "DT", "PEF"}
GAMMA_HINTS = {"GR", "SGR", "CGR"}


@dataclass(frozen=True, slots=True)
class LasCurvePlotPayload:
    """Small sampled curve payload for renderers."""

    mnemonic: str
    unit: str = ""
    track_id: str = "track.other"
    point_count: int = 0
    sampled_count: int = 0
    min_value: float | None = None
    max_value: float | None = None
    points: tuple[dict[str, float], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mnemonic": self.mnemonic,
            "unit": self.unit,
            "track_id": self.track_id,
            "point_count": self.point_count,
            "sampled_count": self.sampled_count,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "points": [dict(point) for point in self.points],
        }


@dataclass(frozen=True, slots=True)
class LasTrackPlotPayload:
    """Track metadata used by UI-neutral LAS plot renderers."""

    id: str
    title: str
    curve_ids: tuple[str, ...] = field(default_factory=tuple)
    width: float = 1.0
    printable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "curve_ids": list(self.curve_ids),
            "width": self.width,
            "printable": self.printable,
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
) -> LasCurvePlotPayload | None:
    if curve == depth_curve:
        return None
    values = pd.to_numeric(frame[curve], errors="coerce")
    depths = pd.to_numeric(frame[depth_curve], errors="coerce") if depth_curve in frame.columns else pd.Series(dtype="float64")
    valid = pd.DataFrame({"depth": depths, "value": values}).dropna()
    if valid.empty:
        return None
    indices = _sample_indices(len(valid), sample_limit)
    sampled = valid.iloc[indices]
    points = tuple({"depth": float(row.depth), "value": float(row.value)} for row in sampled.itertuples(index=False))
    return LasCurvePlotPayload(
        mnemonic=str(curve),
        unit=units.get(str(curve), ""),
        track_id=_track_id(str(curve)),
        point_count=int(len(valid)),
        sampled_count=int(len(points)),
        min_value=float(valid["value"].min()),
        max_value=float(valid["value"].max()),
        points=points,
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
        overlays.append(
            LasIntervalOverlayPayload(
                id=interval_id,
                top=float(top),
                base=float(base),
                label=label,
                fluid_type=str(item.get("fluid_type") or item.get("fluid") or "unknown"),
                confidence=str(item.get("confidence") or item.get("confidence_level") or ""),
                selected=True,
                track_scope=("track.gamma", "track.gas", "track.resistivity", "track.porosity"),
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
            tracks.append(LasTrackPlotPayload(track_id, _track_title(track_id), tuple(grouped[track_id])))
    return tuple(tracks)


class LasVisualizationPayloadService:
    """Create printable renderer-neutral LAS plot payloads from project storage."""

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
    ) -> LasVisualizationPayload:
        clean_project_id = safe_project_id(project_id)
        clean_las_id = str(las_id or "").strip()
        if not clean_las_id:
            raise ValueError("LAS id must not be empty.")
        frame = self.manager.read_dataframe(clean_project_id, clean_las_id)
        unit_map = _units(frame)
        depth_curve = _select_depth_curve(frame)
        if not depth_curve or depth_curve not in frame.columns:
            return LasVisualizationPayload(
                project_id=clean_project_id,
                las_id=clean_las_id,
                sample_limit=sample_limit,
                quality_flags=("missing_depth_curve",),
            )
        candidate_curves = [str(column) for column in frame.columns if str(column) != depth_curve]
        limited_curves = candidate_curves[: max(1, int(curve_limit or DEFAULT_CURVE_LIMIT))]
        curve_payloads = tuple(
            payload
            for payload in (
                _curve_payload(frame, depth_curve=depth_curve, curve=curve, units=unit_map, sample_limit=sample_limit)
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
        depth_info = _depth_range(frame[depth_curve])
        overlays = _build_overlays(
            interval_ids,
            depth_start=depth_info.get("start"),
            depth_stop=depth_info.get("stop"),
            metadata=interval_metadata,
        )
        if interval_ids and not overlays:
            flags.append("interval_overlays_empty")
        return LasVisualizationPayload(
            project_id=clean_project_id,
            las_id=clean_las_id,
            depth_curve=depth_curve,
            depth_unit=unit_map.get(depth_curve, ""),
            depth_range=depth_info,
            sample_limit=max(2, int(sample_limit or DEFAULT_SAMPLE_LIMIT)),
            truncated=bool(flags),
            tracks=_build_tracks(curve_payloads),
            curves=curve_payloads,
            overlays=overlays,
            quality_flags=tuple(flags),
        )

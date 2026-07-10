"""Source-neutral domain model for Visualization Engine 2.0.

The model separates imported data contracts (LAS today, DLIS/WITSML/CSV later)
from scene construction and renderer implementations.  Adapters normalize source
payloads into this model; the scene pipeline consumes only the normalized domain
representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class VisualizationDomainTrack:
    """Logical engineering track before geometry is calculated."""

    id: str
    title: str
    width: float = 1.0
    printable: bool = True
    axis: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "width": self.width,
            "printable": self.printable,
            "axis": dict(self.axis),
            "style": dict(self.style),
        }


@dataclass(frozen=True, slots=True)
class VisualizationDomainCurve:
    """Normalized curve series independent of a file format or renderer."""

    mnemonic: str
    track_id: str
    unit: str = ""
    points: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    point_count: int = 0
    sampled_count: int = 0
    axis: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mnemonic": self.mnemonic,
            "track_id": self.track_id,
            "unit": self.unit,
            "points": [dict(point) for point in self.points],
            "point_count": self.point_count,
            "sampled_count": self.sampled_count,
            "axis": dict(self.axis),
            "style": dict(self.style),
        }


@dataclass(frozen=True, slots=True)
class VisualizationDomainInterval:
    """Normalized interpreted depth interval rendered as an overlay."""

    id: str
    top: float | None = None
    base: float | None = None
    label: str = ""
    fluid_type: str = "unknown"
    confidence: str = ""
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
            "track_scope": list(self.track_scope),
            "style": dict(self.style),
        }


@dataclass(frozen=True, slots=True)
class VisualizationDomainModel:
    """Complete source-neutral engineering visualization document."""

    schema: str = "visualization.domain.model"
    version: str = "1.0"
    source_type: str = "unknown"
    source_id: str = ""
    depth_curve: str = ""
    depth_unit: str = ""
    depth_range: dict[str, Any] = field(default_factory=dict)
    tracks: tuple[VisualizationDomainTrack, ...] = field(default_factory=tuple)
    curves: tuple[VisualizationDomainCurve, ...] = field(default_factory=tuple)
    intervals: tuple[VisualizationDomainInterval, ...] = field(default_factory=tuple)
    quality_flags: tuple[str, ...] = field(default_factory=tuple)
    presentation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "depth_curve": self.depth_curve,
            "depth_unit": self.depth_unit,
            "depth_range": dict(self.depth_range),
            "tracks": [track.to_dict() for track in self.tracks],
            "curves": [curve.to_dict() for curve in self.curves],
            "intervals": [interval.to_dict() for interval in self.intervals],
            "quality_flags": list(self.quality_flags),
            "presentation": dict(self.presentation),
            "raw_dataframe_included": False,
        }

    def to_engine_payload(self) -> dict[str, Any]:
        """Return the stable input expected by VisualizationEngineCore."""
        return {
            "tracks": [track.to_dict() for track in self.tracks],
            "curves": [curve.to_dict() for curve in self.curves],
            "overlays": [interval.to_dict() for interval in self.intervals],
            "depth_curve": self.depth_curve,
            "depth_unit": self.depth_unit,
            "depth_range": dict(self.depth_range),
            "quality_flags": list(self.quality_flags),
            "legend": list(self.presentation.get("legend", []) or []),
            "visible_tracks": list(self.presentation.get("visible_tracks", []) or []),
            "plot_summary": dict(self.presentation.get("plot_summary", {}) or {}),
            "preview": dict(self.presentation.get("preview", {}) or {}),
        }


class VisualizationDomainModelAdapter:
    """Normalize a source payload into VisualizationDomainModel."""

    def from_payload(
        self,
        payload: Mapping[str, Any],
        *,
        source_type: str = "las",
        source_id: str = "",
    ) -> VisualizationDomainModel:
        tracks = tuple(self._track(item) for item in _mappings(payload.get("tracks")) if item.get("id"))
        curves = tuple(
            self._curve(item)
            for item in _mappings(payload.get("curves"))
            if item.get("mnemonic")
        )
        intervals = tuple(
            self._interval(item)
            for item in _mappings(payload.get("overlays"))
            if item.get("id")
        )
        return VisualizationDomainModel(
            source_type=source_type,
            source_id=source_id,
            depth_curve=str(payload.get("depth_curve") or ""),
            depth_unit=str(payload.get("depth_unit") or ""),
            depth_range=dict(payload.get("depth_range", {}) or {}),
            tracks=tracks,
            curves=curves,
            intervals=intervals,
            quality_flags=tuple(str(item) for item in (payload.get("quality_flags", []) or [])),
            presentation={
                "legend": list(payload.get("legend", []) or []),
                "visible_tracks": list(payload.get("visible_tracks", []) or []),
                "plot_summary": dict(payload.get("plot_summary", {}) or {}),
                "preview": dict(payload.get("preview", {}) or {}),
            },
        )

    @staticmethod
    def _track(item: Mapping[str, Any]) -> VisualizationDomainTrack:
        return VisualizationDomainTrack(
            id=str(item.get("id") or ""),
            title=str(item.get("title") or item.get("id") or ""),
            width=float(item.get("width") or 1.0),
            printable=bool(item.get("printable", True)),
            axis=dict(item.get("axis", {}) or {}),
            style=dict(item.get("style", {}) or {}),
        )

    @staticmethod
    def _curve(item: Mapping[str, Any]) -> VisualizationDomainCurve:
        return VisualizationDomainCurve(
            mnemonic=str(item.get("mnemonic") or ""),
            track_id=str(item.get("track_id") or "track.other"),
            unit=str(item.get("unit") or ""),
            points=tuple(dict(point) for point in _mappings(item.get("points"))),
            point_count=int(item.get("point_count") or 0),
            sampled_count=int(item.get("sampled_count") or 0),
            axis=dict(item.get("axis", {}) or {}),
            style=dict(item.get("style", {}) or {}),
        )

    @staticmethod
    def _interval(item: Mapping[str, Any]) -> VisualizationDomainInterval:
        return VisualizationDomainInterval(
            id=str(item.get("id") or ""),
            top=_float_or_none(item.get("top")),
            base=_float_or_none(item.get("base")),
            label=str(item.get("label") or ""),
            fluid_type=str(item.get("fluid_type") or "unknown"),
            confidence=str(item.get("confidence") or ""),
            track_scope=tuple(str(value) for value in (item.get("track_scope", []) or [])),
            style=dict(item.get("style", {}) or {}),
        )


def _mappings(value: Any) -> list[Mapping[str, Any]]:
    if value is None or isinstance(value, (str, bytes, bytearray)):
        return []
    if not isinstance(value, Sequence):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _float_or_none(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None

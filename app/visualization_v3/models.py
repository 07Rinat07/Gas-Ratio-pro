from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True, slots=True)
class DepthTrackSpec:
    title: str = "Depth"
    unit: str = "m"
    width: int = 88
    major_step: float | None = None
    minor_divisions: int = 5


@dataclass(frozen=True, slots=True)
class CurveTrackSpec:
    key: str
    title: str
    unit: str = ""
    width: int = 150
    scale: str = "linear"
    minimum: float | None = None
    maximum: float | None = None
    stroke: str = "#111827"
    stroke_width: float = 1.25
    show_statistics: bool = True


@dataclass(frozen=True, slots=True)
class IntervalBand:
    top: float
    bottom: float
    label: str
    fluid: str = ""
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class CompositeLogSpec:
    depth_key: str = "depth"
    title: str = "Engineering Composite Log"
    depth_track: DepthTrackSpec = field(default_factory=DepthTrackSpec)
    tracks: tuple[CurveTrackSpec, ...] = field(default_factory=tuple)
    intervals: tuple[IntervalBand, ...] = field(default_factory=tuple)
    height: int = 900
    header_height: int = 86
    footer_height: int = 24
    left_padding: int = 12
    right_padding: int = 12
    background: str = "#ffffff"
    major_grid: str = "#94a3b8"
    minor_grid: str = "#d9e1ea"
    border: str = "#475569"
    font_family: str = "Arial, Helvetica, sans-serif"

    @classmethod
    def with_tracks(
        cls,
        tracks: Sequence[CurveTrackSpec],
        **kwargs,
    ) -> "CompositeLogSpec":
        return cls(tracks=tuple(tracks), **kwargs)

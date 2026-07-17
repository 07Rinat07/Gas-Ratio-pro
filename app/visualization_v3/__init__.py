"""Engineering Visualization v3.

Renderer-neutral composite log foundation with an SVG reference renderer.
The package is intentionally isolated from the legacy Plotly dashboards so it
can be introduced incrementally and tested independently.
"""

from .composite_engine import CompositeLogEngine, CompositeLogResult
from .models import CompositeLogSpec, CurveTrackSpec, DepthTrackSpec, IntervalBand

__all__ = [
    "CompositeLogEngine",
    "CompositeLogResult",
    "CompositeLogSpec",
    "CurveTrackSpec",
    "DepthTrackSpec",
    "IntervalBand",
]

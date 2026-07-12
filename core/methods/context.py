from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval
from palettes.config import DEFAULT_PIXLER_ZONES, PixlerZone, TernaryRegion


@dataclass(frozen=True, slots=True)
class MethodContext:
    """Shared immutable input contract for all interval interpretation methods."""

    frame: pd.DataFrame
    interval: HydrocarbonInterval
    interval_id: str
    selected_row: pd.Series | Mapping[str, object]
    pixler_zones: tuple[PixlerZone, ...] = DEFAULT_PIXLER_ZONES
    ternary_regions: tuple[TernaryRegion, ...] = ()
    settings: Mapping[str, Any] = field(default_factory=dict)

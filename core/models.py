from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


STANDARD_FIELDS: tuple[str, ...] = (
    "well",
    "depth",
    "depth_from",
    "depth_to",
    "c1",
    "c2",
    "c3",
    "ic4",
    "nc4",
    "ic5",
    "nc5",
    "co2",
    "h2s",
    "rop",
    "lithology",
)

GAS_COMPONENT_FIELDS: tuple[str, ...] = ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5")

OPTIONAL_NUMERIC_FIELDS: tuple[str, ...] = (
    "depth",
    "depth_from",
    "depth_to",
    "co2",
    "h2s",
    "rop",
)


@dataclass(frozen=True)
class HeaderCandidate:
    row_index: int
    score: int
    recognized_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class HeaderDetectionResult:
    header_row: int
    score: int
    candidates: tuple[HeaderCandidate, ...] = ()


@dataclass(frozen=True)
class MappingResult:
    mapping: dict[str, str]
    unmapped_columns: tuple[str, ...] = ()
    duplicate_matches: dict[str, tuple[str, ...]] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreparedDataFrame:
    data: pd.DataFrame
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CalculationConfig:
    ch_mode: str = "A"


@dataclass(frozen=True)
class CalculationResult:
    data: pd.DataFrame
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

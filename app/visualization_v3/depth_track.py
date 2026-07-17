from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DepthTick:
    value: float
    major: bool


def nice_major_step(span: float, target_major_ticks: int = 12) -> float:
    """Return a stable engineering depth step using 1/2/5 decades."""
    if not math.isfinite(span) or span <= 0:
        return 1.0
    raw = span / max(2, target_major_ticks)
    exponent = math.floor(math.log10(raw))
    fraction = raw / (10**exponent)
    if fraction <= 1:
        nice = 1
    elif fraction <= 2:
        nice = 2
    elif fraction <= 5:
        nice = 5
    else:
        nice = 10
    return float(nice * (10**exponent))


def build_depth_ticks(
    start: float,
    stop: float,
    *,
    major_step: float | None = None,
    minor_divisions: int = 5,
) -> tuple[DepthTick, ...]:
    if not math.isfinite(start) or not math.isfinite(stop) or stop <= start:
        return ()
    major = major_step if major_step and major_step > 0 else nice_major_step(stop - start)
    minor_divisions = max(1, int(minor_divisions))
    minor = major / minor_divisions
    first = math.ceil(start / minor) * minor
    count = int(math.floor((stop - first) / minor)) + 1
    ticks: list[DepthTick] = []
    for index in range(max(0, count)):
        value = first + index * minor
        major_ratio = value / major
        is_major = math.isclose(major_ratio, round(major_ratio), abs_tol=1e-8)
        ticks.append(DepthTick(value=round(value, 8), major=is_major))
    return tuple(ticks)

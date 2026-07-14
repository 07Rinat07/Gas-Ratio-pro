from __future__ import annotations

"""Filtering and analytical summaries for manual interpretation intervals.

The service is pure and Streamlit-independent. It never mutates repository
state, which makes it safe for search, dashboards and filtered exports.
"""

from dataclasses import dataclass
from typing import Iterable, Sequence

from projects.interpretation_intervals import InterpretationInterval


@dataclass(frozen=True)
class InterpretationIntervalFilter:
    query: str = ""
    interval_types: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    depth_top: float | None = None
    depth_base: float | None = None
    min_thickness: float | None = None
    max_thickness: float | None = None


@dataclass(frozen=True)
class InterpretationIntervalTypeSummary:
    interval_type: str
    count: int
    total_thickness: float
    min_top: float
    max_base: float
    average_thickness: float


@dataclass(frozen=True)
class InterpretationIntervalSummary:
    count: int
    total_thickness: float
    min_top: float | None
    max_base: float | None
    average_thickness: float
    covered_depth: float
    type_count: int
    source_count: int
    by_type: tuple[InterpretationIntervalTypeSummary, ...]


def filter_interpretation_intervals(
    intervals: Iterable[InterpretationInterval],
    criteria: InterpretationIntervalFilter,
) -> tuple[InterpretationInterval, ...]:
    """Return a deterministic subset matching text, categorical and depth filters.

    A depth window includes intervals that intersect it with positive thickness.
    Adjacent intervals touching the window boundary are excluded.
    """

    query = criteria.query.strip().casefold()
    type_filter = {value.strip() for value in criteria.interval_types if value.strip()}
    source_filter = {value.strip() for value in criteria.sources if value.strip()}
    depth_top, depth_base = _validate_optional_range(criteria.depth_top, criteria.depth_base)
    min_thickness, max_thickness = _validate_thickness_range(
        criteria.min_thickness, criteria.max_thickness
    )

    matched: list[InterpretationInterval] = []
    for interval in intervals:
        searchable = " ".join(
            (interval.id, interval.label, interval.interval_type, interval.comment, interval.source)
        ).casefold()
        if query and query not in searchable:
            continue
        if type_filter and interval.interval_type not in type_filter:
            continue
        if source_filter and interval.source not in source_filter:
            continue
        if depth_top is not None and interval.base <= depth_top:
            continue
        if depth_base is not None and interval.top >= depth_base:
            continue
        if min_thickness is not None and interval.thickness < min_thickness:
            continue
        if max_thickness is not None and interval.thickness > max_thickness:
            continue
        matched.append(interval)

    return tuple(sorted(matched, key=lambda item: (item.top, item.base, item.label.casefold(), item.id)))


def summarize_interpretation_intervals(
    intervals: Sequence[InterpretationInterval] | Iterable[InterpretationInterval],
) -> InterpretationIntervalSummary:
    ordered = tuple(sorted(intervals, key=lambda item: (item.top, item.base, item.id)))
    if not ordered:
        return InterpretationIntervalSummary(
            count=0,
            total_thickness=0.0,
            min_top=None,
            max_base=None,
            average_thickness=0.0,
            covered_depth=0.0,
            type_count=0,
            source_count=0,
            by_type=(),
        )

    total_thickness = round(sum(item.thickness for item in ordered), 6)
    grouped: dict[str, list[InterpretationInterval]] = {}
    for interval in ordered:
        grouped.setdefault(interval.interval_type, []).append(interval)

    type_rows = tuple(
        InterpretationIntervalTypeSummary(
            interval_type=interval_type,
            count=len(items),
            total_thickness=round(sum(item.thickness for item in items), 6),
            min_top=min(item.top for item in items),
            max_base=max(item.base for item in items),
            average_thickness=round(sum(item.thickness for item in items) / len(items), 6),
        )
        for interval_type, items in sorted(grouped.items(), key=lambda pair: pair[0].casefold())
    )

    return InterpretationIntervalSummary(
        count=len(ordered),
        total_thickness=total_thickness,
        min_top=min(item.top for item in ordered),
        max_base=max(item.base for item in ordered),
        average_thickness=round(total_thickness / len(ordered), 6),
        covered_depth=_calculate_union_thickness(ordered),
        type_count=len(grouped),
        source_count=len({item.source for item in ordered}),
        by_type=type_rows,
    )


def _calculate_union_thickness(intervals: Sequence[InterpretationInterval]) -> float:
    ranges = sorted((item.top, item.base) for item in intervals)
    current_top, current_base = ranges[0]
    covered = 0.0
    for top, base in ranges[1:]:
        if top <= current_base:
            current_base = max(current_base, base)
        else:
            covered += current_base - current_top
            current_top, current_base = top, base
    covered += current_base - current_top
    return round(covered, 6)


def _validate_optional_range(
    top: float | None, base: float | None
) -> tuple[float | None, float | None]:
    clean_top = None if top is None else float(top)
    clean_base = None if base is None else float(base)
    if clean_top is not None and clean_base is not None and clean_top >= clean_base:
        raise ValueError("Верх диапазона фильтра должен быть меньше низа.")
    return clean_top, clean_base


def _validate_thickness_range(
    minimum: float | None, maximum: float | None
) -> tuple[float | None, float | None]:
    clean_min = None if minimum is None else float(minimum)
    clean_max = None if maximum is None else float(maximum)
    if clean_min is not None and clean_min < 0:
        raise ValueError("Минимальная мощность не может быть отрицательной.")
    if clean_max is not None and clean_max < 0:
        raise ValueError("Максимальная мощность не может быть отрицательной.")
    if clean_min is not None and clean_max is not None and clean_min > clean_max:
        raise ValueError("Минимальная мощность не может быть больше максимальной.")
    return clean_min, clean_max

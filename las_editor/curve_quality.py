from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd

from las_editor.curve_categories import suggest_curve_category
from las_editor.curve_grouping import suggest_curve_group
from las_editor.curve_units import suggest_curve_unit

DEFAULT_MISSING_RATIO_THRESHOLD = 0.15
DEFAULT_FLAT_RUN_MIN_LENGTH = 4
DEFAULT_SPIKE_ZSCORE_THRESHOLD = 6.0

QUALITY_FLAG_LABELS: dict[str, str] = {
    "missing": "Missing values",
    "flat": "Flat interval",
    "spike": "Spike candidate",
    "non_numeric": "Non-numeric curve",
    "ok": "OK",
}

QUALITY_SEVERITY_LABELS: dict[str, str] = {
    "critical": "Critical",
    "warning": "Warning",
    "review": "Review",
    "ok": "OK",
}


@dataclass(frozen=True)
class CurveQualityFlag:
    curve_name: str
    flag_type: str
    severity: str
    message: str
    sample_count: int
    affected_count: int
    affected_ratio: float
    group: str
    category: str
    unit: str
    recommendation: str


@dataclass(frozen=True)
class CurveQualityResult:
    flags: tuple[CurveQualityFlag, ...]
    diagnostics: tuple[str, ...]
    summary: dict[str, int]
    references: dict[str, Any]


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def _longest_flat_run(values: pd.Series) -> int:
    clean = values.dropna().reset_index(drop=True)
    if clean.empty:
        return 0
    longest = 1
    current = 1
    previous = clean.iloc[0]
    for value in clean.iloc[1:]:
        if value == previous:
            current += 1
        else:
            longest = max(longest, current)
            current = 1
            previous = value
    return max(longest, current)


def _spike_count(values: pd.Series, threshold: float) -> int:
    clean = values.dropna()
    if len(clean) < 5:
        return 0
    median = clean.median()
    mad = (clean - median).abs().median()
    if pd.isna(mad) or mad == 0:
        std = clean.std(ddof=0)
        if pd.isna(std) or std == 0:
            return 0
        zscores = (clean - clean.mean()).abs() / std
    else:
        zscores = 0.6745 * (clean - median).abs() / mad
    return int((zscores >= threshold).sum())


def _context_for_curve(
    curve: str,
    *,
    group_overrides: dict[str, str],
    category_overrides: dict[str, str],
    unit_overrides: dict[str, str],
) -> tuple[str, str, str]:
    group = group_overrides.get(curve) or suggest_curve_group(curve)
    category = category_overrides.get(curve) or suggest_curve_category(curve, group=group)
    unit = unit_overrides.get(curve) or suggest_curve_unit(curve, group=group, category=category)
    return group, category, unit


def detect_curve_quality_flags(
    df: pd.DataFrame,
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None = None,
    missing_ratio_threshold: float = DEFAULT_MISSING_RATIO_THRESHOLD,
    flat_run_min_length: int = DEFAULT_FLAT_RUN_MIN_LENGTH,
    spike_zscore_threshold: float = DEFAULT_SPIKE_ZSCORE_THRESHOLD,
    references: dict[str, Any] | None = None,
) -> CurveQualityResult:
    """Build diagnostic quality flags for LAS curves without mutating data.

    The function is intentionally metadata/diagnostic only. It reports missing data,
    long flat intervals, spike candidates and non-numeric curves so an engineer can
    decide whether to edit, mask, re-import or keep each curve.
    """

    columns = tuple(str(column) for column in df.columns)
    group_map = {str(curve): str(group) for curve, group in dict(group_overrides or {}).items()}
    category_map = {str(curve): str(category) for curve, category in dict(category_overrides or {}).items()}
    unit_map = {str(curve): str(unit) for curve, unit in dict(unit_overrides or {}).items()}
    flags: list[CurveQualityFlag] = []
    diagnostics = [f"Проверено кривых качества: {len(columns)}."]

    for curve in columns:
        values = _numeric_series(df, curve)
        sample_count = int(len(values))
        numeric_count = int(values.notna().sum())
        group, category, unit = _context_for_curve(
            curve,
            group_overrides=group_map,
            category_overrides=category_map,
            unit_overrides=unit_map,
        )

        if sample_count and numeric_count == 0:
            flags.append(
                CurveQualityFlag(
                    curve_name=curve,
                    flag_type="non_numeric",
                    severity="review",
                    message="Кривая не содержит числовых значений после приведения типов.",
                    sample_count=sample_count,
                    affected_count=sample_count,
                    affected_ratio=1.0,
                    group=group,
                    category=category,
                    unit=unit,
                    recommendation="Проверьте, является ли кривая текстовой metadata-колонкой или ошибкой импорта.",
                )
            )
            continue

        missing_count = int(values.isna().sum())
        missing_ratio = float(missing_count / sample_count) if sample_count else 0.0
        if missing_ratio >= missing_ratio_threshold and missing_count > 0:
            flags.append(
                CurveQualityFlag(
                    curve_name=curve,
                    flag_type="missing",
                    severity="critical" if missing_ratio >= 0.50 else "warning",
                    message=f"Пропуски составляют {missing_ratio:.1%} выборки.",
                    sample_count=sample_count,
                    affected_count=missing_count,
                    affected_ratio=missing_ratio,
                    group=group,
                    category=category,
                    unit=unit,
                    recommendation="Проверьте NULL-значения LAS, интервалы отсутствия записи и правила заполнения.",
                )
            )

        longest_flat = _longest_flat_run(values)
        if longest_flat >= flat_run_min_length:
            flat_ratio = float(longest_flat / sample_count) if sample_count else 0.0
            flags.append(
                CurveQualityFlag(
                    curve_name=curve,
                    flag_type="flat",
                    severity="warning" if longest_flat >= flat_run_min_length * 2 else "review",
                    message=f"Найден плоский участок длиной {longest_flat} последовательных точек.",
                    sample_count=sample_count,
                    affected_count=longest_flat,
                    affected_ratio=flat_ratio,
                    group=group,
                    category=category,
                    unit=unit,
                    recommendation="Сравните с соседними кривыми: это может быть стабильный интервал, зависший датчик или заполнение NULL.",
                )
            )

        spikes = _spike_count(values, spike_zscore_threshold)
        if spikes > 0:
            spike_ratio = float(spikes / sample_count) if sample_count else 0.0
            flags.append(
                CurveQualityFlag(
                    curve_name=curve,
                    flag_type="spike",
                    severity="warning" if spikes > 1 else "review",
                    message=f"Найдено выбросов по robust z-score: {spikes}.",
                    sample_count=sample_count,
                    affected_count=spikes,
                    affected_ratio=spike_ratio,
                    group=group,
                    category=category,
                    unit=unit,
                    recommendation="Проверьте выбросы на графике по глубине перед сглаживанием или удалением.",
                )
            )

    summary: dict[str, int] = {key: 0 for key in QUALITY_FLAG_LABELS}
    for flag in flags:
        summary[flag.flag_type] = summary.get(flag.flag_type, 0) + 1
    summary["total"] = len(flags)
    summary["curves_checked"] = len(columns)
    diagnostics.append(f"Найдено quality flags: {len(flags)}.")

    updated_references = dict(references or {})
    updated_references["curve_quality_flags"] = [flag.__dict__ for flag in flags]
    updated_references["curve_quality_summary"] = dict(summary)
    return CurveQualityResult(tuple(flags), tuple(diagnostics), summary, updated_references)


def curve_quality_flag_rows(flags: Iterable[CurveQualityFlag]) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for flag in flags:
        rows.append(
            {
                "curve_name": flag.curve_name,
                "flag_type": flag.flag_type,
                "flag_label": QUALITY_FLAG_LABELS.get(flag.flag_type, flag.flag_type),
                "severity": flag.severity,
                "severity_label": QUALITY_SEVERITY_LABELS.get(flag.severity, flag.severity),
                "message": flag.message,
                "sample_count": str(flag.sample_count),
                "affected_count": str(flag.affected_count),
                "affected_ratio": f"{flag.affected_ratio:.3f}",
                "group": flag.group,
                "category": flag.category,
                "unit": flag.unit,
                "recommendation": flag.recommendation,
            }
        )
    return tuple(rows)


def curve_quality_summary_rows(summary: dict[str, int]) -> tuple[dict[str, str], ...]:
    rows = [
        {
            "flag_type": key,
            "flag_label": QUALITY_FLAG_LABELS.get(key, key),
            "flag_count": str(summary.get(key, 0)),
        }
        for key in QUALITY_FLAG_LABELS
    ]
    rows.append({"flag_type": "total", "flag_label": "Total", "flag_count": str(summary.get("total", 0))})
    return tuple(rows)

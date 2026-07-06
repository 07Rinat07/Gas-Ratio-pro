from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd

from las_editor.curve_alias import suggest_curve_aliases
from las_editor.curve_categories import suggest_curve_category
from las_editor.curve_grouping import suggest_curve_group
from las_editor.curve_rename import normalize_curve_name
from las_editor.curve_units import suggest_curve_unit

DUPLICATE_SEVERITY_LABELS: dict[str, str] = {
    "exact": "Exact duplicate",
    "high": "High similarity",
    "medium": "Possible duplicate",
    "name": "Name/alias duplicate",
}

DEFAULT_CORRELATION_THRESHOLD = 0.995
DEFAULT_VALUE_MATCH_THRESHOLD = 0.999


@dataclass(frozen=True)
class CurveDuplicateCandidate:
    primary_curve: str
    duplicate_curve: str
    severity: str
    reason: str
    correlation: float | None = None
    value_match_ratio: float | None = None
    shared_non_null: int = 0
    primary_alias: str = ""
    duplicate_alias: str = ""
    group: str = "other"
    category: str = "uncategorized"
    unit: str = "unknown"
    recommendation: str = "Review before merge or removal."


@dataclass(frozen=True)
class CurveDuplicateDetectionResult:
    candidates: tuple[CurveDuplicateCandidate, ...]
    diagnostics: tuple[str, ...]
    summary: dict[str, int]
    references: dict[str, Any]


def _curve_alias(curve_name: str, aliases: dict[str, str] | None) -> str:
    manual_alias = str(dict(aliases or {}).get(curve_name, "")).strip()
    if manual_alias:
        return manual_alias
    suggested = suggest_curve_aliases([curve_name]).get(curve_name, "")
    return str(suggested or "").strip()


def _canonical_curve_key(curve_name: str, alias: str = "") -> str:
    key = alias or curve_name
    return "".join(ch for ch in normalize_curve_name(key).upper() if ch.isalnum())


def _numeric_series(df: pd.DataFrame, curve_name: str) -> pd.Series:
    return pd.to_numeric(df[curve_name], errors="coerce")


def _shared_numeric(series_a: pd.Series, series_b: pd.Series) -> pd.DataFrame:
    values = pd.DataFrame({"a": series_a, "b": series_b}).dropna()
    return values


def _safe_correlation(values: pd.DataFrame) -> float | None:
    if len(values) < 2:
        return None
    if values["a"].nunique(dropna=True) <= 1 or values["b"].nunique(dropna=True) <= 1:
        return None
    corr = values["a"].corr(values["b"])
    if pd.isna(corr):
        return None
    return float(corr)


def _value_match_ratio(values: pd.DataFrame) -> float | None:
    if values.empty:
        return None
    matches = (values["a"] == values["b"]).sum()
    return float(matches / len(values))


def _severity_from_metrics(
    *,
    same_key: bool,
    correlation: float | None,
    value_match_ratio: float | None,
    correlation_threshold: float,
    value_match_threshold: float,
) -> tuple[str, str] | None:
    if value_match_ratio is not None and value_match_ratio >= value_match_threshold:
        return "exact", "numeric values match on shared samples"
    if correlation is not None and correlation >= correlation_threshold:
        return "high", "numeric curves have high correlation"
    if same_key:
        return "name", "curve mnemonic or alias resolves to the same canonical key"
    if correlation is not None and correlation >= 0.98:
        return "medium", "numeric curves are strongly correlated but below strict duplicate threshold"
    return None


def detect_curve_duplicates(
    df: pd.DataFrame,
    *,
    aliases: dict[str, str] | None = None,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None = None,
    correlation_threshold: float = DEFAULT_CORRELATION_THRESHOLD,
    value_match_threshold: float = DEFAULT_VALUE_MATCH_THRESHOLD,
    references: dict[str, Any] | None = None,
) -> CurveDuplicateDetectionResult:
    """Detect duplicate LAS curves without mutating the dataframe.

    The detector combines four safe signals: canonical mnemonic/alias equality,
    exact numeric match, high numeric correlation, and shared Curve Manager context.
    It only returns review candidates; it does not delete or merge curves.
    """

    columns = tuple(str(column) for column in df.columns)
    diagnostics: list[str] = [f"Проверено кривых: {len(columns)}."]
    candidates: list[CurveDuplicateCandidate] = []
    alias_map = {curve: _curve_alias(curve, aliases) for curve in columns}
    group_map = {str(curve): str(group) for curve, group in dict(group_overrides or {}).items()}
    category_map = {str(curve): str(category) for curve, category in dict(category_overrides or {}).items()}
    unit_map = {str(curve): str(unit) for curve, unit in dict(unit_overrides or {}).items()}

    numeric_columns = [curve for curve in columns if pd.api.types.is_numeric_dtype(pd.to_numeric(df[curve], errors="coerce"))]
    diagnostics.append(f"Числовых кривых для сравнения: {len(numeric_columns)}.")

    for left_index, primary in enumerate(columns):
        for duplicate in columns[left_index + 1 :]:
            primary_alias = alias_map.get(primary, "")
            duplicate_alias = alias_map.get(duplicate, "")
            same_key = _canonical_curve_key(primary, primary_alias) == _canonical_curve_key(duplicate, duplicate_alias)

            values = _shared_numeric(_numeric_series(df, primary), _numeric_series(df, duplicate))
            correlation = _safe_correlation(values)
            match_ratio = _value_match_ratio(values)
            severity = _severity_from_metrics(
                same_key=same_key,
                correlation=correlation,
                value_match_ratio=match_ratio,
                correlation_threshold=correlation_threshold,
                value_match_threshold=value_match_threshold,
            )
            if severity is None:
                continue

            group = group_map.get(primary) or group_map.get(duplicate) or suggest_curve_group(primary)
            category = category_map.get(primary) or category_map.get(duplicate) or suggest_curve_category(primary, group=group)
            unit = unit_map.get(primary) or unit_map.get(duplicate) or suggest_curve_unit(primary, group=group, category=category)
            severity_key, reason = severity
            if severity_key == "exact":
                recommendation = "Keep one curve after checking source and metadata; mark the other as duplicate."
            elif severity_key == "high":
                recommendation = "Review units and source; merge only after engineering validation."
            elif severity_key == "name":
                recommendation = "Rename or assign aliases to remove mnemonic ambiguity."
            else:
                recommendation = "Compare plots and metadata before merge/removal."

            candidates.append(
                CurveDuplicateCandidate(
                    primary_curve=primary,
                    duplicate_curve=duplicate,
                    severity=severity_key,
                    reason=reason,
                    correlation=correlation,
                    value_match_ratio=match_ratio,
                    shared_non_null=len(values),
                    primary_alias=primary_alias,
                    duplicate_alias=duplicate_alias,
                    group=group,
                    category=category,
                    unit=unit,
                    recommendation=recommendation,
                )
            )

    summary: dict[str, int] = {key: 0 for key in DUPLICATE_SEVERITY_LABELS}
    for candidate in candidates:
        summary[candidate.severity] = summary.get(candidate.severity, 0) + 1
    summary["total"] = len(candidates)
    diagnostics.append(f"Найдено кандидатов-дубликатов: {len(candidates)}.")

    updated_references = dict(references or {})
    updated_references["curve_duplicate_candidates"] = [candidate.__dict__ for candidate in candidates]
    updated_references["curve_duplicate_summary"] = dict(summary)
    return CurveDuplicateDetectionResult(tuple(candidates), tuple(diagnostics), summary, updated_references)


def curve_duplicate_table_rows(candidates: Iterable[CurveDuplicateCandidate]) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for candidate in candidates:
        rows.append(
            {
                "primary_curve": candidate.primary_curve,
                "duplicate_curve": candidate.duplicate_curve,
                "severity": candidate.severity,
                "severity_label": DUPLICATE_SEVERITY_LABELS.get(candidate.severity, candidate.severity),
                "reason": candidate.reason,
                "correlation": "" if candidate.correlation is None else f"{candidate.correlation:.6f}",
                "value_match_ratio": "" if candidate.value_match_ratio is None else f"{candidate.value_match_ratio:.3f}",
                "shared_non_null": str(candidate.shared_non_null),
                "primary_alias": candidate.primary_alias,
                "duplicate_alias": candidate.duplicate_alias,
                "group": candidate.group,
                "category": candidate.category,
                "unit": candidate.unit,
                "recommendation": candidate.recommendation,
            }
        )
    return tuple(rows)


def curve_duplicate_summary_rows(summary: dict[str, int]) -> tuple[dict[str, str], ...]:
    rows = [
        {
            "severity": key,
            "severity_label": DUPLICATE_SEVERITY_LABELS.get(key, key),
            "candidate_count": str(summary.get(key, 0)),
        }
        for key in DUPLICATE_SEVERITY_LABELS
    ]
    rows.append({"severity": "total", "severity_label": "Total", "candidate_count": str(summary.get("total", 0))})
    return tuple(rows)

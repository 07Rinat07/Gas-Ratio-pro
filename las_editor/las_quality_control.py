from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence
import math

import pandas as pd

from las_editor.las_creator import DEFAULT_NULL_VALUE, normalize_las_mnemonic, normalize_las_unit


LAS_QUALITY_CONTROL_STORAGE_KEY = "las_quality_control"
LAS_QUALITY_CONTROL_SCHEMA = "gas-ratio-pro/las-quality-control/v1"
DEFAULT_DEPTH_MNEMONICS = ("DEPT", "DEPTH", "MD", "TVD")


@dataclass(frozen=True)
class LasQualityIssue:
    """One quality-control finding for LAS ASCII/curve data."""

    severity: str
    code: str
    message: str
    curve: str = ""
    row: int | None = None
    depth: float | None = None
    value: float | None = None
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class CurveQualityProfile:
    """Optional engineering constraints for a curve."""

    mnemonic: str
    unit: str = ""
    min_value: float | None = None
    max_value: float | None = None
    allow_negative: bool = True
    expected_unit: str = ""
    spike_threshold: float | None = None
    flat_window: int = 5


@dataclass(frozen=True)
class LasQualityReport:
    """Complete quality-control report for a LAS working table."""

    schema: str
    generated_at: str
    row_count: int
    curve_count: int
    depth_curve: str
    issues: tuple[LasQualityIssue, ...]
    summary: Mapping[str, Any]


_BUILTIN_PROFILES: dict[str, CurveQualityProfile] = {
    "GR": CurveQualityProfile("GR", unit="API", min_value=0.0, max_value=300.0, allow_negative=False, expected_unit="API", spike_threshold=80.0),
    "CALI": CurveQualityProfile("CALI", unit="IN", min_value=0.0, max_value=40.0, allow_negative=False, expected_unit="IN", spike_threshold=5.0),
    "RHOB": CurveQualityProfile("RHOB", unit="G/C3", min_value=1.0, max_value=3.5, allow_negative=False, spike_threshold=0.35),
    "NPHI": CurveQualityProfile("NPHI", unit="V/V", min_value=-0.15, max_value=1.0, allow_negative=True, spike_threshold=0.25),
    "POR": CurveQualityProfile("POR", unit="V/V", min_value=0.0, max_value=1.0, allow_negative=False, expected_unit="V/V", spike_threshold=0.20),
    "SW": CurveQualityProfile("SW", unit="V/V", min_value=0.0, max_value=1.0, allow_negative=False, expected_unit="V/V", spike_threshold=0.30),
    "SO": CurveQualityProfile("SO", unit="V/V", min_value=0.0, max_value=1.0, allow_negative=False, expected_unit="V/V", spike_threshold=0.30),
    "SG": CurveQualityProfile("SG", unit="V/V", min_value=0.0, max_value=1.0, allow_negative=False, expected_unit="V/V", spike_threshold=0.30),
    "PERM": CurveQualityProfile("PERM", unit="MD", min_value=0.0, max_value=None, allow_negative=False, expected_unit="MD"),
    "RT": CurveQualityProfile("RT", unit="OHMM", min_value=0.0, max_value=None, allow_negative=False, spike_threshold=None),
    "C1": CurveQualityProfile("C1", unit="PPM", min_value=0.0, max_value=None, allow_negative=False, expected_unit="PPM"),
    "C2": CurveQualityProfile("C2", unit="PPM", min_value=0.0, max_value=None, allow_negative=False, expected_unit="PPM"),
    "C3": CurveQualityProfile("C3", unit="PPM", min_value=0.0, max_value=None, allow_negative=False, expected_unit="PPM"),
    "C4": CurveQualityProfile("C4", unit="PPM", min_value=0.0, max_value=None, allow_negative=False, expected_unit="PPM"),
    "C5": CurveQualityProfile("C5", unit="PPM", min_value=0.0, max_value=None, allow_negative=False, expected_unit="PPM"),
}


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _is_null_like(series: pd.Series, *, null_value: float) -> pd.Series:
    numeric = _numeric(series)
    return numeric.isna() | numeric.eq(null_value)


def _depth_curve_name(df: pd.DataFrame, depth_curve: str | None = None) -> str:
    if depth_curve:
        normalized = normalize_las_mnemonic(depth_curve)
        for column in df.columns:
            if normalize_las_mnemonic(str(column)) == normalized:
                return str(column)
    for candidate in DEFAULT_DEPTH_MNEMONICS:
        for column in df.columns:
            if normalize_las_mnemonic(str(column)) == candidate:
                return str(column)
    return str(df.columns[0]) if len(df.columns) else ""


def builtin_quality_profiles() -> tuple[CurveQualityProfile, ...]:
    """Return built-in QC profiles for common LAS curves."""

    return tuple(_BUILTIN_PROFILES[key] for key in sorted(_BUILTIN_PROFILES))


def get_quality_profile(mnemonic: str) -> CurveQualityProfile | None:
    return _BUILTIN_PROFILES.get(normalize_las_mnemonic(mnemonic))


def merge_quality_profiles(profiles: Iterable[CurveQualityProfile] | None = None) -> dict[str, CurveQualityProfile]:
    merged = dict(_BUILTIN_PROFILES)
    for profile in profiles or ():
        merged[normalize_las_mnemonic(profile.mnemonic)] = profile
    return merged


def detect_depth_quality_issues(
    df: pd.DataFrame,
    *,
    depth_curve: str | None = None,
    expected_step: float | None = None,
    step_tolerance: float = 1e-6,
    null_value: float = DEFAULT_NULL_VALUE,
) -> tuple[LasQualityIssue, ...]:
    """Check depth index for duplicates, monotonicity and missing intervals."""

    issues: list[LasQualityIssue] = []
    depth_name = _depth_curve_name(df, depth_curve)
    if not depth_name:
        return (LasQualityIssue("error", "missing_depth_curve", "Depth curve is missing."),)

    depth = _numeric(df[depth_name])
    null_mask = depth.isna() | depth.eq(null_value)
    for row in depth[null_mask].index.tolist():
        issues.append(LasQualityIssue("error", "null_depth", "Depth value is missing or equals LAS null value.", depth_name, int(row) if isinstance(row, int) else None))

    clean = depth[~null_mask]
    if clean.empty:
        issues.append(LasQualityIssue("error", "empty_depth", "Depth curve contains no valid numeric values.", depth_name))
        return tuple(issues)

    duplicates = clean[clean.duplicated(keep=False)]
    for row, value in duplicates.items():
        issues.append(LasQualityIssue("error", "duplicate_depth", "Duplicate depth sample detected.", depth_name, int(row) if isinstance(row, int) else None, float(value), float(value)))

    diffs = clean.diff().dropna()
    if not diffs.empty:
        direction = 1 if diffs.median() >= 0 else -1
        non_monotonic = diffs[diffs * direction <= 0]
        for row, value in non_monotonic.items():
            issues.append(
                LasQualityIssue(
                    "error",
                    "non_monotonic_depth",
                    "Depth curve is not strictly monotonic.",
                    depth_name,
                    int(row) if isinstance(row, int) else None,
                    float(clean.loc[row]),
                    float(value),
                )
            )

        step = abs(float(expected_step)) if expected_step not in (None, 0) else abs(float(diffs.median()))
        if step > 0:
            expected_signed = step * direction
            bad_steps = diffs[(diffs - expected_signed).abs() > max(step_tolerance, step * 1e-6)]
            for row, actual_step in bad_steps.items():
                code = "missing_depth_interval" if abs(float(actual_step)) > step else "irregular_depth_step"
                issues.append(
                    LasQualityIssue(
                        "warning",
                        code,
                        f"Unexpected depth step: {float(actual_step):g}; expected approximately {expected_signed:g}.",
                        depth_name,
                        int(row) if isinstance(row, int) else None,
                        float(clean.loc[row]),
                        float(actual_step),
                        {"expected_step": expected_signed},
                    )
                )

    return tuple(issues)


def detect_null_issues(df: pd.DataFrame, *, null_value: float = DEFAULT_NULL_VALUE, max_null_fraction: float = 0.25) -> tuple[LasQualityIssue, ...]:
    issues: list[LasQualityIssue] = []
    for column in df.columns:
        mask = _is_null_like(df[column], null_value=null_value)
        count = int(mask.sum())
        if count == 0:
            continue
        fraction = count / max(len(df), 1)
        severity = "warning" if fraction <= max_null_fraction else "error"
        issues.append(
            LasQualityIssue(
                severity,
                "missing_values",
                f"Curve contains {count} missing/null values ({fraction:.1%}).",
                str(column),
                details={"null_count": count, "null_fraction": fraction},
            )
        )
    return tuple(issues)


def detect_range_issues(
    df: pd.DataFrame,
    *,
    profiles: Iterable[CurveQualityProfile] | None = None,
    null_value: float = DEFAULT_NULL_VALUE,
) -> tuple[LasQualityIssue, ...]:
    issues: list[LasQualityIssue] = []
    profile_map = merge_quality_profiles(profiles)
    for column in df.columns:
        normalized = normalize_las_mnemonic(str(column))
        profile = profile_map.get(normalized)
        if profile is None:
            continue
        values = _numeric(df[column])
        valid = values[~_is_null_like(values, null_value=null_value)]
        if not profile.allow_negative:
            for row, value in valid[valid < 0].items():
                issues.append(LasQualityIssue("error", "negative_value", "Negative value is not allowed for this curve.", str(column), int(row) if isinstance(row, int) else None, None, float(value)))
        if profile.min_value is not None:
            for row, value in valid[valid < profile.min_value].items():
                issues.append(LasQualityIssue("warning", "below_expected_range", f"Value is below expected minimum {profile.min_value:g}.", str(column), int(row) if isinstance(row, int) else None, None, float(value)))
        if profile.max_value is not None:
            for row, value in valid[valid > profile.max_value].items():
                issues.append(LasQualityIssue("warning", "above_expected_range", f"Value is above expected maximum {profile.max_value:g}.", str(column), int(row) if isinstance(row, int) else None, None, float(value)))
    return tuple(issues)


def detect_outliers(
    df: pd.DataFrame,
    *,
    curves: Sequence[str] | None = None,
    z_threshold: float = 4.0,
    null_value: float = DEFAULT_NULL_VALUE,
) -> tuple[LasQualityIssue, ...]:
    issues: list[LasQualityIssue] = []
    requested = {normalize_las_mnemonic(curve) for curve in curves} if curves else None
    for column in df.columns:
        normalized = normalize_las_mnemonic(str(column))
        if normalized in DEFAULT_DEPTH_MNEMONICS or (requested is not None and normalized not in requested):
            continue
        values = _numeric(df[column])
        valid = values[~_is_null_like(values, null_value=null_value)]
        if len(valid) < 4:
            continue
        mean = float(valid.mean())
        std = float(valid.std(ddof=0))
        if std <= 0 or math.isnan(std):
            continue
        z_scores = (valid - mean).abs() / std
        for row, z_value in z_scores[z_scores > z_threshold].items():
            issues.append(
                LasQualityIssue(
                    "warning",
                    "statistical_outlier",
                    f"Statistical outlier detected (z={float(z_value):.2f}).",
                    str(column),
                    int(row) if isinstance(row, int) else None,
                    None,
                    float(values.loc[row]),
                    {"z_score": float(z_value), "threshold": z_threshold},
                )
            )
    return tuple(issues)


def detect_spikes(
    df: pd.DataFrame,
    *,
    profiles: Iterable[CurveQualityProfile] | None = None,
    curves: Sequence[str] | None = None,
    default_threshold: float | None = None,
    null_value: float = DEFAULT_NULL_VALUE,
) -> tuple[LasQualityIssue, ...]:
    issues: list[LasQualityIssue] = []
    profile_map = merge_quality_profiles(profiles)
    requested = {normalize_las_mnemonic(curve) for curve in curves} if curves else None
    for column in df.columns:
        normalized = normalize_las_mnemonic(str(column))
        if normalized in DEFAULT_DEPTH_MNEMONICS or (requested is not None and normalized not in requested):
            continue
        profile = profile_map.get(normalized)
        threshold = profile.spike_threshold if profile and profile.spike_threshold is not None else default_threshold
        values = _numeric(df[column]).mask(_is_null_like(df[column], null_value=null_value))
        if threshold is None:
            diffs = values.diff().abs().dropna()
            threshold = float(diffs.quantile(0.95) * 3) if len(diffs) >= 5 else None
        if not threshold or threshold <= 0:
            continue
        jumps = values.diff().abs()
        for row, jump in jumps[jumps > threshold].items():
            issues.append(
                LasQualityIssue(
                    "warning",
                    "curve_spike",
                    f"Abrupt curve change detected: {float(jump):g} > threshold {float(threshold):g}.",
                    str(column),
                    int(row) if isinstance(row, int) else None,
                    None,
                    float(values.loc[row]) if pd.notna(values.loc[row]) else None,
                    {"jump": float(jump), "threshold": float(threshold)},
                )
            )
    return tuple(issues)


def detect_flat_lines(
    df: pd.DataFrame,
    *,
    profiles: Iterable[CurveQualityProfile] | None = None,
    curves: Sequence[str] | None = None,
    default_window: int = 5,
    null_value: float = DEFAULT_NULL_VALUE,
) -> tuple[LasQualityIssue, ...]:
    issues: list[LasQualityIssue] = []
    profile_map = merge_quality_profiles(profiles)
    requested = {normalize_las_mnemonic(curve) for curve in curves} if curves else None
    for column in df.columns:
        normalized = normalize_las_mnemonic(str(column))
        if normalized in DEFAULT_DEPTH_MNEMONICS or (requested is not None and normalized not in requested):
            continue
        profile = profile_map.get(normalized)
        window = max(2, int(profile.flat_window if profile else default_window))
        values = _numeric(df[column]).mask(_is_null_like(df[column], null_value=null_value))
        run_start: int | None = None
        last_value: float | None = None
        run_length = 0
        for pos, value in enumerate(values.tolist()):
            if pd.isna(value):
                run_start = None
                last_value = None
                run_length = 0
                continue
            current = float(value)
            if last_value is not None and current == last_value:
                run_length += 1
            else:
                run_start = pos
                run_length = 1
                last_value = current
            if run_length == window:
                issues.append(
                    LasQualityIssue(
                        "warning",
                        "flat_line",
                        f"Flat-line segment detected for at least {window} consecutive samples.",
                        str(column),
                        run_start,
                        None,
                        current,
                        {"window": window},
                    )
                )
    return tuple(issues)


def detect_unit_mismatch(
    df: pd.DataFrame,
    *,
    profiles: Iterable[CurveQualityProfile] | None = None,
    units: Mapping[str, str] | None = None,
) -> tuple[LasQualityIssue, ...]:
    issues: list[LasQualityIssue] = []
    profile_map = merge_quality_profiles(profiles)
    unit_map = {normalize_las_mnemonic(key): normalize_las_unit(value) for key, value in (units or df.attrs.get("las_units", {}) or {}).items()}
    for column in df.columns:
        normalized = normalize_las_mnemonic(str(column))
        profile = profile_map.get(normalized)
        if profile is None or not profile.expected_unit:
            continue
        actual = unit_map.get(normalized, "")
        expected = normalize_las_unit(profile.expected_unit)
        if actual and expected and actual != expected:
            issues.append(
                LasQualityIssue(
                    "warning",
                    "unit_mismatch",
                    f"Unexpected unit {actual!r}; expected {expected!r}.",
                    str(column),
                    details={"actual_unit": actual, "expected_unit": expected},
                )
            )
    return tuple(issues)


def run_las_quality_control(
    df: pd.DataFrame,
    *,
    depth_curve: str | None = None,
    expected_step: float | None = None,
    null_value: float = DEFAULT_NULL_VALUE,
    profiles: Iterable[CurveQualityProfile] | None = None,
    units: Mapping[str, str] | None = None,
) -> LasQualityReport:
    """Run the complete LAS quality-control foundation checks."""

    issues: list[LasQualityIssue] = []
    issues.extend(detect_depth_quality_issues(df, depth_curve=depth_curve, expected_step=expected_step, null_value=null_value))
    issues.extend(detect_null_issues(df, null_value=null_value))
    issues.extend(detect_range_issues(df, profiles=profiles, null_value=null_value))
    issues.extend(detect_outliers(df, null_value=null_value))
    issues.extend(detect_spikes(df, profiles=profiles, null_value=null_value))
    issues.extend(detect_flat_lines(df, profiles=profiles, null_value=null_value))
    issues.extend(detect_unit_mismatch(df, profiles=profiles, units=units))

    by_severity: dict[str, int] = {}
    by_code: dict[str, int] = {}
    for issue in issues:
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
        by_code[issue.code] = by_code.get(issue.code, 0) + 1

    summary = {
        "issue_count": len(issues),
        "error_count": by_severity.get("error", 0),
        "warning_count": by_severity.get("warning", 0),
        "by_severity": by_severity,
        "by_code": by_code,
        "status": "failed" if by_severity.get("error", 0) else ("warning" if by_severity.get("warning", 0) else "passed"),
    }
    return LasQualityReport(
        schema=LAS_QUALITY_CONTROL_SCHEMA,
        generated_at=_timestamp_utc(),
        row_count=int(len(df)),
        curve_count=int(len(df.columns)),
        depth_curve=_depth_curve_name(df, depth_curve),
        issues=tuple(issues),
        summary=summary,
    )


def quality_issue_table_rows(issues: Iterable[LasQualityIssue]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "severity": issue.severity,
            "code": issue.code,
            "curve": issue.curve,
            "row": issue.row,
            "depth": issue.depth,
            "value": issue.value,
            "message": issue.message,
        }
        for issue in issues
    )


def quality_profile_table_rows(profiles: Iterable[CurveQualityProfile] | None = None) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "mnemonic": profile.mnemonic,
            "unit": profile.unit,
            "expected_unit": profile.expected_unit,
            "min_value": profile.min_value,
            "max_value": profile.max_value,
            "allow_negative": profile.allow_negative,
            "spike_threshold": profile.spike_threshold,
            "flat_window": profile.flat_window,
        }
        for profile in (tuple(profiles) if profiles is not None else builtin_quality_profiles())
    )


def build_quality_control_manifest(report: LasQualityReport) -> dict[str, Any]:
    return {
        "schema": report.schema,
        "generated_at": report.generated_at,
        "storage_key": LAS_QUALITY_CONTROL_STORAGE_KEY,
        "row_count": report.row_count,
        "curve_count": report.curve_count,
        "depth_curve": report.depth_curve,
        "summary": dict(report.summary),
        "issues": list(quality_issue_table_rows(report.issues)),
    }


def render_quality_control_report(report: LasQualityReport) -> str:
    lines = [
        "# LAS Quality Control Report",
        "",
        f"Schema: `{report.schema}`",
        f"Generated at: `{report.generated_at}`",
        f"Rows: **{report.row_count}**",
        f"Curves: **{report.curve_count}**",
        f"Depth curve: `{report.depth_curve}`",
        f"Status: **{report.summary.get('status', 'unknown')}**",
        "",
        "## Summary",
        "",
        f"- Errors: {report.summary.get('error_count', 0)}",
        f"- Warnings: {report.summary.get('warning_count', 0)}",
        f"- Total issues: {report.summary.get('issue_count', 0)}",
        "",
        "## Issues",
        "",
    ]
    if not report.issues:
        lines.append("No quality-control issues detected.")
    else:
        for issue in report.issues:
            location = []
            if issue.curve:
                location.append(f"curve `{issue.curve}`")
            if issue.row is not None:
                location.append(f"row {issue.row}")
            if issue.depth is not None:
                location.append(f"depth {issue.depth:g}")
            where = ", ".join(location) or "dataset"
            lines.append(f"- **{issue.severity.upper()}** `{issue.code}` at {where}: {issue.message}")
    return "\n".join(lines) + "\n"

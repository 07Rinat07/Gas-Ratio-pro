from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from las_editor.las_creator import DEFAULT_NULL_VALUE, normalize_las_mnemonic


MUD_GAS_INTERPRETATION_STORAGE_KEY = "mud_gas_interpretation"
MUD_GAS_INTERPRETATION_SCHEMA = "gas-ratio-pro/mud-gas-interpretation/v1"


@dataclass(frozen=True)
class MudGasIssue:
    """One validation or interpretation issue produced by the mud gas toolkit."""

    severity: str
    code: str
    message: str
    curve_name: str = ""
    depth: float | None = None


@dataclass(frozen=True)
class MudGasRatioSet:
    """Calculated gas-ratio curves for one depth sample."""

    depth: float
    wetness: float | None = None
    balance: float | None = None
    character: float | None = None
    pixler_c1_c2: float | None = None
    oil_indicator: float | None = None
    inverse_oil_indicator: float | None = None


@dataclass(frozen=True)
class MudGasInterpretationRow:
    """Interpreted mud-gas fluid character for one depth sample."""

    depth: float
    fluid_character: str
    confidence: str
    primary_method: str
    wetness: float | None = None
    balance: float | None = None
    character: float | None = None
    pixler_c1_c2: float | None = None
    oil_indicator: float | None = None
    inverse_oil_indicator: float | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MudGasIntervalSummary:
    """Aggregated interpretation for a depth interval."""

    top: float
    base: float
    sample_count: int
    dominant_fluid_character: str
    confidence: str
    average_wetness: float | None = None
    average_balance: float | None = None
    average_character: float | None = None
    average_pixler_c1_c2: float | None = None
    average_oil_indicator: float | None = None
    average_inverse_oil_indicator: float | None = None


@dataclass(frozen=True)
class MudGasInterpretationResult:
    """Full mud gas interpretation result for UI, reports and audit manifests."""

    rows: tuple[MudGasInterpretationRow, ...]
    intervals: tuple[MudGasIntervalSummary, ...]
    issues: tuple[MudGasIssue, ...] = ()
    diagnostics: tuple[str, ...] = ()
    source_columns: Mapping[str, str] | None = None


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _column_lookup(df: pd.DataFrame) -> dict[str, str]:
    return {normalize_las_mnemonic(str(column)): str(column) for column in df.columns}


def _find_column(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    lookup = _column_lookup(df)
    for candidate in candidates:
        key = normalize_las_mnemonic(candidate)
        if key in lookup:
            return lookup[key]
    return None


def _to_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric) or numeric == float(DEFAULT_NULL_VALUE):
        return None
    return numeric


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _round_optional(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(float(value), digits)


def build_mud_gas_source_columns(
    df: pd.DataFrame,
    *,
    depth_curve: str = "DEPT",
    c1_curve: str = "C1",
    c2_curve: str = "C2",
    c3_curve: str = "C3",
    c4_curve: str = "C4",
    c5_curve: str = "C5",
) -> tuple[dict[str, str], tuple[MudGasIssue, ...]]:
    """Resolve mud-gas source curves from a LAS-like DataFrame.

    The function accepts common mnemonic aliases and returns the actual DataFrame
    column names. It does not mutate the input table and reports missing curves as
    deterministic issues suitable for a Streamlit UI table.
    """

    requests = {
        "depth": (depth_curve, "DEPTH", "MD", "TVD"),
        "c1": (c1_curve, "METHANE", "C1"),
        "c2": (c2_curve, "ETHANE", "C2"),
        "c3": (c3_curve, "PROPANE", "C3"),
        "c4": (c4_curve, "BUTANE", "C4"),
        "c5": (c5_curve, "PENTANE", "C5"),
    }

    resolved: dict[str, str] = {}
    issues: list[MudGasIssue] = []
    for logical_name, candidates in requests.items():
        column = _find_column(df, candidates)
        if column:
            resolved[logical_name] = column
        else:
            issues.append(
                MudGasIssue(
                    severity="error",
                    code="missing_curve",
                    message=f"Required mud-gas curve is missing: {logical_name.upper()}.",
                    curve_name=logical_name.upper(),
                )
            )
    return resolved, tuple(issues)


def calculate_mud_gas_ratios(df: pd.DataFrame, source_columns: Mapping[str, str]) -> tuple[tuple[MudGasRatioSet, ...], tuple[MudGasIssue, ...]]:
    """Calculate Haworth, Pixler and oil-indicator ratios for each depth sample."""

    required = {"depth", "c1", "c2", "c3", "c4", "c5"}
    missing = sorted(required.difference(source_columns))
    if missing:
        return (), tuple(
            MudGasIssue("error", "missing_source_mapping", f"Missing source mapping: {name}.", name.upper())
            for name in missing
        )

    rows: list[MudGasRatioSet] = []
    issues: list[MudGasIssue] = []
    for index, record in df.iterrows():
        depth = _to_float(record[source_columns["depth"]])
        c1 = _to_float(record[source_columns["c1"]])
        c2 = _to_float(record[source_columns["c2"]])
        c3 = _to_float(record[source_columns["c3"]])
        c4 = _to_float(record[source_columns["c4"]])
        c5 = _to_float(record[source_columns["c5"]])

        if depth is None:
            issues.append(MudGasIssue("warning", "invalid_depth", f"Row {index} has invalid depth."))
            continue

        components = (c1, c2, c3, c4, c5)
        if all(value is None for value in components):
            issues.append(MudGasIssue("warning", "empty_gas_sample", "Gas sample has no C1-C5 values.", depth=depth))
            continue

        c1v = c1 or 0.0
        c2v = c2 or 0.0
        c3v = c3 or 0.0
        c4v = c4 or 0.0
        c5v = c5 or 0.0
        total = c1v + c2v + c3v + c4v + c5v
        wet_components = c2v + c3v + c4v + c5v
        heavy_components = c3v + c4v + c5v

        rows.append(
            MudGasRatioSet(
                depth=depth,
                wetness=_round_optional(_safe_divide(wet_components * 100.0, total)),
                balance=_round_optional(_safe_divide(c1v + c2v, heavy_components)),
                character=_round_optional(_safe_divide(c4v + c5v, c3v)),
                pixler_c1_c2=_round_optional(_safe_divide(c1v, c2v)),
                oil_indicator=_round_optional(_safe_divide(heavy_components, c1v)),
                inverse_oil_indicator=_round_optional(_safe_divide(c1v, heavy_components)),
            )
        )
    return tuple(rows), tuple(issues)


def classify_haworth(wetness: float | None, balance: float | None, character: float | None) -> tuple[str, tuple[str, ...]]:
    """Classify fluid character using Haworth wetness/balance/character logic."""

    notes: list[str] = []
    if wetness is None and balance is None and character is None:
        return "Недостаточно данных", ("Haworth ratios are unavailable.",)

    if wetness is not None and wetness > 40:
        return "Очень тяжелая нефть или остаточная нефть", ("Wetness > 40.",)

    if balance is not None and balance > 100:
        return "Очень легкий сухой газ", ("Balance > 100.",)

    if wetness is not None and balance is not None:
        if wetness < 0.5 and balance < 100:
            return "Легкий сухой газ", ("Wetness < 0.5 and Balance < 100.",)
        if 0.5 <= wetness <= 17.5:
            if balance > wetness:
                return "Газ с увеличением влажности", ("0.5 <= Wetness <= 17.5 and Balance > Wetness.",)
            if balance < wetness:
                fluid = "Очень влажный газ, конденсат или высокогазированная нефть"
                notes.append("Balance < Wetness in 0.5-17.5 wetness range.")
                if character is not None and character > 0.5:
                    fluid = "Газ, ассоциированный с нефтью"
                    notes.append("Character > 0.5 indicates oil association.")
                return fluid, tuple(notes)
        if 17.5 < wetness <= 40:
            if balance < wetness:
                return "Нефть", ("17.5 < Wetness <= 40 and Balance < Wetness.",)
            return "Нефть / переходная зона", ("17.5 < Wetness <= 40.",)

    if character is not None:
        if character < 0.5:
            return "Газ подтвержден по Character Ratio", ("Character < 0.5.",)
        return "Газ ассоциирован с нефтью по Character Ratio", ("Character > 0.5.",)

    return "Неоднозначная интерпретация", ("Haworth ratios do not match a strict rule.",)


def classify_pixler(c1_c2: float | None) -> tuple[str, tuple[str, ...]]:
    """Classify fluid character using the Pixler C1/C2 guideline."""

    if c1_c2 is None:
        return "Недостаточно данных", ("C1/C2 ratio is unavailable.",)
    if c1_c2 < 2:
        return "Непродуктивная остаточная нефть", ("C1/C2 < 2.",)
    if 2 <= c1_c2 < 4:
        return "Низкоплотная / тяжелая нефть API 10-15", ("2 <= C1/C2 < 4.",)
    if 4 <= c1_c2 < 8:
        return "Нефть средней плотности API 15-35", ("4 <= C1/C2 < 8.",)
    if 8 <= c1_c2 < 15:
        return "Легкая нефть API > 35", ("8 <= C1/C2 < 15.",)
    if 15 <= c1_c2 < 65:
        return "Газ / газоконденсат", ("15 <= C1/C2 < 65.",)
    return "Легкий газ, вероятно непродуктивный", ("C1/C2 >= 65.",)


def classify_oil_indicator(oil_indicator: float | None, inverse_oil_indicator: float | None = None) -> tuple[str, tuple[str, ...]]:
    """Classify fluid character using oil indicator or inverse oil indicator."""

    oi = oil_indicator
    if oi is None and inverse_oil_indicator not in (None, 0):
        oi = 1.0 / float(inverse_oil_indicator)  # Equivalent scale, calculated from inverse when direct ratio is absent.
    if oi is None:
        return "Недостаточно данных", ("Oil Indicator is unavailable.",)
    if 0.01 <= oi < 0.07:
        return "Сухой газ", ("0.01 <= OI < 0.07.",)
    if 0.07 <= oi < 0.10:
        return "Конденсат или легкая нефть с высоким GOR", ("0.07 <= OI < 0.10.",)
    if 0.10 <= oi < 0.40:
        return "Нефть", ("0.10 <= OI < 0.40.",)
    if 0.40 <= oi <= 1.0:
        return "Остаточная нефть", ("0.40 <= OI <= 1.0.",)
    return "Вне типового диапазона Oil Indicator", ("Oil Indicator is outside published guideline ranges.",)


def _confidence_from_votes(votes: Sequence[str]) -> str:
    useful = [vote for vote in votes if vote and vote != "Недостаточно данных"]
    if not useful:
        return "low"
    dominant_count = max(useful.count(vote) for vote in set(useful))
    if dominant_count >= 3:
        return "high"
    if dominant_count == 2:
        return "medium"
    return "low"


def _dominant_vote(votes: Sequence[str]) -> str:
    useful = [vote for vote in votes if vote and vote != "Недостаточно данных"]
    if not useful:
        return "Недостаточно данных"
    return sorted(set(useful), key=lambda vote: (-useful.count(vote), vote))[0]


def interpret_mud_gas_ratios(ratios: Iterable[MudGasRatioSet]) -> tuple[MudGasInterpretationRow, ...]:
    """Interpret a sequence of calculated gas ratios into fluid-character rows."""

    interpreted: list[MudGasInterpretationRow] = []
    for ratio in ratios:
        haworth, haworth_notes = classify_haworth(ratio.wetness, ratio.balance, ratio.character)
        pixler, pixler_notes = classify_pixler(ratio.pixler_c1_c2)
        oil_indicator, oil_indicator_notes = classify_oil_indicator(ratio.oil_indicator, ratio.inverse_oil_indicator)
        votes = (haworth, pixler, oil_indicator)
        dominant = _dominant_vote(votes)
        confidence = _confidence_from_votes(votes)
        interpreted.append(
            MudGasInterpretationRow(
                depth=ratio.depth,
                fluid_character=dominant,
                confidence=confidence,
                primary_method="combined_haworth_pixler_oil_indicator",
                wetness=ratio.wetness,
                balance=ratio.balance,
                character=ratio.character,
                pixler_c1_c2=ratio.pixler_c1_c2,
                oil_indicator=ratio.oil_indicator,
                inverse_oil_indicator=ratio.inverse_oil_indicator,
                notes=tuple(haworth_notes) + tuple(pixler_notes) + tuple(oil_indicator_notes),
            )
        )
    return tuple(interpreted)


def summarize_mud_gas_intervals(
    rows: Iterable[MudGasInterpretationRow],
    *,
    interval_size: float | None = None,
) -> tuple[MudGasIntervalSummary, ...]:
    """Aggregate interpreted rows by natural consecutive classes or fixed depth interval."""

    ordered = sorted(tuple(rows), key=lambda row: row.depth)
    if not ordered:
        return ()

    groups: list[list[MudGasInterpretationRow]] = []
    current: list[MudGasInterpretationRow] = [ordered[0]]
    for row in ordered[1:]:
        previous = current[-1]
        same_fixed_interval = False
        if interval_size and interval_size > 0:
            same_fixed_interval = int(row.depth // interval_size) == int(previous.depth // interval_size)
        same_character = row.fluid_character == previous.fluid_character and row.confidence == previous.confidence
        if same_fixed_interval or (not interval_size and same_character):
            current.append(row)
        else:
            groups.append(current)
            current = [row]
    groups.append(current)

    summaries: list[MudGasIntervalSummary] = []
    for group in groups:
        frame = pd.DataFrame([row.__dict__ for row in group])
        characters = [row.fluid_character for row in group]
        confidences = [row.confidence for row in group]
        summaries.append(
            MudGasIntervalSummary(
                top=min(row.depth for row in group),
                base=max(row.depth for row in group),
                sample_count=len(group),
                dominant_fluid_character=_dominant_vote(characters),
                confidence=_dominant_vote(confidences),
                average_wetness=_round_optional(frame["wetness"].mean(skipna=True)),
                average_balance=_round_optional(frame["balance"].mean(skipna=True)),
                average_character=_round_optional(frame["character"].mean(skipna=True)),
                average_pixler_c1_c2=_round_optional(frame["pixler_c1_c2"].mean(skipna=True)),
                average_oil_indicator=_round_optional(frame["oil_indicator"].mean(skipna=True)),
                average_inverse_oil_indicator=_round_optional(frame["inverse_oil_indicator"].mean(skipna=True)),
            )
        )
    return tuple(summaries)


def interpret_mud_gas_dataframe(
    df: pd.DataFrame,
    *,
    interval_size: float | None = None,
    source_columns: Mapping[str, str] | None = None,
) -> MudGasInterpretationResult:
    """Run the complete mud-gas interpretation workflow on a LAS-like table."""

    resolved = dict(source_columns or {})
    source_issues: tuple[MudGasIssue, ...] = ()
    if not resolved:
        resolved, source_issues = build_mud_gas_source_columns(df)
    if any(issue.severity == "error" for issue in source_issues):
        return MudGasInterpretationResult(rows=(), intervals=(), issues=source_issues, source_columns=resolved)

    ratios, ratio_issues = calculate_mud_gas_ratios(df, resolved)
    rows = interpret_mud_gas_ratios(ratios)
    intervals = summarize_mud_gas_intervals(rows, interval_size=interval_size)
    return MudGasInterpretationResult(
        rows=rows,
        intervals=intervals,
        issues=tuple(source_issues) + tuple(ratio_issues),
        diagnostics=(
            f"Интерпретировано точек: {len(rows)}.",
            f"Сформировано интервалов: {len(intervals)}.",
            "Расчет выполнен в памяти и не изменяет исходный LAS-файл.",
        ),
        source_columns=resolved,
    )


def mud_gas_interpretation_table_rows(rows: Iterable[MudGasInterpretationRow]) -> tuple[dict[str, Any], ...]:
    """Return UI-ready rows for Streamlit tables."""

    return tuple(
        {
            "depth": row.depth,
            "fluid_character": row.fluid_character,
            "confidence": row.confidence,
            "WH": row.wetness,
            "BH": row.balance,
            "CH": row.character,
            "C1/C2": row.pixler_c1_c2,
            "OI": row.oil_indicator,
            "IOI": row.inverse_oil_indicator,
            "notes": "; ".join(row.notes),
        }
        for row in rows
    )


def mud_gas_interval_table_rows(intervals: Iterable[MudGasIntervalSummary]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "top": interval.top,
            "base": interval.base,
            "sample_count": interval.sample_count,
            "dominant_fluid_character": interval.dominant_fluid_character,
            "confidence": interval.confidence,
            "avg_WH": interval.average_wetness,
            "avg_BH": interval.average_balance,
            "avg_CH": interval.average_character,
            "avg_C1/C2": interval.average_pixler_c1_c2,
            "avg_OI": interval.average_oil_indicator,
            "avg_IOI": interval.average_inverse_oil_indicator,
        }
        for interval in intervals
    )


def mud_gas_issue_table_rows(issues: Iterable[MudGasIssue]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "severity": issue.severity,
            "code": issue.code,
            "curve_name": issue.curve_name,
            "depth": issue.depth,
            "message": issue.message,
        }
        for issue in issues
    )


def build_mud_gas_interpretation_manifest(result: MudGasInterpretationResult) -> dict[str, Any]:
    return {
        "schema": MUD_GAS_INTERPRETATION_SCHEMA,
        "generated_at": _timestamp_utc(),
        "storage_key": MUD_GAS_INTERPRETATION_STORAGE_KEY,
        "source_columns": dict(result.source_columns or {}),
        "row_count": len(result.rows),
        "interval_count": len(result.intervals),
        "issue_count": len(result.issues),
        "issues": [issue.__dict__ for issue in result.issues],
        "intervals": [interval.__dict__ for interval in result.intervals],
    }


def render_mud_gas_markdown_report(result: MudGasInterpretationResult) -> str:
    """Render a compact engineer-readable Markdown report."""

    manifest = build_mud_gas_interpretation_manifest(result)
    lines = [
        "# Mud Gas Interpretation Report",
        "",
        f"Generated at: {manifest['generated_at']}",
        f"Interpreted samples: {manifest['row_count']}",
        f"Intervals: {manifest['interval_count']}",
        f"Issues: {manifest['issue_count']}",
        "",
        "## Source curves",
    ]
    for key, value in sorted(dict(result.source_columns or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Intervals", "", "| Top | Base | Samples | Dominant character | Confidence |", "| --- | --- | ---: | --- | --- |"])
    for interval in result.intervals:
        lines.append(
            f"| {interval.top} | {interval.base} | {interval.sample_count} | {interval.dominant_fluid_character} | {interval.confidence} |"
        )
    if result.issues:
        lines.extend(["", "## Issues", "", "| Severity | Code | Depth | Message |", "| --- | --- | --- | --- |"])
        for issue in result.issues:
            lines.append(f"| {issue.severity} | {issue.code} | {'' if issue.depth is None else issue.depth} | {issue.message} |")
    return "\n".join(lines).strip() + "\n"

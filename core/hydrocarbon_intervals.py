from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import pandas as pd


HYDROCARBON_INTERVAL_SCHEMA = "gas-ratio-pro/hydrocarbon-intervals/v1"

NON_PROSPECTIVE_LABELS = (
    "Недостаточно данных",
    "Сухой газ / непродуктивно",
    "Остаточная нефть / непродуктивно",
)


@dataclass(frozen=True)
class HydrocarbonIntervalRuleSet:
    """Configuration for depth-sample to hydrocarbon-interval grouping.

    The defaults are intentionally permissive. The engine is used as a reporting
    pipeline, so it should not silently drop weak but potentially interesting
    oil/gas indications. Final economic/productivity decisions remain outside
    this preliminary mud-gas interpretation layer.
    """

    max_depth_gap: float | None = None
    minimum_samples: int = 1
    include_low_confidence: bool = True
    merge_compatible_fluids: bool = True


@dataclass(frozen=True)
class HydrocarbonInterval:
    """Unified interval model for reports, charts and future PDF export."""

    top: float
    base: float
    sample_count: int
    fluid_type: str
    confidence: str
    interpretation: str
    average_wh: float | None = None
    average_bh: float | None = None
    average_ch: float | None = None
    average_bar2: float | None = None
    average_pixler_c1_c2: float | None = None
    average_pixler_c1_c3: float | None = None
    average_oil_indicator: float | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class HydrocarbonIntervalResult:
    """Complete hydrocarbon interval result shared by UI, graph and reports."""

    intervals: tuple[HydrocarbonInterval, ...]
    rows: pd.DataFrame
    diagnostics: tuple[str, ...] = ()
    schema: str = HYDROCARBON_INTERVAL_SCHEMA


def _to_float(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return numeric


def _round_optional(value: object, digits: int = 6) -> float | None:
    numeric = _to_float(value)
    return None if numeric is None else round(numeric, digits)


def _contains_any(text: str, needles: Sequence[str]) -> bool:
    low = text.lower()
    return any(needle.lower() in low for needle in needles)


def normalize_fluid_type(row: Mapping[str, object]) -> str:
    """Normalize mixed Russian/English classification labels to report classes."""

    label = str(row.get("interpretation") or row.get("fluid_character") or "").strip()
    pixler = _to_float(row.get("c1_c2", row.get("pixler_c1_c2")))
    oil_indicator = _to_float(row.get("oil_indicator"))
    wh = _to_float(row.get("wh", row.get("wetness")))
    bh = _to_float(row.get("bh", row.get("balance")))

    if not label and all(value is None for value in (pixler, oil_indicator, wh, bh)):
        return "insufficient"

    if _contains_any(label, ("недостат", "insufficient")):
        return "insufficient"
    if _contains_any(label, ("конденсат", "condensate")):
        return "condensate"
    if _contains_any(label, ("нефт", "oil")) and _contains_any(label, ("газ", "gas")):
        return "mixed"
    if _contains_any(label, ("нефт", "oil")):
        return "oil"
    if _contains_any(label, ("газ", "gas")):
        return "gas"

    # Ratio fallback. This keeps Pixler/OI signals available for reports even
    # when the row has no text interpretation yet.
    if oil_indicator is not None:
        if 0.10 <= oil_indicator < 0.40:
            return "oil"
        if 0.07 <= oil_indicator < 0.10:
            return "condensate"
        if 0.01 <= oil_indicator < 0.07:
            return "gas"
    if pixler is not None:
        if 2 <= pixler < 15:
            return "oil"
        if 15 <= pixler < 65:
            return "condensate"
        if pixler >= 65:
            return "gas"
    if wh is not None and bh is not None:
        if 17.5 <= wh < 40:
            return "oil"
        if 0.5 <= wh < 17.5 and bh > wh:
            return "gas"
        if 0.5 <= wh < 17.5 and bh <= wh:
            return "condensate"
    return "mixed"


def is_prospective_fluid(fluid_type: str, *, include_low_confidence: bool = True) -> bool:
    if fluid_type in {"oil", "gas", "condensate", "mixed"}:
        return True
    return bool(include_low_confidence and fluid_type == "transition")


def _fluid_group(fluid_type: str, *, merge_compatible_fluids: bool) -> str:
    if not merge_compatible_fluids:
        return fluid_type
    if fluid_type in {"oil", "gas", "condensate", "mixed"}:
        return "hydrocarbon"
    return fluid_type


def _dominant(values: Iterable[str], default: str = "mixed") -> str:
    useful = [str(value) for value in values if str(value).strip()]
    if not useful:
        return default
    return sorted(set(useful), key=lambda value: (-useful.count(value), value))[0]


def _confidence(values: Iterable[str]) -> str:
    useful = [value for value in values if value]
    if not useful:
        return "low"
    if "high" in useful:
        return "high"
    if "medium" in useful:
        return "medium"
    return "low"


def _mean(frame: pd.DataFrame, *columns: str) -> float | None:
    for column in columns:
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            if not values.empty:
                return _round_optional(values.mean())
    return None


def _evidence_for_group(frame: pd.DataFrame, fluid_type: str) -> tuple[str, ...]:
    evidence: list[str] = []
    wh = _mean(frame, "wh", "wetness")
    bh = _mean(frame, "bh", "balance")
    ch = _mean(frame, "ch", "character")
    c1_c2 = _mean(frame, "c1_c2", "pixler_c1_c2")
    oil_indicator = _mean(frame, "oil_indicator")

    if wh is not None or bh is not None:
        evidence.append(f"Haworth Wh/Bh: Wh={'' if wh is None else wh:g}, Bh={'' if bh is None else bh:g}.")
    if ch is not None:
        evidence.append(f"Character ratio CH={ch:g}.")
    if c1_c2 is not None:
        evidence.append(f"Pixler C1/C2={c1_c2:g}.")
    if oil_indicator is not None:
        evidence.append(f"Oil indicator={oil_indicator:g}.")
    if not evidence:
        evidence.append("Интервал выделен по текстовой классификации строк.")
    evidence.append(f"Итоговый тип интервала: {fluid_type}.")
    return tuple(evidence)


def _interval_from_group(group: Sequence[Mapping[str, object]]) -> HydrocarbonInterval:
    frame = pd.DataFrame(group)
    fluid_type = _dominant(frame["hydrocarbon_fluid_type"].astype(str), default="mixed")
    top = float(pd.to_numeric(frame["depth"], errors="coerce").min())
    base = float(pd.to_numeric(frame["depth"], errors="coerce").max())
    interpretation = _dominant(frame.get("interpretation", pd.Series(dtype=str)).astype(str), default=fluid_type)
    confidence_values = frame.get("confidence", pd.Series(dtype=str)).astype(str)

    return HydrocarbonInterval(
        top=top,
        base=base,
        sample_count=len(frame),
        fluid_type=fluid_type,
        confidence=_confidence(confidence_values),
        interpretation=interpretation,
        average_wh=_mean(frame, "wh", "wetness"),
        average_bh=_mean(frame, "bh", "balance"),
        average_ch=_mean(frame, "ch", "character"),
        average_bar2=_mean(frame, "bar2"),
        average_pixler_c1_c2=_mean(frame, "c1_c2", "pixler_c1_c2"),
        average_pixler_c1_c3=_mean(frame, "c1_c3"),
        average_oil_indicator=_mean(frame, "oil_indicator"),
        evidence=_evidence_for_group(frame, fluid_type),
    )


def detect_hydrocarbon_intervals(
    df: pd.DataFrame,
    *,
    depth_column: str = "depth",
    rules: HydrocarbonIntervalRuleSet | None = None,
) -> HydrocarbonIntervalResult:
    """Detect report-ready hydrocarbon intervals from calculated gas-ratio rows.

    The function expects calculated columns when available (`wh`, `bh`, `c1_c2`,
    `oil_indicator`) but also works with already interpreted rows. It enriches the
    returned rows with `hydrocarbon_fluid_type` and `hydrocarbon_candidate` so the
    same model can drive tables, marked charts and future PDF export.
    """

    rules = rules or HydrocarbonIntervalRuleSet()
    if df is None or df.empty:
        return HydrocarbonIntervalResult(intervals=(), rows=pd.DataFrame(), diagnostics=("Нет строк для поиска УВ-интервалов.",))

    if depth_column not in df.columns:
        return HydrocarbonIntervalResult(
            intervals=(),
            rows=df.copy(),
            diagnostics=(f"Колонка глубины не найдена: {depth_column}.",),
        )

    rows = df.copy()
    rows[depth_column] = pd.to_numeric(rows[depth_column], errors="coerce")
    rows = rows.dropna(subset=[depth_column]).sort_values(depth_column).reset_index(drop=True)
    if rows.empty:
        return HydrocarbonIntervalResult(intervals=(), rows=rows, diagnostics=("Нет числовых значений глубины.",))

    fluid_types = [normalize_fluid_type(row._asdict() if hasattr(row, "_asdict") else row) for _, row in rows.iterrows()]
    rows["hydrocarbon_fluid_type"] = fluid_types
    rows["hydrocarbon_candidate"] = [
        is_prospective_fluid(fluid_type, include_low_confidence=rules.include_low_confidence)
        for fluid_type in fluid_types
    ]

    groups: list[list[Mapping[str, object]]] = []
    current: list[Mapping[str, object]] = []
    previous_depth: float | None = None
    previous_group: str | None = None

    for record in rows.to_dict(orient="records"):
        if not record.get("hydrocarbon_candidate"):
            if current:
                groups.append(current)
                current = []
            previous_depth = None
            previous_group = None
            continue

        depth = float(record[depth_column])
        group_key = _fluid_group(str(record["hydrocarbon_fluid_type"]), merge_compatible_fluids=rules.merge_compatible_fluids)
        gap_ok = rules.max_depth_gap is None or previous_depth is None or abs(depth - previous_depth) <= rules.max_depth_gap
        group_ok = previous_group is None or group_key == previous_group
        if current and not (gap_ok and group_ok):
            groups.append(current)
            current = []
        current.append(record)
        previous_depth = depth
        previous_group = group_key

    if current:
        groups.append(current)

    intervals = tuple(
        _interval_from_group(group)
        for group in groups
        if len(group) >= max(1, int(rules.minimum_samples))
    )
    diagnostics = (
        f"Проверено строк: {len(rows)}.",
        f"Кандидатов УВ: {int(rows['hydrocarbon_candidate'].sum())}.",
        f"Сформировано УВ-интервалов: {len(intervals)}.",
    )
    return HydrocarbonIntervalResult(intervals=intervals, rows=rows, diagnostics=diagnostics)


def hydrocarbon_interval_table_rows(intervals: Iterable[HydrocarbonInterval]) -> tuple[dict[str, object], ...]:
    """Return UI/report-friendly serializable interval rows."""

    return tuple(
        {
            "top": interval.top,
            "base": interval.base,
            "samples": interval.sample_count,
            "fluid_type": interval.fluid_type,
            "confidence": interval.confidence,
            "interpretation": interval.interpretation,
            "avg_Wh": interval.average_wh,
            "avg_Bh": interval.average_bh,
            "avg_Ch": interval.average_ch,
            "avg_BAR2": interval.average_bar2,
            "avg_C1/C2": interval.average_pixler_c1_c2,
            "avg_C1/C3": interval.average_pixler_c1_c3,
            "avg_OI": interval.average_oil_indicator,
            "evidence": " ".join(interval.evidence),
        }
        for interval in intervals
    )


def hydrocarbon_interval_dataframe(intervals: Iterable[HydrocarbonInterval]) -> pd.DataFrame:
    """Convert interval model to DataFrame for HTML/PDF report tables."""

    return pd.DataFrame(hydrocarbon_interval_table_rows(intervals))

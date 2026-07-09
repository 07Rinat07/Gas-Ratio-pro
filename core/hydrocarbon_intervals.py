from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import pandas as pd


HYDROCARBON_INTERVAL_SCHEMA = "gas-ratio-pro/hydrocarbon-intervals/v6"

NON_PROSPECTIVE_LABELS = (
    "Недостаточно данных",
    "Сухой газ / непродуктивно",
    "Остаточная нефть / непродуктивно",
)

FLUID_TYPE_LABELS = {
    "gas": "Газовый интервал",
    "oil": "Нефтяной интервал",
    "gas_oil": "Газонефтяной интервал",
    "oil_gas": "Нефтегазовый интервал",
    "condensate": "Газоконденсатный интервал",
    "mixed": "Смешанный нефтегазовый интервал",
    "transition": "Переходный интервал",
    "water": "Водонасыщенный интервал",
    "uncertain": "Неопределенный интервал",
    "insufficient": "Недостаточно данных",
}

CONFIDENCE_LABELS = {
    "high": "высокая уверенность",
    "medium": "средняя уверенность",
    "low": "низкая уверенность",
}

MARKER_STYLE_BY_FLUID = {
    "gas": {"label": "GAS", "color": "#d62728", "fill": "rgba(214,39,40,0.18)"},
    "oil": {"label": "OIL", "color": "#2ca02c", "fill": "rgba(44,160,44,0.18)"},
    "gas_oil": {"label": "GAS→OIL", "color": "#8c564b", "fill": "rgba(140,86,75,0.18)"},
    "oil_gas": {"label": "OIL→GAS", "color": "#17becf", "fill": "rgba(23,190,207,0.18)"},
    "condensate": {"label": "COND", "color": "#ff7f0e", "fill": "rgba(255,127,14,0.18)"},
    "mixed": {"label": "GAS/OIL", "color": "#9467bd", "fill": "rgba(148,103,189,0.18)"},
    "transition": {"label": "CHECK", "color": "#7f7f7f", "fill": "rgba(127,127,127,0.14)"},
    "uncertain": {"label": "UNCERTAIN", "color": "#bcbd22", "fill": "rgba(188,189,34,0.16)"},
    "water": {"label": "WATER", "color": "#1f77b4", "fill": "rgba(31,119,180,0.12)"},
}


LITHOLOGY_CLASS_LABELS = {
    "clay": "Clay",
    "claystone": "Claystone",
    "shale": "Shale",
    "siltstone": "Siltstone",
    "sandstone": "Sandstone",
    "limestone": "Limestone",
    "dolomite": "Dolomite",
    "coal": "Coal",
    "tight": "Tight interval",
    "barrier": "Barrier",
    "unknown_barrier": "Unclassified barrier",
    "unknown": "Unknown",
}

BARRIER_LITHOLOGY_CLASSES = {"clay", "claystone", "shale", "tight", "barrier", "unknown_barrier"}


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
    preserve_explicit_gaps: bool = True
    barrier_lithology_labels: tuple[str, ...] = ("clay", "claystone", "shale", "tight", "barrier")


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
    engineering_note: str = ""
    warnings: tuple[str, ...] = ()
    source_start_row: int | None = None
    source_end_row: int | None = None
    separated_by_gap: bool = False

    @property
    def thickness(self) -> float:
        """Interval thickness in depth units used by the source dataset."""

        return round(abs(float(self.base) - float(self.top)), 6)


@dataclass(frozen=True)
class LithologyBarrier:
    """Non-productive lithological separator between interpreted intervals.

    The barrier is not a reservoir interval. It is stored separately so reports can
    show gas/oil intervals exactly as detected while still preserving claystone,
    shale or tight separators that may matter for geological interpretation.
    """

    top: float
    base: float
    lithology: str
    seal_quality: str = "possible"
    remarks: str = ""
    source_start_row: int | None = None
    source_end_row: int | None = None
    inferred: bool = False

    @property
    def thickness(self) -> float:
        """Barrier thickness in depth units used by the source dataset."""

        return round(abs(float(self.base) - float(self.top)), 6)


@dataclass(frozen=True)
class HydrocarbonIntervalResult:
    """Complete hydrocarbon interval result shared by UI, graph and reports."""

    intervals: tuple[HydrocarbonInterval, ...]
    rows: pd.DataFrame
    barriers: tuple[LithologyBarrier, ...] = ()
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


def _ordered_mixed_type(label: str) -> str:
    """Return directional gas/oil class when the label expresses both fluids."""

    low = label.lower()
    gas_positions = [pos for token in ("газ", "gas") if (pos := low.find(token)) >= 0]
    oil_positions = [pos for token in ("нефт", "oil") if (pos := low.find(token)) >= 0]
    if gas_positions and oil_positions:
        return "gas_oil" if min(gas_positions) < min(oil_positions) else "oil_gas"
    return "mixed"


def normalize_lithology(row: Mapping[str, object]) -> str:
    """Normalize common lithology labels to project terminology.

    The project uses `Claystone` for аргиллит / indurated clay-rich rock and
    `Clay` for unconsolidated глина. The returned value is a stable machine key;
    display labels are defined in `LITHOLOGY_CLASS_LABELS`.
    """

    text_parts = [
        str(row.get(column) or "")
        for column in ("lithology", "lithology_class", "rock_type", "facies", "formation", "barrier_type", "interpretation")
    ]
    text = " ".join(text_parts).lower()
    if not text.strip():
        return "unknown"
    # Russian and legacy English terms are accepted on input, but project output
    # must use Clay / Claystone / Shale terminology.
    if any(token in text for token in ("аргил", "argillite", "claystone")):
        return "claystone"
    if any(token in text for token in ("глина", "clay")) and "claystone" not in text:
        return "clay"
    if any(token in text for token in ("слан", "shale")):
        return "shale"
    if any(token in text for token in ("алев", "siltstone")):
        return "siltstone"
    if any(token in text for token in ("песч", "sandstone", "sand")):
        return "sandstone"
    if any(token in text for token in ("извест", "limestone")):
        return "limestone"
    if any(token in text for token in ("долом", "dolomite")):
        return "dolomite"
    if any(token in text for token in ("уголь", "coal")):
        return "coal"
    if any(token in text for token in ("плотн", "tight")):
        return "tight"
    if any(token in text for token in ("перемыч", "seal", "barrier")):
        return "barrier"
    return "unknown"


def _is_barrier_lithology(lithology: str, rules: HydrocarbonIntervalRuleSet) -> bool:
    labels = {label.lower() for label in rules.barrier_lithology_labels}
    return lithology in BARRIER_LITHOLOGY_CLASSES or lithology.lower() in labels

def _ratio_conflict_type(oil_indicator: float | None, pixler: float | None, wh: float | None, bh: float | None) -> str | None:
    """Detect mixed oil/gas indications when independent ratios disagree.

    The function deliberately returns a directional class only when there are
    competing oil and gas indicators. Pure oil/gas/condensate fallbacks remain in
    `normalize_fluid_type` so existing behaviour stays backward compatible.
    """

    oil_votes = 0
    gas_votes = 0
    if oil_indicator is not None:
        if 0.10 <= oil_indicator < 0.40:
            oil_votes += 1
        elif 0.01 <= oil_indicator < 0.07:
            gas_votes += 1
    if pixler is not None:
        if 2 <= pixler < 15:
            oil_votes += 1
        elif pixler >= 65:
            gas_votes += 1
    if wh is not None and bh is not None:
        if 17.5 <= wh < 40:
            oil_votes += 1
        elif 0.5 <= wh < 17.5 and bh > wh:
            gas_votes += 1
    if oil_votes and gas_votes:
        return "oil_gas" if oil_votes >= gas_votes else "gas_oil"
    return None


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
    if _contains_any(label, ("вода", "водона", "water", "aquifer")):
        return "water"
    if _contains_any(label, ("неопредел", "сомнит", "uncertain", "ambiguous")):
        return "uncertain"
    if _contains_any(label, ("переход", "transition", "границ", "boundary")):
        return "transition"
    if _contains_any(label, ("конденсат", "condensate")):
        return "condensate"
    if _contains_any(label, ("нефт", "oil")) and _contains_any(label, ("газ", "gas")):
        return _ordered_mixed_type(label)
    if _contains_any(label, ("нефт", "oil")):
        return "oil"
    if _contains_any(label, ("газ", "gas")):
        return "gas"

    # Ratio fallback. This keeps Pixler/OI signals available for reports even
    # when the row has no text interpretation yet. Ranges are deliberately
    # broad and should be treated as preliminary engineering hints.
    conflict_type = _ratio_conflict_type(oil_indicator, pixler, wh, bh)
    if conflict_type is not None:
        return conflict_type
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
    return "uncertain"


def is_prospective_fluid(fluid_type: str, *, include_low_confidence: bool = True) -> bool:
    if fluid_type in {"oil", "gas", "condensate", "mixed", "gas_oil", "oil_gas"}:
        return True
    return bool(include_low_confidence and fluid_type in {"transition", "uncertain"})


def _fluid_group(fluid_type: str, *, merge_compatible_fluids: bool) -> str:
    if not merge_compatible_fluids:
        return fluid_type
    if fluid_type in {"oil", "gas", "condensate", "mixed", "gas_oil", "oil_gas", "transition", "uncertain"}:
        return "hydrocarbon"
    return fluid_type


def _dominant(values: Iterable[str], default: str = "mixed") -> str:
    useful = [str(value) for value in values if str(value).strip()]
    if not useful:
        return default
    return sorted(set(useful), key=lambda value: (-useful.count(value), value))[0]


def _confidence(values: Iterable[str]) -> str:
    useful = [value for value in values if value and value != "nan"]
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


def _classification_confidence(frame: pd.DataFrame, fluid_type: str) -> str:
    """Estimate confidence from independent evidence count.

    This is intentionally conservative: it does not prove a reservoir, it only
    grades how many mud-gas indicators consistently support the interval type.
    """

    signals = 0
    wh = _mean(frame, "wh", "wetness")
    bh = _mean(frame, "bh", "balance")
    pixler = _mean(frame, "c1_c2", "pixler_c1_c2")
    oi = _mean(frame, "oil_indicator")

    if wh is not None and bh is not None:
        signals += 1
    if pixler is not None:
        signals += 1
    if oi is not None:
        signals += 1
    if "interpretation" in frame.columns and frame["interpretation"].astype(str).str.strip().ne("").any():
        signals += 1

    if fluid_type in {"transition", "uncertain"}:
        return "low"
    if signals >= 3 and len(frame) >= 2:
        return "high"
    if signals >= 2:
        return "medium"
    return "low"


def _evidence_for_group(frame: pd.DataFrame, fluid_type: str) -> tuple[str, ...]:
    evidence: list[str] = []
    wh = _mean(frame, "wh", "wetness")
    bh = _mean(frame, "bh", "balance")
    ch = _mean(frame, "ch", "character")
    c1_c2 = _mean(frame, "c1_c2", "pixler_c1_c2")
    c1_c3 = _mean(frame, "c1_c3", "pixler_c1_c3")
    oil_indicator = _mean(frame, "oil_indicator")

    if wh is not None or bh is not None:
        evidence.append(f"Haworth Wh/Bh: Wh={'' if wh is None else wh:g}, Bh={'' if bh is None else bh:g}.")
    if ch is not None:
        evidence.append(f"Character ratio CH={ch:g}.")
    if c1_c2 is not None:
        evidence.append(f"Pixler C1/C2={c1_c2:g}.")
    if c1_c3 is not None:
        evidence.append(f"Pixler C1/C3={c1_c3:g}.")
    if oil_indicator is not None:
        evidence.append(f"Oil indicator={oil_indicator:g}.")
    if not evidence:
        evidence.append("Интервал выделен по текстовой классификации строк.")
    evidence.append(f"Итоговый тип интервала: {fluid_type}.")
    return tuple(evidence)


def _warnings_for_group(frame: pd.DataFrame, fluid_type: str) -> tuple[str, ...]:
    warnings: list[str] = []
    numeric_columns = ["wh", "bh", "c1_c2", "c1_c3", "oil_indicator"]
    available = [column for column in numeric_columns if column in frame.columns]
    if not available:
        warnings.append("Нет числовых газовых коэффициентов; интервал основан только на текстовой классификации.")
    elif any(pd.to_numeric(frame[column], errors="coerce").isna().all() for column in available):
        warnings.append("Часть расчетных коэффициентов отсутствует или содержит только NaN.")
    if fluid_type == "transition":
        warnings.append("Переходный тип требует ручной проверки по соседним интервалам, ГИС и литологии.")
    if fluid_type == "uncertain":
        warnings.append("Тип флюида неустойчивый: признаки недостаточно согласованы для уверенной классификации.")
    if len(frame) == 1:
        warnings.append("Интервал представлен одной строкой; проверьте устойчивость признака по соседним глубинам.")
    return tuple(warnings)


def build_interval_engineering_note(interval: HydrocarbonInterval) -> str:
    """Return short printable interpretation text for one hydrocarbon interval."""

    label = FLUID_TYPE_LABELS.get(interval.fluid_type, interval.fluid_type)
    confidence = CONFIDENCE_LABELS.get(interval.confidence, interval.confidence)
    parts = [
        f"{label} {interval.top:g}-{interval.base:g} м, мощность {interval.thickness:g} м, {confidence}.",
    ]
    if interval.average_wh is not None or interval.average_bh is not None:
        parts.append(
            f"Средние Haworth-показатели: Wh={'' if interval.average_wh is None else f'{interval.average_wh:g}'}, "
            f"Bh={'' if interval.average_bh is None else f'{interval.average_bh:g}'}.",
        )
    if interval.average_pixler_c1_c2 is not None:
        parts.append(f"Pixler C1/C2={interval.average_pixler_c1_c2:g} используется как один из признаков флюидного характера.")
    if interval.average_oil_indicator is not None:
        parts.append(f"Oil indicator={interval.average_oil_indicator:g} добавлен в доказательную базу интервала.")
    parts.append("Вывод предварительный: требуется сверка с ГИС, литологией, испытаниями и качеством газового каротажа.")
    return " ".join(parts)


def _barrier_seal_quality(lithology: str) -> str:
    if lithology in {"claystone", "shale", "tight", "barrier"}:
        return "probable"
    if lithology == "clay":
        return "possible"
    return "unknown"


def _barrier_from_group(group: Sequence[Mapping[str, object]], *, inferred: bool = False) -> LithologyBarrier:
    frame = pd.DataFrame(group)
    top_values = pd.to_numeric(frame.get("top", frame["depth"]), errors="coerce")
    base_values = pd.to_numeric(frame.get("base", frame["depth"]), errors="coerce")
    top = float(top_values.min())
    base = float(base_values.max())
    lithology = _dominant(frame.get("lithology_class", pd.Series(dtype=str)).astype(str), default="unknown_barrier")
    if lithology == "unknown":
        lithology = "unknown_barrier"
    remarks = "Inferred from explicit top/base gap between productive intervals." if inferred else "Detected from non-productive lithology row(s)."
    return LithologyBarrier(
        top=top,
        base=base,
        lithology=lithology,
        seal_quality=_barrier_seal_quality(lithology),
        remarks=remarks,
        source_start_row=int(frame.get("__source_row", pd.Series([0])).min()) if "__source_row" in frame.columns else None,
        source_end_row=int(frame.get("__source_row", pd.Series([0])).max()) if "__source_row" in frame.columns else None,
        inferred=inferred,
    )


def _interval_from_group(group: Sequence[Mapping[str, object]]) -> HydrocarbonInterval:
    frame = pd.DataFrame(group)
    fluid_type = _dominant(frame["hydrocarbon_fluid_type"].astype(str), default="mixed")
    top_values = pd.to_numeric(frame.get("top", frame["depth"]), errors="coerce")
    base_values = pd.to_numeric(frame.get("base", frame["depth"]), errors="coerce")
    top = float(top_values.min())
    base = float(base_values.max())
    interpretation = _dominant(frame.get("interpretation", pd.Series(dtype=str)).astype(str), default=fluid_type)
    confidence_values = frame.get("confidence", pd.Series(dtype=str)).astype(str)
    confidence = _confidence(confidence_values)
    if confidence == "low":
        confidence = _classification_confidence(frame, fluid_type)

    interval = HydrocarbonInterval(
        top=top,
        base=base,
        sample_count=len(frame),
        fluid_type=fluid_type,
        confidence=confidence,
        interpretation=interpretation,
        average_wh=_mean(frame, "wh", "wetness"),
        average_bh=_mean(frame, "bh", "balance"),
        average_ch=_mean(frame, "ch", "character"),
        average_bar2=_mean(frame, "bar2"),
        average_pixler_c1_c2=_mean(frame, "c1_c2", "pixler_c1_c2"),
        average_pixler_c1_c3=_mean(frame, "c1_c3", "pixler_c1_c3"),
        average_oil_indicator=_mean(frame, "oil_indicator"),
        evidence=_evidence_for_group(frame, fluid_type),
        warnings=_warnings_for_group(frame, fluid_type),
        source_start_row=int(frame.get("__source_row", pd.Series([0])).min()) if "__source_row" in frame.columns else None,
        source_end_row=int(frame.get("__source_row", pd.Series([0])).max()) if "__source_row" in frame.columns else None,
        separated_by_gap=bool(frame.get("__separated_by_gap", pd.Series([False])).astype(bool).any()) if "__separated_by_gap" in frame.columns else False,
    )
    return HydrocarbonInterval(
        **{**interval.__dict__, "engineering_note": build_interval_engineering_note(interval)}
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
    rows["__source_row"] = range(len(rows))
    has_explicit_bounds = "top" in rows.columns and "base" in rows.columns
    rows[depth_column] = pd.to_numeric(rows[depth_column], errors="coerce")
    rows = rows.dropna(subset=[depth_column]).sort_values(depth_column).reset_index(drop=True)
    if rows.empty:
        return HydrocarbonIntervalResult(intervals=(), rows=rows, diagnostics=("Нет числовых значений глубины.",))

    fluid_types = [normalize_fluid_type(row._asdict() if hasattr(row, "_asdict") else row) for _, row in rows.iterrows()]
    rows["hydrocarbon_fluid_type"] = fluid_types
    lithology_classes = [normalize_lithology(row._asdict() if hasattr(row, "_asdict") else row) for _, row in rows.iterrows()]
    rows["lithology_class"] = lithology_classes
    lithology_barriers = [_is_barrier_lithology(lithology, rules) for lithology in lithology_classes]
    rows["hydrocarbon_candidate"] = [
        is_prospective_fluid(fluid_type, include_low_confidence=rules.include_low_confidence) and not is_barrier
        for fluid_type, is_barrier in zip(fluid_types, lithology_barriers)
    ]
    rows["barrier_candidate"] = [
        (not bool(candidate)) and bool(is_barrier)
        for candidate, is_barrier in zip(rows["hydrocarbon_candidate"], lithology_barriers)
    ]

    groups: list[list[Mapping[str, object]]] = []
    barrier_groups: list[list[Mapping[str, object]]] = []
    inferred_barriers: list[LithologyBarrier] = []
    current_barrier: list[Mapping[str, object]] = []
    current: list[Mapping[str, object]] = []
    previous_depth: float | None = None
    previous_base: float | None = None
    previous_group: str | None = None

    for record in rows.to_dict(orient="records"):
        if not record.get("hydrocarbon_candidate"):
            if current:
                groups.append(current)
                current = []
            if record.get("barrier_candidate"):
                current_barrier.append(record)
            elif current_barrier:
                barrier_groups.append(current_barrier)
                current_barrier = []
            previous_depth = None
            previous_base = None
            previous_group = None
            continue

        if current_barrier:
            barrier_groups.append(current_barrier)
            current_barrier = []

        depth = float(record[depth_column])
        row_top = _to_float(record.get("top"))
        row_base = _to_float(record.get("base"))
        explicit_top = depth if row_top is None else row_top
        explicit_base = depth if row_base is None else row_base
        explicit_gap = bool(has_explicit_bounds and previous_base is not None and explicit_top > previous_base)
        if explicit_gap and rules.preserve_explicit_gaps:
            inferred_barriers.append(
                _barrier_from_group(
                    (
                        {
                            "top": previous_base,
                            "base": explicit_top,
                            "depth": previous_base,
                            "lithology_class": "unknown_barrier",
                            "__source_row": record.get("__source_row"),
                        },
                    ),
                    inferred=True,
                )
            )
        record["__separated_by_gap"] = bool(explicit_gap)
        group_key = _fluid_group(str(record["hydrocarbon_fluid_type"]), merge_compatible_fluids=rules.merge_compatible_fluids)
        gap_ok = rules.max_depth_gap is None or previous_depth is None or abs(depth - previous_depth) <= rules.max_depth_gap
        explicit_gap_ok = not (rules.preserve_explicit_gaps and explicit_gap)
        group_ok = previous_group is None or group_key == previous_group
        if current and not (gap_ok and explicit_gap_ok and group_ok):
            groups.append(current)
            current = []
        current.append(record)
        previous_depth = depth
        previous_base = explicit_base
        previous_group = group_key

    if current:
        groups.append(current)
    if current_barrier:
        barrier_groups.append(current_barrier)

    barriers = tuple(_barrier_from_group(group) for group in barrier_groups) + tuple(inferred_barriers)

    intervals = tuple(
        _interval_from_group(group)
        for group in groups
        if len(group) >= max(1, int(rules.minimum_samples))
    )
    diagnostics = (
        f"Проверено строк: {len(rows)}.",
        f"Кандидатов УВ: {int(rows['hydrocarbon_candidate'].sum())}.",
        f"Сформировано УВ-интервалов: {len(intervals)}.",
        f"Обнаружено литологических перемычек: {len(barriers)}.",
        f"Схема интервалов: {HYDROCARBON_INTERVAL_SCHEMA}.",
    )
    return HydrocarbonIntervalResult(intervals=intervals, rows=rows, barriers=barriers, diagnostics=diagnostics)


def hydrocarbon_interval_table_rows(intervals: Iterable[HydrocarbonInterval]) -> tuple[dict[str, object], ...]:
    """Return UI/report-friendly serializable interval rows."""

    return tuple(
        {
            "top": interval.top,
            "base": interval.base,
            "thickness": interval.thickness,
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
            "engineering_note": interval.engineering_note,
            "warnings": " ".join(interval.warnings),
            "source_start_row": interval.source_start_row,
            "source_end_row": interval.source_end_row,
            "separated_by_gap": interval.separated_by_gap,
        }
        for interval in intervals
    )


def hydrocarbon_interval_dataframe(intervals: Iterable[HydrocarbonInterval]) -> pd.DataFrame:
    """Convert interval model to DataFrame for HTML/PDF report tables."""

    return pd.DataFrame(hydrocarbon_interval_table_rows(intervals))


def lithology_barrier_table_rows(barriers: Iterable[LithologyBarrier]) -> tuple[dict[str, object], ...]:
    """Return report-friendly lithology barrier rows."""

    return tuple(
        {
            "top": barrier.top,
            "base": barrier.base,
            "thickness": barrier.thickness,
            "lithology": barrier.lithology,
            "lithology_label": LITHOLOGY_CLASS_LABELS.get(barrier.lithology, barrier.lithology),
            "seal_quality": barrier.seal_quality,
            "remarks": barrier.remarks,
            "source_start_row": barrier.source_start_row,
            "source_end_row": barrier.source_end_row,
            "inferred": barrier.inferred,
        }
        for barrier in barriers
    )


def lithology_barrier_dataframe(barriers: Iterable[LithologyBarrier]) -> pd.DataFrame:
    """Convert barrier model to DataFrame for reports and UI grids."""

    return pd.DataFrame(lithology_barrier_table_rows(barriers))


def hydrocarbon_interval_marker_rows(intervals: Iterable[HydrocarbonInterval]) -> tuple[dict[str, object], ...]:
    """Return graph/report marker rows for highlighted hydrocarbon intervals.

    The marker model is intentionally presentation-neutral. Plot widgets, printable
    HTML/PDF reports and future LAS Workspace overlays can all use the same rows
    without re-running interpretation logic or inventing their own colors.
    """

    rows: list[dict[str, object]] = []
    for index, interval in enumerate(intervals, start=1):
        style = MARKER_STYLE_BY_FLUID.get(interval.fluid_type, MARKER_STYLE_BY_FLUID["transition"])
        rows.append(
            {
                "marker_id": f"HC-{index:03d}",
                "top": interval.top,
                "base": interval.base,
                "thickness": interval.thickness,
                "label": style["label"],
                "fluid_type": interval.fluid_type,
                "confidence": interval.confidence,
                "line_color": style["color"],
                "fill_color": style["fill"],
                "annotation": f"{style['label']} {interval.top:g}-{interval.base:g} м ({interval.confidence})",
                "engineering_note": interval.engineering_note,
            }
        )
    return tuple(rows)


def hydrocarbon_interval_marker_dataframe(intervals: Iterable[HydrocarbonInterval]) -> pd.DataFrame:
    """Convert marker model to DataFrame for printable reports and UI grids."""

    return pd.DataFrame(hydrocarbon_interval_marker_rows(intervals))

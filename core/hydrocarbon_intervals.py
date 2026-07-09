from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from core.method_registry import get_method_profile, method_id_for_parameter, method_registry_rows

import pandas as pd


HYDROCARBON_INTERVAL_SCHEMA = "gas-ratio-pro/hydrocarbon-intervals/v12"

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
class HydrocarbonInterpretationRule:
    """Auditable interval-level interpretation rule.

    Rules do not replace published methods. They are project-level decision
    logic that combines registered evidence, quality flags, lithology/barrier
    context and confidence factors into practical engineering interpretation.
    """

    rule_id: str
    target_fluid_types: tuple[str, ...]
    title: str
    method_id: str = "hydrocarbon_interval_engine"
    minimum_confidence_score: int = 0
    required_methods: tuple[str, ...] = ()
    required_parameters: tuple[str, ...] = ()
    forbidden_quality_flags: tuple[str, ...] = ()
    required_quality_flags: tuple[str, ...] = ()
    confidence_bonus: int = 0
    message: str = ""
    recommendation: str = ""


@dataclass(frozen=True)
class HydrocarbonRuleTrace:
    """Trace of one interpretation rule evaluation for an interval."""

    rule_id: str
    title: str
    status: str
    reasons: tuple[str, ...] = ()
    confidence_delta: int = 0
    message: str = ""
    recommendation: str = ""
    method_id: str = "hydrocarbon_interval_engine"
    reference: str = ""


INTERPRETATION_RULES: tuple[HydrocarbonInterpretationRule, ...] = (
    HydrocarbonInterpretationRule(
        rule_id="HC-GAS-HIGH-001",
        target_fluid_types=("gas",),
        title="High probability gas-bearing interval",
        minimum_confidence_score=70,
        required_methods=("haworth", "pixler"),
        required_parameters=("wh", "bh", "c1/c2"),
        forbidden_quality_flags=("no_numeric_gas_ratios", "contains_barrier_rows"),
        confidence_bonus=4,
        message="Вероятный газонасыщенный интервал высокой достоверности.",
        recommendation="Проверить по ГИС, литологии, испытаниям и буровому контексту перед окончательным выводом.",
    ),
    HydrocarbonInterpretationRule(
        rule_id="HC-OIL-HIGH-001",
        target_fluid_types=("oil",),
        title="High probability oil-bearing interval",
        minimum_confidence_score=70,
        required_methods=("haworth", "pixler"),
        required_parameters=("wh", "bh", "oil indicator"),
        forbidden_quality_flags=("no_numeric_gas_ratios", "contains_barrier_rows"),
        confidence_bonus=4,
        message="Вероятный нефтенасыщенный интервал высокой достоверности.",
        recommendation="Сопоставить с коллекторскими свойствами, ГИС, керном и результатами испытаний.",
    ),
    HydrocarbonInterpretationRule(
        rule_id="HC-COND-MED-001",
        target_fluid_types=("condensate",),
        title="Possible gas-condensate interval",
        minimum_confidence_score=55,
        required_methods=("haworth",),
        required_parameters=("wh", "bh"),
        forbidden_quality_flags=("no_numeric_gas_ratios",),
        confidence_bonus=2,
        message="Возможный газоконденсатный интервал.",
        recommendation="Уточнить по составу газа, динамике тяжелых компонентов и данным испытаний.",
    ),
    HydrocarbonInterpretationRule(
        rule_id="HC-MIXED-CHECK-001",
        target_fluid_types=("gas_oil", "oil_gas", "mixed", "transition"),
        title="Mixed or transition fluid character",
        minimum_confidence_score=35,
        required_methods=(),
        required_parameters=(),
        confidence_bonus=0,
        message="Смешанный или переходный характер флюида; требуется ручная проверка.",
        recommendation="Проверить границы интервала, соседние пласты, литологические перемычки и согласованность методов.",
    ),
    HydrocarbonInterpretationRule(
        rule_id="HC-LOW-DATA-001",
        target_fluid_types=("gas", "oil", "condensate", "mixed", "gas_oil", "oil_gas", "transition", "uncertain"),
        title="Limited data quality warning",
        required_quality_flags=("limited_numeric_evidence",),
        confidence_bonus=-6,
        message="Интерпретация ограничена неполной числовой доказательной базой.",
        recommendation="Не использовать интервал как окончательный вывод без проверки исходных кривых и пропусков данных.",
    ),
    HydrocarbonInterpretationRule(
        rule_id="HC-SINGLE-SAMPLE-001",
        target_fluid_types=("gas", "oil", "condensate", "mixed", "gas_oil", "oil_gas", "transition", "uncertain"),
        title="Single sample interval warning",
        required_quality_flags=("single_sample_interval",),
        confidence_bonus=-8,
        message="Интервал представлен одной глубинной точкой и может быть одиночным всплеском.",
        recommendation="Проверить устойчивость признака по соседним глубинам до включения в инженерное заключение.",
    ),
)


@dataclass(frozen=True)
class IntervalEvidence:
    """Structured evidence item used by interval interpretation and reports.

    Evidence is intentionally auditable. Each item stores method, parameter,
    observed value, expected condition, status and source reference metadata so
    printable reports can explain *why* an interval was classified without
    re-running or reverse-engineering the calculation.
    """

    method: str
    parameter: str
    value: float | str | None
    direction: str = "observed"
    weight: float = 1.0
    description: str = ""
    method_id: str = "hydrocarbon_interval_engine"
    source_id: str = "project_internal"
    evidence_id: str = ""
    expected: str = ""
    status: str = "observed"
    comment: str = ""
    reference: str = ""




@dataclass(frozen=True)
class HydrocarbonValidationCase:
    """Expected interpretation outcome for a reference validation dataset.

    This object is intentionally small and serializable. It is used to verify
    that changes in the interval engine do not silently break practical
    geological scenarios such as gas, oil, gas-condensate, mixed fluid,
    Claystone barrier separation or low-quality data handling.
    """

    case_id: str
    title: str
    expected_fluid_types: tuple[str, ...]
    expected_min_intervals: int = 1
    expected_barriers: int = 0
    minimum_confidence_score: int = 0
    required_quality_flags: tuple[str, ...] = ()
    required_rule_ids: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class HydrocarbonValidationResult:
    """Result of one validation-case check against engine output."""

    case_id: str
    title: str
    passed: bool
    messages: tuple[str, ...]
    observed_fluid_types: tuple[str, ...]
    observed_interval_count: int
    observed_barrier_count: int
    minimum_observed_confidence_score: int | None = None

@dataclass(frozen=True)
class HydrocarbonInterval:
    """Unified interval model for reports, charts and future PDF export."""

    top: float
    base: float
    sample_count: int
    fluid_type: str
    confidence: str
    interpretation: str
    confidence_score: int = 0
    confidence_factors: tuple[str, ...] = ()
    rule_traces: tuple[HydrocarbonRuleTrace, ...] = ()
    applied_rule_ids: tuple[str, ...] = ()
    interpretation_status: str = "preliminary"
    average_wh: float | None = None
    average_bh: float | None = None
    average_ch: float | None = None
    average_bar2: float | None = None
    average_pixler_c1_c2: float | None = None
    average_pixler_c1_c3: float | None = None
    average_oil_indicator: float | None = None
    evidence_items: tuple[IntervalEvidence, ...] = ()
    evidence: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
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


def _evidence_status(value: float | str | None, *, expected: str = "") -> str:
    """Return a conservative PASS/OBSERVED status for structured evidence.

    Threshold interpretation remains intentionally lightweight in this engine.
    Exact scientific classification belongs to the method-specific calculator;
    here we only mark whether a usable value exists for audit/report purposes.
    """

    if value is None:
        return "missing"
    if isinstance(value, str) and not value.strip():
        return "missing"
    return "pass" if expected else "observed"


def _method_reference(method_id: str) -> str:
    """Return short source reference string for one registered method."""

    profile = get_method_profile(method_id)
    authors = ", ".join(profile.authors)
    return f"{authors} ({profile.year}). {profile.source_title}."


def _evidence_id(method_id: str, parameter: str) -> str:
    """Build stable evidence identifier from registered method and parameter."""

    clean = str(parameter).lower().replace("/", "_").replace(" ", "_")
    return f"{method_id}:{clean}"


def _confidence_label_from_score(score: int) -> str:
    """Convert numeric engineering confidence score to a stable label."""

    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _confidence_score_for_group(
    frame: pd.DataFrame,
    fluid_type: str,
    evidence_items: Sequence[IntervalEvidence],
    quality_flags: Sequence[str],
) -> tuple[int, tuple[str, ...]]:
    """Calculate evidence-based confidence score for one interval.

    The score is not a reserve/economic probability. It only describes how well
    the current mud-gas indicators support the interval classification. The
    calculation is intentionally transparent: every bonus or penalty is returned
    as a machine-readable factor for reports, QA and future audit trails.
    """

    score = 20
    factors: list[str] = ["base=20"]

    methods = {item.method.lower() for item in evidence_items}
    parameters = {item.parameter.lower() for item in evidence_items}

    if "haworth" in methods:
        score += 18
        factors.append("haworth_evidence=+18")
    if "pixler" in methods:
        score += 18
        factors.append("pixler_evidence=+18")
    if "oil indicator" in parameters:
        score += 12
        factors.append("oil_indicator=+12")
    if "text interpretation" in parameters:
        score += 8
        factors.append("row_interpretation=+8")

    sample_count = len(frame)
    if sample_count >= 3:
        score += 12
        factors.append("multi_sample_interval=+12")
    elif sample_count == 2:
        score += 6
        factors.append("two_sample_interval=+6")

    if fluid_type in {"transition", "uncertain"}:
        score -= 18
        factors.append("uncertain_or_transition=-18")
    if fluid_type == "water":
        score -= 10
        factors.append("water_class=-10")

    penalty_by_flag = {
        "no_numeric_gas_ratios": -30,
        "limited_numeric_evidence": -12,
        "single_sample_interval": -10,
        "uncertain_fluid_character": -18,
        "contains_missing_ratio_values": -8,
        "contains_barrier_rows": -20,
    }
    for flag in quality_flags:
        penalty = penalty_by_flag.get(flag, 0)
        if penalty:
            score += penalty
            factors.append(f"{flag}={penalty}")

    # Explicit Claystone/Shale/Tight barriers are handled outside productive
    # intervals. If a barrier row still leaked into the group, keep the interval
    # printable but reduce confidence strongly instead of hiding it.
    if "lithology_class" in frame.columns:
        barrier_rows = frame["lithology_class"].astype(str).isin(BARRIER_LITHOLOGY_CLASSES).sum()
        if barrier_rows:
            penalty = -15 * int(barrier_rows)
            score += penalty
            factors.append(f"barrier_lithology_rows={penalty}")

    score = max(0, min(100, int(round(score))))
    factors.append(f"final={score}")
    return score, tuple(factors)

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


def _evidence_items_for_group(frame: pd.DataFrame, fluid_type: str) -> tuple[IntervalEvidence, ...]:
    """Build structured evidence records for one interpreted interval."""

    items: list[IntervalEvidence] = []
    wh = _mean(frame, "wh", "wetness")
    bh = _mean(frame, "bh", "balance")
    ch = _mean(frame, "ch", "character")
    c1_c2 = _mean(frame, "c1_c2", "pixler_c1_c2")
    c1_c3 = _mean(frame, "c1_c3", "pixler_c1_c3")
    oil_indicator = _mean(frame, "oil_indicator")

    if wh is not None:
        items.append(
            IntervalEvidence(
                method="Haworth",
                parameter="Wh",
                value=wh,
                direction="wetness",
                weight=1.0,
                description="Average wetness ratio inside the interval.",
                method_id="haworth_mud_gas",
                source_id="haworth_mud_gas",
                evidence_id=_evidence_id("haworth_mud_gas", "Wh"),
                expected="Published Haworth wetness ratio component; interpret with Bh/Ch and field calibration.",
                status=_evidence_status(wh, expected="haworth_wh"),
                comment="Supporting mud-gas wetness evidence, not a standalone pay flag.",
                reference=_method_reference("haworth_mud_gas"),
            )
        )
    if bh is not None:
        items.append(
            IntervalEvidence(
                method="Haworth",
                parameter="Bh",
                value=bh,
                direction="balance",
                weight=1.0,
                description="Average balance ratio inside the interval.",
                method_id="haworth_mud_gas",
                source_id="haworth_mud_gas",
                evidence_id=_evidence_id("haworth_mud_gas", "Bh"),
                expected="Published Haworth balance ratio component; interpret with Wh/Ch and field calibration.",
                status=_evidence_status(bh, expected="haworth_bh"),
                comment="Supporting mud-gas balance evidence.",
                reference=_method_reference("haworth_mud_gas"),
            )
        )
    if ch is not None:
        items.append(
            IntervalEvidence(
                method="Haworth",
                parameter="Ch",
                value=ch,
                direction="character",
                weight=0.8,
                description="Character ratio from heavy hydrocarbon components.",
                method_id="haworth_mud_gas",
                source_id="haworth_mud_gas",
                evidence_id=_evidence_id("haworth_mud_gas", "Ch"),
                expected="Haworth character ratio based on heavier hydrocarbon components.",
                status=_evidence_status(ch, expected="haworth_ch"),
                comment="Supports fluid character evaluation with Wh/Bh.",
                reference=_method_reference("haworth_mud_gas"),
            )
        )
    if c1_c2 is not None:
        items.append(
            IntervalEvidence(
                method="Pixler",
                parameter="C1/C2",
                value=c1_c2,
                direction="gas_ratio",
                weight=1.0,
                description="Pixler methane-to-ethane ratio used as one fluid-character indicator.",
                method_id="pixler_gas_ratio",
                source_id="pixler_gas_ratio",
                evidence_id=_evidence_id("pixler_gas_ratio", "C1/C2"),
                expected="Pixler methane-to-ethane ratio evidence; use only with other ratios and calibration.",
                status=_evidence_status(c1_c2, expected="pixler_c1_c2"),
                comment="Supporting Pixler gas-ratio evidence, not standalone proof of productivity.",
                reference=_method_reference("pixler_gas_ratio"),
            )
        )
    if c1_c3 is not None:
        items.append(
            IntervalEvidence(
                method="Pixler",
                parameter="C1/C3",
                value=c1_c3,
                direction="gas_ratio",
                weight=0.8,
                description="Pixler methane-to-propane ratio used as supporting evidence.",
                method_id="pixler_gas_ratio",
                source_id="pixler_gas_ratio",
                evidence_id=_evidence_id("pixler_gas_ratio", "C1/C3"),
                expected="Pixler methane-to-propane ratio evidence; use only with other ratios and calibration.",
                status=_evidence_status(c1_c3, expected="pixler_c1_c3"),
                comment="Supporting Pixler ratio evidence.",
                reference=_method_reference("pixler_gas_ratio"),
            )
        )
    if oil_indicator is not None:
        items.append(
            IntervalEvidence(
                method="Project",
                parameter="Oil indicator",
                value=oil_indicator,
                direction="oil_gas_indicator",
                weight=1.0,
                description="Project oil/gas indicator derived from calculated ratio fields.",
                method_id="project_oil_indicator",
                source_id="project_oil_indicator",
                evidence_id=_evidence_id("project_oil_indicator", "Oil indicator"),
                expected="Internal project hint; must be calibrated before field-grade interpretation.",
                status=_evidence_status(oil_indicator, expected="project_oil_indicator"),
                comment="Internal engineering hint, clearly separated from published methods.",
                reference=_method_reference("project_oil_indicator"),
            )
        )

    if "interpretation" in frame.columns:
        labels = sorted({str(value).strip() for value in frame["interpretation"] if str(value).strip() and str(value).lower() != "nan"})
        if labels:
            items.append(
                IntervalEvidence(
                    method="Classification",
                    parameter="Text interpretation",
                    value="; ".join(labels[:3]),
                    direction="label",
                    weight=0.6,
                    description="Existing row-level interpretation label supplied by calculation or import pipeline.",
                    method_id="hydrocarbon_interval_engine",
                    source_id="hydrocarbon_interval_engine",
                    evidence_id=_evidence_id("hydrocarbon_interval_engine", "Text interpretation"),
                    expected="Existing row-level classification labels are used as contextual support only.",
                    status=_evidence_status("; ".join(labels[:3]), expected="text_interpretation"),
                    comment="Imported or calculated label retained for traceability.",
                    reference=_method_reference("hydrocarbon_interval_engine"),
                )
            )

    items.append(
        IntervalEvidence(
            method="HydrocarbonIntervalEngine",
            parameter="fluid_type",
            value=fluid_type,
            direction="final_class",
            weight=1.0,
            description="Final interval class after rule-based normalization and grouping.",
            method_id="hydrocarbon_interval_engine",
            source_id="hydrocarbon_interval_engine",
            evidence_id=_evidence_id("hydrocarbon_interval_engine", "fluid_type"),
            expected="Final class must be derived from registered evidence and explicit project rules.",
            status="pass",
            comment="Final interval classification output of the Hydrocarbon Interval Engine.",
            reference=_method_reference("hydrocarbon_interval_engine"),
        )
    )
    return tuple(items)


def _format_evidence_item(item: IntervalEvidence) -> str:
    value = item.value
    if isinstance(value, float):
        value_text = f"{value:g}"
    elif value is None:
        value_text = ""
    else:
        value_text = str(value)
    if value_text:
        return f"{item.method} {item.parameter}={value_text}."
    return f"{item.method} {item.parameter}."


def _evidence_provenance(item: IntervalEvidence) -> dict[str, object]:
    """Return auditable provenance for one evidence item."""

    method_id = item.method_id or method_id_for_parameter(item.parameter)
    profile = get_method_profile(method_id)
    return {
        "method_id": method_id,
        "method": item.method,
        "parameter": item.parameter,
        "value": item.value,
        "expected": item.expected,
        "status": item.status,
        "weight": item.weight,
        "comment": item.comment,
        "reference": item.reference or _method_reference(method_id),
        "source_id": item.source_id or method_id,
        "source_title": profile.source_title,
        "authors": "; ".join(profile.authors),
        "year": profile.year,
        "status": profile.status,
        "implementation_status": profile.implementation_status,
        "limitations": profile.limitations,
        "citation_note": profile.citation_note,
    }


def hydrocarbon_method_registry_rows() -> tuple[dict[str, object], ...]:
    """Return registered method metadata used by Hydrocarbon Interval Engine."""

    return method_registry_rows()


def _evidence_for_group(frame: pd.DataFrame, fluid_type: str) -> tuple[str, ...]:
    """Return legacy printable evidence strings from structured evidence."""

    items = _evidence_items_for_group(frame, fluid_type)
    if not items:
        return ("Интервал выделен по текстовой классификации строк.",)
    return tuple(_format_evidence_item(item) for item in items)


def _quality_flags_for_group(frame: pd.DataFrame, fluid_type: str) -> tuple[str, ...]:
    """Return machine-readable quality flags for interval QA and reporting."""

    flags: list[str] = []
    numeric_columns = ["wh", "bh", "c1_c2", "c1_c3", "oil_indicator"]
    available = [column for column in numeric_columns if column in frame.columns]
    valid_numeric = 0
    for column in available:
        if not pd.to_numeric(frame[column], errors="coerce").dropna().empty:
            valid_numeric += 1

    if not available or valid_numeric == 0:
        flags.append("no_numeric_gas_ratios")
    elif valid_numeric < 2:
        flags.append("limited_numeric_evidence")

    if len(frame) == 1:
        flags.append("single_sample_interval")
    if fluid_type in {"transition", "uncertain"}:
        flags.append("uncertain_fluid_character")
    if any(pd.to_numeric(frame[column], errors="coerce").isna().any() for column in available):
        flags.append("contains_missing_ratio_values")
    if "barrier_candidate" in frame.columns and frame["barrier_candidate"].astype(bool).any():
        flags.append("contains_barrier_rows")
    return tuple(dict.fromkeys(flags))

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


def _rule_reference(rule: HydrocarbonInterpretationRule) -> str:
    """Return source reference for project rule evaluation."""

    return _method_reference(rule.method_id)


def _rule_matches(
    rule: HydrocarbonInterpretationRule,
    *,
    fluid_type: str,
    confidence_score: int,
    evidence_items: Sequence[IntervalEvidence],
    quality_flags: Sequence[str],
) -> tuple[bool, tuple[str, ...]]:
    """Evaluate one rule and return match status with human-readable reasons."""

    reasons: list[str] = []
    if fluid_type not in rule.target_fluid_types:
        reasons.append(f"fluid_type {fluid_type} not in {','.join(rule.target_fluid_types)}")
        return False, tuple(reasons)
    reasons.append(f"fluid_type={fluid_type}")

    if confidence_score < rule.minimum_confidence_score:
        reasons.append(f"confidence_score {confidence_score} < {rule.minimum_confidence_score}")
        return False, tuple(reasons)
    if rule.minimum_confidence_score:
        reasons.append(f"confidence_score {confidence_score} >= {rule.minimum_confidence_score}")

    methods = {item.method.lower() for item in evidence_items}
    parameters = {item.parameter.lower() for item in evidence_items}
    flags = {str(flag).lower() for flag in quality_flags}

    for method in rule.required_methods:
        if method.lower() not in methods:
            reasons.append(f"missing method {method}")
            return False, tuple(reasons)
        reasons.append(f"method {method}=present")

    for parameter in rule.required_parameters:
        if parameter.lower() not in parameters:
            reasons.append(f"missing parameter {parameter}")
            return False, tuple(reasons)
        reasons.append(f"parameter {parameter}=present")

    for flag in rule.required_quality_flags:
        if flag.lower() not in flags:
            reasons.append(f"required flag {flag}=absent")
            return False, tuple(reasons)
        reasons.append(f"required flag {flag}=present")

    for flag in rule.forbidden_quality_flags:
        if flag.lower() in flags:
            reasons.append(f"forbidden flag {flag}=present")
            return False, tuple(reasons)
        reasons.append(f"forbidden flag {flag}=absent")

    return True, tuple(reasons)


def _rule_traces_for_interval(
    *,
    fluid_type: str,
    confidence_score: int,
    evidence_items: Sequence[IntervalEvidence],
    quality_flags: Sequence[str],
) -> tuple[HydrocarbonRuleTrace, ...]:
    """Evaluate registered project interpretation rules for one interval."""

    traces: list[HydrocarbonRuleTrace] = []
    for rule in INTERPRETATION_RULES:
        matched, reasons = _rule_matches(
            rule,
            fluid_type=fluid_type,
            confidence_score=confidence_score,
            evidence_items=evidence_items,
            quality_flags=quality_flags,
        )
        traces.append(
            HydrocarbonRuleTrace(
                rule_id=rule.rule_id,
                title=rule.title,
                status="applied" if matched else "skipped",
                reasons=reasons,
                confidence_delta=rule.confidence_bonus if matched else 0,
                message=rule.message if matched else "",
                recommendation=rule.recommendation if matched else "",
                method_id=rule.method_id,
                reference=_rule_reference(rule),
            )
        )
    return tuple(traces)


def _apply_rule_confidence_delta(score: int, traces: Sequence[HydrocarbonRuleTrace]) -> tuple[int, tuple[str, ...]]:
    """Apply transparent rule bonuses/penalties after base evidence score."""

    delta = sum(trace.confidence_delta for trace in traces if trace.status == "applied")
    if not delta:
        return score, ()
    adjusted = max(0, min(100, int(round(score + delta))))
    return adjusted, (f"rule_delta={delta:+d}", f"rule_adjusted_final={adjusted}")


def _interpretation_status_from_rules(confidence_score: int, traces: Sequence[HydrocarbonRuleTrace], quality_flags: Sequence[str]) -> str:
    """Return practical readiness status for interval reporting."""

    applied = {trace.rule_id for trace in traces if trace.status == "applied"}
    if "HC-SINGLE-SAMPLE-001" in applied or "HC-LOW-DATA-001" in applied:
        return "requires_review"
    if confidence_score >= 75 and any(rule_id.endswith("HIGH-001") for rule_id in applied):
        return "high_confidence_preliminary"
    if "uncertain_fluid_character" in quality_flags:
        return "requires_review"
    return "preliminary"


def _trace_rows(traces: Iterable[HydrocarbonRuleTrace]) -> tuple[dict[str, object], ...]:
    """Serialize rule traces for report payloads and UI diagnostics."""

    return tuple(trace.__dict__ for trace in traces)


def build_interval_engineering_note(interval: HydrocarbonInterval) -> str:
    """Return short printable interpretation text for one hydrocarbon interval."""

    label = FLUID_TYPE_LABELS.get(interval.fluid_type, interval.fluid_type)
    confidence = CONFIDENCE_LABELS.get(interval.confidence, interval.confidence)
    parts = [
        f"{label} {interval.top:g}-{interval.base:g} м, мощность {interval.thickness:g} м, {confidence}, score {interval.confidence_score}%.",
    ]
    applied_messages = [trace.message for trace in interval.rule_traces if trace.status == "applied" and trace.message]
    if applied_messages:
        parts.append(applied_messages[0])
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
    source_confidence = _confidence(confidence_values)
    evidence_items = _evidence_items_for_group(frame, fluid_type)
    quality_flags = _quality_flags_for_group(frame, fluid_type)
    confidence_score, confidence_factors = _confidence_score_for_group(frame, fluid_type, evidence_items, quality_flags)
    rule_traces = _rule_traces_for_interval(
        fluid_type=fluid_type,
        confidence_score=confidence_score,
        evidence_items=evidence_items,
        quality_flags=quality_flags,
    )
    adjusted_score, rule_factors = _apply_rule_confidence_delta(confidence_score, rule_traces)
    confidence_score = adjusted_score
    confidence_factors = confidence_factors + rule_factors
    confidence = _confidence_label_from_score(confidence_score)
    if source_confidence == "high" and confidence == "medium":
        confidence = "high"
    if confidence == "low":
        legacy_confidence = _classification_confidence(frame, fluid_type)
        if legacy_confidence == "medium" and confidence_score >= 45:
            confidence = "medium"

    interval = HydrocarbonInterval(
        top=top,
        base=base,
        sample_count=len(frame),
        fluid_type=fluid_type,
        confidence=confidence,
        interpretation=interpretation,
        confidence_score=confidence_score,
        confidence_factors=confidence_factors,
        rule_traces=rule_traces,
        applied_rule_ids=tuple(trace.rule_id for trace in rule_traces if trace.status == "applied"),
        interpretation_status=_interpretation_status_from_rules(confidence_score, rule_traces, quality_flags),
        average_wh=_mean(frame, "wh", "wetness"),
        average_bh=_mean(frame, "bh", "balance"),
        average_ch=_mean(frame, "ch", "character"),
        average_bar2=_mean(frame, "bar2"),
        average_pixler_c1_c2=_mean(frame, "c1_c2", "pixler_c1_c2"),
        average_pixler_c1_c3=_mean(frame, "c1_c3", "pixler_c1_c3"),
        average_oil_indicator=_mean(frame, "oil_indicator"),
        evidence_items=evidence_items,
        evidence=tuple(_format_evidence_item(item) for item in evidence_items),
        quality_flags=quality_flags,
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
            "confidence_score": interval.confidence_score,
            "confidence_factors": " ".join(interval.confidence_factors),
            "applied_rule_ids": " ".join(interval.applied_rule_ids),
            "rule_traces": _trace_rows(interval.rule_traces),
            "interpretation_status": interval.interpretation_status,
            "interpretation": interval.interpretation,
            "avg_Wh": interval.average_wh,
            "avg_Bh": interval.average_bh,
            "avg_Ch": interval.average_ch,
            "avg_BAR2": interval.average_bar2,
            "avg_C1/C2": interval.average_pixler_c1_c2,
            "avg_C1/C3": interval.average_pixler_c1_c3,
            "avg_OI": interval.average_oil_indicator,
            "evidence": " ".join(interval.evidence),
            "evidence_items": tuple(item.__dict__ for item in interval.evidence_items),
            "evidence_provenance": tuple(_evidence_provenance(item) for item in interval.evidence_items),
            "quality_flags": " ".join(interval.quality_flags),
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
                "confidence_score": interval.confidence_score,
                "applied_rule_ids": " ".join(interval.applied_rule_ids),
                "interpretation_status": interval.interpretation_status,
                "line_color": style["color"],
                "fill_color": style["fill"],
                "annotation": f"{style['label']} {interval.top:g}-{interval.base:g} м ({interval.confidence}, {interval.confidence_score}%)",
                "engineering_note": interval.engineering_note,
                "quality_flags": " ".join(interval.quality_flags),
            }
        )
    return tuple(rows)


def hydrocarbon_interval_marker_dataframe(intervals: Iterable[HydrocarbonInterval]) -> pd.DataFrame:
    """Convert marker model to DataFrame for printable reports and UI grids."""

    return pd.DataFrame(hydrocarbon_interval_marker_rows(intervals))


def validate_hydrocarbon_interval_result(
    result: HydrocarbonIntervalResult,
    case: HydrocarbonValidationCase,
) -> HydrocarbonValidationResult:
    """Validate one engine result against a practical reference case.

    The validator does not decide geological truth. It protects the software
    from regressions: if a known gas case stops producing a gas interval, if a
    Claystone barrier disappears, or if confidence unexpectedly drops below the
    agreed threshold, the validation result fails and documents why.
    """

    messages: list[str] = []
    intervals = tuple(result.intervals)
    observed_fluid_types = tuple(interval.fluid_type for interval in intervals)
    observed_rule_ids = {rule_id for interval in intervals for rule_id in interval.applied_rule_ids}
    observed_quality_flags = {flag for interval in intervals for flag in interval.quality_flags}
    confidence_scores = [interval.confidence_score for interval in intervals]
    minimum_observed_confidence = min(confidence_scores) if confidence_scores else None

    if len(intervals) < case.expected_min_intervals:
        messages.append(
            f"Expected at least {case.expected_min_intervals} interval(s), got {len(intervals)}."
        )

    missing_fluids = [fluid for fluid in case.expected_fluid_types if fluid not in observed_fluid_types]
    if missing_fluids:
        messages.append(f"Missing expected fluid types: {', '.join(missing_fluids)}.")

    if len(result.barriers) < case.expected_barriers:
        messages.append(
            f"Expected at least {case.expected_barriers} barrier(s), got {len(result.barriers)}."
        )

    if case.minimum_confidence_score and (minimum_observed_confidence is None or minimum_observed_confidence < case.minimum_confidence_score):
        messages.append(
            f"Minimum confidence score below expected threshold: expected >= {case.minimum_confidence_score}, got {minimum_observed_confidence}."
        )

    missing_flags = [flag for flag in case.required_quality_flags if flag not in observed_quality_flags]
    if missing_flags:
        messages.append(f"Missing expected quality flags: {', '.join(missing_flags)}.")

    missing_rules = [rule_id for rule_id in case.required_rule_ids if rule_id not in observed_rule_ids]
    if missing_rules:
        messages.append(f"Missing expected rule ids: {', '.join(missing_rules)}.")

    return HydrocarbonValidationResult(
        case_id=case.case_id,
        title=case.title,
        passed=not messages,
        messages=tuple(messages),
        observed_fluid_types=observed_fluid_types,
        observed_interval_count=len(intervals),
        observed_barrier_count=len(result.barriers),
        minimum_observed_confidence_score=minimum_observed_confidence,
    )


def hydrocarbon_validation_result_rows(
    validation_results: Iterable[HydrocarbonValidationResult],
) -> tuple[dict[str, object], ...]:
    """Return serializable validation rows for QA tables and documentation."""

    return tuple(
        {
            "case_id": item.case_id,
            "title": item.title,
            "passed": item.passed,
            "messages": " ".join(item.messages),
            "observed_fluid_types": " ".join(item.observed_fluid_types),
            "observed_interval_count": item.observed_interval_count,
            "observed_barrier_count": item.observed_barrier_count,
            "minimum_observed_confidence_score": item.minimum_observed_confidence_score,
        }
        for item in validation_results
    )


def hydrocarbon_engine_api_contract() -> dict[str, object]:
    """Return the stable public API contract for downstream modules.

    Professional reports, plot tracks, dashboards and future PDF/DOCX exporters
    should consume this contract instead of re-calculating intervals or reading
    private implementation fields. This keeps the Hydrocarbon Interval Engine as
    the single source of truth.
    """

    return {
        "schema": HYDROCARBON_INTERVAL_SCHEMA,
        "result_model": "HydrocarbonIntervalResult",
        "interval_model": "HydrocarbonInterval",
        "barrier_model": "LithologyBarrier",
        "public_builders": (
            "detect_hydrocarbon_intervals",
            "hydrocarbon_interval_table_rows",
            "hydrocarbon_interval_marker_rows",
            "lithology_barrier_table_rows",
            "hydrocarbon_method_registry_rows",
            "validate_hydrocarbon_interval_result",
        ),
        "consumer_rule": "Reports, plots, UI and export layers must consume interval/barrier/evidence payloads from this engine and must not duplicate interval-classification logic.",
        "technical_details_policy": "Diagnostics, source row counts, NaN statistics, rule traces and provenance belong to expert/technical views, not to the default engineer-facing report summary.",
    }

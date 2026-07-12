from __future__ import annotations

import pandas as pd


INTERPRETATION_NOTE = (
    "Предварительная инженерная интерпретация. Требуется проверка по ГИС, "
    "литологии, буровому контексту, фону, СПО, наращиваниям и рециркуляции."
)


def classify_interval(wh, bh) -> str:
    if pd.isna(wh) or pd.isna(bh):
        return "Недостаточно данных"

    if wh < 0.5 and bh > 100:
        return "Сухой газ / непродуктивно"
    if 0.5 <= wh < 17.5 and wh < bh < 100:
        return "Газовая залежь"
    if 0.5 <= wh < 17.5 and bh <= wh:
        return "Жирный газ / конденсат"
    if 17.5 <= wh < 40 and bh < wh:
        return "Нефтяная залежь"
    if wh >= 40:
        return "Остаточная нефть / непродуктивно"
    return "Переходная зона / проверить"


def add_interpretation(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()
    result["interpretation"] = [
        classify_interval(wh, bh) for wh, bh in zip(result.get("wh"), result.get("bh"))
    ]
    result["interpretation_note"] = INTERPRETATION_NOTE
    return result


def summarize_interpretation(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "interpretation" not in df.columns:
        return pd.DataFrame(columns=["interpretation", "count"])

    summary = (
        df["interpretation"]
        .fillna("Недостаточно данных")
        .value_counts()
        .rename_axis("interpretation")
        .reset_index(name="count")
    )
    return summary


def engineering_interval_summary(df: pd.DataFrame, *, depth_column: str = "depth") -> pd.DataFrame:
    """Return an engineer-facing interval table instead of dataframe row counters.

    The table answers where the interpreted interval is, what fluid is probable,
    how thick it is and how reliable the conclusion is.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "Интервал, м", "Мощность, м", "Вероятный флюид",
            "Достоверность", "Уровень решения", "Инженерное заключение",
        ])

    from core.hydrocarbon_intervals import (
        FLUID_TYPE_LABELS,
        detect_hydrocarbon_intervals,
    )

    result = detect_hydrocarbon_intervals(df, depth_column=depth_column)
    rows: list[dict[str, object]] = []
    for interval in sorted(
        result.intervals,
        key=lambda item: (-int(item.confidence_score or 0), -float(item.thickness or 0), float(item.top)),
    ):
        if interval.fluid_type in {"insufficient"}:
            continue
        conclusion = (
            interval.explanation.summary
            if interval.explanation is not None and interval.explanation.summary
            else interval.engineering_note or interval.interpretation
        )
        rows.append({
            "Интервал, м": f"{interval.top:g}–{interval.base:g}",
            "Мощность, м": round(float(interval.thickness or 0.0), 2),
            "Вероятный флюид": FLUID_TYPE_LABELS.get(interval.fluid_type, interval.fluid_type),
            "Достоверность": f"{int(interval.confidence_score or 0)}%",
            "Данные": f"{int(interval.data_confidence_score or 0)}%",
            "Геология": f"{int(interval.geological_confidence_score or 0)}%",
            "Уровень решения": interval.decision_level or "неопределенный",
            "Инженерное заключение": str(conclusion or "Требуется инженерная проверка.").strip(),
        })
    return pd.DataFrame(rows)

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

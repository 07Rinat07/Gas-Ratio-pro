from __future__ import annotations

import math
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from core.models import GAS_COMPONENT_FIELDS


FIELD_LABELS: dict[str, str] = {
    "depth": "Depth",
    "depth_from": "Depth from",
    "depth_to": "Depth to",
    "c1": "C1",
    "c2": "C2",
    "c3": "C3",
    "ic4": "iC4",
    "nc4": "nC4",
    "ic5": "iC5",
    "nc5": "nC5",
}

RATIO_LABELS: dict[str, str] = {
    "wh": "Wh",
    "bh": "Bh",
    "ch": "Ch",
    "bar2": "BAR2",
    "c1_c2": "C1/C2",
    "c1_c3": "C1/C3",
    "c1_c4": "C1/C4",
    "c1_c5": "C1/C5",
}

RATIO_INPUTS: dict[str, tuple[str, ...]] = {
    "wh": ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5"),
    "bh": ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5"),
    "ch": ("c3", "ic4", "nc4", "ic5", "nc5"),
    "bar2": ("c1", "c2"),
    "c1_c2": ("c1", "c2"),
    "c1_c3": ("c1", "c3"),
    "c1_c4": ("c1", "ic4", "nc4"),
    "c1_c5": ("c1", "ic5", "nc5"),
}

DEFAULT_MAPPING_FIELDS: tuple[str, ...] = ("depth",) + GAS_COMPONENT_FIELDS
DEFAULT_RATIO_FIELDS: tuple[str, ...] = ("wh", "bh", "ch", "bar2")


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, RATIO_LABELS.get(field, field))


def _source_exists(source_name: str | None, source_columns: Iterable[object] | None) -> bool:
    if not source_name:
        return False
    if source_columns is None:
        return True
    return str(source_name) in {str(column) for column in source_columns}


def build_mapping_diagnostics(
    mapping: Mapping[str, str],
    source_columns: Iterable[object] | None = None,
    fields: Iterable[str] = DEFAULT_MAPPING_FIELDS,
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    has_interval_depth = bool(mapping.get("depth_from") and mapping.get("depth_to"))

    for field in fields:
        source_name = mapping.get(field, "")
        source_is_valid = _source_exists(source_name, source_columns)
        if source_is_valid:
            status = "ok"
            effect = "колонка используется в расчете"
            action = "нет"
        elif source_name:
            status = "source_missing"
            effect = "поле ссылается на колонку, которой нет в данных"
            action = "выберите существующую колонку"
        elif field == "depth" and has_interval_depth:
            status = "from_interval"
            effect = "depth будет рассчитан по середине depth_from/depth_to"
            action = "проверьте границы интервала"
        elif field == "depth":
            status = "missing"
            effect = "графики и интервалы будут использовать технический индекс строки"
            action = "сопоставьте depth или depth_from/depth_to"
        else:
            status = "missing"
            effect = f"{_label(field)} будет принят как 0"
            action = f"сопоставьте колонку {_label(field)}, если она есть в файле"

        rows.append(
            {
                "field": field,
                "label": _label(field),
                "source_column": str(source_name) if source_name else "",
                "status": status,
                "effect": effect,
                "action": action,
            }
        )

    return pd.DataFrame(rows)


def mapping_warning_messages(
    mapping: Mapping[str, str],
    source_columns: Iterable[object] | None = None,
) -> tuple[str, ...]:
    diagnostics = build_mapping_diagnostics(mapping, source_columns)
    messages: list[str] = []

    for row in diagnostics.to_dict("records"):
        status = row["status"]
        if status == "ok":
            continue
        if status == "from_interval":
            messages.append(
                "Mapping: depth не выбран напрямую; глубина будет рассчитана по середине depth_from/depth_to."
            )
            continue
        if row["field"] == "depth":
            messages.append(
                "Mapping: depth не сопоставлен; графики будут использовать технический индекс строки. "
                "Проверьте depth или пару depth_from/depth_to."
            )
            continue
        if status == "source_missing":
            messages.append(
                f"Mapping: {_label(row['field'])} выбран как `{row['source_column']}`, "
                "но такой колонки нет в текущих данных."
            )
            continue
        messages.append(
            f"Mapping: {_label(row['field'])} не сопоставлен; компонент будет принят как 0. "
            "Проверьте названия колонок и единицы измерения."
        )

    return tuple(dict.fromkeys(messages))


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _row_number_text(count: int) -> str:
    return "строка" if count == 1 else "строк"


def _denominator_for_ratio(df: pd.DataFrame, ratio: str) -> tuple[pd.Series, str, str]:
    if ratio == "wh":
        if "sum_c" in df.columns:
            return _numeric_series(df, "sum_c"), "sum_c", "C1+C2+C3+iC4+nC4+iC5+nC5"
        denominator = sum(_numeric_series(df, column) for column in GAS_COMPONENT_FIELDS)
        return denominator, "sum_c", "C1+C2+C3+iC4+nC4+iC5+nC5"
    if ratio == "bh":
        if "sum_c4" in df.columns and "sum_c5" in df.columns:
            denominator = _numeric_series(df, "c3") + _numeric_series(df, "sum_c4") + _numeric_series(df, "sum_c5")
        else:
            denominator = (
                _numeric_series(df, "c3")
                + _numeric_series(df, "ic4")
                + _numeric_series(df, "nc4")
                + _numeric_series(df, "ic5")
                + _numeric_series(df, "nc5")
            )
        return denominator, "bh_denominator", "C3+iC4+nC4+iC5+nC5"
    if ratio == "ch":
        if "sum_c4" in df.columns and "sum_c5" in df.columns:
            denominator = _numeric_series(df, "sum_c4") + _numeric_series(df, "sum_c5")
        else:
            denominator = (
                _numeric_series(df, "ic4")
                + _numeric_series(df, "nc4")
                + _numeric_series(df, "ic5")
                + _numeric_series(df, "nc5")
            )
        return denominator, "ch_denominator", "iC4+nC4+iC5+nC5"
    if ratio in {"bar2", "c1_c2"}:
        return _numeric_series(df, "c2"), "c2", "C2"
    if ratio == "c1_c3":
        return _numeric_series(df, "c3"), "c3", "C3"
    if ratio == "c1_c4":
        denominator = _numeric_series(df, "sum_c4") if "sum_c4" in df.columns else _numeric_series(df, "ic4") + _numeric_series(df, "nc4")
        return denominator, "sum_c4", "iC4+nC4"
    if ratio == "c1_c5":
        denominator = _numeric_series(df, "sum_c5") if "sum_c5" in df.columns else _numeric_series(df, "ic5") + _numeric_series(df, "nc5")
        return denominator, "sum_c5", "iC5+nC5"

    return pd.Series(np.nan, index=df.index, dtype=float), "unknown", "неизвестный знаменатель"


def _input_nan_details(df: pd.DataFrame, inputs: Iterable[str], nan_mask: pd.Series) -> tuple[str, ...]:
    details: list[str] = []
    for column in inputs:
        if column not in df.columns:
            continue
        values = _numeric_series(df, column)
        count = int((nan_mask & values.isna()).sum())
        if count > 0:
            details.append(f"{_label(column)}: {count}")
    return tuple(details)


def build_ratio_nan_diagnostics(
    df: pd.DataFrame,
    ratios: Iterable[str] = DEFAULT_RATIO_FIELDS,
    ch_mode: str = "A",
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    row_count = 0 if df is None else len(df)

    if df is None or df.empty:
        return pd.DataFrame(
            [
                {
                    "ratio": ratio,
                    "label": _label(ratio),
                    "nan_count": 0,
                    "row_count": 0,
                    "causes": "нет строк для диагностики",
                    "action": "загрузите данные",
                }
                for ratio in ratios
            ]
        )

    for ratio in ratios:
        label = _label(ratio)
        if ratio not in df.columns:
            rows.append(
                {
                    "ratio": ratio,
                    "label": label,
                    "nan_count": row_count,
                    "row_count": row_count,
                    "causes": "расчетная колонка отсутствует",
                    "action": "проверьте расчетный workflow",
                }
            )
            continue

        ratio_values = pd.to_numeric(df[ratio], errors="coerce")
        nan_mask = ratio_values.isna()
        nan_count = int(nan_mask.sum())
        if nan_count == 0:
            rows.append(
                {
                    "ratio": ratio,
                    "label": label,
                    "nan_count": 0,
                    "row_count": row_count,
                    "causes": "рассчитан во всех строках",
                    "action": "нет",
                }
            )
            continue

        inputs = RATIO_INPUTS.get(ratio, ())
        missing_inputs = tuple(column for column in inputs if column not in df.columns)
        denominator, _denominator_key, denominator_label = _denominator_for_ratio(df, ratio)
        bad_denominator_mask = denominator.isna() | (denominator == 0)
        bad_denominator_count = int((nan_mask & bad_denominator_mask).sum())
        input_nan_details = _input_nan_details(df, inputs, nan_mask)
        causes: list[str] = []

        if ratio == "ch" and ch_mode != "A":
            causes.append("выбран режим Ch без расчета формулы")
        if missing_inputs:
            causes.append("нет колонок: " + ", ".join(_label(column) for column in missing_inputs))
        if bad_denominator_count > 0:
            causes.append(
                f"нулевой или пустой знаменатель {denominator_label}: "
                f"{bad_denominator_count} {_row_number_text(bad_denominator_count)}"
            )
        if input_nan_details:
            causes.append("пустые или нечисловые входные значения: " + ", ".join(input_nan_details))
        if not causes:
            causes.append("проверьте входные C1-C5 и mapping")

        rows.append(
            {
                "ratio": ratio,
                "label": label,
                "nan_count": nan_count,
                "row_count": row_count,
                "causes": "; ".join(causes),
                "action": "проверьте mapping, числовой формат и нули в знаменателях",
            }
        )

    return pd.DataFrame(rows)


def ratio_nan_warning_messages(
    df: pd.DataFrame,
    ratios: Iterable[str] = DEFAULT_RATIO_FIELDS,
    ch_mode: str = "A",
) -> tuple[str, ...]:
    diagnostics = build_ratio_nan_diagnostics(df, ratios=ratios, ch_mode=ch_mode)
    messages: list[str] = []

    for row in diagnostics.to_dict("records"):
        nan_count = int(row["nan_count"])
        row_count = int(row["row_count"])
        if nan_count <= 0 or row_count <= 0:
            continue
        messages.append(
            f"{row['label']}: NaN в {nan_count} из {row_count} строк. "
            f"Причина: {row['causes']}. Что проверить: {row['action']}."
        )

    return tuple(messages)


def interval_ratio_diagnostic_messages(
    row: pd.Series,
    ratios: Iterable[str] = DEFAULT_RATIO_FIELDS,
    ch_mode: str = "A",
) -> tuple[str, ...]:
    if row is None:
        return ("Нет выбранной строки для диагностики коэффициентов.",)

    messages: list[str] = []
    for ratio in ratios:
        value = row.get(ratio, np.nan)
        try:
            is_missing = pd.isna(value) or math.isinf(float(value))
        except (TypeError, ValueError):
            is_missing = True

        if not is_missing:
            continue

        diagnostics = build_ratio_nan_diagnostics(pd.DataFrame([row.to_dict()]), ratios=(ratio,), ch_mode=ch_mode)
        if diagnostics.empty:
            continue
        detail = diagnostics.iloc[0]
        messages.append(
            f"{detail['label']}: нет расчета в выбранной строке. "
            f"Причина: {detail['causes']}. Проверьте mapping и входные C1-C5."
        )

    return tuple(messages)

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd

from core.models import CalculationConfig, CalculationResult, GAS_COMPONENT_FIELDS


CH_WARNING = "Формула Ch требует подтверждения по корпоративной методике. См. docs/formulas.md#ch."
METHODOLOGY_WARNING = (
    "Расчеты Wh/Bh/BAR2/Pixler/oil indicator являются предварительной инженерной "
    "подсказкой; проверьте единицы измерения C1-C5, mapping, нули и буровой контекст. "
    "См. docs/formulas.md и docs/mud_gas_analysis_literature.md."
)


def safe_divide(numerator, denominator):
    """Возвращает NaN при делении на 0 вместо исключения или inf."""
    if isinstance(numerator, pd.Series) or isinstance(denominator, pd.Series):
        num = pd.to_numeric(numerator, errors="coerce")
        den = pd.to_numeric(denominator, errors="coerce")
        if isinstance(den, pd.Series):
            den = den.replace(0, np.nan)
        elif den == 0 or pd.isna(den):
            den = np.nan
        with np.errstate(divide="ignore", invalid="ignore"):
            return num / den

    try:
        num_value = float(numerator)
        den_value = float(denominator)
    except (TypeError, ValueError):
        return np.nan

    if den_value == 0 or math.isnan(den_value):
        return np.nan
    return num_value / den_value


def _coerce_numeric(df: pd.DataFrame, columns: Iterable[str]) -> tuple[pd.DataFrame, list[str]]:
    result = df.copy()
    warnings: list[str] = []

    for column in columns:
        if column not in result.columns:
            continue

        original_not_empty = result[column].notna() & (result[column].astype(str).str.strip() != "")
        result[column] = pd.to_numeric(result[column], errors="coerce")
        invalid_count = int(original_not_empty.sum() - result[column].notna().sum())
        if invalid_count > 0:
            warnings.append(
                f"Колонка {column}: {invalid_count} значений не удалось преобразовать в число."
            )

    return result, warnings


def _depth_from_interval(result: pd.DataFrame) -> pd.Series | None:
    depth_from = pd.to_numeric(result.get("depth_from"), errors="coerce") if "depth_from" in result else None
    depth_to = pd.to_numeric(result.get("depth_to"), errors="coerce") if "depth_to" in result else None

    if depth_from is None and depth_to is None:
        return None
    if depth_from is not None and depth_to is not None:
        midpoint = (depth_from + depth_to) / 2
        combined = midpoint.combine_first(depth_from).combine_first(depth_to)
    elif depth_from is not None:
        combined = depth_from
    else:
        combined = depth_to

    return combined if not combined.isna().all() else None


def ensure_depth_column(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    result = df.copy()
    warnings: list[str] = []
    interval_depth = _depth_from_interval(result)

    if "depth" not in result.columns:
        if interval_depth is not None:
            result["depth"] = interval_depth
            warnings.append(
                "Колонка depth не найдена: используется середина интервала depth_from/depth_to."
            )
            return result, warnings

        result["depth"] = range(len(result))
        warnings.append(
            "Колонка depth не найдена: используется индекс строки как техническая глубина."
        )
        return result, warnings

    result["depth"] = pd.to_numeric(result["depth"], errors="coerce")
    if result["depth"].isna().all():
        if interval_depth is not None:
            result["depth"] = interval_depth
            warnings.append(
                "Колонка depth есть, но не содержит числовых значений: используется середина интервала depth_from/depth_to."
            )
            return result, warnings

        result["depth"] = range(len(result))
        warnings.append(
            "Колонка depth есть, но не содержит числовых значений: используется индекс строки."
        )

    return result, warnings


def calculate_gas_ratios(
    df: pd.DataFrame,
    config: CalculationConfig | None = None,
) -> CalculationResult:
    config = config or CalculationConfig()
    warnings: list[str] = []

    if df is None or df.empty:
        return CalculationResult(
            data=pd.DataFrame(),
            warnings=("Нет данных для расчета.",),
            metadata={"ch_notice": CH_WARNING, "methodology_notice": METHODOLOGY_WARNING},
        )

    result = df.copy()

    for component in GAS_COMPONENT_FIELDS:
        if component not in result.columns:
            result[component] = 0.0
            warnings.append(f"Компонент {component} отсутствует: для расчетов принят 0.")

    result, numeric_warnings = _coerce_numeric(
        result,
        list(GAS_COMPONENT_FIELDS) + ["depth", "depth_from", "depth_to", "co2", "h2s", "rop"],
    )
    warnings.extend(numeric_warnings)

    result, depth_warnings = ensure_depth_column(result)
    warnings.extend(depth_warnings)

    # Формулы взяты из предоставленного ТЗ/методики газопоказаний.
    result["sum_c4"] = result["ic4"] + result["nc4"]
    result["sum_c5"] = result["ic5"] + result["nc5"]
    result["sum_c"] = result["c1"] + result["c2"] + result["c3"] + result["sum_c4"] + result["sum_c5"]

    result["wh"] = safe_divide(
        (result["c2"] + result["c3"] + result["sum_c4"] + result["sum_c5"]) * 100,
        result["sum_c"],
    )
    result["bh"] = safe_divide(
        result["c1"] + result["c2"],
        result["c3"] + result["sum_c4"] + result["sum_c5"],
    )
    result["bar2"] = safe_divide(result["c1"], result["c2"])

    heavy_components = result["c3"] + result["sum_c4"] + result["sum_c5"]
    result["oil_indicator"] = safe_divide(heavy_components, result["c1"])
    result["inverse_oil_indicator"] = safe_divide(result["c1"], heavy_components)

    result["c1_c2"] = safe_divide(result["c1"], result["c2"])
    result["c1_c3"] = safe_divide(result["c1"], result["c3"])
    result["c1_c4"] = safe_divide(result["c1"], result["sum_c4"])
    result["c1_c5"] = safe_divide(result["c1"], result["sum_c5"])

    result["c2_sumc"] = safe_divide(result["c2"], result["sum_c"])
    result["c3_sumc"] = safe_divide(result["c3"], result["sum_c"])
    result["nc4_sumc"] = safe_divide(result["nc4"], result["sum_c"])

    if config.ch_mode == "A":
        result["ch"] = safe_divide(
            result["c3"] + result["sum_c4"] + result["sum_c5"],
            result["sum_c4"] + result["sum_c5"],
        )
    else:
        result["ch"] = np.nan
        warnings.append("Ch отключен: выбран резервный режим без подтвержденной формулы.")

    warnings.append(CH_WARNING)
    warnings.append(METHODOLOGY_WARNING)

    return CalculationResult(
        data=result,
        warnings=tuple(dict.fromkeys(warnings)),
        metadata={"ch_notice": CH_WARNING, "methodology_notice": METHODOLOGY_WARNING, "ch_mode": config.ch_mode},
    )

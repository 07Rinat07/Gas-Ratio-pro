from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import pandas as pd


FILL_STRATEGIES: tuple[str, ...] = ("empty", "top", "bottom", "average", "linear")


@dataclass(frozen=True)
class DepthGap:
    start_depth: float
    end_depth: float
    missing_depths: tuple[float, ...]


@dataclass(frozen=True)
class DepthDiagnostics:
    depth_column: str
    row_count: int
    valid_depth_count: int
    null_depth_count: int
    min_depth: float | None
    max_depth: float | None
    inferred_step: float | None
    duplicate_depths: tuple[float, ...] = ()
    reverse_step_count: int = 0
    gaps: tuple[DepthGap, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LasResampleResult:
    data: pd.DataFrame
    diagnostics: DepthDiagnostics
    added_depths: tuple[float, ...] = ()
    fill_strategy: str = "empty"
    depth_order_fixed: bool = False
    warnings: tuple[str, ...] = ()


def _to_decimal(value) -> Decimal:
    try:
        normalized = str(value).strip().replace(",", ".")
        decimal_value = Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Некорректное числовое значение глубины или шага: {value!r}") from exc

    if not decimal_value.is_finite():
        raise ValueError(f"Некорректное числовое значение глубины или шага: {value!r}")
    return decimal_value


def _to_float(value: Decimal) -> float:
    return float(value.normalize())


def _round_depth(value: float) -> float:
    return round(float(value), 10)


def _coerce_depth_series(df: pd.DataFrame, depth_column: str) -> pd.Series:
    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")
    return pd.to_numeric(df[depth_column], errors="coerce")


def _infer_step(sorted_depths: pd.Series) -> float | None:
    diffs = sorted_depths.diff().dropna()
    positive_diffs = diffs[diffs > 0].round(10)
    if positive_diffs.empty:
        return None
    return float(positive_diffs.value_counts().idxmax())


def build_depth_grid(start_depth, end_depth, step) -> tuple[float, ...]:
    start = _to_decimal(start_depth)
    end = _to_decimal(end_depth)
    depth_step = _to_decimal(step)

    if depth_step <= 0:
        raise ValueError("Шаг глубины должен быть больше 0.")
    if start > end:
        raise ValueError("Начальная глубина не может быть больше конечной.")

    values: list[float] = []
    current = start
    while current <= end:
        values.append(_to_float(current))
        current += depth_step

    return tuple(values)


def diagnose_depths(
    df: pd.DataFrame,
    depth_column: str = "depth",
    expected_step=None,
) -> DepthDiagnostics:
    depths = _coerce_depth_series(df, depth_column)
    valid_depths = depths.dropna()
    warnings: list[str] = []

    null_depth_count = int(depths.isna().sum())
    if null_depth_count:
        warnings.append(f"Колонка {depth_column}: пустых или нечисловых глубин: {null_depth_count}.")

    if valid_depths.empty:
        return DepthDiagnostics(
            depth_column=depth_column,
            row_count=len(df),
            valid_depth_count=0,
            null_depth_count=null_depth_count,
            min_depth=None,
            max_depth=None,
            inferred_step=None,
            warnings=tuple(warnings + ["Нет числовых глубин для проверки."]),
        )

    rounded_depths = valid_depths.map(_round_depth)
    duplicate_depths = tuple(sorted(float(value) for value in rounded_depths[rounded_depths.duplicated()].unique()))
    if duplicate_depths:
        warnings.append("Найдены дубликаты глубин: " + ", ".join(str(value) for value in duplicate_depths) + ".")

    ordered_diffs = valid_depths.diff().dropna()
    reverse_step_count = int((ordered_diffs < 0).sum())
    if reverse_step_count:
        warnings.append(f"Найдены шаги глубины в обратном порядке: {reverse_step_count}.")

    sorted_unique = pd.Series(sorted(rounded_depths.drop_duplicates()))
    inferred_step = _infer_step(sorted_unique)

    gaps: list[DepthGap] = []
    if expected_step is not None:
        step_value = float(_to_decimal(expected_step))
        if step_value <= 0:
            raise ValueError("Ожидаемый шаг глубины должен быть больше 0.")
        for previous, current in zip(sorted_unique, sorted_unique.iloc[1:]):
            if current - previous <= step_value + 1e-9:
                continue
            missing = build_depth_grid(_round_depth(previous + step_value), _round_depth(current - step_value), step_value)
            if missing:
                gaps.append(DepthGap(float(previous), float(current), missing))
        if gaps:
            warnings.append(f"Найдены пропуски глубины по шагу {step_value}: {len(gaps)} интервалов.")

    return DepthDiagnostics(
        depth_column=depth_column,
        row_count=len(df),
        valid_depth_count=int(valid_depths.count()),
        null_depth_count=null_depth_count,
        min_depth=float(valid_depths.min()),
        max_depth=float(valid_depths.max()),
        inferred_step=inferred_step,
        duplicate_depths=duplicate_depths,
        reverse_step_count=reverse_step_count,
        gaps=tuple(gaps),
        warnings=tuple(warnings),
    )


def _fill_added_rows(data: pd.DataFrame, depth_column: str, fill_strategy: str) -> pd.DataFrame:
    if fill_strategy == "empty":
        return data
    if fill_strategy == "top":
        return data.ffill()
    if fill_strategy == "bottom":
        return data.bfill()

    result = data.copy()
    value_columns = [column for column in result.columns if column != depth_column]
    numeric_values = result[value_columns].apply(pd.to_numeric, errors="coerce")

    if fill_strategy == "average":
        filled = (numeric_values.ffill() + numeric_values.bfill()) / 2
    elif fill_strategy == "linear":
        filled = numeric_values.interpolate(method="linear", limit_area="inside")
    else:
        raise ValueError(f"Стратегия заполнения {fill_strategy!r} не поддерживается.")

    result[value_columns] = result[value_columns].combine_first(filled)
    return result


def resample_las_data(
    df: pd.DataFrame,
    depth_column: str = "depth",
    target_step=0.1,
    fill_strategy: str = "empty",
) -> LasResampleResult:
    if fill_strategy not in FILL_STRATEGIES:
        raise ValueError(f"Стратегия заполнения {fill_strategy!r} не поддерживается.")

    diagnostics = diagnose_depths(df, depth_column=depth_column, expected_step=target_step)
    warnings = list(diagnostics.warnings)
    if diagnostics.min_depth is None or diagnostics.max_depth is None:
        return LasResampleResult(
            data=df.copy(),
            diagnostics=diagnostics,
            fill_strategy=fill_strategy,
            warnings=tuple(warnings),
        )

    working = df.copy()
    working[depth_column] = _coerce_depth_series(working, depth_column)
    working = working.dropna(subset=[depth_column])
    if diagnostics.null_depth_count:
        warnings.append("Строки без числовой глубины не включены в сетку редактора.")

    if diagnostics.duplicate_depths:
        working = working.drop_duplicates(subset=[depth_column], keep="first")
        warnings.append("Дубликаты глубин свернуты: оставлена первая строка для каждой глубины.")

    depth_order_fixed = diagnostics.reverse_step_count > 0
    if depth_order_fixed:
        warnings.append("Порядок глубины исправлен: строки отсортированы по возрастанию глубины.")

    grid = build_depth_grid(diagnostics.min_depth, diagnostics.max_depth, target_step)
    existing_depths = {_round_depth(value) for value in working[depth_column]}
    added_depths = tuple(depth for depth in grid if _round_depth(depth) not in existing_depths)

    indexed = working.set_index(depth_column).sort_index()
    resampled = indexed.reindex(grid)
    resampled.index.name = depth_column
    resampled = resampled.reset_index()
    resampled = _fill_added_rows(resampled, depth_column, fill_strategy)

    if added_depths:
        warnings.append(f"Добавлено строк по сетке глубины: {len(added_depths)}.")
        if fill_strategy != "empty":
            warnings.append(f"Добавленные строки заполнены стратегией: {fill_strategy}.")

    return LasResampleResult(
        data=resampled,
        diagnostics=diagnostics,
        added_depths=added_depths,
        fill_strategy=fill_strategy,
        depth_order_fixed=depth_order_fixed,
        warnings=tuple(dict.fromkeys(warnings)),
    )

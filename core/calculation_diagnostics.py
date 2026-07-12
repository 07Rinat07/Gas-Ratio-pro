from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from core.models import GAS_COMPONENT_FIELDS


FORMULA_INPUTS: dict[str, tuple[str, ...]] = {
    "wh": ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5"),
    "bh": ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5"),
    "ch": ("c3", "ic4", "nc4", "ic5", "nc5"),
    "bar2": ("c1", "c2"),
    "oil_indicator": ("c1", "c3", "ic4", "nc4", "ic5", "nc5"),
    "inverse_oil_indicator": ("c1", "c3", "ic4", "nc4", "ic5", "nc5"),
}

FORMULA_LABELS: dict[str, str] = {
    "wh": "Wh",
    "bh": "Bh",
    "ch": "Ch",
    "bar2": "BAR2",
    "oil_indicator": "Oil indicator",
    "inverse_oil_indicator": "Inverse oil indicator",
}

FORMULA_TEXT: dict[str, str] = {
    "wh": "(C2 + C3 + iC4 + nC4 + iC5 + nC5) × 100 / ΣC",
    "bh": "(C1 + C2) / (C3 + iC4 + nC4 + iC5 + nC5)",
    "ch": "(iC4 + nC4 + iC5 + nC5) / C3",
    "bar2": "C1 / C2",
    "oil_indicator": "(C3 + iC4 + nC4 + iC5 + nC5) / C1",
    "inverse_oil_indicator": "C1 / (C3 + iC4 + nC4 + iC5 + nC5)",
}


@dataclass(frozen=True, slots=True)
class ColumnQuality:
    field: str
    total_rows: int
    numeric_rows: int
    missing_rows: int
    zero_rows: int
    negative_rows: int
    minimum: float | None
    maximum: float | None

    @property
    def filled_percent(self) -> float:
        return 0.0 if self.total_rows <= 0 else self.numeric_rows * 100.0 / self.total_rows


@dataclass(frozen=True, slots=True)
class FormulaDiagnostic:
    formula: str
    label: str
    expression: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    missing_input_rows: int
    zero_denominator_rows: int
    non_numeric_rows: int
    dominant_reason: str
    recommendations: tuple[str, ...]

    @property
    def valid_percent(self) -> float:
        return 0.0 if self.total_rows <= 0 else self.valid_rows * 100.0 / self.total_rows


@dataclass(frozen=True, slots=True)
class CalculationDiagnosticsReport:
    total_rows: int
    columns: tuple[ColumnQuality, ...]
    formulas: tuple[FormulaDiagnostic, ...]
    recommendations: tuple[str, ...]
    problematic_rows: pd.DataFrame


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _denominator(df: pd.DataFrame, formula: str) -> pd.Series:
    c1, c2, c3 = _numeric(df, "c1"), _numeric(df, "c2"), _numeric(df, "c3")
    c4 = _numeric(df, "ic4") + _numeric(df, "nc4")
    c5 = _numeric(df, "ic5") + _numeric(df, "nc5")
    if formula == "wh":
        return c1 + c2 + c3 + c4 + c5
    if formula in {"bh", "inverse_oil_indicator"}:
        return c3 + c4 + c5
    if formula == "ch":
        return c3
    if formula == "bar2":
        return c2
    if formula == "oil_indicator":
        return c1
    return pd.Series(np.nan, index=df.index, dtype=float)


def build_column_quality(df: pd.DataFrame, fields: Iterable[str] = GAS_COMPONENT_FIELDS) -> tuple[ColumnQuality, ...]:
    total = 0 if df is None else len(df)
    if df is None:
        df = pd.DataFrame()
    rows: list[ColumnQuality] = []
    for field in fields:
        values = _numeric(df, field)
        numeric_rows = int(values.notna().sum())
        finite_values = values.replace([np.inf, -np.inf], np.nan).dropna()
        rows.append(
            ColumnQuality(
                field=field,
                total_rows=total,
                numeric_rows=numeric_rows,
                missing_rows=max(0, total - numeric_rows),
                zero_rows=int((values == 0).sum()),
                negative_rows=int((values < 0).sum()),
                minimum=None if finite_values.empty else float(finite_values.min()),
                maximum=None if finite_values.empty else float(finite_values.max()),
            )
        )
    return tuple(rows)


def _formula_diagnostic(df: pd.DataFrame, formula: str, *, ch_mode: str) -> FormulaDiagnostic:
    total = len(df)
    result = _numeric(df, formula)
    valid_mask = result.notna() & np.isfinite(result)
    invalid_mask = ~valid_mask

    inputs = FORMULA_INPUTS[formula]
    numeric_inputs = {name: _numeric(df, name) for name in inputs}
    missing_input_mask = pd.Series(False, index=df.index)
    non_numeric_mask = pd.Series(False, index=df.index)
    for name, values in numeric_inputs.items():
        missing_input_mask |= values.isna()
        if name in df.columns:
            raw = df[name]
            raw_present = raw.notna() & raw.astype(str).str.strip().ne("")
            non_numeric_mask |= raw_present & values.isna()

    denominator = _denominator(df, formula)
    zero_denominator_mask = denominator.eq(0)
    if formula == "ch" and ch_mode != "A":
        valid_mask = pd.Series(False, index=df.index)
        invalid_mask = ~valid_mask

    missing_count = int((invalid_mask & missing_input_mask).sum())
    zero_count = int((invalid_mask & zero_denominator_mask).sum())
    non_numeric_count = int((invalid_mask & non_numeric_mask).sum())
    valid_count = int(valid_mask.sum())
    invalid_count = total - valid_count

    reasons = {
        "пустые входные значения": missing_count,
        "нулевой знаменатель": zero_count,
        "нечисловые значения": non_numeric_count,
    }
    if formula == "ch" and ch_mode != "A":
        dominant = "формула отключена выбранным режимом Ch"
    else:
        dominant = max(reasons, key=reasons.get) if invalid_count and max(reasons.values()) > 0 else ("нет проблем" if invalid_count == 0 else "требуется анализ строк")

    recommendations: list[str] = []
    if missing_count:
        recommendations.append("Проверьте заполненность колонок: " + ", ".join(name.upper() for name in inputs))
    if zero_count:
        recommendations.append("Проверьте строки, где знаменатель формулы равен нулю.")
    if non_numeric_count:
        recommendations.append("Проверьте текстовые значения, разделитель дробной части и единицы измерения.")
    if formula == "ch" and ch_mode != "A":
        recommendations.append("Выберите режим Ch A для расчёта Haworth Character Ratio.")
    if not recommendations:
        recommendations.append("Дополнительных действий не требуется.")

    return FormulaDiagnostic(
        formula=formula,
        label=FORMULA_LABELS[formula],
        expression=FORMULA_TEXT[formula],
        total_rows=total,
        valid_rows=valid_count,
        invalid_rows=invalid_count,
        missing_input_rows=missing_count,
        zero_denominator_rows=zero_count,
        non_numeric_rows=non_numeric_count,
        dominant_reason=dominant,
        recommendations=tuple(recommendations),
    )


def build_calculation_diagnostics_report(
    df: pd.DataFrame,
    *,
    ch_mode: str = "A",
    formulas: Iterable[str] = tuple(FORMULA_INPUTS),
    problem_row_limit: int = 100,
) -> CalculationDiagnosticsReport:
    if df is None:
        df = pd.DataFrame()
    formula_rows = tuple(_formula_diagnostic(df, name, ch_mode=ch_mode) for name in formulas)
    column_rows = build_column_quality(df)

    recommendations: list[str] = []
    for item in column_rows:
        if item.total_rows and item.missing_rows / item.total_rows >= 0.2:
            recommendations.append(f"{item.field.upper()}: заполнено только {item.filled_percent:.1f}% строк; проверьте источник и mapping.")
        if item.negative_rows:
            recommendations.append(f"{item.field.upper()}: найдено отрицательных значений: {item.negative_rows}.")
    for item in formula_rows:
        if item.invalid_rows:
            recommendations.append(f"{item.label}: рассчитано {item.valid_percent:.1f}% строк; основная причина — {item.dominant_reason}.")
    recommendations = list(dict.fromkeys(recommendations))
    if not recommendations:
        recommendations.append("Критичных проблем качества данных не обнаружено.")

    problem_mask = pd.Series(False, index=df.index)
    for name in formulas:
        if name in df.columns:
            values = _numeric(df, name)
            problem_mask |= values.isna() | ~np.isfinite(values)
    preferred = [column for column in ("depth", *GAS_COMPONENT_FIELDS, *formulas) if column in df.columns]
    problematic = df.loc[problem_mask, preferred].head(max(0, int(problem_row_limit))).copy()
    if not problematic.empty:
        reasons: list[str] = []
        for _, row in problematic.iterrows():
            bad = [FORMULA_LABELS[name] for name in formulas if name in row.index and pd.isna(pd.to_numeric(pd.Series([row[name]]), errors="coerce").iloc[0])]
            reasons.append(", ".join(bad) if bad else "входные данные")
        problematic["Причина"] = reasons

    return CalculationDiagnosticsReport(
        total_rows=len(df),
        columns=column_rows,
        formulas=formula_rows,
        recommendations=tuple(recommendations),
        problematic_rows=problematic,
    )


def column_quality_dataframe(report: CalculationDiagnosticsReport) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Компонент": item.field.upper(),
            "Заполнено, %": round(item.filled_percent, 2),
            "Числовых": item.numeric_rows,
            "NaN/пусто": item.missing_rows,
            "Нулей": item.zero_rows,
            "Отрицательных": item.negative_rows,
            "Минимум": item.minimum,
            "Максимум": item.maximum,
        }
        for item in report.columns
    ])


def formula_diagnostics_dataframe(report: CalculationDiagnosticsReport) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Коэффициент": item.label,
            "Формула": item.expression,
            "Рассчитано": item.valid_rows,
            "Рассчитано, %": round(item.valid_percent, 2),
            "Не рассчитано": item.invalid_rows,
            "Пустые входы": item.missing_input_rows,
            "Нулевой знаменатель": item.zero_denominator_rows,
            "Нечисловые": item.non_numeric_rows,
            "Основная причина": item.dominant_reason,
        }
        for item in report.formulas
    ])


def calculation_diagnostics_to_dict(report: CalculationDiagnosticsReport) -> dict[str, object]:
    """Serialize a diagnostics report without leaking pandas/numpy objects."""
    return {
        "schema_version": 1,
        "total_rows": int(report.total_rows),
        "columns": [
            {
                "field": item.field,
                "total_rows": int(item.total_rows),
                "numeric_rows": int(item.numeric_rows),
                "missing_rows": int(item.missing_rows),
                "zero_rows": int(item.zero_rows),
                "negative_rows": int(item.negative_rows),
                "minimum": item.minimum,
                "maximum": item.maximum,
            }
            for item in report.columns
        ],
        "formulas": [
            {
                "formula": item.formula,
                "label": item.label,
                "expression": item.expression,
                "total_rows": int(item.total_rows),
                "valid_rows": int(item.valid_rows),
                "invalid_rows": int(item.invalid_rows),
                "missing_input_rows": int(item.missing_input_rows),
                "zero_denominator_rows": int(item.zero_denominator_rows),
                "non_numeric_rows": int(item.non_numeric_rows),
                "dominant_reason": item.dominant_reason,
                "recommendations": list(item.recommendations),
            }
            for item in report.formulas
        ],
        "recommendations": list(report.recommendations),
        "problematic_rows": report.problematic_rows.replace({np.nan: None}).to_dict(orient="records"),
    }


def calculation_diagnostics_from_dict(payload: Mapping[str, object]) -> CalculationDiagnosticsReport:
    """Restore a persisted diagnostics snapshot without recalculating source data."""
    columns = tuple(ColumnQuality(
        field=str(item.get("field", "")),
        total_rows=int(item.get("total_rows", 0) or 0),
        numeric_rows=int(item.get("numeric_rows", 0) or 0),
        missing_rows=int(item.get("missing_rows", 0) or 0),
        zero_rows=int(item.get("zero_rows", 0) or 0),
        negative_rows=int(item.get("negative_rows", 0) or 0),
        minimum=None if item.get("minimum") is None else float(item["minimum"]),
        maximum=None if item.get("maximum") is None else float(item["maximum"]),
    ) for item in payload.get("columns", ()) if isinstance(item, Mapping))
    formulas = tuple(FormulaDiagnostic(
        formula=str(item.get("formula", "")),
        label=str(item.get("label", "")),
        expression=str(item.get("expression", "")),
        total_rows=int(item.get("total_rows", 0) or 0),
        valid_rows=int(item.get("valid_rows", 0) or 0),
        invalid_rows=int(item.get("invalid_rows", 0) or 0),
        missing_input_rows=int(item.get("missing_input_rows", 0) or 0),
        zero_denominator_rows=int(item.get("zero_denominator_rows", 0) or 0),
        non_numeric_rows=int(item.get("non_numeric_rows", 0) or 0),
        dominant_reason=str(item.get("dominant_reason", "")),
        recommendations=tuple(str(v) for v in item.get("recommendations", ()) if str(v)),
    ) for item in payload.get("formulas", ()) if isinstance(item, Mapping))
    rows = payload.get("problematic_rows", ())
    return CalculationDiagnosticsReport(
        total_rows=int(payload.get("total_rows", 0) or 0),
        columns=columns,
        formulas=formulas,
        recommendations=tuple(str(v) for v in payload.get("recommendations", ()) if str(v)),
        problematic_rows=pd.DataFrame(list(rows) if isinstance(rows, (list, tuple)) else []),
    )

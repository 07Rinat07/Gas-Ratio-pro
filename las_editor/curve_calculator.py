from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence
import ast
import math

import pandas as pd

from las_editor.las_creator import DEFAULT_NULL_VALUE, LasCurveSpec, normalize_las_mnemonic, normalize_las_unit


CURVE_CALCULATOR_STORAGE_KEY = "las_curve_calculator"
CURVE_CALCULATOR_SCHEMA = "gas-ratio-pro/las-curve-calculator/v1"


@dataclass(frozen=True)
class CurveCalculationIssue:
    """One validation/calculation issue produced by the curve calculator."""

    severity: str
    code: str
    message: str
    curve_name: str = ""
    expression: str = ""


@dataclass(frozen=True)
class CurveCalculationHistoryEntry:
    """Audit trail entry for a non-destructive calculated curve operation."""

    action: str
    timestamp: str
    details: dict[str, Any]
    reason: str = "manual"
    source: str = "las_editor.curve_calculator"


@dataclass(frozen=True)
class CurveFormulaTemplate:
    """Reusable formula template for engineering calculations."""

    key: str
    output_curve: str
    expression: str
    unit: str = ""
    description: str = ""
    category: str = "general"


@dataclass(frozen=True)
class CurveCalculationPlan:
    """Normalized calculation plan checked before values are written."""

    output_curve: str
    expression: str
    unit: str
    description: str
    null_value: float
    overwrite: bool = False
    issues: tuple[CurveCalculationIssue, ...] = ()
    used_curves: tuple[str, ...] = ()


@dataclass(frozen=True)
class CurveCalculationResult:
    """Result of calculating a new LAS curve in a working copy."""

    data: pd.DataFrame
    plan: CurveCalculationPlan
    history: tuple[CurveCalculationHistoryEntry, ...]
    issues: tuple[CurveCalculationIssue, ...] = ()
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


_BUILTIN_FORMULAS: dict[str, CurveFormulaTemplate] = {
    "wetness_haworth": CurveFormulaTemplate(
        key="wetness_haworth",
        output_curve="WH",
        expression="((C2 + C3 + C4 + C5) / (C1 + C2 + C3 + C4 + C5)) * 100",
        unit="PCT",
        description="Haworth wetness ratio",
        category="mud_gas",
    ),
    "balance_haworth": CurveFormulaTemplate(
        key="balance_haworth",
        output_curve="BH",
        expression="(C1 + C2) / (C3 + C4 + C5)",
        unit="RATIO",
        description="Haworth balance ratio",
        category="mud_gas",
    ),
    "character_haworth": CurveFormulaTemplate(
        key="character_haworth",
        output_curve="CH",
        expression="(C4 + C5) / C3",
        unit="RATIO",
        description="Haworth character ratio",
        category="mud_gas",
    ),
    "pixler_c1_c2": CurveFormulaTemplate(
        key="pixler_c1_c2",
        output_curve="C1C2",
        expression="C1 / C2",
        unit="RATIO",
        description="Pixler C1/C2 ratio",
        category="mud_gas",
    ),
    "oil_indicator": CurveFormulaTemplate(
        key="oil_indicator",
        output_curve="OI",
        expression="(C3 + C4 + C5) / C1",
        unit="RATIO",
        description="Oil indicator ratio",
        category="mud_gas",
    ),
    "inverse_oil_indicator": CurveFormulaTemplate(
        key="inverse_oil_indicator",
        output_curve="IOI",
        expression="C1 / (C3 + C4 + C5)",
        unit="RATIO",
        description="Inverse oil indicator ratio",
        category="mud_gas",
    ),
    "net_gross_from_facies": CurveFormulaTemplate(
        key="net_gross_from_facies",
        output_curve="NG",
        expression="IF(FACIES == 0, 1, 0)",
        unit="V/V",
        description="Net/Gross flag from discrete facies code",
        category="petrophysics",
    ),
    "porosity_percent": CurveFormulaTemplate(
        key="porosity_percent",
        output_curve="POR_PCT",
        expression="POR * 100",
        unit="PCT",
        description="Porosity converted from fraction to percent",
        category="petrophysics",
    ),
}

_ALLOWED_BINARY_OPS = {
    ast.Add: lambda left, right: left + right,
    ast.Sub: lambda left, right: left - right,
    ast.Mult: lambda left, right: left * right,
    ast.Div: lambda left, right: left / right,
    ast.Pow: lambda left, right: left ** right,
    ast.Mod: lambda left, right: left % right,
}

_ALLOWED_COMPARE_OPS = {
    ast.Eq: lambda left, right: left == right,
    ast.NotEq: lambda left, right: left != right,
    ast.Lt: lambda left, right: left < right,
    ast.LtE: lambda left, right: left <= right,
    ast.Gt: lambda left, right: left > right,
    ast.GtE: lambda left, right: left >= right,
}


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _copy_attrs(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target.attrs.update(source.attrs)
    return target


def _append_history(
    history: Sequence[CurveCalculationHistoryEntry],
    *,
    action: str,
    details: Mapping[str, Any],
    reason: str = "manual",
    source: str = "las_editor.curve_calculator",
) -> tuple[CurveCalculationHistoryEntry, ...]:
    return tuple(history) + (
        CurveCalculationHistoryEntry(
            action=action,
            timestamp=_timestamp_utc(),
            details=dict(details),
            reason=reason or "manual",
            source=source or "las_editor.curve_calculator",
        ),
    )


def _as_series(value: Any, index: pd.Index) -> pd.Series:
    if isinstance(value, pd.Series):
        return value.reindex(index)
    return pd.Series([value] * len(index), index=index)


def _safe_division_cleanup(series: pd.Series, *, null_value: float) -> pd.Series:
    result = pd.to_numeric(series, errors="coerce")
    result = result.mask(result.apply(lambda value: isinstance(value, float) and (math.isinf(value) or math.isnan(value))))
    return result.fillna(null_value)


def _safe_function(name: str, args: list[Any], *, index: pd.Index) -> Any:
    key = name.upper()

    if key == "IF":
        if len(args) != 3:
            raise ValueError("IF requires exactly three arguments: IF(condition, true_value, false_value).")
        condition = _as_series(args[0], index).astype(bool)
        true_values = _as_series(args[1], index)
        false_values = _as_series(args[2], index)
        return true_values.where(condition, false_values)

    if key == "ABS" and len(args) == 1:
        return _as_series(args[0], index).abs()
    if key == "SQRT" and len(args) == 1:
        return _as_series(args[0], index).pow(0.5)
    if key == "LOG" and len(args) == 1:
        return _as_series(args[0], index).apply(lambda value: math.log(value) if value and value > 0 else math.nan)
    if key == "LOG10" and len(args) == 1:
        return _as_series(args[0], index).apply(lambda value: math.log10(value) if value and value > 0 else math.nan)
    if key == "EXP" and len(args) == 1:
        return _as_series(args[0], index).apply(lambda value: math.exp(value) if pd.notna(value) else math.nan)
    if key == "ROUND" and len(args) in (1, 2):
        digits = 0 if len(args) == 1 else int(args[1])
        return _as_series(args[0], index).round(digits)
    if key == "MIN" and len(args) >= 1:
        frame = pd.concat([_as_series(arg, index) for arg in args], axis=1)
        return frame.min(axis=1)
    if key == "MAX" and len(args) >= 1:
        frame = pd.concat([_as_series(arg, index) for arg in args], axis=1)
        return frame.max(axis=1)

    raise ValueError(f"Unsupported function {name!r}.")


class _FormulaEvaluator:
    """Small AST evaluator for LAS curve formulas.

    The evaluator deliberately avoids Python eval/exec. It supports arithmetic,
    comparisons and a small set of engineering functions that operate on pandas
    Series. This keeps calculated curves reproducible and safe for project files.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df
        self.index = df.index
        self.columns = {normalize_las_mnemonic(str(column)): str(column) for column in df.columns}
        self.used_curves: set[str] = set()

    def evaluate(self, expression: str) -> pd.Series:
        tree = ast.parse(expression, mode="eval")
        value = self._eval(tree.body)
        return _as_series(value, self.index)

    def _eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, bool)):
                return node.value
            raise ValueError("Only numeric and boolean constants are allowed in formulas.")

        if isinstance(node, ast.Name):
            name = normalize_las_mnemonic(node.id)
            if name not in self.columns:
                raise ValueError(f"Unknown curve or variable {node.id!r}.")
            self.used_curves.add(name)
            return pd.to_numeric(self.df[self.columns[name]], errors="coerce")

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = self._eval(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_BINARY_OPS:
                raise ValueError("Unsupported arithmetic operator.")
            left = self._eval(node.left)
            right = self._eval(node.right)
            return _ALLOWED_BINARY_OPS[op_type](left, right)

        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            result: Any | None = None
            current_left = left
            for operator, comparator in zip(node.ops, node.comparators):
                op_type = type(operator)
                if op_type not in _ALLOWED_COMPARE_OPS:
                    raise ValueError("Unsupported comparison operator.")
                right = self._eval(comparator)
                comparison = _ALLOWED_COMPARE_OPS[op_type](current_left, right)
                result = comparison if result is None else (result & comparison)
                current_left = right
            return result

        if isinstance(node, ast.BoolOp):
            values = [_as_series(self._eval(value), self.index).astype(bool) for value in node.values]
            if not values:
                raise ValueError("Empty boolean expression is not allowed.")
            result = values[0]
            for value in values[1:]:
                if isinstance(node.op, ast.And):
                    result = result & value
                elif isinstance(node.op, ast.Or):
                    result = result | value
                else:
                    raise ValueError("Unsupported boolean operator.")
            return result

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls are allowed.")
            args = [self._eval(arg) for arg in node.args]
            return _safe_function(node.func.id, args, index=self.index)

        raise ValueError(f"Unsupported formula syntax: {type(node).__name__}.")


def builtin_curve_formula_templates() -> tuple[CurveFormulaTemplate, ...]:
    """Return built-in curve formula templates sorted by key."""

    return tuple(_BUILTIN_FORMULAS[key] for key in sorted(_BUILTIN_FORMULAS))


def get_curve_formula_template(key: str) -> CurveFormulaTemplate:
    normalized = str(key or "").strip().lower()
    if normalized not in _BUILTIN_FORMULAS:
        raise KeyError(f"Unknown curve formula template: {key!r}")
    return _BUILTIN_FORMULAS[normalized]


def build_curve_calculation_plan(
    df: pd.DataFrame,
    *,
    output_curve: str,
    expression: str,
    unit: str = "",
    description: str = "",
    null_value: float | None = None,
    overwrite: bool = False,
) -> CurveCalculationPlan:
    """Validate and normalize a curve calculation before applying it."""

    output = normalize_las_mnemonic(output_curve)
    expr = str(expression or "").strip()
    issues: list[CurveCalculationIssue] = []
    used_curves: tuple[str, ...] = ()

    if not expr:
        issues.append(CurveCalculationIssue("error", "empty_expression", "Formula expression is empty.", output, expr))

    if output in {normalize_las_mnemonic(str(column)) for column in df.columns} and not overwrite:
        issues.append(CurveCalculationIssue("error", "curve_exists", f"Curve {output} already exists. Enable overwrite or choose another mnemonic.", output, expr))

    if expr:
        evaluator = _FormulaEvaluator(df)
        try:
            evaluator.evaluate(expr)
            used_curves = tuple(sorted(evaluator.used_curves))
        except Exception as exc:  # noqa: BLE001 - returned as a user-facing validation issue
            issues.append(CurveCalculationIssue("error", "invalid_expression", str(exc), output, expr))

    return CurveCalculationPlan(
        output_curve=output,
        expression=expr,
        unit=normalize_las_unit(unit),
        description=str(description or ""),
        null_value=float(DEFAULT_NULL_VALUE if null_value is None else null_value),
        overwrite=bool(overwrite),
        issues=tuple(issues),
        used_curves=used_curves,
    )


def build_curve_calculation_plan_from_template(
    df: pd.DataFrame,
    template_key: str,
    *,
    output_curve: str | None = None,
    overwrite: bool = False,
    null_value: float | None = None,
) -> CurveCalculationPlan:
    template = get_curve_formula_template(template_key)
    return build_curve_calculation_plan(
        df,
        output_curve=output_curve or template.output_curve,
        expression=template.expression,
        unit=template.unit,
        description=template.description,
        overwrite=overwrite,
        null_value=null_value,
    )


def calculate_curve_values(df: pd.DataFrame, plan: CurveCalculationPlan) -> tuple[pd.Series, tuple[CurveCalculationIssue, ...]]:
    """Calculate values for a validated plan without mutating the DataFrame."""

    fatal = [issue for issue in plan.issues if issue.severity == "error"]
    if fatal:
        return pd.Series([plan.null_value] * len(df), index=df.index), tuple(fatal)

    try:
        evaluator = _FormulaEvaluator(df)
        values = evaluator.evaluate(plan.expression)
        cleaned = _safe_division_cleanup(values, null_value=plan.null_value)
        return cleaned, ()
    except Exception as exc:  # noqa: BLE001 - converted to a deterministic issue object
        return pd.Series([plan.null_value] * len(df), index=df.index), (
            CurveCalculationIssue("error", "calculation_failed", str(exc), plan.output_curve, plan.expression),
        )


def apply_curve_calculation(
    df: pd.DataFrame,
    plan: CurveCalculationPlan,
    *,
    history: Sequence[CurveCalculationHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.curve_calculator",
) -> CurveCalculationResult:
    """Apply a calculated curve to a working copy without overwriting the source LAS."""

    values, calculation_issues = calculate_curve_values(df, plan)
    issues = tuple(plan.issues) + tuple(calculation_issues)
    if any(issue.severity == "error" for issue in issues):
        return CurveCalculationResult(
            data=df.copy(),
            plan=plan,
            history=tuple(history),
            issues=issues,
            warnings=("Расчетная кривая не создана из-за ошибок формулы.",),
        )

    result = df.copy()
    result[plan.output_curve] = values.values
    result = _copy_attrs(df, result)
    units = dict(result.attrs.get("las_units", {}))
    units[plan.output_curve] = plan.unit
    result.attrs["las_units"] = units
    descriptions = dict(result.attrs.get("las_descriptions", {}))
    descriptions[plan.output_curve] = plan.description
    result.attrs["las_descriptions"] = descriptions

    new_history = _append_history(
        history,
        action="calculate_curve",
        details={
            "output_curve": plan.output_curve,
            "expression": plan.expression,
            "unit": plan.unit,
            "used_curves": list(plan.used_curves),
            "overwrite": plan.overwrite,
        },
        reason=reason,
        source=source,
    )
    return CurveCalculationResult(
        data=result,
        plan=plan,
        history=new_history,
        issues=issues,
        diagnostics=(
            f"Создана расчетная кривая: {plan.output_curve}.",
            "Расчет выполнен только в рабочей копии LAS-таблицы.",
            "Исходный LAS-файл не перезаписывается.",
        ),
        warnings=tuple(issue.message for issue in issues if issue.severity == "warning"),
    )


def preview_curve_calculation(df: pd.DataFrame, plan: CurveCalculationPlan, *, max_rows: int = 10) -> tuple[dict[str, Any], ...]:
    values, _issues = calculate_curve_values(df, plan)
    rows: list[dict[str, Any]] = []
    for index, value in values.head(max_rows).items():
        rows.append({"row": int(index) if isinstance(index, int) else str(index), plan.output_curve: None if pd.isna(value) else float(value)})
    return tuple(rows)


def calculated_curve_spec(plan: CurveCalculationPlan) -> LasCurveSpec:
    return LasCurveSpec(plan.output_curve, plan.unit, plan.description or f"Calculated curve: {plan.expression}")


def curve_calculation_template_table_rows(templates: Iterable[CurveFormulaTemplate] | None = None) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "key": template.key,
            "category": template.category,
            "output_curve": template.output_curve,
            "unit": template.unit,
            "expression": template.expression,
            "description": template.description,
        }
        for template in (tuple(templates) if templates is not None else builtin_curve_formula_templates())
    )


def curve_calculation_issue_table_rows(issues: Iterable[CurveCalculationIssue]) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "severity": issue.severity,
            "code": issue.code,
            "curve_name": issue.curve_name,
            "expression": issue.expression,
            "message": issue.message,
        }
        for issue in issues
    )


def build_curve_calculation_manifest(result: CurveCalculationResult) -> dict[str, Any]:
    return {
        "schema": CURVE_CALCULATOR_SCHEMA,
        "generated_at": _timestamp_utc(),
        "storage_key": CURVE_CALCULATOR_STORAGE_KEY,
        "output_curve": result.plan.output_curve,
        "expression": result.plan.expression,
        "unit": result.plan.unit,
        "description": result.plan.description,
        "used_curves": list(result.plan.used_curves),
        "row_count": int(len(result.data)),
        "issue_count": len(result.issues),
        "issues": [issue.__dict__ for issue in result.issues],
    }

from __future__ import annotations

import ast
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

PROJECT_FORMULA_BUILDER_FILE_NAME = "formula_builder.json"
FORMULA_TEMPLATE_CATEGORIES = {"petrophysics", "gas", "quality", "custom"}
FORMULA_ALLOWED_FUNCTIONS = {"abs", "sqrt", "log", "log10", "exp", "min", "max"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _formula_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_FORMULA_BUILDER_FILE_NAME


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_text(value: Any, field_label: str, *, max_length: int = 180, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_id(value: str, default: str = "formula") -> str:
    raw = _clean_text(value, "ID", max_length=140) or default
    normalized = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", raw).strip("-_").lower() or default
    return safe_well_id(normalized)


def _clean_category(value: Any) -> str:
    category = _clean_text(value, "Категория", max_length=40).lower() or "custom"
    if category not in FORMULA_TEMPLATE_CATEGORIES:
        raise ValueError(f"Категория должна быть одной из: {', '.join(sorted(FORMULA_TEMPLATE_CATEGORIES))}.")
    return category


def _clean_curve_name(value: Any, field_label: str = "Кривая") -> str:
    curve = _clean_text(value, field_label, max_length=80, required=True).upper()
    if not re.fullmatch(r"[A-ZА-Я_][0-9A-ZА-Я_]*", curve):
        raise ValueError(f"{field_label}: используйте буквы, цифры и подчеркивание; первый символ должен быть буквой или _.")
    return curve


@dataclass(frozen=True)
class FormulaTemplate:
    id: str
    name: str
    expression: str
    output_curve: str
    description: str = ""
    units: str = ""
    category: str = "custom"
    variables: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormulaValidationResult:
    valid: bool
    expression: str
    dependencies: tuple[str, ...] = ()
    functions: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormulaRecord:
    id: str
    name: str
    expression: str
    output_curve: str
    source_type: str = "manual"
    source_id: str = ""
    well_id: str = ""
    variables: tuple[str, ...] = ()
    units: str = ""
    category: str = "custom"
    created_at: str = ""


@dataclass(frozen=True)
class FormulaBuilderSummary:
    formulas: int
    templates: int
    output_curves: int
    dependencies: int


DEFAULT_FORMULA_TEMPLATES: tuple[FormulaTemplate, ...] = (
    FormulaTemplate(
        id="vsh-gamma-ray",
        name="VSH from GR",
        expression="(GR - GR_MIN) / (GR_MAX - GR_MIN)",
        output_curve="VSH",
        description="Расчет глинистости по нормированной гамма-кривой.",
        units="v/v",
        category="petrophysics",
        variables=("GR", "GR_MIN", "GR_MAX"),
    ),
    FormulaTemplate(
        id="effective-porosity",
        name="Effective porosity",
        expression="PHIT * (1 - VSH)",
        output_curve="PHIE",
        description="Эффективная пористость с учетом глинистости.",
        units="v/v",
        category="petrophysics",
        variables=("PHIT", "VSH"),
    ),
    FormulaTemplate(
        id="archie-water-saturation",
        name="Archie Sw",
        expression="sqrt((A * RW) / (PHIE ** M * RT))",
        output_curve="SW",
        description="Базовый расчет водонасыщенности по Archie для чистых коллекторов.",
        units="v/v",
        category="petrophysics",
        variables=("A", "RW", "PHIE", "M", "RT"),
    ),
    FormulaTemplate(
        id="wetness-ratio",
        name="Wetness ratio",
        expression="(C2 + C3 + C4 + C5) / (C1 + C2 + C3 + C4 + C5)",
        output_curve="WH",
        description="Индекс влажности газа по компонентам C1-C5.",
        units="ratio",
        category="gas",
        variables=("C1", "C2", "C3", "C4", "C5"),
    ),
)


_ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)
_ALLOWED_UNARY_OPS = (ast.UAdd, ast.USub)


class _FormulaAstValidator(ast.NodeVisitor):
    def __init__(self, allowed_names: set[str] | None = None) -> None:
        self.allowed_names = allowed_names
        self.dependencies: set[str] = set()
        self.functions: set[str] = set()
        self.errors: list[str] = []

    def visit_Expression(self, node: ast.Expression) -> Any:
        self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if not isinstance(node.value, (int, float)):
            self.errors.append("В формулах разрешены только числовые константы.")

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in FORMULA_ALLOWED_FUNCTIONS:
            return
        if self.allowed_names is not None and node.id not in self.allowed_names:
            self.errors.append(f"Неизвестная переменная: {node.id}.")
        self.dependencies.add(node.id)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if not isinstance(node.op, _ALLOWED_BIN_OPS):
            self.errors.append("Оператор не поддерживается в Formula Builder.")
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        if not isinstance(node.op, _ALLOWED_UNARY_OPS):
            self.errors.append("Унарный оператор не поддерживается.")
        self.visit(node.operand)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name) or node.func.id not in FORMULA_ALLOWED_FUNCTIONS:
            self.errors.append("Разрешены только функции: " + ", ".join(sorted(FORMULA_ALLOWED_FUNCTIONS)) + ".")
        else:
            self.functions.add(node.func.id)
        for arg in node.args:
            self.visit(arg)
        if node.keywords:
            self.errors.append("Именованные аргументы функций не поддерживаются.")

    def visit_Compare(self, node: ast.Compare) -> Any:
        self.errors.append("Сравнения в расчетных формулах не поддерживаются.")

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        self.errors.append("Логические операции в расчетных формулах не поддерживаются.")

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        self.errors.append("Доступ к атрибутам запрещен в Formula Builder.")

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        self.errors.append("Индексация запрещена в Formula Builder.")

    def generic_visit(self, node: ast.AST) -> Any:
        allowed = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.BinOp, ast.UnaryOp, ast.Call) + _ALLOWED_BIN_OPS + _ALLOWED_UNARY_OPS
        if not isinstance(node, allowed):
            self.errors.append(f"Недопустимый элемент выражения: {type(node).__name__}.")
            return
        super().generic_visit(node)


def validate_formula_expression(expression: str, allowed_variables: Iterable[str] | None = None) -> FormulaValidationResult:
    clean_expression = _clean_text(expression, "Формула", max_length=600, required=True)
    allowed_names = {str(value).strip() for value in allowed_variables} if allowed_variables is not None else None
    try:
        tree = ast.parse(clean_expression, mode="eval")
    except SyntaxError as exc:
        return FormulaValidationResult(False, clean_expression, errors=(f"Синтаксическая ошибка: {exc.msg}.",))
    validator = _FormulaAstValidator(allowed_names)
    validator.visit(tree)
    errors = tuple(dict.fromkeys(validator.errors))
    return FormulaValidationResult(
        valid=not errors,
        expression=clean_expression,
        dependencies=tuple(sorted(validator.dependencies)),
        functions=tuple(sorted(validator.functions)),
        errors=errors,
    )


def detect_formula_dependencies(expression: str) -> tuple[str, ...]:
    return validate_formula_expression(expression).dependencies


def _series_safe_function(name: str):
    if name == "abs":
        return abs
    if name == "sqrt":
        return lambda value: value ** 0.5
    if name == "log":
        return lambda value: value.apply(math.log) if isinstance(value, pd.Series) else math.log(value)
    if name == "log10":
        return lambda value: value.apply(math.log10) if isinstance(value, pd.Series) else math.log10(value)
    if name == "exp":
        return lambda value: value.apply(math.exp) if isinstance(value, pd.Series) else math.exp(value)
    if name == "min":
        return lambda *values: pd.concat([v if isinstance(v, pd.Series) else pd.Series(v) for v in values], axis=1).min(axis=1)
    if name == "max":
        return lambda *values: pd.concat([v if isinstance(v, pd.Series) else pd.Series(v) for v in values], axis=1).max(axis=1)
    raise ValueError(f"Функция не разрешена: {name}.")


def _eval_formula_node(node: ast.AST, env: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_formula_node(node.body, env)
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError("В формуле разрешены только числовые константы.")
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ValueError(f"Переменная не найдена в данных: {node.id}.")
        return env[node.id]
    if isinstance(node, ast.UnaryOp):
        value = _eval_formula_node(node.operand, env)
        if isinstance(node.op, ast.UAdd):
            return value
        if isinstance(node.op, ast.USub):
            return -value
    if isinstance(node, ast.BinOp):
        left = _eval_formula_node(node.left, env)
        right = _eval_formula_node(node.right, env)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left ** right
        if isinstance(node.op, ast.Mod):
            return left % right
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _series_safe_function(node.func.id)
        return fn(*[_eval_formula_node(arg, env) for arg in node.args])
    raise ValueError("Формула содержит неподдерживаемую операцию.")


def calculate_formula_curve(
    data_frame: pd.DataFrame,
    expression: str,
    output_curve: str,
    *,
    constants: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    if not isinstance(data_frame, pd.DataFrame):
        raise TypeError("Ожидается pandas.DataFrame.")
    clean_output = _clean_curve_name(output_curve, "Выходная кривая")
    validation = validate_formula_expression(expression)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    frame = data_frame.copy()
    env: dict[str, Any] = {}
    constants = constants or {}
    for column in frame.columns:
        env[str(column)] = pd.to_numeric(frame[column], errors="coerce")
    for key, value in constants.items():
        env[str(key)] = float(value)
    missing = [name for name in validation.dependencies if name not in env]
    if missing:
        raise ValueError(f"В данных отсутствуют переменные: {', '.join(missing)}.")
    tree = ast.parse(validation.expression, mode="eval")
    frame[clean_output] = _eval_formula_node(tree, env)
    return frame


def _template_to_dict(template: FormulaTemplate) -> dict[str, Any]:
    return {**template.__dict__, "variables": list(template.variables)}


def _template_from_dict(raw: dict[str, Any]) -> FormulaTemplate:
    return FormulaTemplate(
        id=_safe_id(str(raw.get("id", "template")), "template"),
        name=_clean_text(raw.get("name"), "Название шаблона", required=True),
        expression=_clean_text(raw.get("expression"), "Формула", max_length=600, required=True),
        output_curve=_clean_curve_name(raw.get("output_curve"), "Выходная кривая"),
        description=_clean_text(raw.get("description"), "Описание", max_length=400),
        units=_clean_text(raw.get("units"), "Единицы", max_length=40),
        category=_clean_category(raw.get("category", "custom")),
        variables=tuple(_clean_curve_name(value, "Переменная") for value in raw.get("variables", []) if str(value).strip()),
    )


def list_formula_templates(extra_templates: Iterable[FormulaTemplate | dict[str, Any]] = ()) -> tuple[FormulaTemplate, ...]:
    templates = list(DEFAULT_FORMULA_TEMPLATES)
    for item in extra_templates:
        templates.append(item if isinstance(item, FormulaTemplate) else _template_from_dict(item))
    unique: dict[str, FormulaTemplate] = {template.id: template for template in templates}
    return tuple(unique.values())


def _record_to_dict(record: FormulaRecord) -> dict[str, Any]:
    return {**record.__dict__, "variables": list(record.variables)}


def _record_from_dict(raw: dict[str, Any]) -> FormulaRecord:
    return FormulaRecord(
        id=_safe_id(str(raw.get("id", "formula")), "formula"),
        name=_clean_text(raw.get("name"), "Название формулы", required=True),
        expression=_clean_text(raw.get("expression"), "Формула", max_length=600, required=True),
        output_curve=_clean_curve_name(raw.get("output_curve"), "Выходная кривая"),
        source_type=_clean_text(raw.get("source_type", "manual"), "Источник", max_length=40) or "manual",
        source_id=_clean_text(raw.get("source_id"), "ID источника", max_length=160),
        well_id=_safe_id(str(raw.get("well_id", "")), "well") if raw.get("well_id") else "",
        variables=tuple(_clean_curve_name(value, "Переменная") for value in raw.get("variables", []) if str(value).strip()),
        units=_clean_text(raw.get("units"), "Единицы", max_length=40),
        category=_clean_category(raw.get("category", "custom")),
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
    )


def list_formula_records(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[FormulaRecord, ...]:
    payload = _json_read(_formula_path(root, project_id), {"formulas": []})
    formulas = []
    for item in payload.get("formulas", []):
        if isinstance(item, dict):
            formulas.append(_record_from_dict(item))
    return tuple(sorted(formulas, key=lambda item: item.created_at, reverse=True))


def save_formula_record(
    root: Path | str,
    project_id: str,
    name: str,
    expression: str,
    output_curve: str,
    *,
    formula_id: str | None = None,
    source_type: str = "manual",
    source_id: str = "",
    well_id: str = "",
    units: str = "",
    category: str = "custom",
) -> FormulaRecord:
    validation = validate_formula_expression(expression)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    record = FormulaRecord(
        id=_safe_id(formula_id or f"formula-{name}"),
        name=_clean_text(name, "Название формулы", required=True),
        expression=validation.expression,
        output_curve=_clean_curve_name(output_curve, "Выходная кривая"),
        source_type=_clean_text(source_type, "Источник", max_length=40) or "manual",
        source_id=_clean_text(source_id, "ID источника", max_length=160),
        well_id=_safe_id(well_id, "well") if well_id else "",
        variables=validation.dependencies,
        units=_clean_text(units, "Единицы", max_length=40),
        category=_clean_category(category),
        created_at=_utc_now(),
    )
    existing = [item for item in list_formula_records(root, project_id) if item.id != record.id]
    _json_write(_formula_path(root, project_id), {"version": 1, "formulas": [_record_to_dict(record), *[_record_to_dict(item) for item in existing]]})
    append_project_history(root, project_id, "formula-builder", f"Saved formula {record.name}", object_type="formula", object_id=record.id)
    return record


def summarize_formula_builder(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> FormulaBuilderSummary:
    records = list_formula_records(root, project_id)
    return FormulaBuilderSummary(
        formulas=len(records),
        templates=len(DEFAULT_FORMULA_TEMPLATES),
        output_curves=len({record.output_curve for record in records}),
        dependencies=len({dependency for record in records for dependency in record.variables}),
    )


def build_formula_template_table(templates: Iterable[FormulaTemplate]) -> list[dict[str, Any]]:
    return [
        {
            "Шаблон": template.name,
            "ID": template.id,
            "Выход": template.output_curve,
            "Формула": template.expression,
            "Переменные": ", ".join(template.variables),
            "Единицы": template.units or "—",
            "Категория": template.category,
            "Описание": template.description,
        }
        for template in templates
    ]


def build_formula_records_table(records: Iterable[FormulaRecord]) -> list[dict[str, Any]]:
    return [
        {
            "Формула": record.name,
            "ID": record.id,
            "Выход": record.output_curve,
            "Выражение": record.expression,
            "Переменные": ", ".join(record.variables),
            "Источник": record.source_type,
            "Скважина": record.well_id or "—",
            "Единицы": record.units or "—",
            "Категория": record.category,
            "Создано": record.created_at,
        }
        for record in records
    ]


def build_formula_dependency_graph(records: Iterable[FormulaRecord]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for record in records:
        for dependency in record.variables:
            edges.append({"from": dependency, "to": record.output_curve, "formula": record.name})
    return edges

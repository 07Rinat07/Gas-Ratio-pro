from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

import pandas as pd

from las_editor.curve_categories import suggest_curve_category
from las_editor.curve_grouping import suggest_curve_group
from las_editor.curve_metadata import EDITABLE_FIELDS, normalize_metadata_field, normalize_metadata_value
from las_editor.curve_rename import normalize_curve_name
from las_editor.curve_units import suggest_curve_unit

BULK_EDIT_ACTION_LABELS: dict[str, str] = {
    "assign_group": "Assign group",
    "assign_category": "Assign category",
    "assign_unit": "Assign unit",
    "assign_metadata": "Assign metadata",
    "prefix": "Add prefix",
    "suffix": "Add suffix",
}


@dataclass(frozen=True)
class CurveBulkEditOperation:
    curve_name: str
    action: str
    previous_value: str
    new_value: str
    status: str
    message: str
    timestamp: str


@dataclass(frozen=True)
class CurveBulkEditResult:
    data: pd.DataFrame
    group_overrides: dict[str, str]
    category_overrides: dict[str, str]
    unit_overrides: dict[str, str]
    metadata: dict[str, dict[str, str]]
    operations: tuple[CurveBulkEditOperation, ...]
    warnings: tuple[str, ...]
    references: dict[str, Any]


def _stable_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_selected_curves(columns: Iterable[object], selected_curves: Iterable[object]) -> tuple[str, ...]:
    available = tuple(str(column) for column in columns)
    selected: list[str] = []
    for item in selected_curves:
        curve = str(item)
        if curve in available and curve not in selected:
            selected.append(curve)
    return tuple(selected)


def _add_warning(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)


def _rename_with_affix(columns: tuple[str, ...], curve: str, *, prefix: str = "", suffix: str = "") -> tuple[str, str | None]:
    new_name = normalize_curve_name(f"{prefix}{curve}{suffix}")
    if not new_name:
        return curve, "Новое имя кривой пустое после нормализации."
    if new_name == curve:
        return curve, "Имя кривой не изменилось."
    if new_name in columns:
        return curve, f"Кривая {new_name!r} уже существует."
    return new_name, None


def _metadata_with_patch(existing: Mapping[str, Any] | None, patch: Mapping[str, Any] | None) -> dict[str, str]:
    base = {
        "description": "",
        "source": "LAS import",
        "tool": "unknown",
        "comment": "",
        "status": "draft",
        "quality": "unknown",
    }
    for key, value in dict(existing or {}).items():
        field = normalize_metadata_field(key)
        if field in EDITABLE_FIELDS:
            base[field] = normalize_metadata_value(field, value)
    for key, value in dict(patch or {}).items():
        field = normalize_metadata_field(key)
        if field in EDITABLE_FIELDS and value is not None:
            base[field] = normalize_metadata_value(field, value)
    return base


def apply_curve_bulk_edit(
    df: pd.DataFrame,
    *,
    selected_curves: Iterable[object],
    action: str,
    group: str | None = None,
    category: str | None = None,
    unit: str | None = None,
    metadata_patch: Mapping[str, Any] | None = None,
    prefix: str = "",
    suffix: str = "",
    group_overrides: Mapping[str, str] | None = None,
    category_overrides: Mapping[str, str] | None = None,
    unit_overrides: Mapping[str, str] | None = None,
    metadata: Mapping[str, Mapping[str, Any]] | None = None,
    references: Mapping[str, Any] | None = None,
) -> CurveBulkEditResult:
    """Apply one explicit bulk edit to selected LAS curves.

    The function never mutates the input dataframe. Metadata/group/category/unit actions update
    override dictionaries only. Prefix/suffix actions rename columns in a copied dataframe and
    move existing override records to the new curve names.
    """

    if action not in BULK_EDIT_ACTION_LABELS:
        raise ValueError(f"Неподдерживаемое bulk edit действие: {action!r}.")

    columns = tuple(str(column) for column in df.columns)
    selected = _normalize_selected_curves(columns, selected_curves)
    if not selected:
        raise ValueError("Выберите хотя бы одну существующую кривую для bulk edit.")

    working = df.copy()
    group_map = {str(key): str(value) for key, value in dict(group_overrides or {}).items()}
    category_map = {str(key): str(value) for key, value in dict(category_overrides or {}).items()}
    unit_map = {str(key): str(value) for key, value in dict(unit_overrides or {}).items()}
    metadata_map: dict[str, dict[str, str]] = {
        str(key): _metadata_with_patch(value, None) for key, value in dict(metadata or {}).items()
    }
    warnings: list[str] = []
    operations: list[CurveBulkEditOperation] = []
    timestamp = _stable_timestamp()

    for curve in selected:
        previous_value = ""
        new_value = ""
        status = "applied"
        message = "Bulk edit applied."

        if action == "assign_group":
            new_value = str(group or suggest_curve_group(curve))
            previous_value = group_map.get(curve, suggest_curve_group(curve))
            group_map[curve] = new_value
            message = f"Группа назначена: {new_value}."

        elif action == "assign_category":
            base_group = group_map.get(curve, suggest_curve_group(curve))
            new_value = str(category or suggest_curve_category(curve, group=base_group))
            previous_value = category_map.get(curve, suggest_curve_category(curve, group=base_group))
            category_map[curve] = new_value
            message = f"Категория назначена: {new_value}."

        elif action == "assign_unit":
            base_group = group_map.get(curve, suggest_curve_group(curve))
            base_category = category_map.get(curve, suggest_curve_category(curve, group=base_group))
            new_value = str(unit or suggest_curve_unit(curve, group=base_group, category=base_category))
            previous_value = unit_map.get(curve, suggest_curve_unit(curve, group=base_group, category=base_category))
            unit_map[curve] = new_value
            message = f"Единица назначена: {new_value}."

        elif action == "assign_metadata":
            previous_value = str(metadata_map.get(curve, {}))
            metadata_map[curve] = _metadata_with_patch(metadata_map.get(curve), metadata_patch)
            new_value = str(metadata_map[curve])
            message = "Metadata обновлена для выбранной кривой."

        elif action in {"prefix", "suffix"}:
            new_name, warning = _rename_with_affix(
                tuple(str(column) for column in working.columns),
                curve,
                prefix=prefix if action == "prefix" else "",
                suffix=suffix if action == "suffix" else "",
            )
            previous_value = curve
            new_value = new_name
            if warning:
                status = "skipped"
                message = warning
                _add_warning(warnings, f"{curve}: {warning}")
            else:
                working = working.rename(columns={curve: new_name})
                if curve in group_map:
                    group_map[new_name] = group_map.pop(curve)
                if curve in category_map:
                    category_map[new_name] = category_map.pop(curve)
                if curve in unit_map:
                    unit_map[new_name] = unit_map.pop(curve)
                if curve in metadata_map:
                    metadata_map[new_name] = metadata_map.pop(curve)
                message = f"Кривая переименована: {curve} -> {new_name}."

        operations.append(
            CurveBulkEditOperation(
                curve_name=curve,
                action=action,
                previous_value=previous_value,
                new_value=new_value,
                status=status,
                message=message,
                timestamp=timestamp,
            )
        )

    updated_references = dict(references or {})
    updated_references["curve_bulk_edit"] = [operation.__dict__ for operation in operations]
    updated_references["curve_bulk_edit_summary"] = {
        "selected_curves": len(selected),
        "applied": sum(1 for operation in operations if operation.status == "applied"),
        "skipped": sum(1 for operation in operations if operation.status == "skipped"),
        "action": action,
    }

    return CurveBulkEditResult(
        data=working,
        group_overrides=group_map,
        category_overrides=category_map,
        unit_overrides=unit_map,
        metadata=metadata_map,
        operations=tuple(operations),
        warnings=tuple(warnings),
        references=updated_references,
    )


def curve_bulk_edit_operation_rows(operations: Iterable[CurveBulkEditOperation]) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for operation in operations:
        rows.append(
            {
                "curve_name": operation.curve_name,
                "action": operation.action,
                "action_label": BULK_EDIT_ACTION_LABELS.get(operation.action, operation.action),
                "previous_value": operation.previous_value,
                "new_value": operation.new_value,
                "status": operation.status,
                "message": operation.message,
                "timestamp": operation.timestamp,
            }
        )
    return tuple(rows)

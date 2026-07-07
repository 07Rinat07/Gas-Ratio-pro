from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd

from las_editor.las_creator import (
    DEFAULT_NULL_VALUE,
    LasCreationSpec,
    LasCurveSpec,
    build_las_creation_spec,
    builtin_las_templates,
    create_las_dataframe,
)
from las_editor.las_safe_export import builtin_las_template_profiles, las_template_table_rows

LAS_WORKSPACE_HOME_SCHEMA = "gas-ratio-pro.las-workspace-home.v1"


@dataclass(frozen=True)
class LasWorkspaceAction:
    """One visible entry point on LAS Workspace Home.

    These actions are intentionally available before any LAS file is loaded.
    The UI layer can render them as large buttons/cards, while tests can verify
    that the workspace never collapses to an empty upload-only screen.
    """

    action_id: str
    title: str
    description: str
    icon: str
    enabled_without_file: bool = True
    target_panel: str = ""


@dataclass(frozen=True)
class LasWorkspaceHomeState:
    """Renderer-independent model for LAS Workspace 2.0 home screen."""

    schema: str
    title: str
    subtitle: str
    actions: tuple[LasWorkspaceAction, ...]
    templates: tuple[dict[str, Any], ...]
    recent_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class LasCreationWizardPreview:
    """Preview returned by the creation wizard before export/save."""

    spec: LasCreationSpec
    data: pd.DataFrame
    row_count: int
    curve_count: int
    depth_start: float
    depth_stop: float
    depth_step: float
    template_name: str
    warnings: tuple[str, ...] = ()


def las_workspace_home_actions() -> tuple[LasWorkspaceAction, ...]:
    """Return the primary LAS actions that must be visible with no file loaded."""

    return (
        LasWorkspaceAction(
            "create_las",
            "Создать LAS",
            "Открыть мастер создания нового LAS-файла с нуля.",
            "📄",
            True,
            "creation_wizard",
        ),
        LasWorkspaceAction(
            "open_las",
            "Открыть LAS",
            "Загрузить существующий LAS-файл для проверки, правки и экспорта.",
            "📂",
            True,
            "file_upload",
        ),
        LasWorkspaceAction(
            "import_csv",
            "Импорт CSV",
            "Подготовить кривые из CSV и затем сохранить их как LAS.",
            "📥",
            True,
            "csv_import",
        ),
        LasWorkspaceAction(
            "import_excel",
            "Импорт Excel",
            "Подготовить кривые из XLSX/XLSM и затем сохранить их как LAS.",
            "📊",
            True,
            "excel_import",
        ),
        LasWorkspaceAction(
            "templates",
            "Шаблоны LAS",
            "Выбрать готовый профиль: пустой LAS, mud gas или петрофизика.",
            "📋",
            True,
            "templates",
        ),
        LasWorkspaceAction(
            "validator",
            "Проверка LAS",
            "Проверить структуру LAS, глубины, кривые, NULL и ASCII-данные.",
            "✅",
            False,
            "validator",
        ),
    )


def build_las_workspace_home_state(recent_files: Iterable[str] = ()) -> LasWorkspaceHomeState:
    """Build the visible Home state for LAS Workspace 2.0."""

    return LasWorkspaceHomeState(
        schema=LAS_WORKSPACE_HOME_SCHEMA,
        title="LAS Workspace 2.0",
        subtitle="Создание, открытие, редактирование, проверка и экспорт LAS-файлов.",
        actions=las_workspace_home_actions(),
        templates=tuple(las_template_table_rows(builtin_las_template_profiles())),
        recent_files=tuple(str(item) for item in recent_files if str(item).strip()),
    )


def action_table_rows(actions: Iterable[LasWorkspaceAction]) -> list[dict[str, Any]]:
    """Return UI-ready rows for action launcher tables/tests."""

    return [
        {
            "action_id": action.action_id,
            "title": action.title,
            "description": action.description,
            "icon": action.icon,
            "enabled_without_file": action.enabled_without_file,
            "target_panel": action.target_panel,
        }
        for action in actions
    ]


def parse_curve_text(raw_text: str) -> tuple[LasCurveSpec, ...]:
    """Parse user-entered curve lines.

    Supported formats:
    - GR
    - GR,API,Gamma ray
    - RHOB|G/C3|Bulk density
    """

    curves: list[LasCurveSpec] = []
    for line in str(raw_text or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        separator = "|" if "|" in cleaned else ","
        parts = [part.strip() for part in cleaned.split(separator)]
        mnemonic = parts[0] if parts else ""
        unit = parts[1] if len(parts) > 1 else ""
        description = parts[2] if len(parts) > 2 else mnemonic
        curves.append(LasCurveSpec(mnemonic=mnemonic, unit=unit, description=description))
    return tuple(curves)


def build_las_creation_wizard_preview(
    *,
    well_name: str,
    start_depth: float,
    stop_depth: float,
    step: float,
    template_name: str = "empty",
    curve_text: str = "",
    depth_unit: str = "M",
    null_value: float = DEFAULT_NULL_VALUE,
    company: str = "",
    field: str = "",
    uwi: str = "",
    api: str = "",
    service_company: str = "GAS RATIO PRO",
) -> LasCreationWizardPreview:
    """Create a preview model for the visible LAS creation wizard."""

    warnings: list[str] = []
    if float(step) <= 0:
        raise ValueError("Depth step must be positive.")
    if float(stop_depth) < float(start_depth):
        raise ValueError("Stop depth must be greater than or equal to start depth.")

    custom_curves = parse_curve_text(curve_text)
    spec = build_las_creation_spec(
        well_name=well_name,
        start_depth=start_depth,
        stop_depth=stop_depth,
        step=step,
        template_name=template_name,
        curves=custom_curves,
        depth_unit=depth_unit,
        null_value=null_value,
        company=company,
        field=field,
        uwi=uwi,
        api=api,
        service_company=service_company,
    )
    data = create_las_dataframe(spec)
    if not spec.curves:
        warnings.append("LAS будет создан только с кривой глубины DEPT. Дополнительные кривые можно добавить позже.")

    return LasCreationWizardPreview(
        spec=spec,
        data=data,
        row_count=len(data),
        curve_count=len(data.columns),
        depth_start=float(data["DEPT"].min()) if not data.empty else float(start_depth),
        depth_stop=float(data["DEPT"].max()) if not data.empty else float(stop_depth),
        depth_step=float(step),
        template_name=template_name,
        warnings=tuple(warnings),
    )

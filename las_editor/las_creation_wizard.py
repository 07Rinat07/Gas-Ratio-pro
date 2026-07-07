from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Iterable

import pandas as pd

from las_editor.las_creator import (
    DEFAULT_NULL_VALUE,
    LasCreationResult,
    LasCreationSpec,
    LasCurveSpec,
    LasValidationIssue,
    build_las_creation_spec,
    build_las_text,
    builtin_las_templates,
    create_las_dataframe,
    create_las_document,
    get_las_template_curves,
    normalize_las_mnemonic,
    normalize_las_unit,
    validate_las_creation,
)
from las_editor.depth_grid import build_safe_las_filename
from projects.project_explorer_foundation import (
    OperationJournalEntry,
    OperationStatus,
    build_operation_entry,
)

LAS_CREATION_WIZARD_SCHEMA = "gas-ratio-pro.las-creation-wizard.v2"


class LasCreationMode(str, Enum):
    """Supported user-facing modes of LAS Creation Wizard 2.0."""

    EMPTY = "empty"
    TEMPLATE = "template"
    FROM_LAS = "from_las"
    FROM_CSV = "from_csv"
    FROM_EXCEL = "from_excel"
    MANUAL = "manual"


@dataclass(frozen=True)
class LasWizardStep:
    """One step in the professional LAS creation wizard."""

    step_id: str
    title: str
    description: str
    required: bool = True
    completed: bool = False
    issue_count: int = 0


@dataclass(frozen=True)
class LasWizardSourceSummary:
    """Metadata extracted from an optional source LAS/CSV/XLSX object."""

    source_type: str = "none"
    well_name: str = ""
    start_depth: float | None = None
    stop_depth: float | None = None
    step: float | None = None
    curve_count: int = 0
    curves: tuple[LasCurveSpec, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LasCreationWizardDraft:
    """Renderer-independent draft state for LAS Creation Wizard 2.0.

    The UI can keep this object in session state, render each step, build a
    preview, validate it, then finalize only when the user explicitly confirms.
    """

    schema: str
    mode: LasCreationMode
    spec: LasCreationSpec
    source_summary: LasWizardSourceSummary = field(default_factory=LasWizardSourceSummary)
    steps: tuple[LasWizardStep, ...] = ()
    source_object_id: str = ""
    target_well_id: str = ""
    filename: str = ""


@dataclass(frozen=True)
class LasCreationWizardPreviewV2:
    """Full preview shown before LAS creation is finalized."""

    draft: LasCreationWizardDraft
    data: pd.DataFrame
    las_text: str
    issues: tuple[LasValidationIssue, ...]
    journal_entry: OperationJournalEntry
    table_rows: tuple[dict[str, Any], ...]
    curve_rows: tuple[dict[str, Any], ...]
    can_finalize: bool


@dataclass(frozen=True)
class LasCreationWizardFinalizeResult:
    """Result of a confirmed LAS creation operation."""

    result: LasCreationResult
    filename: str
    las_bytes: bytes
    journal_entry: OperationJournalEntry
    preview: LasCreationWizardPreviewV2


def las_creation_mode_rows() -> list[dict[str, str]]:
    """Return UI-ready rows for the first wizard screen."""

    return [
        {
            "mode": LasCreationMode.EMPTY.value,
            "title": "Пустой LAS",
            "description": "Создать LAS только с глубиной, затем добавить кривые вручную.",
        },
        {
            "mode": LasCreationMode.TEMPLATE.value,
            "title": "Из шаблона",
            "description": "Создать LAS на основе профилей empty, mud gas или petrophysics.",
        },
        {
            "mode": LasCreationMode.FROM_LAS.value,
            "title": "По другому LAS",
            "description": "Взять структуру заголовка и список кривых из существующего LAS.",
        },
        {
            "mode": LasCreationMode.FROM_CSV.value,
            "title": "Из CSV",
            "description": "Подготовить LAS по табличным данным CSV.",
        },
        {
            "mode": LasCreationMode.FROM_EXCEL.value,
            "title": "Из Excel",
            "description": "Подготовить LAS по листу Excel.",
        },
        {
            "mode": LasCreationMode.MANUAL.value,
            "title": "Ручное создание",
            "description": "Заполнить все основные поля, глубину и кривые вручную.",
        },
    ]


def las_creation_template_rows() -> list[dict[str, Any]]:
    """Return built-in template rows for UI tables."""

    rows: list[dict[str, Any]] = []
    for name in builtin_las_templates():
        curves = get_las_template_curves(name)
        rows.append(
            {
                "template": name,
                "curve_count": len(curves),
                "curves": ", ".join(curve.mnemonic for curve in curves) or "DEPT only",
            }
        )
    return rows


def _parse_las_card_value(line: str) -> tuple[str, str, str]:
    """Parse a simple LAS card line into mnemonic, value and description."""

    before_comment, _sep, description = line.partition(":")
    mnemonic_part, _dot, value_part = before_comment.partition(".")
    mnemonic = normalize_las_mnemonic(mnemonic_part)
    # Remove optional unit token from cards like STRT.M 1000.
    value = value_part.strip()
    if value:
        parts = value.split(None, 1)
        if len(parts) == 2 and not _looks_number(parts[0]) and _looks_number(parts[1]):
            value = parts[1]
    return mnemonic, value.strip(), description.strip()


def _looks_number(value: str) -> bool:
    try:
        float(str(value).replace(",", "."))
        return True
    except Exception:
        return False


def _section_lines(las_text: str, section_prefix: str) -> list[str]:
    """Return raw lines from a LAS section until the next section marker."""

    target = section_prefix.upper()
    in_section = False
    lines: list[str] = []
    for raw_line in str(las_text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("~"):
            in_section = line.upper().startswith(target)
            continue
        if in_section:
            lines.append(line)
    return lines


def summarize_source_las(las_text: str) -> LasWizardSourceSummary:
    """Extract a safe, lightweight source summary from existing LAS text.

    The parser is intentionally conservative. It is used for a creation wizard
    preview, not as a full LAS reader. Existing importer modules remain the
    authoritative source for production file loading.
    """

    warnings: list[str] = []
    well_name = ""
    start_depth: float | None = None
    stop_depth: float | None = None
    step: float | None = None

    for line in _section_lines(las_text, "~W"):
        mnemonic, value, _description = _parse_las_card_value(line)
        if mnemonic == "WELL" and value:
            well_name = value
        elif mnemonic == "STRT" and _looks_number(value):
            start_depth = float(value.replace(",", "."))
        elif mnemonic == "STOP" and _looks_number(value):
            stop_depth = float(value.replace(",", "."))
        elif mnemonic == "STEP" and _looks_number(value):
            step = abs(float(value.replace(",", ".")))

    curves: list[LasCurveSpec] = []
    for line in _section_lines(las_text, "~C"):
        mnemonic_part, _dot, rest = line.partition(".")
        mnemonic = normalize_las_mnemonic(mnemonic_part)
        if not mnemonic or mnemonic == "DEPT":
            continue
        unit_part, _sep, description = rest.partition(":")
        unit = normalize_las_unit(unit_part.split()[0] if unit_part.strip() else "")
        curves.append(LasCurveSpec(mnemonic=mnemonic, unit=unit, description=description.strip() or mnemonic))

    if start_depth is None or stop_depth is None or step is None:
        warnings.append("Источник LAS не содержит полного набора STRT/STOP/STEP; будут использованы значения мастера.")
    if not curves:
        warnings.append("В источнике LAS не найден список кривых кроме DEPT.")

    return LasWizardSourceSummary(
        source_type="las",
        well_name=well_name,
        start_depth=start_depth,
        stop_depth=stop_depth,
        step=step,
        curve_count=len(curves),
        curves=tuple(curves),
        warnings=tuple(warnings),
    )


def summarize_tabular_source(df: pd.DataFrame, *, source_type: str) -> LasWizardSourceSummary:
    """Build a source summary from CSV/Excel-like table columns."""

    columns = [str(column) for column in df.columns]
    depth_column = next((column for column in columns if normalize_las_mnemonic(column) in {"DEPT", "DEPTH", "MD", "TVD"}), "")
    curves = tuple(LasCurveSpec(normalize_las_mnemonic(column), description=column) for column in columns if column != depth_column)
    start_depth: float | None = None
    stop_depth: float | None = None
    step: float | None = None
    warnings: list[str] = []

    if depth_column:
        depth = pd.to_numeric(df[depth_column], errors="coerce").dropna()
        if not depth.empty:
            start_depth = float(depth.min())
            stop_depth = float(depth.max())
            unique_depth = sorted(depth.unique())
            if len(unique_depth) > 1:
                step = float(min(abs(unique_depth[i + 1] - unique_depth[i]) for i in range(len(unique_depth) - 1)))
    else:
        warnings.append("Табличный источник не содержит явной колонки глубины DEPT/DEPTH/MD/TVD.")

    return LasWizardSourceSummary(
        source_type=source_type,
        start_depth=start_depth,
        stop_depth=stop_depth,
        step=step,
        curve_count=len(curves),
        curves=curves,
        warnings=tuple(warnings),
    )


def _safe_validate_creation(spec: LasCreationSpec, data: pd.DataFrame | None = None, las_text: str | None = None) -> tuple[LasValidationIssue, ...]:
    """Validate a draft without allowing grid-building errors to break preview."""

    try:
        return validate_las_creation(spec, data, las_text)
    except ValueError as exc:
        message = str(exc)
        issues: list[LasValidationIssue] = []
        if spec.start_depth > spec.stop_depth:
            issues.append(LasValidationIssue("error", "DEPTH_RANGE_INVALID", "Start depth cannot be greater than stop depth."))
        if spec.step <= 0:
            issues.append(LasValidationIssue("error", "STEP_INVALID", "Depth step must be positive."))
        if not issues:
            issues.append(LasValidationIssue("error", "CREATION_INVALID", message))
        return tuple(issues)


def _safe_dataframe(spec: LasCreationSpec) -> pd.DataFrame:
    """Create a dataframe when possible; return an empty preview table for invalid drafts."""

    try:
        return create_las_dataframe(spec)
    except ValueError:
        df = pd.DataFrame({"DEPT": []})
        df.attrs["las_units"] = {"DEPT": spec.depth_unit}
        df.attrs["las_null_value"] = spec.null_value
        return df


def _safe_las_text(spec: LasCreationSpec, data: pd.DataFrame) -> str:
    """Build LAS text when possible; otherwise return an empty preview string."""

    try:
        return build_las_text(spec, data)
    except ValueError:
        return ""


def _wizard_steps(spec: LasCreationSpec, issues: Iterable[LasValidationIssue]) -> tuple[LasWizardStep, ...]:
    issue_list = tuple(issues)
    error_count = sum(1 for issue in issue_list if issue.severity == "error")
    return (
        LasWizardStep("mode", "Режим создания", "Выбор сценария: пустой LAS, шаблон, источник или ручной ввод.", completed=True),
        LasWizardStep("header", "Header", "WELL, FIELD, COMPANY, UWI/API, сервисная компания и служебные поля.", completed=bool(spec.well_name.strip())),
        LasWizardStep("depth", "Глубина", "START, STOP, STEP, NULL и единицы глубины.", completed=spec.step > 0 and spec.start_depth <= spec.stop_depth),
        LasWizardStep("curves", "Кривые", "Список кривых, единицы и описания.", completed=True),
        LasWizardStep("preview", "Предпросмотр", "Проверка таблицы, LAS-текста и предупреждений перед сохранением.", completed=error_count == 0, issue_count=len(issue_list)),
        LasWizardStep("save", "Сохранение", "Создание нового LAS без изменения существующих файлов.", completed=False, issue_count=error_count),
    )


def build_las_creation_wizard_draft(
    *,
    mode: str | LasCreationMode = LasCreationMode.EMPTY,
    well_name: str = "WELL",
    start_depth: float | str = 0.0,
    stop_depth: float | str = 0.0,
    step: float | str = 0.5,
    template_name: str = "empty",
    curves: Iterable[LasCurveSpec | dict[str, object] | str] = (),
    las_version: str = "2.0",
    depth_unit: str = "M",
    null_value: float | str = DEFAULT_NULL_VALUE,
    uwi: str = "",
    api: str = "",
    company: str = "",
    field: str = "",
    location: str = "",
    service_company: str = "GAS RATIO PRO",
    source_las_text: str = "",
    source_dataframe: pd.DataFrame | None = None,
    source_object_id: str = "",
    target_well_id: str = "",
    filename: str = "",
) -> LasCreationWizardDraft:
    """Build a complete LAS Creation Wizard 2.0 draft from UI values."""

    creation_mode = LasCreationMode(str(mode).lower()) if not isinstance(mode, LasCreationMode) else mode
    source_summary = LasWizardSourceSummary()
    selected_template = template_name
    selected_curves: list[LasCurveSpec | dict[str, object] | str] = list(curves)

    resolved_well_name = well_name
    resolved_start = start_depth
    resolved_stop = stop_depth
    resolved_step = step

    if creation_mode == LasCreationMode.FROM_LAS and source_las_text:
        source_summary = summarize_source_las(source_las_text)
        selected_template = "empty"
        selected_curves.extend(source_summary.curves)
        resolved_well_name = resolved_well_name or source_summary.well_name or "WELL"
        resolved_start = source_summary.start_depth if source_summary.start_depth is not None else start_depth
        resolved_stop = source_summary.stop_depth if source_summary.stop_depth is not None else stop_depth
        resolved_step = source_summary.step if source_summary.step is not None else step
    elif creation_mode in {LasCreationMode.FROM_CSV, LasCreationMode.FROM_EXCEL} and source_dataframe is not None:
        source_summary = summarize_tabular_source(source_dataframe, source_type=creation_mode.value)
        selected_template = "empty"
        selected_curves.extend(source_summary.curves)
        resolved_start = source_summary.start_depth if source_summary.start_depth is not None else start_depth
        resolved_stop = source_summary.stop_depth if source_summary.stop_depth is not None else stop_depth
        resolved_step = source_summary.step if source_summary.step is not None else step
    elif creation_mode == LasCreationMode.EMPTY:
        selected_template = "empty"
    elif creation_mode == LasCreationMode.MANUAL:
        selected_template = "empty"

    spec = build_las_creation_spec(
        well_name=resolved_well_name,
        start_depth=resolved_start,
        stop_depth=resolved_stop,
        step=resolved_step,
        template_name=selected_template,
        curves=selected_curves,
        las_version=las_version,
        depth_unit=depth_unit,
        null_value=null_value,
        uwi=uwi,
        api=api,
        company=company,
        field=field,
        location=location,
        service_company=service_company,
    )
    issues = _safe_validate_creation(spec)
    return LasCreationWizardDraft(
        schema=LAS_CREATION_WIZARD_SCHEMA,
        mode=creation_mode,
        spec=spec,
        source_summary=source_summary,
        steps=_wizard_steps(spec, issues),
        source_object_id=source_object_id,
        target_well_id=target_well_id,
        filename=filename or build_safe_las_filename(spec.well_name, suffix="created"),
    )


def build_las_creation_wizard_preview_v2(draft: LasCreationWizardDraft) -> LasCreationWizardPreviewV2:
    """Create a safe preview for LAS Creation Wizard 2.0."""

    data = _safe_dataframe(draft.spec)
    las_text = _safe_las_text(draft.spec, data)
    issues = _safe_validate_creation(draft.spec, data, las_text)
    errors = [issue for issue in issues if issue.severity == "error"]
    journal = build_operation_entry(
        operation_type="las_creation_wizard",
        title="Создание нового LAS",
        source_object_id=draft.source_object_id,
        result_object_id=draft.filename,
        status=OperationStatus.PREVIEW,
        creates_copy=True,
        can_undo=False,
        summary="Предпросмотр нового LAS. Существующие LAS-файлы не изменяются.",
        details={
            "mode": draft.mode.value,
            "well_name": draft.spec.well_name,
            "row_count": int(len(data)),
            "curve_count": int(len(data.columns)),
            "filename": draft.filename,
        },
    )

    table_rows = (
        {"property": "Mode", "value": draft.mode.value},
        {"property": "Well", "value": draft.spec.well_name},
        {"property": "LAS Version", "value": draft.spec.las_version},
        {"property": "Depth", "value": f"{draft.spec.start_depth:g} - {draft.spec.stop_depth:g} {draft.spec.depth_unit}"},
        {"property": "Step", "value": f"{draft.spec.step:g} {draft.spec.depth_unit}"},
        {"property": "Rows", "value": len(data)},
        {"property": "Curves", "value": len(data.columns)},
        {"property": "Output", "value": draft.filename},
    )
    curve_rows = tuple(
        {"mnemonic": column, "unit": data.attrs.get("las_units", {}).get(column, ""), "source": "depth" if column == "DEPT" else draft.mode.value}
        for column in data.columns
    )
    return LasCreationWizardPreviewV2(
        draft=draft,
        data=data,
        las_text=las_text,
        issues=issues,
        journal_entry=journal,
        table_rows=table_rows,
        curve_rows=curve_rows,
        can_finalize=not errors,
    )


def finalize_las_creation_wizard(draft: LasCreationWizardDraft) -> LasCreationWizardFinalizeResult:
    """Finalize a confirmed wizard draft into a new LAS document."""

    preview = build_las_creation_wizard_preview_v2(draft)
    if not preview.can_finalize:
        error_text = "; ".join(issue.message for issue in preview.issues if issue.severity == "error")
        raise ValueError(f"LAS cannot be created until validation errors are fixed: {error_text}")

    result = create_las_document(draft.spec)
    completed = build_operation_entry(
        operation_type="las_creation_wizard",
        title="Создание нового LAS",
        source_object_id=draft.source_object_id,
        result_object_id=draft.filename,
        status=OperationStatus.COMPLETED,
        creates_copy=True,
        can_undo=True,
        summary="Создан новый LAS-файл. Исходные файлы не изменялись.",
        details={
            "mode": draft.mode.value,
            "well_name": draft.spec.well_name,
            "filename": draft.filename,
            "row_count": int(len(result.data)),
            "curve_count": int(len(result.data.columns)),
        },
    )
    return LasCreationWizardFinalizeResult(
        result=result,
        filename=draft.filename,
        las_bytes=result.las_bytes,
        journal_entry=completed,
        preview=preview,
    )


def wizard_step_rows(draft: LasCreationWizardDraft) -> list[dict[str, Any]]:
    """Return UI-ready rows for progress/stepper components."""

    return [
        {
            "step_id": step.step_id,
            "title": step.title,
            "description": step.description,
            "required": step.required,
            "completed": step.completed,
            "issue_count": step.issue_count,
        }
        for step in draft.steps
    ]


def wizard_issue_rows(issues: Iterable[LasValidationIssue]) -> list[dict[str, str]]:
    """Return UI-ready validation issue rows."""

    return [{"severity": issue.severity, "code": issue.code, "message": issue.message} for issue in issues]

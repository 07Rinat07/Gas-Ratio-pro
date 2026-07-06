from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from projects.batch_processing import BATCH_OPERATION_TYPES
from projects.project_manager import append_project_history
from projects.repository import safe_project_id
from projects.well_cards import safe_well_id

PROJECT_TEMPLATE_WORKFLOW_FILE_NAME = "template_workflows.json"
WORKFLOW_STEP_TYPES = {
    "import_las",
    "reverse_depth",
    "sort_depth",
    "remove_duplicate_depths",
    "resample",
    "shift_depth",
    "crop_interval",
    "rename_curves",
    "apply_aliases",
    "normalize_units",
    "validate_las",
    "formula_builder",
    "calculate_vsh",
    "calculate_phie",
    "calculate_sw",
    "calculate_perm",
    "calculate_net_pay",
    "data_quality_report",
    "generate_report",
    "export_las",
    "export_results",
    "batch_processing",
} | set(BATCH_OPERATION_TYPES)
WORKFLOW_RUN_STATUSES = {"queued", "running", "done", "failed", "cancelled", "paused"}
WORKFLOW_CATEGORIES = {"las", "depth", "petrophysics", "quality", "reporting", "batch", "custom"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workflow_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_TEMPLATE_WORKFLOW_FILE_NAME


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


def _payload(root: Path | str, project_id: str) -> dict[str, Any]:
    payload = _json_read(_workflow_path(root, project_id), {"templates": [], "runs": []})
    if not isinstance(payload, dict):
        payload = {"templates": [], "runs": []}
    payload.setdefault("templates", [])
    payload.setdefault("runs", [])
    return payload


def _clean_text(value: Any, field_label: str = "value", *, max_length: int = 220, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_id(value: str, default: str = "workflow") -> str:
    raw = _clean_text(value, "ID", max_length=160) or default
    normalized = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", raw).strip("-_").lower() or default
    return safe_well_id(normalized)


def _clean_category(value: Any) -> str:
    text = _clean_text(value, "Категория", max_length=60).lower() or "custom"
    return text if text in WORKFLOW_CATEGORIES else "custom"


@dataclass(frozen=True)
class WorkflowStep:
    id: str
    type: str
    name: str = ""
    parameters: Mapping[str, Any] = field(default_factory=dict)
    enabled: bool = True
    order: int = 0
    stop_on_error: bool = True


@dataclass(frozen=True)
class WorkflowTemplate:
    id: str
    name: str
    description: str = ""
    category: str = "custom"
    steps: tuple[WorkflowStep, ...] = ()
    favorite: bool = False
    version: int = 1
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class WorkflowRunLog:
    id: str
    template_id: str
    status: str
    message: str = ""
    current_step_id: str = ""
    completed_steps: int = 0
    total_steps: int = 0
    progress: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowValidationIssue:
    severity: str
    code: str
    message: str
    step_id: str = ""
    recommendation: str = ""


@dataclass(frozen=True)
class WorkflowSummary:
    templates: int
    favorites: int
    steps: int
    categories: tuple[str, ...]
    runs: int
    failed_runs: int


def normalize_workflow_step(step: WorkflowStep | Mapping[str, Any], index: int = 0) -> WorkflowStep:
    if isinstance(step, WorkflowStep):
        item = step
    elif isinstance(step, Mapping):
        raw_type = _clean_text(step.get("type"), "Тип шага", max_length=80, required=True).lower()
        item = WorkflowStep(
            id=_safe_id(str(step.get("id") or step.get("name") or raw_type or f"step-{index + 1}"), "step"),
            type=raw_type,
            name=_clean_text(step.get("name"), "Название шага", max_length=140) or raw_type.replace("_", " ").title(),
            parameters=step.get("parameters", {}) if isinstance(step.get("parameters", {}), Mapping) else {},
            enabled=bool(step.get("enabled", True)),
            order=int(step.get("order") or 0),
            stop_on_error=bool(step.get("stop_on_error", True)),
        )
    else:
        raise TypeError("Шаг workflow должен быть WorkflowStep или mapping.")
    if item.type not in WORKFLOW_STEP_TYPES:
        raise ValueError(f"Неизвестный тип шага workflow: {item.type}.")
    order = item.order if item.order else (index + 1) * 10
    name = item.name or item.type.replace("_", " ").title()
    return WorkflowStep(
        id=_safe_id(item.id or f"{item.type}-{index + 1}", "step"),
        type=item.type,
        name=_clean_text(name, "Название шага", max_length=140, required=True),
        parameters=dict(item.parameters),
        enabled=bool(item.enabled),
        order=int(order),
        stop_on_error=bool(item.stop_on_error),
    )


def normalize_workflow_steps(steps: Sequence[WorkflowStep | Mapping[str, Any]] | None) -> tuple[WorkflowStep, ...]:
    result = [normalize_workflow_step(step, index) for index, step in enumerate(steps or default_las_cleanup_steps())]
    seen: set[str] = set()
    unique: list[WorkflowStep] = []
    for step in sorted(result, key=lambda row: (row.order, row.id)):
        step_id = step.id
        if step_id in seen:
            step_id = _safe_id(f"{step.id}-{len(seen) + 1}", "step")
            step = WorkflowStep(**{**step.__dict__, "id": step_id})
        seen.add(step_id)
        unique.append(step)
    return tuple(unique)


def default_las_cleanup_steps() -> tuple[WorkflowStep, ...]:
    return (
        WorkflowStep("validate-input", "validate_las", "Проверить LAS", order=10),
        WorkflowStep("sort-depth", "sort_depth", "Отсортировать глубину", order=20),
        WorkflowStep("remove-duplicates", "remove_duplicate_depths", "Удалить дубликаты глубин", order=30),
        WorkflowStep("apply-aliases", "apply_aliases", "Применить словарь Alias", order=40, stop_on_error=False),
        WorkflowStep("validate-output", "validate_las", "Проверить результат", {"stage": "after_cleanup"}, order=90),
    )


def default_petrophysics_steps() -> tuple[WorkflowStep, ...]:
    return (
        WorkflowStep("validate-input", "validate_las", "Проверить LAS", order=10),
        WorkflowStep("calculate-vsh", "calculate_vsh", "Рассчитать VSH", order=20),
        WorkflowStep("calculate-phie", "calculate_phie", "Рассчитать PHIE", order=30),
        WorkflowStep("calculate-sw", "calculate_sw", "Рассчитать SW", order=40),
        WorkflowStep("calculate-net-pay", "calculate_net_pay", "Рассчитать Net Pay", order=50),
        WorkflowStep("export-las", "export_las", "Экспортировать LAS", {"suffix": "interpretation"}, order=80),
        WorkflowStep("generate-report", "generate_report", "Сформировать отчет", {"formats": ["pdf", "xlsx", "json"]}, order=90, stop_on_error=False),
    )


def default_quality_control_steps() -> tuple[WorkflowStep, ...]:
    return (
        WorkflowStep("validate-las", "validate_las", "Проверить LAS", order=10),
        WorkflowStep("quality-report", "data_quality_report", "Сформировать отчет качества", {"formats": ["html", "json"]}, order=20),
        WorkflowStep("export-results", "export_results", "Экспортировать результаты", order=90),
    )


def builtin_workflow_templates() -> tuple[WorkflowTemplate, ...]:
    now = _utc_now()
    return (
        WorkflowTemplate(
            id="las-cleanup",
            name="Standard LAS Cleanup",
            description="Очистка глубины, дубликатов и alias-кривых перед интерпретацией.",
            category="las",
            steps=default_las_cleanup_steps(),
            favorite=True,
            created_at=now,
            updated_at=now,
        ),
        WorkflowTemplate(
            id="standard-petrophysics",
            name="Complete Petrophysical Interpretation",
            description="Базовый сценарий расчета VSH, PHIE, SW, Net Pay и экспорта результата.",
            category="petrophysics",
            steps=default_petrophysics_steps(),
            favorite=True,
            created_at=now,
            updated_at=now,
        ),
        WorkflowTemplate(
            id="quality-control",
            name="Quality Control",
            description="Проверка качества LAS и формирование QC-отчета.",
            category="quality",
            steps=default_quality_control_steps(),
            created_at=now,
            updated_at=now,
        ),
    )


def _step_to_dict(step: WorkflowStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "type": step.type,
        "name": step.name,
        "parameters": dict(step.parameters),
        "enabled": step.enabled,
        "order": step.order,
        "stop_on_error": step.stop_on_error,
    }


def _step_from_dict(row: Mapping[str, Any], index: int = 0) -> WorkflowStep:
    return normalize_workflow_step(row, index)


def _template_to_dict(template: WorkflowTemplate) -> dict[str, Any]:
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "steps": [_step_to_dict(step) for step in template.steps],
        "favorite": template.favorite,
        "version": template.version,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


def _template_from_dict(row: Mapping[str, Any]) -> WorkflowTemplate:
    return WorkflowTemplate(
        id=_safe_id(str(row.get("id") or row.get("name") or "workflow"), "workflow"),
        name=_clean_text(row.get("name"), "Название workflow", required=True),
        description=_clean_text(row.get("description"), "Описание", max_length=1000),
        category=_clean_category(row.get("category")),
        steps=normalize_workflow_steps(row.get("steps") if isinstance(row.get("steps"), Sequence) else None),
        favorite=bool(row.get("favorite", False)),
        version=max(1, int(row.get("version") or 1)),
        created_at=_clean_text(row.get("created_at"), "Дата создания", max_length=80) or _utc_now(),
        updated_at=_clean_text(row.get("updated_at"), "Дата изменения", max_length=80) or _utc_now(),
    )


def _run_to_dict(run: WorkflowRunLog) -> dict[str, Any]:
    return {**run.__dict__, "errors": list(run.errors)}


def _run_from_dict(row: Mapping[str, Any]) -> WorkflowRunLog:
    status = _clean_text(row.get("status"), "Статус", max_length=40).lower() or "queued"
    if status not in WORKFLOW_RUN_STATUSES:
        status = "failed"
    return WorkflowRunLog(
        id=_clean_text(row.get("id"), "ID запуска", required=True),
        template_id=_clean_text(row.get("template_id"), "ID workflow", required=True),
        status=status,
        message=_clean_text(row.get("message"), "Сообщение", max_length=800),
        current_step_id=_clean_text(row.get("current_step_id"), "Текущий шаг", max_length=160),
        completed_steps=int(row.get("completed_steps") or 0),
        total_steps=int(row.get("total_steps") or 0),
        progress=float(row.get("progress") or 0.0),
        created_at=_clean_text(row.get("created_at"), "Дата создания", max_length=80) or _utc_now(),
        updated_at=_clean_text(row.get("updated_at"), "Дата изменения", max_length=80) or _utc_now(),
        errors=tuple(str(item) for item in row.get("errors", []) if str(item).strip()) if isinstance(row.get("errors", []), Sequence) else (),
    )


def create_workflow_template(
    root: Path | str,
    project_id: str,
    name: str,
    *,
    steps: Sequence[WorkflowStep | Mapping[str, Any]] | None = None,
    description: str = "",
    category: str = "custom",
    favorite: bool = False,
) -> WorkflowTemplate:
    now = _utc_now()
    clean_name = _clean_text(name, "Название workflow", required=True)
    template = WorkflowTemplate(
        id=_safe_id(f"{clean_name}-{now}", "workflow"),
        name=clean_name,
        description=_clean_text(description, "Описание", max_length=1000),
        category=_clean_category(category),
        steps=normalize_workflow_steps(steps),
        favorite=bool(favorite),
        created_at=now,
        updated_at=now,
    )
    payload = _payload(root, project_id)
    templates = payload.get("templates", [])
    templates.append(_template_to_dict(template))
    _json_write(_workflow_path(root, project_id), {**payload, "templates": templates})
    append_project_history(root, project_id, "workflow_template_created", f"Создан workflow {clean_name}", object_type="workflow", object_id=template.id)
    return template


def list_workflow_templates(root: Path | str, project_id: str, *, include_builtin: bool = True) -> list[WorkflowTemplate]:
    payload = _payload(root, project_id)
    stored = [_template_from_dict(row) for row in payload.get("templates", []) if isinstance(row, Mapping)]
    if include_builtin:
        stored_ids = {item.id for item in stored}
        return [item for item in builtin_workflow_templates() if item.id not in stored_ids] + stored
    return stored


def get_workflow_template(root: Path | str, project_id: str, template_id: str, *, include_builtin: bool = True) -> WorkflowTemplate | None:
    target = _safe_id(template_id, "workflow")
    return next((item for item in list_workflow_templates(root, project_id, include_builtin=include_builtin) if item.id == target), None)


def clone_workflow_template(root: Path | str, project_id: str, template_id: str, *, new_name: str | None = None) -> WorkflowTemplate:
    source = get_workflow_template(root, project_id, template_id)
    if source is None:
        raise ValueError("Workflow не найден.")
    return create_workflow_template(
        root,
        project_id,
        new_name or f"{source.name} Copy",
        steps=source.steps,
        description=source.description,
        category=source.category,
        favorite=source.favorite,
    )


def set_workflow_favorite(root: Path | str, project_id: str, template_id: str, favorite: bool = True) -> WorkflowTemplate:
    payload = _payload(root, project_id)
    target = _safe_id(template_id, "workflow")
    rows = payload.get("templates", [])
    for index, row in enumerate(rows):
        if isinstance(row, Mapping) and _safe_id(str(row.get("id") or ""), "workflow") == target:
            updated = {**row, "favorite": bool(favorite), "updated_at": _utc_now()}
            rows[index] = updated
            _json_write(_workflow_path(root, project_id), {**payload, "templates": rows})
            return _template_from_dict(updated)
    builtin = get_workflow_template(root, project_id, target, include_builtin=True)
    if builtin is None:
        raise ValueError("Workflow не найден.")
    cloned = create_workflow_template(root, project_id, builtin.name, steps=builtin.steps, description=builtin.description, category=builtin.category, favorite=favorite)
    return cloned


def export_workflow_template(template: WorkflowTemplate) -> str:
    return json.dumps({"schema": "gas-ratio-pro.workflow.v1", "template": _template_to_dict(template)}, ensure_ascii=False, indent=2)


def import_workflow_template(root: Path | str, project_id: str, payload_json: str) -> WorkflowTemplate:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Некорректный JSON workflow.") from exc
    raw_template = payload.get("template") if isinstance(payload, Mapping) else None
    if not isinstance(raw_template, Mapping):
        raise ValueError("JSON не содержит объект template.")
    template = _template_from_dict(raw_template)
    return create_workflow_template(
        root,
        project_id,
        template.name,
        steps=template.steps,
        description=template.description,
        category=template.category,
        favorite=template.favorite,
    )


def validate_workflow_template(template: WorkflowTemplate | Mapping[str, Any], *, available_inputs: Iterable[str] | None = None) -> list[WorkflowValidationIssue]:
    if not isinstance(template, WorkflowTemplate):
        template = _template_from_dict(template)
    issues: list[WorkflowValidationIssue] = []
    enabled_steps = [step for step in template.steps if step.enabled]
    if not enabled_steps:
        issues.append(WorkflowValidationIssue("error", "NO_ENABLED_STEPS", "В workflow нет активных шагов.", recommendation="Включите хотя бы один шаг."))
    seen_outputs: set[str] = set(str(item).lower() for item in (available_inputs or []))
    seen_step_types: set[str] = set()
    for step in enabled_steps:
        seen_step_types.add(step.type)
        params = dict(step.parameters)
        if step.type == "resample" and float(params.get("step", params.get("target_step", 0)) or 0) <= 0:
            issues.append(WorkflowValidationIssue("error", "INVALID_RESAMPLE_STEP", "Шаг Resample требует положительный шаг дискретизации.", step.id, "Укажите step > 0."))
        if step.type == "shift_depth" and "shift" not in params and "offset" not in params:
            issues.append(WorkflowValidationIssue("warning", "MISSING_DEPTH_SHIFT", "Шаг Shift Depth не содержит величину смещения.", step.id, "Укажите shift или offset."))
        if step.type in {"calculate_vsh", "calculate_phie", "calculate_sw", "calculate_perm", "calculate_net_pay"} and "validate_las" not in seen_step_types:
            issues.append(WorkflowValidationIssue("warning", "MISSING_PRE_VALIDATION", "Расчет выполняется без предварительной проверки LAS.", step.id, "Добавьте validate_las перед расчетами."))
        if step.type in {"export_las", "export_results", "generate_report"} and not params.get("output_dir"):
            issues.append(WorkflowValidationIssue("info", "OUTPUT_DIR_NOT_SET", "Выходной каталог не задан явно.", step.id, "Будет использован каталог проекта по умолчанию."))
        seen_outputs.add(step.type)
    return issues


def start_workflow_run(root: Path | str, project_id: str, template_id: str, *, message: str = "") -> WorkflowRunLog:
    template = get_workflow_template(root, project_id, template_id)
    if template is None:
        raise ValueError("Workflow не найден.")
    enabled_steps = [step for step in template.steps if step.enabled]
    now = _utc_now()
    run = WorkflowRunLog(
        id=f"run-{now.replace(':', '').replace('-', '')}-{_safe_id(template.id)}",
        template_id=template.id,
        status="queued",
        message=_clean_text(message, "Сообщение", max_length=800) or "Workflow поставлен в очередь.",
        current_step_id=enabled_steps[0].id if enabled_steps else "",
        completed_steps=0,
        total_steps=len(enabled_steps),
        progress=0.0,
        created_at=now,
        updated_at=now,
    )
    payload = _payload(root, project_id)
    runs = payload.get("runs", [])
    runs.append(_run_to_dict(run))
    _json_write(_workflow_path(root, project_id), {**payload, "runs": runs})
    append_project_history(root, project_id, "workflow_run_started", f"Запущен workflow {template.name}", object_type="workflow", object_id=template.id)
    return run


def update_workflow_run(root: Path | str, project_id: str, run_id: str, status: str, *, current_step_id: str = "", completed_steps: int | None = None, errors: Sequence[str] | None = None, message: str = "") -> WorkflowRunLog:
    normalized_status = _clean_text(status, "Статус", max_length=40).lower()
    if normalized_status not in WORKFLOW_RUN_STATUSES:
        raise ValueError(f"Недопустимый статус workflow: {status}.")
    payload = _payload(root, project_id)
    rows = payload.get("runs", [])
    target = _clean_text(run_id, "ID запуска", required=True)
    for index, row in enumerate(rows):
        if isinstance(row, Mapping) and row.get("id") == target:
            previous = _run_from_dict(row)
            completed = previous.completed_steps if completed_steps is None else max(0, int(completed_steps))
            total = max(0, previous.total_steps)
            progress = 100.0 if normalized_status == "done" else (round((completed / total) * 100, 2) if total else 0.0)
            updated = WorkflowRunLog(
                id=previous.id,
                template_id=previous.template_id,
                status=normalized_status,
                message=_clean_text(message, "Сообщение", max_length=800) or previous.message,
                current_step_id=_clean_text(current_step_id, "Текущий шаг", max_length=160) or previous.current_step_id,
                completed_steps=completed,
                total_steps=total,
                progress=progress,
                created_at=previous.created_at,
                updated_at=_utc_now(),
                errors=tuple(errors or previous.errors),
            )
            rows[index] = _run_to_dict(updated)
            _json_write(_workflow_path(root, project_id), {**payload, "runs": rows})
            return updated
    raise ValueError("Запуск workflow не найден.")


def simulate_workflow_execution(root: Path | str, project_id: str, template_id: str) -> WorkflowRunLog:
    template = get_workflow_template(root, project_id, template_id)
    if template is None:
        raise ValueError("Workflow не найден.")
    issues = validate_workflow_template(template)
    blocking = [issue for issue in issues if issue.severity in {"error", "critical"}]
    run = start_workflow_run(root, project_id, template.id)
    if blocking:
        return update_workflow_run(root, project_id, run.id, "failed", errors=[issue.message for issue in blocking], message="Workflow не прошел валидацию.")
    enabled = [step for step in template.steps if step.enabled]
    current_step = enabled[-1].id if enabled else ""
    return update_workflow_run(root, project_id, run.id, "done", current_step_id=current_step, completed_steps=len(enabled), message="Workflow выполнен в режиме планирования.")


def list_workflow_runs(root: Path | str, project_id: str, *, template_id: str | None = None) -> list[WorkflowRunLog]:
    rows = [_run_from_dict(row) for row in _payload(root, project_id).get("runs", []) if isinstance(row, Mapping)]
    if template_id:
        target = _safe_id(template_id, "workflow")
        rows = [run for run in rows if run.template_id == target]
    return sorted(rows, key=lambda row: row.created_at, reverse=True)


def summarize_workflows(templates: Sequence[WorkflowTemplate], runs: Sequence[WorkflowRunLog] | None = None) -> WorkflowSummary:
    categories = tuple(sorted({template.category for template in templates}))
    runs = tuple(runs or ())
    return WorkflowSummary(
        templates=len(templates),
        favorites=sum(1 for template in templates if template.favorite),
        steps=sum(len(template.steps) for template in templates),
        categories=categories,
        runs=len(runs),
        failed_runs=sum(1 for run in runs if run.status == "failed"),
    )


def build_workflow_template_table(templates: Sequence[WorkflowTemplate]) -> list[dict[str, Any]]:
    return [
        {
            "Название": template.name,
            "Категория": template.category,
            "Шагов": len(template.steps),
            "Избранное": "Да" if template.favorite else "Нет",
            "Версия": template.version,
            "Обновлено": template.updated_at,
        }
        for template in templates
    ]


def build_workflow_step_table(steps: Sequence[WorkflowStep]) -> list[dict[str, Any]]:
    return [
        {
            "Порядок": step.order,
            "Шаг": step.name,
            "Тип": step.type,
            "Активен": "Да" if step.enabled else "Нет",
            "Останов при ошибке": "Да" if step.stop_on_error else "Нет",
            "Параметров": len(step.parameters),
        }
        for step in sorted(steps, key=lambda row: (row.order, row.id))
    ]


def build_workflow_issue_table(issues: Sequence[WorkflowValidationIssue]) -> list[dict[str, Any]]:
    return [
        {
            "Severity": issue.severity,
            "Code": issue.code,
            "Шаг": issue.step_id,
            "Сообщение": issue.message,
            "Рекомендация": issue.recommendation,
        }
        for issue in issues
    ]


def build_workflow_run_table(runs: Sequence[WorkflowRunLog]) -> list[dict[str, Any]]:
    return [
        {
            "Workflow": run.template_id,
            "Статус": run.status,
            "Прогресс": run.progress,
            "Шаги": f"{run.completed_steps}/{run.total_steps}",
            "Сообщение": run.message,
            "Обновлено": run.updated_at,
        }
        for run in runs
    ]


def workflow_to_batch_operations(template: WorkflowTemplate) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for step in template.steps:
        if step.enabled and step.type in BATCH_OPERATION_TYPES:
            operations.append({"type": step.type, "parameters": dict(step.parameters), "enabled": True, "order": step.order})
    return operations

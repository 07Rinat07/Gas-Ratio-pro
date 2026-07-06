from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from projects.project_manager import append_project_history
from projects.repository import safe_project_id
from projects.well_cards import safe_well_id

PROJECT_BATCH_PROCESSING_FILE_NAME = "batch_processing.json"
BATCH_TASK_STATUSES = {"queued", "running", "paused", "done", "failed", "cancelled"}
BATCH_OPERATION_TYPES = {
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
    "calculate_vsh",
    "calculate_phie",
    "calculate_sw",
    "calculate_perm",
    "calculate_net_pay",
    "export_las",
    "export_report",
    "export_json_log",
}
BATCH_EXPORT_FORMATS = {"las", "pdf", "docx", "xlsx", "html", "json", "zip"}
BATCH_IMPORT_EXTENSIONS = {".las", ".LAS"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _batch_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_BATCH_PROCESSING_FILE_NAME


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


def _clean_text(value: Any, field_label: str = "value", *, max_length: int = 220, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_id(value: str, default: str = "batch") -> str:
    raw = _clean_text(value, "ID", max_length=160) or default
    normalized = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", raw).strip("-_").lower() or default
    return safe_well_id(normalized)


def _payload(root: Path | str, project_id: str) -> dict[str, Any]:
    payload = _json_read(_batch_path(root, project_id), {"tasks": [], "runs": [], "presets": []})
    if not isinstance(payload, dict):
        payload = {"tasks": [], "runs": [], "presets": []}
    payload.setdefault("tasks", [])
    payload.setdefault("runs", [])
    payload.setdefault("presets", [])
    return payload


@dataclass(frozen=True)
class BatchOperation:
    type: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    enabled: bool = True
    order: int = 0


@dataclass(frozen=True)
class BatchTask:
    id: str
    name: str
    source_path: str
    well_id: str = ""
    status: str = "queued"
    operations: tuple[BatchOperation, ...] = ()
    priority: int = 100
    progress: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    error: str = ""
    output_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class BatchPreset:
    id: str
    name: str
    operations: tuple[BatchOperation, ...]
    description: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class BatchRunLog:
    id: str
    task_id: str
    operation_type: str
    status: str
    message: str = ""
    created_at: str = ""
    duration_seconds: float | None = None


@dataclass(frozen=True)
class BatchQueueSummary:
    tasks: int
    queued: int
    running: int
    done: int
    failed: int
    cancelled: int
    progress: float
    estimated_operations: int


@dataclass(frozen=True)
class BatchValidationIssue:
    severity: str
    code: str
    message: str
    task_id: str = ""
    recommendation: str = ""


def normalize_batch_operation(operation: BatchOperation | Mapping[str, Any]) -> BatchOperation:
    if isinstance(operation, BatchOperation):
        item = operation
    elif isinstance(operation, Mapping):
        item = BatchOperation(
            type=_clean_text(operation.get("type"), "Тип операции", max_length=80, required=True).lower(),
            parameters=operation.get("parameters", {}) if isinstance(operation.get("parameters", {}), Mapping) else {},
            enabled=bool(operation.get("enabled", True)),
            order=int(operation.get("order", 0) or 0),
        )
    else:
        raise TypeError("Операция должна быть BatchOperation или mapping.")
    if item.type not in BATCH_OPERATION_TYPES:
        raise ValueError(f"Неизвестная batch-операция: {item.type}.")
    return item


def normalize_batch_operations(operations: Sequence[BatchOperation | Mapping[str, Any]] | None) -> tuple[BatchOperation, ...]:
    result: list[BatchOperation] = []
    for index, operation in enumerate(operations or default_las_batch_operations()):
        item = normalize_batch_operation(operation)
        order = item.order if item.order else (index + 1) * 10
        result.append(BatchOperation(type=item.type, parameters=dict(item.parameters), enabled=item.enabled, order=int(order)))
    return tuple(sorted(result, key=lambda row: (row.order, row.type)))


def default_las_batch_operations() -> tuple[BatchOperation, ...]:
    return (
        BatchOperation("validate_las", order=10),
        BatchOperation("sort_depth", order=20),
        BatchOperation("remove_duplicate_depths", order=30),
        BatchOperation("validate_las", {"stage": "after_depth_cleanup"}, order=90),
    )


def default_petrophysics_batch_operations() -> tuple[BatchOperation, ...]:
    return (
        BatchOperation("validate_las", order=10),
        BatchOperation("calculate_vsh", order=20),
        BatchOperation("calculate_phie", order=30),
        BatchOperation("calculate_sw", order=40),
        BatchOperation("calculate_perm", order=50),
        BatchOperation("calculate_net_pay", order=60),
        BatchOperation("export_las", {"suffix": "interpretation"}, order=80),
        BatchOperation("export_report", {"formats": ["pdf", "xlsx", "json"]}, order=90),
    )


def _operation_to_dict(operation: BatchOperation) -> dict[str, Any]:
    return {
        "type": operation.type,
        "parameters": dict(operation.parameters),
        "enabled": operation.enabled,
        "order": operation.order,
    }


def _operation_from_dict(row: Mapping[str, Any]) -> BatchOperation:
    return normalize_batch_operation(row)


def _task_to_dict(task: BatchTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "name": task.name,
        "source_path": task.source_path,
        "well_id": task.well_id,
        "status": task.status,
        "operations": [_operation_to_dict(item) for item in task.operations],
        "priority": task.priority,
        "progress": task.progress,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "error": task.error,
        "output_paths": list(task.output_paths),
    }


def _task_from_dict(row: Mapping[str, Any]) -> BatchTask:
    return BatchTask(
        id=_clean_text(row.get("id"), "ID задачи", required=True),
        name=_clean_text(row.get("name"), "Название задачи", required=True),
        source_path=_clean_text(row.get("source_path"), "Файл", required=True, max_length=500),
        well_id=_clean_text(row.get("well_id"), "Скважина", max_length=160),
        status=_clean_status(row.get("status", "queued")),
        operations=normalize_batch_operations(row.get("operations", [])),
        priority=int(row.get("priority", 100) or 100),
        progress=_bounded_progress(row.get("progress", 0.0)),
        created_at=_clean_text(row.get("created_at"), "Дата", max_length=80),
        updated_at=_clean_text(row.get("updated_at"), "Дата", max_length=80),
        error=_clean_text(row.get("error"), "Ошибка", max_length=1000),
        output_paths=tuple(str(item) for item in row.get("output_paths", []) if str(item).strip()),
    )


def _preset_to_dict(preset: BatchPreset) -> dict[str, Any]:
    return {
        "id": preset.id,
        "name": preset.name,
        "description": preset.description,
        "operations": [_operation_to_dict(item) for item in preset.operations],
        "created_at": preset.created_at,
        "updated_at": preset.updated_at,
    }


def _preset_from_dict(row: Mapping[str, Any]) -> BatchPreset:
    return BatchPreset(
        id=_clean_text(row.get("id"), "ID пресета", required=True),
        name=_clean_text(row.get("name"), "Название пресета", required=True),
        description=_clean_text(row.get("description"), "Описание", max_length=500),
        operations=normalize_batch_operations(row.get("operations", [])),
        created_at=_clean_text(row.get("created_at"), "Дата", max_length=80),
        updated_at=_clean_text(row.get("updated_at"), "Дата", max_length=80),
    )


def _run_to_dict(run: BatchRunLog) -> dict[str, Any]:
    return {
        "id": run.id,
        "task_id": run.task_id,
        "operation_type": run.operation_type,
        "status": run.status,
        "message": run.message,
        "created_at": run.created_at,
        "duration_seconds": run.duration_seconds,
    }


def _run_from_dict(row: Mapping[str, Any]) -> BatchRunLog:
    return BatchRunLog(
        id=_clean_text(row.get("id"), "ID журнала", required=True),
        task_id=_clean_text(row.get("task_id"), "ID задачи", required=True),
        operation_type=_clean_text(row.get("operation_type"), "Операция", required=True),
        status=_clean_status(row.get("status", "queued")),
        message=_clean_text(row.get("message"), "Сообщение", max_length=1000),
        created_at=_clean_text(row.get("created_at"), "Дата", max_length=80),
        duration_seconds=float(row["duration_seconds"]) if row.get("duration_seconds") is not None else None,
    )


def _clean_status(value: Any) -> str:
    status = _clean_text(value, "Статус", max_length=40).lower() or "queued"
    if status not in BATCH_TASK_STATUSES:
        raise ValueError(f"Статус batch-задачи должен быть одним из: {', '.join(sorted(BATCH_TASK_STATUSES))}.")
    return status


def _bounded_progress(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, min(100.0, number)), 2)


def list_batch_tasks(root: Path | str, project_id: str, *, statuses: Iterable[str] | None = None) -> tuple[BatchTask, ...]:
    allowed = set(statuses or [])
    if allowed:
        allowed = {_clean_status(item) for item in allowed}
    rows = _payload(root, project_id).get("tasks", [])
    tasks = tuple(_task_from_dict(item) for item in rows if isinstance(item, Mapping))
    if allowed:
        tasks = tuple(item for item in tasks if item.status in allowed)
    return tuple(sorted(tasks, key=lambda row: (row.priority, row.created_at, row.name.lower())))


def add_batch_task(
    root: Path | str,
    project_id: str,
    source_path: str | Path,
    *,
    name: str | None = None,
    well_id: str = "",
    operations: Sequence[BatchOperation | Mapping[str, Any]] | None = None,
    priority: int = 100,
) -> BatchTask:
    source = _clean_text(str(source_path), "Файл LAS", max_length=500, required=True)
    source_name = name or Path(source).stem or "Batch task"
    now = _utc_now()
    task = BatchTask(
        id=_safe_id(f"{source_name}-{now}", "batch-task"),
        name=_clean_text(source_name, "Название задачи", required=True),
        source_path=source,
        well_id=_clean_text(well_id, "Скважина", max_length=160),
        status="queued",
        operations=normalize_batch_operations(operations),
        priority=int(priority),
        progress=0.0,
        created_at=now,
        updated_at=now,
    )
    payload = _payload(root, project_id)
    tasks = [item for item in payload.get("tasks", []) if isinstance(item, Mapping) and item.get("id") != task.id]
    tasks.append(_task_to_dict(task))
    payload["tasks"] = tasks
    _json_write(_batch_path(root, project_id), payload)
    append_project_history(root, project_id, "batch_task_added", f"Добавлена batch-задача {task.name}", object_type="batch_task", object_id=task.id)
    return task


def add_batch_tasks_from_paths(
    root: Path | str,
    project_id: str,
    paths: Iterable[str | Path],
    *,
    operations: Sequence[BatchOperation | Mapping[str, Any]] | None = None,
) -> tuple[BatchTask, ...]:
    tasks: list[BatchTask] = []
    for index, path in enumerate(paths):
        if str(path).strip():
            tasks.append(add_batch_task(root, project_id, path, operations=operations, priority=100 + index))
    return tuple(tasks)


def discover_las_files(paths: Iterable[str | Path], *, recursive: bool = True) -> tuple[str, ...]:
    discovered: list[str] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.suffix in BATCH_IMPORT_EXTENSIONS:
            discovered.append(str(path))
        elif path.is_dir():
            pattern = "**/*.las" if recursive else "*.las"
            discovered.extend(str(item) for item in sorted(path.glob(pattern)) if item.is_file())
            pattern_upper = "**/*.LAS" if recursive else "*.LAS"
            discovered.extend(str(item) for item in sorted(path.glob(pattern_upper)) if item.is_file())
    return tuple(dict.fromkeys(discovered))


def update_batch_task_status(
    root: Path | str,
    project_id: str,
    task_id: str,
    status: str,
    *,
    progress: float | None = None,
    error: str = "",
    output_paths: Sequence[str] | None = None,
) -> BatchTask:
    clean_status = _clean_status(status)
    payload = _payload(root, project_id)
    tasks = [_task_from_dict(item) for item in payload.get("tasks", []) if isinstance(item, Mapping)]
    updated: BatchTask | None = None
    now = _utc_now()
    next_tasks: list[dict[str, Any]] = []
    for task in tasks:
        if task.id == task_id:
            next_progress = 100.0 if clean_status == "done" and progress is None else (task.progress if progress is None else _bounded_progress(progress))
            updated = BatchTask(
                **{
                    **task.__dict__,
                    "status": clean_status,
                    "progress": next_progress,
                    "error": _clean_text(error or task.error, "Ошибка", max_length=1000),
                    "output_paths": tuple(output_paths) if output_paths is not None else task.output_paths,
                    "updated_at": now,
                }
            )
            next_tasks.append(_task_to_dict(updated))
        else:
            next_tasks.append(_task_to_dict(task))
    if updated is None:
        raise KeyError(f"Batch task not found: {task_id}")
    payload["tasks"] = next_tasks
    _json_write(_batch_path(root, project_id), payload)
    return updated


def pause_batch_queue(root: Path | str, project_id: str) -> tuple[BatchTask, ...]:
    changed = []
    for task in list_batch_tasks(root, project_id):
        if task.status in {"queued", "running"}:
            changed.append(update_batch_task_status(root, project_id, task.id, "paused"))
    return tuple(changed)


def resume_batch_queue(root: Path | str, project_id: str) -> tuple[BatchTask, ...]:
    changed = []
    for task in list_batch_tasks(root, project_id, statuses={"paused"}):
        changed.append(update_batch_task_status(root, project_id, task.id, "queued"))
    return tuple(changed)


def cancel_batch_task(root: Path | str, project_id: str, task_id: str, *, reason: str = "") -> BatchTask:
    message = reason or "Задача отменена пользователем."
    return update_batch_task_status(root, project_id, task_id, "cancelled", error=message)


def retry_failed_batch_tasks(root: Path | str, project_id: str) -> tuple[BatchTask, ...]:
    retried = []
    for task in list_batch_tasks(root, project_id, statuses={"failed"}):
        retried.append(update_batch_task_status(root, project_id, task.id, "queued", progress=0.0, error=""))
    return tuple(retried)


def reorder_batch_tasks(root: Path | str, project_id: str, ordered_task_ids: Sequence[str]) -> tuple[BatchTask, ...]:
    order = {task_id: index for index, task_id in enumerate(ordered_task_ids)}
    payload = _payload(root, project_id)
    tasks = [_task_from_dict(item) for item in payload.get("tasks", []) if isinstance(item, Mapping)]
    reordered = []
    for index, task in enumerate(tasks):
        priority = (order[task.id] + 1) * 10 if task.id in order else task.priority + len(order) * 10 + index
        reordered.append(BatchTask(**{**task.__dict__, "priority": priority, "updated_at": _utc_now()}))
    payload["tasks"] = [_task_to_dict(item) for item in reordered]
    _json_write(_batch_path(root, project_id), payload)
    return list_batch_tasks(root, project_id)


def save_batch_preset(
    root: Path | str,
    project_id: str,
    name: str,
    operations: Sequence[BatchOperation | Mapping[str, Any]],
    *,
    description: str = "",
) -> BatchPreset:
    clean_name = _clean_text(name, "Название пресета", required=True)
    now = _utc_now()
    preset = BatchPreset(
        id=_safe_id(f"{clean_name}-{now}", "batch-preset"),
        name=clean_name,
        description=_clean_text(description, "Описание", max_length=500),
        operations=normalize_batch_operations(operations),
        created_at=now,
        updated_at=now,
    )
    payload = _payload(root, project_id)
    presets = [item for item in payload.get("presets", []) if isinstance(item, Mapping) and item.get("id") != preset.id]
    presets.append(_preset_to_dict(preset))
    payload["presets"] = presets
    _json_write(_batch_path(root, project_id), payload)
    return preset


def list_batch_presets(root: Path | str, project_id: str) -> tuple[BatchPreset, ...]:
    rows = _payload(root, project_id).get("presets", [])
    return tuple(sorted((_preset_from_dict(item) for item in rows if isinstance(item, Mapping)), key=lambda row: row.name.lower()))


def append_batch_run_log(
    root: Path | str,
    project_id: str,
    task_id: str,
    operation_type: str,
    status: str,
    *,
    message: str = "",
    duration_seconds: float | None = None,
) -> BatchRunLog:
    clean_operation = normalize_batch_operation({"type": operation_type}).type
    clean_status = _clean_status(status)
    now = _utc_now()
    run = BatchRunLog(
        id=_safe_id(f"{task_id}-{clean_operation}-{now}", "batch-run"),
        task_id=_clean_text(task_id, "ID задачи", required=True),
        operation_type=clean_operation,
        status=clean_status,
        message=_clean_text(message, "Сообщение", max_length=1000),
        created_at=now,
        duration_seconds=duration_seconds,
    )
    payload = _payload(root, project_id)
    runs = payload.get("runs", []) if isinstance(payload.get("runs", []), list) else []
    runs.insert(0, _run_to_dict(run))
    payload["runs"] = runs[:1000]
    _json_write(_batch_path(root, project_id), payload)
    return run


def list_batch_run_logs(root: Path | str, project_id: str, *, task_id: str | None = None) -> tuple[BatchRunLog, ...]:
    rows = _payload(root, project_id).get("runs", [])
    logs = tuple(_run_from_dict(item) for item in rows if isinstance(item, Mapping))
    if task_id:
        logs = tuple(item for item in logs if item.task_id == task_id)
    return logs


def summarize_batch_queue(tasks: Sequence[BatchTask]) -> BatchQueueSummary:
    counts = {status: 0 for status in BATCH_TASK_STATUSES}
    total_progress = 0.0
    total_operations = 0
    for task in tasks:
        counts[task.status] = counts.get(task.status, 0) + 1
        total_progress += task.progress
        total_operations += len([item for item in task.operations if item.enabled])
    return BatchQueueSummary(
        tasks=len(tasks),
        queued=counts.get("queued", 0),
        running=counts.get("running", 0),
        done=counts.get("done", 0),
        failed=counts.get("failed", 0),
        cancelled=counts.get("cancelled", 0),
        progress=round(total_progress / len(tasks), 2) if tasks else 0.0,
        estimated_operations=total_operations,
    )


def build_batch_task_table(tasks: Sequence[BatchTask]) -> list[dict[str, Any]]:
    return [
        {
            "ID": task.id,
            "Название": task.name,
            "Файл": task.source_path,
            "Скважина": task.well_id,
            "Статус": task.status,
            "Прогресс, %": task.progress,
            "Операций": len([item for item in task.operations if item.enabled]),
            "Ошибка": task.error,
        }
        for task in tasks
    ]


def build_batch_operation_table(operations: Sequence[BatchOperation]) -> list[dict[str, Any]]:
    return [
        {
            "Порядок": operation.order,
            "Операция": operation.type,
            "Включена": operation.enabled,
            "Параметры": json.dumps(dict(operation.parameters), ensure_ascii=False),
        }
        for operation in sorted(operations, key=lambda row: (row.order, row.type))
    ]


def validate_batch_task(task: BatchTask) -> tuple[BatchValidationIssue, ...]:
    issues: list[BatchValidationIssue] = []
    path = Path(task.source_path)
    if not task.source_path:
        issues.append(BatchValidationIssue("error", "MISSING_SOURCE", "Не указан исходный файл.", task.id, "Выберите LAS-файл или папку импорта."))
    elif path.suffix and path.suffix not in BATCH_IMPORT_EXTENSIONS:
        issues.append(BatchValidationIssue("warning", "UNSUPPORTED_EXTENSION", f"Расширение {path.suffix} пока не является основным LAS-форматом.", task.id, "Для batch LAS используйте .las."))
    if not task.operations:
        issues.append(BatchValidationIssue("error", "NO_OPERATIONS", "В задаче нет операций обработки.", task.id, "Добавьте validate_las, depth cleanup или расчетные операции."))
    operation_types = [item.type for item in task.operations if item.enabled]
    if "resample" in operation_types:
        resample_ops = [item for item in task.operations if item.type == "resample" and item.enabled]
        for operation in resample_ops:
            step = operation.parameters.get("step")
            try:
                if float(step) <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                issues.append(BatchValidationIssue("error", "INVALID_RESAMPLE_STEP", "Для resample нужен положительный шаг глубины.", task.id, "Укажите step, например 0.1."))
    if any(item in operation_types for item in ("calculate_vsh", "calculate_phie", "calculate_sw", "calculate_net_pay")) and "validate_las" not in operation_types:
        issues.append(BatchValidationIssue("warning", "NO_PRE_VALIDATION", "Петрофизический batch запускается без предварительной проверки LAS.", task.id, "Добавьте validate_las первым шагом."))
    return tuple(issues)


def validate_batch_queue(tasks: Sequence[BatchTask]) -> tuple[BatchValidationIssue, ...]:
    issues: list[BatchValidationIssue] = []
    seen_sources: set[str] = set()
    for task in tasks:
        issues.extend(validate_batch_task(task))
        normalized_source = str(Path(task.source_path)).lower()
        if normalized_source in seen_sources:
            issues.append(BatchValidationIssue("warning", "DUPLICATE_SOURCE", f"Файл {task.source_path} добавлен в очередь повторно.", task.id, "Удалите дубликат или обработайте его осознанно."))
        seen_sources.add(normalized_source)
    return tuple(issues)


def plan_batch_output_path(source_path: str | Path, operation_suffix: str, *, output_dir: str | Path | None = None, extension: str | None = None) -> str:
    source = Path(source_path)
    suffix = _safe_id(operation_suffix, "batch")
    ext = extension or source.suffix or ".las"
    if not ext.startswith("."):
        ext = f".{ext}"
    target_dir = Path(output_dir) if output_dir else source.parent
    return str(target_dir / f"{source.stem}_{suffix}{ext}")


def plan_batch_exports(task: BatchTask, formats: Sequence[str] | None = None, *, output_dir: str | Path | None = None) -> tuple[str, ...]:
    selected = tuple(dict.fromkeys(str(item).lower().strip() for item in (formats or ("las", "json")) if str(item).strip()))
    invalid = [item for item in selected if item not in BATCH_EXPORT_FORMATS]
    if invalid:
        raise ValueError(f"Неподдерживаемые batch export форматы: {', '.join(invalid)}.")
    return tuple(plan_batch_output_path(task.source_path, "batch", output_dir=output_dir, extension=item) for item in selected)


def next_runnable_batch_task(tasks: Sequence[BatchTask]) -> BatchTask | None:
    candidates = [task for task in tasks if task.status == "queued"]
    return sorted(candidates, key=lambda row: (row.priority, row.created_at, row.name.lower()))[0] if candidates else None

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

GEOLOGICAL_MODEL_INTEGRATION_FILE_NAME = "geological_model_integration_workspace.json"
INTEGRATION_OBJECT_TYPES = {
    "geological_model",
    "structural_model",
    "grid",
    "horizon",
    "zone",
    "layer",
    "surface",
    "fault",
    "well",
    "las_dataset",
    "interval",
    "facies_model",
    "property_cube",
    "geostatistics_job",
    "interpolation_job",
    "simulation_job",
    "volumetrics_case",
    "petrophysical_case",
    "report_package",
    "source_document",
    "custom",
}
DEPENDENCY_ROLES = {"input", "output", "derived_from", "validates", "documents", "visualizes", "exports", "references"}
ISSUE_SEVERITIES = {"info", "warning", "error"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workspace_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / GEOLOGICAL_MODEL_INTEGRATION_FILE_NAME


def _clean_text(value: Any, label: str, *, required: bool = False, max_length: int = 220) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{label}: максимум {max_length} символов.")
    return text


def _choice(value: Any, label: str, choices: set[str], *, default: str) -> str:
    text = _clean_text(value if value not in (None, "") else default, label, required=True, max_length=80).lower()
    if text not in choices:
        raise ValueError(f"{label}: допустимые значения: {', '.join(sorted(choices))}.")
    return text


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


def _as_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = [values]
    return tuple(_clean_text(value, "Список", max_length=160) for value in values if _clean_text(value, "Список", max_length=160))


@dataclass(frozen=True)
class IntegratedModelObject:
    object_id: str
    object_type: str
    name: str
    source_module: str = ""
    source_id: str = ""
    status: str = "draft"
    version: str = "1.0"
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelDependency:
    dependency_id: str
    from_object_id: str
    to_object_id: str
    role: str = "input"
    description: str = ""
    required: bool = True


@dataclass(frozen=True)
class IntegrationView:
    view_id: str
    name: str
    object_ids: tuple[str, ...] = ()
    description: str = ""
    status: str = "draft"


@dataclass(frozen=True)
class IntegrationValidationIssue:
    severity: str
    code: str
    message: str
    object_id: str = ""
    dependency_id: str = ""


@dataclass(frozen=True)
class GeologicalModelIntegrationManifest:
    project_id: str
    generated_at: str
    object_count: int
    dependency_count: int
    view_count: int
    missing_dependency_count: int
    orphan_object_count: int
    warning_count: int
    error_count: int
    object_type_counts: dict[str, int] = field(default_factory=dict)


def _object_to_dict(item: IntegratedModelObject) -> dict[str, Any]:
    data = item.__dict__.copy()
    data["tags"] = list(item.tags)
    return data


def _object_from_dict(raw: dict[str, Any]) -> IntegratedModelObject:
    return IntegratedModelObject(
        object_id=_clean_text(raw.get("object_id"), "Object ID", required=True),
        object_type=_choice(raw.get("object_type"), "Object type", INTEGRATION_OBJECT_TYPES, default="custom"),
        name=_clean_text(raw.get("name"), "Название объекта", required=True),
        source_module=_clean_text(raw.get("source_module"), "Модуль", max_length=140),
        source_id=_clean_text(raw.get("source_id"), "Source ID", max_length=180),
        status=_clean_text(raw.get("status"), "Статус", max_length=80) or "draft",
        version=_clean_text(raw.get("version"), "Версия", max_length=40) or "1.0",
        tags=_as_tuple(raw.get("tags")),
        metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
    )


def _dependency_to_dict(item: ModelDependency) -> dict[str, Any]:
    return item.__dict__.copy()


def _dependency_from_dict(raw: dict[str, Any]) -> ModelDependency:
    return ModelDependency(
        dependency_id=_clean_text(raw.get("dependency_id"), "Dependency ID", required=True),
        from_object_id=_clean_text(raw.get("from_object_id"), "From object", required=True),
        to_object_id=_clean_text(raw.get("to_object_id"), "To object", required=True),
        role=_choice(raw.get("role"), "Dependency role", DEPENDENCY_ROLES, default="input"),
        description=_clean_text(raw.get("description"), "Описание", max_length=800),
        required=bool(raw.get("required", True)),
    )


def _view_to_dict(item: IntegrationView) -> dict[str, Any]:
    data = item.__dict__.copy()
    data["object_ids"] = list(item.object_ids)
    return data


def _view_from_dict(raw: dict[str, Any]) -> IntegrationView:
    return IntegrationView(
        view_id=_clean_text(raw.get("view_id"), "View ID", required=True),
        name=_clean_text(raw.get("name"), "Название представления", required=True),
        object_ids=_as_tuple(raw.get("object_ids")),
        description=_clean_text(raw.get("description"), "Описание", max_length=1000),
        status=_clean_text(raw.get("status"), "Статус", max_length=80) or "draft",
    )


def _empty_workspace() -> dict[str, Any]:
    return {
        "version": "1.0",
        "updated_at": _now_iso(),
        "objects": [],
        "dependencies": [],
        "views": [],
    }


def load_geological_model_integration_workspace(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> dict[str, Any]:
    workspace = _json_read(_workspace_path(root, project_id), _empty_workspace())
    if not isinstance(workspace, dict):
        workspace = _empty_workspace()
    for key in ("objects", "dependencies", "views"):
        if not isinstance(workspace.get(key), list):
            workspace[key] = []
    workspace.setdefault("version", "1.0")
    workspace.setdefault("updated_at", _now_iso())
    return workspace


def _save_workspace(workspace: dict[str, Any], project_id: str, root: Any) -> dict[str, Any]:
    workspace["updated_at"] = _now_iso()
    _json_write(_workspace_path(root, project_id), workspace)
    return workspace


def _upsert(workspace: dict[str, Any], key: str, id_field: str, payload: dict[str, Any]) -> None:
    items = [item for item in workspace.get(key, []) if item.get(id_field) != payload[id_field]]
    items.append(payload)
    workspace[key] = items


def save_integrated_model_object(
    item: IntegratedModelObject | dict[str, Any],
    project_id: str = DEFAULT_PROJECT_ID,
    root: Any = DEFAULT_PROJECTS_ROOT,
) -> IntegratedModelObject:
    obj = item if isinstance(item, IntegratedModelObject) else _object_from_dict(item)
    workspace = load_geological_model_integration_workspace(project_id, root)
    _upsert(workspace, "objects", "object_id", _object_to_dict(obj))
    _save_workspace(workspace, project_id, root)
    append_project_history(root, project_id, "integration_object_saved", f"Integration object saved: {obj.name}", object_type="integration_object", object_id=obj.object_id)
    return obj


def list_integrated_model_objects(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT, *, object_type: str = "") -> list[IntegratedModelObject]:
    workspace = load_geological_model_integration_workspace(project_id, root)
    objects = [_object_from_dict(raw) for raw in workspace.get("objects", [])]
    if object_type:
        checked = _choice(object_type, "Object type", INTEGRATION_OBJECT_TYPES, default="custom")
        objects = [obj for obj in objects if obj.object_type == checked]
    return objects


def save_model_dependency(
    item: ModelDependency | dict[str, Any],
    project_id: str = DEFAULT_PROJECT_ID,
    root: Any = DEFAULT_PROJECTS_ROOT,
) -> ModelDependency:
    dep = item if isinstance(item, ModelDependency) else _dependency_from_dict(item)
    workspace = load_geological_model_integration_workspace(project_id, root)
    _upsert(workspace, "dependencies", "dependency_id", _dependency_to_dict(dep))
    _save_workspace(workspace, project_id, root)
    append_project_history(root, project_id, "integration_dependency_saved", f"Integration dependency saved: {dep.dependency_id}", object_type="integration_dependency", object_id=dep.dependency_id)
    return dep


def list_model_dependencies(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[ModelDependency]:
    workspace = load_geological_model_integration_workspace(project_id, root)
    return [_dependency_from_dict(raw) for raw in workspace.get("dependencies", [])]


def save_integration_view(
    item: IntegrationView | dict[str, Any],
    project_id: str = DEFAULT_PROJECT_ID,
    root: Any = DEFAULT_PROJECTS_ROOT,
) -> IntegrationView:
    view = item if isinstance(item, IntegrationView) else _view_from_dict(item)
    workspace = load_geological_model_integration_workspace(project_id, root)
    _upsert(workspace, "views", "view_id", _view_to_dict(view))
    _save_workspace(workspace, project_id, root)
    append_project_history(root, project_id, "integration_view_saved", f"Integration view saved: {view.name}", object_type="integration_view", object_id=view.view_id)
    return view


def list_integration_views(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[IntegrationView]:
    workspace = load_geological_model_integration_workspace(project_id, root)
    return [_view_from_dict(raw) for raw in workspace.get("views", [])]


def build_dependency_graph(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> dict[str, Any]:
    objects = {obj.object_id: obj for obj in list_integrated_model_objects(project_id, root)}
    dependencies = list_model_dependencies(project_id, root)
    nodes = [
        {
            "id": obj.object_id,
            "label": obj.name,
            "type": obj.object_type,
            "status": obj.status,
            "source_module": obj.source_module,
        }
        for obj in objects.values()
    ]
    edges = [
        {
            "id": dep.dependency_id,
            "from": dep.from_object_id,
            "to": dep.to_object_id,
            "role": dep.role,
            "required": dep.required,
        }
        for dep in dependencies
    ]
    return {"nodes": nodes, "edges": edges}


def validate_geological_model_integration_workspace(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[IntegrationValidationIssue]:
    objects = {obj.object_id: obj for obj in list_integrated_model_objects(project_id, root)}
    dependencies = list_model_dependencies(project_id, root)
    views = list_integration_views(project_id, root)
    issues: list[IntegrationValidationIssue] = []

    if not any(obj.object_type == "geological_model" for obj in objects.values()):
        issues.append(IntegrationValidationIssue("warning", "MISSING_GEOLOGICAL_MODEL", "Не зарегистрирован главный объект geological_model."))
    if not any(obj.object_type == "structural_model" for obj in objects.values()):
        issues.append(IntegrationValidationIssue("warning", "MISSING_STRUCTURAL_MODEL", "Не зарегистрирована структурная модель."))

    connected: set[str] = set()
    for dep in dependencies:
        if dep.from_object_id not in objects:
            severity = "error" if dep.required else "warning"
            issues.append(IntegrationValidationIssue(severity, "MISSING_FROM_OBJECT", "Источник зависимости отсутствует.", dep.from_object_id, dep.dependency_id))
        else:
            connected.add(dep.from_object_id)
        if dep.to_object_id not in objects:
            severity = "error" if dep.required else "warning"
            issues.append(IntegrationValidationIssue(severity, "MISSING_TO_OBJECT", "Целевой объект зависимости отсутствует.", dep.to_object_id, dep.dependency_id))
        else:
            connected.add(dep.to_object_id)
        if dep.from_object_id == dep.to_object_id:
            issues.append(IntegrationValidationIssue("warning", "SELF_DEPENDENCY", "Объект ссылается сам на себя.", dep.from_object_id, dep.dependency_id))

    for obj_id, obj in objects.items():
        if obj.object_type not in {"geological_model", "source_document"} and obj_id not in connected:
            issues.append(IntegrationValidationIssue("warning", "ORPHAN_OBJECT", f"Объект не связан с моделью: {obj.name}.", obj_id))

    for view in views:
        for obj_id in view.object_ids:
            if obj_id not in objects:
                issues.append(IntegrationValidationIssue("warning", "VIEW_MISSING_OBJECT", f"В представлении {view.name} указан отсутствующий объект.", obj_id))

    return issues


def build_geological_model_integration_manifest(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> GeologicalModelIntegrationManifest:
    objects = list_integrated_model_objects(project_id, root)
    dependencies = list_model_dependencies(project_id, root)
    views = list_integration_views(project_id, root)
    issues = validate_geological_model_integration_workspace(project_id, root)
    type_counts: dict[str, int] = {}
    for obj in objects:
        type_counts[obj.object_type] = type_counts.get(obj.object_type, 0) + 1
    return GeologicalModelIntegrationManifest(
        project_id=safe_project_id(project_id),
        generated_at=_now_iso(),
        object_count=len(objects),
        dependency_count=len(dependencies),
        view_count=len(views),
        missing_dependency_count=sum(1 for issue in issues if issue.code in {"MISSING_FROM_OBJECT", "MISSING_TO_OBJECT"}),
        orphan_object_count=sum(1 for issue in issues if issue.code == "ORPHAN_OBJECT"),
        warning_count=sum(1 for issue in issues if issue.severity == "warning"),
        error_count=sum(1 for issue in issues if issue.severity == "error"),
        object_type_counts=type_counts,
    )


def manifest_to_dict(manifest: GeologicalModelIntegrationManifest) -> dict[str, Any]:
    return manifest.__dict__.copy()


def build_integration_object_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [_object_to_dict(obj) for obj in list_integrated_model_objects(project_id, root)]


def build_dependency_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [_dependency_to_dict(dep) for dep in list_model_dependencies(project_id, root)]


def build_integration_view_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [_view_to_dict(view) for view in list_integration_views(project_id, root)]


def build_integration_issue_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [issue.__dict__.copy() for issue in validate_geological_model_integration_workspace(project_id, root)]


def render_geological_model_integration_markdown(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> str:
    manifest = build_geological_model_integration_manifest(project_id, root)
    objects = list_integrated_model_objects(project_id, root)
    deps = list_model_dependencies(project_id, root)
    issues = validate_geological_model_integration_workspace(project_id, root)
    lines = [
        "# Geological Model Integration Workspace",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: {manifest.generated_at}",
        "",
        "## Summary",
        f"- Objects: {manifest.object_count}",
        f"- Dependencies: {manifest.dependency_count}",
        f"- Views: {manifest.view_count}",
        f"- Warnings: {manifest.warning_count}",
        f"- Errors: {manifest.error_count}",
        "",
        "## Object Types",
    ]
    if manifest.object_type_counts:
        for object_type, count in sorted(manifest.object_type_counts.items()):
            lines.append(f"- {object_type}: {count}")
    else:
        lines.append("- No objects registered.")
    lines.extend(["", "## Objects"])
    for obj in objects:
        lines.append(f"- `{obj.object_id}` — {obj.name} ({obj.object_type}, {obj.status})")
    lines.extend(["", "## Dependencies"])
    for dep in deps:
        lines.append(f"- `{dep.dependency_id}`: {dep.from_object_id} → {dep.to_object_id} ({dep.role})")
    lines.extend(["", "## Validation"])
    if issues:
        for issue in issues:
            lines.append(f"- **{issue.severity.upper()}** `{issue.code}`: {issue.message}")
    else:
        lines.append("- No integration issues found.")
    return "\n".join(lines) + "\n"


def seed_geological_model_integration_workspace(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> dict[str, Any]:
    objects = [
        IntegratedModelObject("gm-main", "geological_model", "Integrated Geological Model", "geological_model_workspace", "gm1", "active"),
        IntegratedModelObject("struct-main", "structural_model", "Structural Framework", "structural_modeling_workspace", "sf1", "active"),
        IntegratedModelObject("grid-main", "grid", "Corner Point Grid", "geological_model_workspace", "grid1", "draft"),
        IntegratedModelObject("facies-main", "facies_model", "Facies Model", "facies_modeling_workspace", "facies_job_1", "draft"),
        IntegratedModelObject("props-main", "property_cube", "Reservoir Property Cubes", "property_modeling_workspace", "por_perm_sw", "draft"),
        IntegratedModelObject("vol-main", "volumetrics_case", "Base Volumetrics Case", "reservoir_volumetrics_workspace", "base", "draft"),
    ]
    for obj in objects:
        save_integrated_model_object(obj, project_id, root)
    deps = [
        ModelDependency("dep-struct-to-gm", "struct-main", "gm-main", "input", "Structural framework defines the model geometry."),
        ModelDependency("dep-grid-to-gm", "grid-main", "gm-main", "input", "Grid defines cell topology."),
        ModelDependency("dep-facies-to-props", "facies-main", "props-main", "input", "Facies constrain property modeling."),
        ModelDependency("dep-props-to-vol", "props-main", "vol-main", "input", "Property cubes are used for volumetrics."),
        ModelDependency("dep-vol-to-gm", "vol-main", "gm-main", "documents", "Volumetrics summarize the geological model."),
    ]
    for dep in deps:
        save_model_dependency(dep, project_id, root)
    save_integration_view(
        IntegrationView("view-main", "Main Geological Model View", tuple(obj.object_id for obj in objects), "Default integration overview.", "active"),
        project_id,
        root,
    )
    return load_geological_model_integration_workspace(project_id, root)

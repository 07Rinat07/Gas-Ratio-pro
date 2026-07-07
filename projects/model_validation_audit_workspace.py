from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.geological_model_integration_workspace import (
    build_dependency_graph,
    list_integrated_model_objects,
    list_model_dependencies,
    validate_geological_model_integration_workspace,
)
from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

MODEL_VALIDATION_AUDIT_FILE_NAME = "model_validation_audit_workspace.json"
AUDIT_SEVERITIES = {"info", "warning", "error"}
REQUIRED_FOUNDATION_TYPES = {
    "geological_model",
    "structural_model",
    "grid",
    "facies_model",
    "property_cube",
    "volumetrics_case",
}
OPTIONAL_PROFESSIONAL_TYPES = {
    "well",
    "las_dataset",
    "interval",
    "geostatistics_job",
    "interpolation_job",
    "simulation_job",
    "petrophysical_case",
    "report_package",
    "source_document",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workspace_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / MODEL_VALIDATION_AUDIT_FILE_NAME


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


def _clean_text(value: Any, label: str, *, required: bool = False, max_length: int = 240) -> str:
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


@dataclass(frozen=True)
class ModelAuditIssue:
    severity: str
    code: str
    message: str
    object_id: str = ""
    object_type: str = ""
    recommendation: str = ""


@dataclass(frozen=True)
class ModelAuditCheck:
    check_id: str
    name: str
    category: str
    status: str
    severity: str = "info"
    issue_count: int = 0
    description: str = ""


@dataclass(frozen=True)
class ModelValidationAuditManifest:
    project_id: str
    generated_at: str
    readiness_score: float
    readiness_status: str
    object_count: int
    dependency_count: int
    check_count: int
    issue_count: int
    error_count: int
    warning_count: int
    info_count: int
    missing_required_type_count: int
    orphan_object_count: int
    broken_dependency_count: int
    type_coverage: dict[str, bool] = field(default_factory=dict)


def _empty_workspace() -> dict[str, Any]:
    return {"version": "1.0", "updated_at": _now_iso(), "audits": []}


def load_model_validation_audit_workspace(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> dict[str, Any]:
    workspace = _json_read(_workspace_path(root, project_id), _empty_workspace())
    if not isinstance(workspace, dict):
        workspace = _empty_workspace()
    if not isinstance(workspace.get("audits"), list):
        workspace["audits"] = []
    workspace.setdefault("version", "1.0")
    workspace.setdefault("updated_at", _now_iso())
    return workspace


def _save_workspace(workspace: dict[str, Any], project_id: str, root: Any) -> dict[str, Any]:
    workspace["updated_at"] = _now_iso()
    _json_write(_workspace_path(root, project_id), workspace)
    return workspace


def _issue_to_dict(issue: ModelAuditIssue) -> dict[str, Any]:
    return issue.__dict__.copy()


def _check_to_dict(check: ModelAuditCheck) -> dict[str, Any]:
    return check.__dict__.copy()


def manifest_to_dict(manifest: ModelValidationAuditManifest) -> dict[str, Any]:
    return manifest.__dict__.copy()


def _readiness_status(score: float, error_count: int, warning_count: int) -> str:
    if error_count > 0 or score < 60:
        return "not_ready"
    if warning_count > 0 or score < 85:
        return "partially_ready"
    return "ready"


def _score_from_counts(error_count: int, warning_count: int, missing_required: int, orphan_count: int, broken_count: int, object_count: int) -> float:
    score = 100.0
    score -= error_count * 18.0
    score -= warning_count * 5.0
    score -= missing_required * 12.0
    score -= orphan_count * 3.0
    score -= broken_count * 10.0
    if object_count == 0:
        score = 0.0
    return round(max(0.0, min(100.0, score)), 2)


def audit_dependency_graph(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[ModelAuditIssue]:
    """Проверяет граф зависимостей интегрированной геологической модели."""
    integration_issues = validate_geological_model_integration_workspace(project_id, root)
    issues: list[ModelAuditIssue] = []
    for issue in integration_issues:
        recommendation = "Проверьте регистрацию объекта и связи в Geological Model Integration Workspace."
        issues.append(
            ModelAuditIssue(
                severity=_choice(issue.severity, "Severity", AUDIT_SEVERITIES, default="warning"),
                code=f"INTEGRATION_{issue.code}",
                message=issue.message,
                object_id=issue.object_id,
                recommendation=recommendation,
            )
        )

    graph = build_dependency_graph(project_id, root)
    edges = graph.get("edges", []) if isinstance(graph, dict) else []
    for edge in edges:
        if edge.get("from") == edge.get("to"):
            issues.append(
                ModelAuditIssue(
                    "warning",
                    "SELF_REFERENCE_EDGE",
                    "В графе зависимостей обнаружена ссылка объекта на самого себя.",
                    str(edge.get("from", "")),
                    recommendation="Удалите самоссылку или замените ее корректной зависимостью.",
                )
            )
    return issues


def audit_required_model_components(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[ModelAuditIssue]:
    """Проверяет наличие обязательных foundation-компонентов геологической модели."""
    objects = list_integrated_model_objects(project_id, root)
    present_types = {obj.object_type for obj in objects}
    issues: list[ModelAuditIssue] = []
    for object_type in sorted(REQUIRED_FOUNDATION_TYPES - present_types):
        issues.append(
            ModelAuditIssue(
                "error",
                "MISSING_REQUIRED_COMPONENT",
                f"В интегрированной модели отсутствует обязательный компонент: {object_type}.",
                object_type=object_type,
                recommendation="Зарегистрируйте компонент в Geological Model Integration Workspace и свяжите его с главным объектом модели.",
            )
        )
    for object_type in sorted(OPTIONAL_PROFESSIONAL_TYPES - present_types):
        issues.append(
            ModelAuditIssue(
                "info",
                "OPTIONAL_COMPONENT_NOT_REGISTERED",
                f"Профессиональный компонент пока не зарегистрирован: {object_type}.",
                object_type=object_type,
                recommendation="Добавьте компонент, когда соответствующий модуль будет готов к включению в модель.",
            )
        )
    return issues


def audit_object_metadata(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[ModelAuditIssue]:
    """Проверяет статусы, source metadata и базовую заполненность объектов модели."""
    issues: list[ModelAuditIssue] = []
    for obj in list_integrated_model_objects(project_id, root):
        if not obj.name.strip():
            issues.append(ModelAuditIssue("error", "EMPTY_OBJECT_NAME", "Объект модели не имеет названия.", obj.object_id, obj.object_type, "Заполните человекочитаемое название объекта."))
        if not obj.source_module:
            issues.append(ModelAuditIssue("warning", "MISSING_SOURCE_MODULE", f"Для объекта {obj.name} не указан исходный модуль.", obj.object_id, obj.object_type, "Укажите модуль-источник для трассируемости данных."))
        if obj.status.lower() in {"failed", "invalid", "broken"}:
            issues.append(ModelAuditIssue("error", "INVALID_OBJECT_STATUS", f"Объект {obj.name} имеет проблемный статус: {obj.status}.", obj.object_id, obj.object_type, "Пересчитайте объект или исключите его из активной модели."))
        if obj.status.lower() in {"draft", "pending"}:
            issues.append(ModelAuditIssue("info", "DRAFT_OBJECT", f"Объект {obj.name} находится в статусе {obj.status}.", obj.object_id, obj.object_type, "Перед релизом модели переведите ключевые объекты в active/validated."))
    return issues


def run_model_validation_audit(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[ModelAuditIssue]:
    """Выполняет полный аудит модели и возвращает найденные замечания."""
    issues: list[ModelAuditIssue] = []
    issues.extend(audit_dependency_graph(project_id, root))
    issues.extend(audit_required_model_components(project_id, root))
    issues.extend(audit_object_metadata(project_id, root))
    return issues


def build_model_audit_checks(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[ModelAuditCheck]:
    issues = run_model_validation_audit(project_id, root)

    def count(prefix: str) -> int:
        return sum(1 for issue in issues if issue.code.startswith(prefix))

    definitions = [
        ("dependency_graph", "Dependency Graph Audit", "integration", count("INTEGRATION_") + count("SELF_REFERENCE"), "Проверка связей между объектами модели."),
        ("required_components", "Required Components", "completeness", sum(1 for issue in issues if issue.code == "MISSING_REQUIRED_COMPONENT"), "Проверка обязательных foundation-компонентов."),
        ("optional_components", "Optional Components", "completeness", sum(1 for issue in issues if issue.code == "OPTIONAL_COMPONENT_NOT_REGISTERED"), "Информационный контроль профессиональных компонентов."),
        ("object_metadata", "Object Metadata", "traceability", sum(1 for issue in issues if issue.code in {"EMPTY_OBJECT_NAME", "MISSING_SOURCE_MODULE", "INVALID_OBJECT_STATUS", "DRAFT_OBJECT"}), "Проверка статусов и трассируемости объектов."),
    ]
    checks: list[ModelAuditCheck] = []
    for check_id, name, category, issue_count, description in definitions:
        related = [issue for issue in issues if (
            (check_id == "dependency_graph" and (issue.code.startswith("INTEGRATION_") or issue.code.startswith("SELF_REFERENCE")))
            or (check_id == "required_components" and issue.code == "MISSING_REQUIRED_COMPONENT")
            or (check_id == "optional_components" and issue.code == "OPTIONAL_COMPONENT_NOT_REGISTERED")
            or (check_id == "object_metadata" and issue.code in {"EMPTY_OBJECT_NAME", "MISSING_SOURCE_MODULE", "INVALID_OBJECT_STATUS", "DRAFT_OBJECT"})
        )]
        severity = "info"
        if any(issue.severity == "error" for issue in related):
            severity = "error"
        elif any(issue.severity == "warning" for issue in related):
            severity = "warning"
        status = "passed" if issue_count == 0 else "issues_found"
        checks.append(ModelAuditCheck(check_id, name, category, status, severity, issue_count, description))
    return checks


def build_model_validation_audit_manifest(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> ModelValidationAuditManifest:
    objects = list_integrated_model_objects(project_id, root)
    deps = list_model_dependencies(project_id, root)
    issues = run_model_validation_audit(project_id, root)
    checks = build_model_audit_checks(project_id, root)
    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    info_count = sum(1 for issue in issues if issue.severity == "info")
    missing_required = sum(1 for issue in issues if issue.code == "MISSING_REQUIRED_COMPONENT")
    orphan_count = sum(1 for issue in issues if issue.code == "INTEGRATION_ORPHAN_OBJECT")
    broken_count = sum(1 for issue in issues if issue.code in {"INTEGRATION_MISSING_FROM_OBJECT", "INTEGRATION_MISSING_TO_OBJECT"})
    score = _score_from_counts(error_count, warning_count, missing_required, orphan_count, broken_count, len(objects))
    present_types = {obj.object_type for obj in objects}
    coverage = {object_type: object_type in present_types for object_type in sorted(REQUIRED_FOUNDATION_TYPES | OPTIONAL_PROFESSIONAL_TYPES)}
    return ModelValidationAuditManifest(
        project_id=safe_project_id(project_id),
        generated_at=_now_iso(),
        readiness_score=score,
        readiness_status=_readiness_status(score, error_count, warning_count),
        object_count=len(objects),
        dependency_count=len(deps),
        check_count=len(checks),
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        missing_required_type_count=missing_required,
        orphan_object_count=orphan_count,
        broken_dependency_count=broken_count,
        type_coverage=coverage,
    )


def save_model_validation_audit(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> dict[str, Any]:
    manifest = build_model_validation_audit_manifest(project_id, root)
    checks = build_model_audit_checks(project_id, root)
    issues = run_model_validation_audit(project_id, root)
    record = {
        "audit_id": f"audit-{manifest.generated_at}",
        "manifest": manifest_to_dict(manifest),
        "checks": [_check_to_dict(check) for check in checks],
        "issues": [_issue_to_dict(issue) for issue in issues],
    }
    workspace = load_model_validation_audit_workspace(project_id, root)
    workspace["audits"].append(record)
    _save_workspace(workspace, project_id, root)
    append_project_history(root, project_id, "model_validation_audit_saved", "Model validation audit saved", object_type="model_validation_audit", object_id=record["audit_id"])
    return record


def build_model_audit_issue_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [_issue_to_dict(issue) for issue in run_model_validation_audit(project_id, root)]


def build_model_audit_check_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [_check_to_dict(check) for check in build_model_audit_checks(project_id, root)]


def build_model_audit_coverage_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    manifest = build_model_validation_audit_manifest(project_id, root)
    return [
        {
            "object_type": object_type,
            "registered": registered,
            "required": object_type in REQUIRED_FOUNDATION_TYPES,
        }
        for object_type, registered in sorted(manifest.type_coverage.items())
    ]


def render_model_validation_audit_markdown(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> str:
    manifest = build_model_validation_audit_manifest(project_id, root)
    checks = build_model_audit_checks(project_id, root)
    issues = run_model_validation_audit(project_id, root)
    lines = [
        "# Model Validation & Audit Workspace",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: {manifest.generated_at}",
        "",
        "## Readiness",
        f"- Score: {manifest.readiness_score}%",
        f"- Status: {manifest.readiness_status}",
        f"- Objects: {manifest.object_count}",
        f"- Dependencies: {manifest.dependency_count}",
        f"- Errors: {manifest.error_count}",
        f"- Warnings: {manifest.warning_count}",
        f"- Info: {manifest.info_count}",
        "",
        "## Checks",
    ]
    for check in checks:
        lines.append(f"- `{check.check_id}` — {check.name}: {check.status} ({check.issue_count} issues, {check.severity})")
    lines.extend(["", "## Required Coverage"])
    for object_type in sorted(REQUIRED_FOUNDATION_TYPES):
        mark = "yes" if manifest.type_coverage.get(object_type) else "no"
        lines.append(f"- {object_type}: {mark}")
    lines.extend(["", "## Issues"])
    if issues:
        for issue in issues:
            target = issue.object_id or issue.object_type or "model"
            lines.append(f"- **{issue.severity.upper()}** `{issue.code}` [{target}]: {issue.message}")
            if issue.recommendation:
                lines.append(f"  - Recommendation: {issue.recommendation}")
    else:
        lines.append("- No audit issues found.")
    return "\n".join(lines) + "\n"

from __future__ import annotations

import ast
import importlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PlatformHealthCheck:
    """Single platform-health check result used by Sprint 1.5 diagnostics."""

    name: str
    status: str
    message: str


@dataclass(frozen=True)
class PlatformHealthReport:
    """Aggregated platform-health report.

    The report is intentionally framework-agnostic: it can be rendered in
    Streamlit, used by tests, or written into logs without importing UI code.
    """

    checks: tuple[PlatformHealthCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.status != "error" for check in self.checks)

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "checks": [
                {"name": check.name, "status": check.status, "message": check.message}
                for check in self.checks
            ],
        }


REQUIRED_SERVICE_CONTRACTS: dict[str, tuple[str, ...]] = {
    "services.dataset_manager_service.DatasetManagerService": (
        "section_specs",
        "list_records",
        "delete_dataset",
        "delete_selected",
        "clear_section",
        "clear_all",
        "delete",
        "clear",
        "refresh",
    ),
    "services.project_manager_service.ProjectManagerService": (
        "list_projects",
        "get_project",
        "create_project",
        "delete_project_complete",
        "record_recent_project",
        "list_recent_projects",
        "clear_recent_history",
    ),
    "services.las_manager_service.LasManagerService": (
        "list_files",
        "delete_file",
        "clear_files",
        "delete",
        "clear",
        "refresh",
    ),
    "services.well_manager_service.WellManagerService": (
        "list_wells",
        "delete_well",
        "delete_version",
        "delete",
    ),
    "services.export_manager_service.ExportManagerService": (
        "list_exports",
        "delete_export",
        "clear_exports",
        "list",
        "count",
        "read_bytes",
        "delete",
        "clear",
        "refresh",
    ),
}

DESTRUCTIVE_UI_CALLS: tuple[tuple[str, str], ...] = (
    ("shutil", "rmtree"),
    ("os", "remove"),
    ("os", "rmdir"),
)
DESTRUCTIVE_PATH_METHODS: tuple[str, ...] = ("unlink", "rmdir")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ok(name: str, message: str) -> PlatformHealthCheck:
    return PlatformHealthCheck(name=name, status="ok", message=message)


def _warning(name: str, message: str) -> PlatformHealthCheck:
    return PlatformHealthCheck(name=name, status="warning", message=message)


def _error(name: str, message: str) -> PlatformHealthCheck:
    return PlatformHealthCheck(name=name, status="error", message=message)


def _resolve_object(path: str) -> object:
    module_name, object_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, object_name)


def check_storage_lifecycle_imports() -> PlatformHealthCheck:
    try:
        from core.storage_lifecycle import (  # noqa: F401
            CacheManager,
            DeleteEngine,
            FileHandleManager,
            IndexManager,
            ResourceManager,
        )
    except Exception as exc:  # pragma: no cover - defensive diagnostic path
        return _error("storage_lifecycle", f"Storage Lifecycle imports failed: {exc}")
    return _ok("storage_lifecycle", "Storage Lifecycle components are importable.")


def check_service_contracts(contracts: dict[str, tuple[str, ...]] | None = None) -> PlatformHealthCheck:
    missing: list[str] = []
    for object_path, required_members in (contracts or REQUIRED_SERVICE_CONTRACTS).items():
        try:
            service_cls = _resolve_object(object_path)
        except Exception as exc:
            missing.append(f"{object_path}: import failed: {exc}")
            continue
        for member in required_members:
            if not hasattr(service_cls, member):
                missing.append(f"{object_path}.{member}")
    if missing:
        return _error("service_contracts", "Missing service contract members: " + "; ".join(missing))
    return _ok("service_contracts", "All service compatibility contracts are present.")


def _is_destructive_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr in DESTRUCTIVE_PATH_METHODS:
            return True
        if isinstance(func.value, ast.Name):
            return (func.value.id, func.attr) in DESTRUCTIVE_UI_CALLS
    return False


def find_destructive_ui_calls(path: Path | str) -> tuple[tuple[int, str], ...]:
    source_path = Path(path)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_destructive_call(node):
            func = node.func
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    label = f"{func.value.id}.{func.attr}"
                else:
                    label = f"*.{func.attr}"
            else:  # pragma: no cover - guarded by _is_destructive_call
                label = "unknown"
            findings.append((getattr(node, "lineno", 0), label))
    return tuple(findings)


def check_ui_storage_boundaries(root: Path | str | None = None) -> PlatformHealthCheck:
    resolved_root = Path(root) if root is not None else project_root()
    app_path = resolved_root / "app" / "streamlit_app.py"
    if not app_path.exists():
        return _error("ui_storage_boundaries", f"Missing UI entry point: {app_path}")
    findings = find_destructive_ui_calls(app_path)
    if findings:
        details = "; ".join(f"line {line}: {call}" for line, call in findings[:10])
        return _error(
            "ui_storage_boundaries",
            "UI contains direct destructive filesystem calls: " + details,
        )
    return _ok("ui_storage_boundaries", "UI has no direct destructive filesystem calls.")


def check_required_storage_dirs(root: Path | str | None = None) -> PlatformHealthCheck:
    resolved_root = Path(root) if root is not None else project_root()
    required = (resolved_root / "data" / "projects", resolved_root / "data" / "wells", resolved_root / "logs")
    missing: list[str] = []
    for directory in required:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            missing.append(f"{directory}: {exc}")
    if missing:
        return _error("storage_dirs", "Storage directories are not writable: " + "; ".join(missing))
    return _ok("storage_dirs", "Storage directories are present and writable.")


def check_streamlit_compatibility(root: Path | str | None = None) -> PlatformHealthCheck:
    resolved_root = Path(root) if root is not None else project_root()
    try:
        from core.streamlit_compatibility import scan_streamlit_deprecations

        report = scan_streamlit_deprecations(resolved_root)
    except Exception as exc:  # pragma: no cover - defensive diagnostic path
        return _error("streamlit_compatibility", f"Streamlit compatibility scan failed: {exc}")
    if not report.ok:
        first = report.findings[0]
        return _warning(
            "streamlit_compatibility",
            f"Deprecated Streamlit API usage found: {len(report.findings)} finding(s). "
            f"First: {first.file}:{first.line} {first.detail}",
        )
    return _ok("streamlit_compatibility", "No deprecated Streamlit width arguments found.")


def run_platform_health(root: Path | str | None = None) -> PlatformHealthReport:
    resolved_root = Path(root) if root is not None else project_root()
    checks = (
        check_required_storage_dirs(resolved_root),
        check_storage_lifecycle_imports(),
        check_service_contracts(),
        check_ui_storage_boundaries(resolved_root),
        check_streamlit_compatibility(resolved_root),
    )
    return PlatformHealthReport(checks=checks)

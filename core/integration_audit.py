from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class AuditFinding:
    """Single source-code finding produced during Sprint 1.5 integration audit."""

    file: str
    line: int
    kind: str
    detail: str


@dataclass(frozen=True)
class IntegrationAuditReport:
    """Aggregated Sprint 1.5 source-level audit report."""

    findings: tuple[AuditFinding, ...]

    @property
    def errors(self) -> tuple[AuditFinding, ...]:
        return tuple(finding for finding in self.findings if finding.kind == "error")

    @property
    def warnings(self) -> tuple[AuditFinding, ...]:
        return tuple(finding for finding in self.findings if finding.kind == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors

    def count_by_detail(self, detail_prefix: str) -> int:
        return sum(1 for finding in self.findings if finding.detail.startswith(detail_prefix))

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "findings": [
                {
                    "file": finding.file,
                    "line": finding.line,
                    "kind": finding.kind,
                    "detail": finding.detail,
                }
                for finding in self.findings
            ],
        }


DESTRUCTIVE_MODULE_CALLS: tuple[tuple[str, str], ...] = (
    ("os", "remove"),
    ("os", "rmdir"),
    ("shutil", "rmtree"),
)
DESTRUCTIVE_PATH_METHODS: tuple[str, ...] = ("unlink", "rmdir")
DIRECT_REPOSITORY_MODULE_PREFIXES: tuple[str, ...] = (
    "projects.repository",
    "wells.repository",
    "projects.datasets",
    "projects.project_las_files",
    "projects.project_exports",
)
ALLOWED_DIRECT_REPOSITORY_IMPORT_NAMES: frozenset[str] = frozenset(
    {
        # Legacy read-only/domain imports still used by the large Streamlit shell
        # during Sprint 1.5.  Destructive operations are blocked separately.
        "ProjectRecord",
        "DEFAULT_PROJECT_ID",
        "DEFAULT_PROJECTS_ROOT",
        "safe_project_id",
    }
)


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        return f"*.{func.attr}"
    if isinstance(func, ast.Name):
        return func.id
    return None


def scan_destructive_filesystem_calls(path: Path, root: Path) -> tuple[AuditFinding, ...]:
    """Find direct delete calls that must go through DeleteEngine."""

    tree = _parse(path)
    findings: list[AuditFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        detail: str | None = None
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and (func.value.id, func.attr) in DESTRUCTIVE_MODULE_CALLS:
                detail = f"direct filesystem delete call: {func.value.id}.{func.attr}"
            elif func.attr in DESTRUCTIVE_PATH_METHODS:
                detail = f"direct Path delete call: {func.attr}"
        if detail:
            findings.append(
                AuditFinding(
                    file=_relative(path, root),
                    line=getattr(node, "lineno", 0),
                    kind="error",
                    detail=detail,
                )
            )
    return tuple(findings)


def scan_direct_repository_imports(path: Path, root: Path) -> tuple[AuditFinding, ...]:
    """Find UI imports that still bypass service layer.

    This is a warning-level audit during Sprint 1.5 because the application shell
    is still being migrated.  It becomes an error after Workspace Framework is
    split out of ``app/streamlit_app.py``.
    """

    tree = _parse(path)
    findings: list[AuditFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if any(node.module == prefix or node.module.startswith(prefix + ".") for prefix in DIRECT_REPOSITORY_MODULE_PREFIXES):
                imported_names = {alias.name for alias in node.names}
                unsafe = imported_names - ALLOWED_DIRECT_REPOSITORY_IMPORT_NAMES
                if unsafe:
                    findings.append(
                        AuditFinding(
                            file=_relative(path, root),
                            line=getattr(node, "lineno", 0),
                            kind="warning",
                            detail=f"direct repository import from UI: {node.module} -> {', '.join(sorted(unsafe))}",
                        )
                    )
    return tuple(findings)



def _enclosing_function_names(tree: ast.AST) -> dict[int, str]:
    """Map AST node object ids to the function that contains each node.

    The audit uses this small parent-context map to allow the single Streamlit
    adapter boundary that constructs ``ApplicationStateController`` from
    ``st.session_state`` while blocking every other direct UI access.
    """

    owners: dict[int, str] = {}

    def visit(node: ast.AST, current_function: str = "") -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            current_function = node.name
        owners[id(node)] = current_function
        for child in ast.iter_child_nodes(node):
            visit(child, current_function)

    visit(tree)
    return owners


def scan_session_state_access(
    path: Path,
    root: Path,
    *,
    allowed_functions: tuple[str, ...] = ("_application_state_controller",),
) -> tuple[AuditFinding, ...]:
    """Find direct Streamlit session-state access outside approved boundaries.

    After the ApplicationStateController migration, ``streamlit_app.py`` may
    touch ``st.session_state`` only once: inside the controller factory where the
    Streamlit mapping is adapted to the framework-neutral controller.  All reads,
    writes and method calls elsewhere must go through controller helpers.
    """

    tree = _parse(path)
    owners = _enclosing_function_names(tree)
    allowed = set(allowed_functions)
    findings: list[AuditFinding] = []
    seen: set[tuple[str, int]] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if not (isinstance(node.value, ast.Name) and node.value.id == "st" and node.attr == "session_state"):
            continue
        owner = owners.get(id(node), "")
        if owner in allowed:
            continue
        key = (owner, getattr(node, "lineno", 0))
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            AuditFinding(
                file=_relative(path, root),
                line=getattr(node, "lineno", 0),
                kind="error",
                detail="direct st.session_state access outside ApplicationStateController boundary",
            )
        )
    return tuple(findings)

def scan_session_state_writes(path: Path, root: Path) -> tuple[AuditFinding, ...]:
    """Find direct Streamlit session-state writes in UI shell.

    These are warnings while ``streamlit_app.py`` is still the monolithic shell.
    They document migration debt for ApplicationStateController.
    """

    tree = _parse(path)
    findings: list[AuditFinding] = []
    for node in ast.walk(tree):
        target_nodes: Iterable[ast.AST] = ()
        if isinstance(node, ast.Assign):
            target_nodes = node.targets
        elif isinstance(node, ast.AugAssign):
            target_nodes = (node.target,)
        elif isinstance(node, ast.AnnAssign):
            target_nodes = (node.target,)
        for target in target_nodes:
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Attribute):
                attr = target.value
                if isinstance(attr.value, ast.Name) and attr.value.id == "st" and attr.attr == "session_state":
                    findings.append(
                        AuditFinding(
                            file=_relative(path, root),
                            line=getattr(node, "lineno", 0),
                            kind="warning",
                            detail="direct st.session_state write in UI shell",
                        )
                    )
            elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Attribute):
                attr = target.value
                if isinstance(attr.value, ast.Name) and attr.value.id == "st" and attr.attr == "session_state":
                    findings.append(
                        AuditFinding(
                            file=_relative(path, root),
                            line=getattr(node, "lineno", 0),
                            kind="warning",
                            detail="direct st.session_state attribute write in UI shell",
                        )
                    )
    return tuple(findings)


def audit_streamlit_app(root: Path | str) -> IntegrationAuditReport:
    root_path = Path(root)
    app_path = root_path / "app" / "streamlit_app.py"
    findings: list[AuditFinding] = []
    findings.extend(scan_destructive_filesystem_calls(app_path, root_path))
    findings.extend(scan_direct_repository_imports(app_path, root_path))
    findings.extend(scan_session_state_access(app_path, root_path))
    findings.extend(scan_session_state_writes(app_path, root_path))
    return IntegrationAuditReport(findings=tuple(findings))


def audit_service_files(root: Path | str) -> IntegrationAuditReport:
    root_path = Path(root)
    findings: list[AuditFinding] = []
    for path in sorted((root_path / "services").glob("*_service.py")):
        findings.extend(scan_destructive_filesystem_calls(path, root_path))
    return IntegrationAuditReport(findings=tuple(findings))


def run_integration_audit(root: Path | str) -> IntegrationAuditReport:
    """Run the source-level Sprint 1.5 audit.

    Error-level findings are blockers. Warning-level findings are migration debt
    to be burned down during Sprint 1.5 and Sprint 2.
    """

    reports = (audit_streamlit_app(root), audit_service_files(root))
    findings: list[AuditFinding] = []
    for report in reports:
        findings.extend(report.findings)
    return IntegrationAuditReport(findings=tuple(findings))

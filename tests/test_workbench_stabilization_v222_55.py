from __future__ import annotations

import ast
from pathlib import Path

from core.workbench_error_boundary import capture_workbench_exception, run_with_workbench_boundary


def test_renderer_does_not_shadow_application_service_container() -> None:
    path = Path(__file__).resolve().parents[1] / "app" / "workbench_renderer.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "core.application_service_container"
        and any(alias.name == "application_service_container" for alias in node.names)
    ]
    assert len(imports) == 1
    assert isinstance(imports[0].parent if hasattr(imports[0], "parent") else tree, ast.AST)
    assert imports[0] in tree.body


def test_error_boundary_returns_serializable_incident() -> None:
    state: dict[str, object] = {}
    incident = capture_workbench_exception(
        state,
        RuntimeError("boom"),
        boundary="project_menu",
        operation="list_projects",
    )
    payload = incident.to_dict()
    assert payload["correlation_id"].startswith("err-")
    assert payload["exception_type"] == "RuntimeError"
    assert state["workbench.runtime_diagnostics.incidents"]


def test_run_with_boundary_preserves_success_and_captures_failure() -> None:
    state: dict[str, object] = {}
    value, incident = run_with_workbench_boundary(
        state, lambda: 42, boundary="test", operation="success"
    )
    assert value == 42 and incident is None

    value, incident = run_with_workbench_boundary(
        state,
        lambda: (_ for _ in ()).throw(ValueError("bad")),
        boundary="test",
        operation="failure",
    )
    assert value is None
    assert incident is not None and incident.exception_type == "ValueError"

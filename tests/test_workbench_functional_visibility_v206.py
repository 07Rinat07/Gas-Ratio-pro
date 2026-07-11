from __future__ import annotations

import inspect
from pathlib import Path

from app import workbench_renderer


def test_native_workspace_does_not_insert_a_fixed_height_empty_html_shell() -> None:
    """Regression: an empty HTML block previously pushed real widgets below the fold."""
    source = inspect.getsource(workbench_renderer._render_native_streamlit_layout)
    assert 'markdown("<div class=\'workbench-workspace-shell\'>"' not in source
    assert "render_modern_workbench_workspace(active_navigation_id)" in source
    assert "Workspace host:" in source


def test_workspace_shell_css_no_longer_reserves_an_empty_viewport() -> None:
    css = workbench_renderer.build_workbench_responsive_css()
    shell_rule = next(line for line in css.splitlines() if line.startswith(".workbench-workspace-shell"))
    assert "min-height:calc(100vh" not in shell_rule


def test_real_workflow_routes_are_bound_to_existing_production_renderers() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "_render_workbench_las_workspace(logger, project)" in source
    assert "_render_interpretation_graphs_tab(logger, project)" in source
    assert "_render_project_exports_panel(project, logger)" in source
    assert "_render_documentation_tab()" in source

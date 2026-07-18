from __future__ import annotations

import inspect
from pathlib import Path

from app import workbench_renderer


def test_native_workspace_does_not_insert_a_fixed_height_empty_html_shell() -> None:
    """The native renderer exposes real controls and no reserved empty viewport."""
    from app.workbench_renderer import render_streamlit_workbench

    class Container:
        def __init__(self, owner): self.owner = owner
        def __enter__(self): return self.owner
        def __exit__(self, exc_type, exc, tb): return False

    class FakeStreamlit:
        def __init__(self):
            self.markdown_calls = []
            self.button_keys = []
        def markdown(self, body, *args, **kwargs): self.markdown_calls.append(str(body))
        def button(self, label, *args, **kwargs):
            self.button_keys.append(str(kwargs.get("key", "")))
            return False
        def columns(self, spec, *args, **kwargs):
            return [Container(self) for _ in range(spec if isinstance(spec, int) else len(spec))]
        def info(self, body, *args, **kwargs): self.markdown_calls.append(str(body))

    fake = FakeStreamlit()
    render_streamlit_workbench({}, fake)
    html = "\n".join(fake.markdown_calls)
    assert "workbench_quick_nav_las_workspace" in fake.button_keys
    assert "Активная рабочая область" in html
    assert "<div class='workbench-workspace-shell'>" not in html

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

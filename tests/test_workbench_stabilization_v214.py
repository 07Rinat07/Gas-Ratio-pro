from pathlib import Path

from app.workbench_renderer import render_streamlit_workbench
from core.workbench_ui_providers import WorkbenchUIProviderService
from core.workbench_context import WorkspaceContext


class _Container:
    def __init__(self, owner): self.owner = owner
    def __enter__(self): return self.owner
    def __exit__(self, exc_type, exc, tb): return False


class _FakeStreamlit:
    def __init__(self): self.buttons = []
    def markdown(self, *args, **kwargs): return None
    def button(self, label, *args, **kwargs):
        self.buttons.append(str(label))
        return False
    def columns(self, spec, *args, **kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        return [_Container(self) for _ in range(count)]
    def info(self, *args, **kwargs): return None


def test_renderer_does_not_duplicate_navigation_or_dock_actions_in_ribbon():
    fake = _FakeStreamlit()
    render_streamlit_workbench({}, fake)
    assert "Collapse Explorer" not in fake.buttons
    assert "Collapse Properties" not in fake.buttons
    assert not any(label.startswith("● Dashboard") for label in fake.buttons)


def test_project_tree_uses_real_project_counts():
    state = {"workbench_project_counts": {"calculations": 3, "correlations": 2, "reports": 1, "exports": 4}}
    context = WorkspaceContext.from_state({})
    payload = WorkbenchUIProviderService(state).build(context, {"tool": {"title": "Dashboard"}})
    counts = {item["id"]: item.get("count") for item in payload.project_tree}
    assert counts["tree.calculations"] == 3
    assert counts["tree.correlation"] == 2
    assert counts["tree.reports"] == 1
    assert counts["tree.exports"] == 4


def test_saved_calculation_archive_is_opt_in():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "Архив расчетов проекта" in source
    assert "Показать сохраненные расчеты" in source
    assert "Текущая рабочая сессия пуста" in source

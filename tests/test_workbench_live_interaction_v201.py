from __future__ import annotations

from app.workbench_renderer import render_streamlit_workbench
from core.build_info import BUILD_CHANNEL, BUILD_VERSION


class Container:
    def __init__(self, owner):
        self.owner = owner
    def __enter__(self):
        return self.owner
    def __exit__(self, exc_type, exc, tb):
        return False


class FakeStreamlit:
    def __init__(self, pressed_key: str = ""):
        self.pressed_key = pressed_key
        self.markdown_calls: list[str] = []
        self.button_calls: list[tuple[str, str, dict]] = []
    def markdown(self, body, *args, **kwargs):
        self.markdown_calls.append(str(body))
    def button(self, label, *args, **kwargs):
        key = str(kwargs.get("key", ""))
        self.button_calls.append((str(label), key, dict(kwargs)))
        return key == self.pressed_key
    def columns(self, spec, *args, **kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        return [Container(self) for _ in range(count)]
    def info(self, body, *args, **kwargs):
        self.markdown_calls.append(str(body))


def test_v201_build_identity():
    assert BUILD_VERSION == "v222"
    assert BUILD_CHANNEL == "stable"


def test_empty_workspace_exposes_command_backed_quick_actions():
    fake = FakeStreamlit()
    render_streamlit_workbench({}, fake)
    labels = [label for label, _key, _kwargs in fake.button_calls]
    assert "Open LAS Workspace" in labels
    assert "Open Interpretation" in labels
    assert "Open Reports" in labels


def test_quick_action_changes_workspace_through_command_registry():
    state: dict = {}
    fake = FakeStreamlit("workbench_quick_nav_las_workspace")
    results = render_streamlit_workbench(state, fake)
    assert results and results[0].executed is True
    assert results[0].command_id == "workbench.navigation.select"
    assert state["workbench_active_navigation"] == "nav.las_workspace"


def test_workspace_context_and_title_reflect_navigation_after_rerender():
    state: dict = {}
    render_streamlit_workbench(state, FakeStreamlit("workbench_quick_nav_interpretation"))
    second = FakeStreamlit()
    render_streamlit_workbench(state, second)
    html = "\n".join(second.markdown_calls)
    assert "Active workspace:" in html
    assert "interpretation" in html
    assert "Interpretation" in html

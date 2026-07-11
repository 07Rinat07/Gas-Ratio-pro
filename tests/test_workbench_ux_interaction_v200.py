from __future__ import annotations

from app.workbench_renderer import (
    WORKBENCH_LAST_UI_ACTION_KEY,
    build_streamlit_workbench_adapter,
    build_workbench_responsive_css,
    render_streamlit_workbench,
)
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


def test_current_build_identity_keeps_v200_interaction_contract():
    assert BUILD_VERSION == "v204"
    assert BUILD_CHANNEL == "workbench-functional-integration"


def test_titlebar_is_pushed_below_streamlit_system_header():
    css = build_workbench_responsive_css()
    assert "padding:2.65rem .55rem .2rem" in css
    assert ".workbench-titlebar { position:relative; z-index:2" in css


def test_navigation_button_mutates_state_and_records_visible_feedback():
    state: dict = {}
    fake = FakeStreamlit("workbench_toolbar_toolbar_navigation_nav_las_workspace")
    results = render_streamlit_workbench(state, fake)

    assert results and results[0].executed
    assert state["workbench_active_navigation"] == "nav.las_workspace"
    assert state[WORKBENCH_LAST_UI_ACTION_KEY]["executed"] is True

    second = FakeStreamlit()
    render_streamlit_workbench(state, second)
    html = "\n".join(second.markdown_calls)
    assert "workbench-command-feedback" in html
    assert "LAS Workspace" in html


def test_toolbar_hides_redundant_activate_and_mutually_exclusive_restore_actions():
    state: dict = {}
    fake = FakeStreamlit()
    render_streamlit_workbench(state, fake)
    labels = [label for label, _key, _kwargs in fake.button_calls]

    assert "Activate tool" not in labels
    assert "Collapse Explorer" in labels
    assert "Collapse Properties" in labels
    assert "Restore Explorer" not in labels
    assert "Restore Properties" not in labels
    assert any(label.startswith("● Dashboard") for label in labels)


def test_current_navigation_is_primary_and_disabled():
    fake = FakeStreamlit()
    render_streamlit_workbench({}, fake)
    dashboard = next(item for item in fake.button_calls if item[0].startswith("● Dashboard"))
    assert dashboard[2]["type"] == "primary"
    assert dashboard[2]["disabled"] is True

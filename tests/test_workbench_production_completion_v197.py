from __future__ import annotations

from contextlib import nullcontext

from app.streamlit_app import _run_modern_workbench
from app.workbench_renderer import render_streamlit_workbench
from core.command_framework import CommandExecutionResult


class NativeContainer:
    def __init__(self, owner):
        self.owner = owner
    def __enter__(self):
        return self.owner
    def __exit__(self, exc_type, exc, tb):
        return False


class NativeFakeStreamlit:
    def __init__(self, pressed_key: str = ""):
        self.pressed_key = pressed_key
        self.markdown_calls = []
        self.button_calls = []
        self.column_calls = []
        self.info_calls = []
    def markdown(self, body, *args, **kwargs):
        self.markdown_calls.append(str(body))
    def button(self, label, *args, **kwargs):
        key = str(kwargs.get("key", ""))
        self.button_calls.append((str(label), key))
        return key == self.pressed_key
    def columns(self, spec, *args, **kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        self.column_calls.append(spec)
        return [NativeContainer(self) for _ in range(count)]
    def info(self, body, *args, **kwargs):
        self.info_calls.append(str(body))


def test_native_renderer_uses_real_streamlit_regions_instead_of_cross_call_html_nesting():
    fake = NativeFakeStreamlit()
    render_streamlit_workbench({}, fake)

    assert len(fake.column_calls) >= 2
    assert any(isinstance(spec, list) and len(spec) == 3 for spec in fake.column_calls)
    html = "\n".join(fake.markdown_calls)
    assert "workbench-titlebar" in html
    assert "workbench-pane-title" in html
    assert "workbench-properties" in html
    assert "workbench-statusbar" in html
    assert "Активная рабочая область" in html

def test_native_renderer_button_returns_command_execution_result_with_executed_contract():
    fake = NativeFakeStreamlit("workbench_menu_las")
    results = render_streamlit_workbench({}, fake)
    assert len(results) == 1
    assert all(isinstance(item, CommandExecutionResult) for item in results)
    assert all(hasattr(item, "executed") for item in results)
    assert not any(hasattr(item, "success") for item in results)


def test_production_entry_point_checks_executed_not_removed_success_attribute(monkeypatch):
    class AppFake(NativeFakeStreamlit):
        def __init__(self):
            super().__init__()
            self.rerun_count = 0
            self.page_config = None
        def set_page_config(self, **kwargs):
            self.page_config = kwargs
        def rerun(self):
            self.rerun_count += 1

    fake = AppFake()
    result = CommandExecutionResult("x", executed=True)
    monkeypatch.setattr("app.streamlit_app.st", fake)
    monkeypatch.setattr("app.workbench_renderer.render_streamlit_workbench", lambda state, st: (result,))
    monkeypatch.setattr(
        "app.streamlit_app._application_state_controller",
        lambda: type(
            "C",
            (),
            {
                "state": {},
                "context": lambda self: type("Context", (), {"project_id": "default"})(),
            },
        )(),
    )
    monkeypatch.setattr("app.streamlit_app.configure_logging", lambda: type("L", (), {"info": lambda self, *a, **k: None})())
    monkeypatch.setattr("app.streamlit_app._app_icon_data_uri", lambda: "")

    _run_modern_workbench()
    assert fake.rerun_count == 1

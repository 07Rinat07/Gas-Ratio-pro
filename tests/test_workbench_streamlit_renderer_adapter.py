from __future__ import annotations

from app.workbench_renderer import (
    WORKBENCH_RENDERER_NAME,
    build_streamlit_workbench_adapter,
    dispatch_workbench_renderer_action,
    render_streamlit_workbench_contract,
)
from core.workbench_shell import WORKBENCH_ACTIVE_DOCK_PANE_KEY, WORKBENCH_ACTIVE_NAVIGATION_KEY


class FakeStreamlit:
    def __init__(self, clicked_keys=()):
        self.clicked_keys = set(clicked_keys)
        self.markdown_calls = []
        self.button_calls = []

    def markdown(self, body, *args, **kwargs):
        self.markdown_calls.append(str(body))

    def button(self, label, *args, **kwargs):
        key = kwargs.get("key", "")
        self.button_calls.append((label, key))
        return key in self.clicked_keys


def test_streamlit_workbench_adapter_builds_renderer_contract():
    adapter = build_streamlit_workbench_adapter({})
    payload = adapter.payload()

    assert payload["renderer"] == WORKBENCH_RENDERER_NAME
    assert payload["navigation"][0]["id"] == "nav.dashboard"
    assert "action.select_navigation" in adapter.contract.action_ids()


def test_streamlit_renderer_dispatches_action_through_command_registry():
    state = {}
    adapter = build_streamlit_workbench_adapter(state)

    result = dispatch_workbench_renderer_action(
        adapter.contract,
        adapter.registry,
        "action.select_navigation",
        {"navigation_id": "nav.reports"},
    )

    assert result.executed is True
    assert result.command_id == "workbench.navigation.select"
    assert state[WORKBENCH_ACTIVE_NAVIGATION_KEY] == "nav.reports"


def test_streamlit_renderer_click_translates_to_command_without_direct_state_mutation():
    state = {}
    adapter = build_streamlit_workbench_adapter(state)
    fake_st = FakeStreamlit(clicked_keys=("workbench_nav_nav_exports", "workbench_dock_dock_properties"))

    results = render_streamlit_workbench_contract(adapter.contract, adapter.registry, fake_st)

    assert [result.command_id for result in results] == [
        "workbench.navigation.select",
        "workbench.dock.activate",
    ]
    assert state[WORKBENCH_ACTIVE_NAVIGATION_KEY] == "nav.exports"
    assert state[WORKBENCH_ACTIVE_DOCK_PANE_KEY] == "dock.properties"
    assert any("Modern Workbench" in call for call in fake_st.markdown_calls)
    assert any(key == "workbench_nav_nav_exports" for _label, key in fake_st.button_calls)

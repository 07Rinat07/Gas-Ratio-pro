from core.workbench_shell import (
    WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID,
    WORKBENCH_SELECT_NAVIGATION_COMMAND_ID,
    WorkbenchShellBuilder,
    build_workbench_renderer_contract,
)


def test_renderer_contract_exposes_stable_payload_sections():
    model = WorkbenchShellBuilder({}).build()

    contract = build_workbench_renderer_contract(model)
    payload = contract.to_dict()

    assert payload["version"] == "workbench-renderer-contract"
    assert payload["renderer"] == "streamlit"
    assert payload["navigation"]
    assert payload["dock_regions"]["center"] == ["dock.workspace_area"]
    assert payload["interaction"]["active_navigation_id"] == "nav.dashboard"
    assert payload["interaction"]["active_dock_pane_id"] == "dock.workspace_area"


def test_renderer_contract_lists_only_command_backed_actions():
    model = WorkbenchShellBuilder({}).build()

    contract = build_workbench_renderer_contract(model)
    actions = {item["id"]: item for item in contract.to_dict()["actions"]}

    assert contract.action_ids() == (
        "action.select_navigation",
        "action.activate_dock_pane",
    )
    assert actions["action.select_navigation"]["command_id"] == WORKBENCH_SELECT_NAVIGATION_COMMAND_ID
    assert actions["action.select_navigation"]["payload_schema"] == {"navigation_id": "string"}
    assert actions["action.activate_dock_pane"]["command_id"] == WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID
    assert actions["action.activate_dock_pane"]["payload_schema"] == {"pane_id": "string"}


def test_renderer_contract_reflects_command_updated_state():
    state = {}
    builder = WorkbenchShellBuilder(state)
    builder.command_registry.execute(WORKBENCH_SELECT_NAVIGATION_COMMAND_ID, {"navigation_id": "nav.reports"})
    builder.command_registry.execute(WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID, {"pane_id": "dock.properties"})

    payload = build_workbench_renderer_contract(builder.build(), renderer="streamlit-modern").to_dict()

    assert payload["renderer"] == "streamlit-modern"
    assert payload["interaction"]["active_navigation_id"] == "nav.reports"
    assert payload["interaction"]["active_dock_pane_id"] == "dock.properties"
    action_metadata = {item["id"]: item["metadata"] for item in payload["actions"]}
    assert action_metadata["action.select_navigation"]["active_navigation_id"] == "nav.reports"
    assert action_metadata["action.activate_dock_pane"]["active_dock_pane_id"] == "dock.properties"

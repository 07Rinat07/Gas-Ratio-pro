from core.workbench_context import WorkspaceContext
from core.workbench_controller import build_workbench_controller
from core.workbench_ui_providers import WorkbenchUIProviderService


def _provider_payload(state: dict):
    controller = build_workbench_controller(state)
    context = WorkspaceContext.from_state(state, controller.shell())
    return WorkbenchUIProviderService(state).build(context, {"tool": {"title": "Documentation", "status": "ready"}})


def test_properties_has_useful_empty_state_without_none_rows() -> None:
    payload = _provider_payload({"active_project_id": "default"})
    rows = payload.properties
    assert rows[0]["label"] == "Nothing selected"
    assert "Choose a project" in rows[0]["value"]
    encoded = str(rows)
    assert "Selection', 'value': 'None" not in encoded
    assert "Object', 'value': '—" not in encoded


def test_selected_project_hydrates_contextual_properties() -> None:
    state = {"active_project_id": "default"}
    controller = build_workbench_controller(state)
    controller.select_object("project", "default", {"title": "Основной проект", "count": 1, "status": "ready"})
    payload = _provider_payload(state)
    rows = {item["label"]: item["value"] for item in payload.properties}
    assert rows["Selected"] == "Project"
    assert rows["Object"] == "default"
    assert rows["Title"] == "Основной проект"
    assert rows["Count"] == "1"
    assert rows["Status"] == "ready"


def test_collapsed_properties_does_not_render_diagnostics_in_narrow_rail() -> None:
    source = open("app/workbench_renderer.py", encoding="utf-8").read()
    assert 'if properties_open and diagnostics_enabled()' in source
    assert 'widths = [1.15 if explorer_open else 0.10, 4.9, 1.35 if properties_open else 0.10]' in source


def test_project_tree_buttons_select_objects_before_navigation() -> None:
    source = open("app/workbench_renderer.py", encoding="utf-8").read()
    assert 'controller.select_object(target, object_id, metadata)' in source
    assert 'metadata.setdefault("navigation_id", navigation_id)' in source

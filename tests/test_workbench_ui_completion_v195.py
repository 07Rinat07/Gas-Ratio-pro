from core.workbench_controller import build_workbench_controller
from core.workbench_ui_layout import build_workbench_ui_layout
from app.workbench_renderer import build_workbench_responsive_css, render_streamlit_workbench


class FakeStreamlit:
    def __init__(self):
        self.markdown_calls = []
        self.button_calls = []
    def markdown(self, body, *args, **kwargs):
        self.markdown_calls.append(str(body))
    def button(self, label, *args, **kwargs):
        self.button_calls.append((str(label), kwargs.get("key", "")))
        return False


def test_ui_layout_contract_fills_all_engineering_regions():
    payload = build_workbench_controller({}).view_model()
    layout = build_workbench_ui_layout(payload).to_dict()
    assert layout["regions"] == {
        "left": "project_explorer", "center": "workspace_host", "right": "properties",
        "top": "command_toolbar", "bottom": "status_bar",
    }
    assert layout["workspace"]["id"] == "workspace.host"
    assert [node["title"] for node in layout["project_tree"]][1:] == [
        "Wells", "LAS", "Curves", "Correlation", "Calculations", "Reports", "Exports"
    ]
    assert {item["title"] for item in layout["toolbar"]} >= {"File", "Project", "Data", "Las", "Interpretation", "Report", "Settings"}


def test_ui_layout_contract_is_serializable_and_has_no_runtime_objects():
    import json
    payload = build_workbench_controller({}).view_model()
    encoded = json.dumps(build_workbench_ui_layout(payload).to_dict())
    assert "DataFrame" not in encoded
    assert "WorkbenchCommandRegistry" not in encoded


def test_streamlit_renderer_outputs_full_workspace_structure():
    fake = FakeStreamlit()
    render_streamlit_workbench({}, fake)
    html = "\n".join(fake.markdown_calls)
    assert "workbench-main" in html
    assert "Project Explorer" in html
    assert "Workspace host" in html
    assert "Properties" in html
    assert "Status bar" in html
    assert "workbench-toolbar" in html


def test_responsive_css_uses_three_column_desktop_and_single_column_mobile():
    css = build_workbench_responsive_css()
    assert "@media (min-width: 1024px)" in css
    assert "grid-template-columns:minmax(14rem, 18rem) minmax(0, 1fr) minmax(16rem, 20rem)" in css
    assert "@media (max-width: 1023px)" in css
    assert ".workbench-main { grid-template-columns:1fr; }" in css

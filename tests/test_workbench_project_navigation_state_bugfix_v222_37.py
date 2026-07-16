from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py").read_text(encoding="utf-8")


def test_project_navigation_sections_uses_controller_api_not_missing_dict_get():
    start = SOURCE.index("def _workbench_project_navigation_sections")
    end = SOURCE.index("\ndef _build_workbench_project_navigation", start)
    function_source = SOURCE[start:end]

    assert 'state.get_value("workbench_project_explorer_requested_sections", ())' in function_source
    assert 'state.get_value("workbench_project_explorer_search")' in function_source
    assert "state.get(" not in function_source

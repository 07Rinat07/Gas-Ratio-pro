from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    marker = f"def {name}"
    start = SOURCE.index(marker)
    next_def = SOURCE.find("\ndef ", start + len(marker))
    if next_def == -1:
        return SOURCE[start:]
    return SOURCE[start:next_def]


def test_project_selector_uses_application_state_controller() -> None:
    body = _function_source("_render_project_selector")

    assert "state = _application_state_controller()" in body
    assert "state.consume_pending_project_activation()" in body
    assert "state.ensure_project(current_project_id)" in body
    assert "state.request_project_activation(selected_project_id)" in body
    assert "st.session_state[ACTIVE_PROJECT_ID_KEY]" not in body


def test_recent_projects_manager_uses_pending_project_activation() -> None:
    body = _function_source("_render_recent_projects_manager")

    assert "_application_state_controller().request_project_activation(selected_id)" in body
    assert "_application_state_controller().request_project_activation(DEFAULT_PROJECT_ID)" in body
    assert "st.session_state[ACTIVE_PROJECT_ID_KEY]" not in body

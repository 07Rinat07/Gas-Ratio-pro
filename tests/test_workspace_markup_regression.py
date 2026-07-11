from pathlib import Path

SOURCE = Path('app/streamlit_app.py').read_text(encoding='utf-8')


def test_workspace_uses_supported_streamlit_html_renderer():
    assert 'import streamlit.components.v1 as components' not in SOURCE
    assert 'components.html(workspace_component_html' not in SOURCE
    assert 'html_renderer = getattr(st, "html", None)' in SOURCE
    assert 'st.markdown(workspace_component_html, unsafe_allow_html=True)' in SOURCE
    assert 'workspace_component_html = dedent' in SOURCE


def test_workspace_keeps_layout_markup_inside_supported_html_payload():
    assert 'data-dashboard-information-hierarchy="workspace-v1"' in SOURCE
    assert 'class="dashboard-layout dashboard-information-priority"' in SOURCE
    assert 'id="dashboard-project-status"' in SOURCE
    assert 'id="dashboard-favorites"' in SOURCE


def test_workspace_component_has_responsive_grid_guard():
    assert 'overflow-x: hidden' in SOURCE
    assert '@media (max-width: 1366px)' in SOURCE
    assert 'grid-template-columns: repeat(12, minmax(0, 1fr))' in SOURCE

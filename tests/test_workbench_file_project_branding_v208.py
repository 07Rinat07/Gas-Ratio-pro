from pathlib import Path

from app.workbench_renderer import _branding_logo_data_uri, WORKBENCH_MENU_PANEL_KEY
from core.build_info import BUILD_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_v208_build_identity():
    assert BUILD_VERSION == "v221-rc2"


def test_title_bar_uses_real_brand_logo():
    source = (ROOT / "app" / "workbench_renderer.py").read_text(encoding="utf-8")
    assert "workbench-logo-image" in source
    assert "assets\" / \"branding\" / \"gas_ratio_pro_logo.png" in source
    assert _branding_logo_data_uri().startswith("data:image/")


def test_file_and_project_are_interactive_panels():
    source = (ROOT / "app" / "workbench_renderer.py").read_text(encoding="utf-8")
    assert '("File", "menu.file")' in source
    assert '("Project", "menu.project")' in source
    assert WORKBENCH_MENU_PANEL_KEY == "workbench_menu_panel"
    assert "workbench_file_open_project" in source
    assert "workbench_project_open_" in source


def test_documentation_does_not_overlay_second_logo():
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    function = source[source.index("def _render_documentation_tab"):source.index("def _render_las_editor")]
    assert "docs-hero-brand-badge" not in function
    assert "logo_html = \"\"" in function

from pathlib import Path

from app.workbench_renderer import _branding_logo_data_uri, WORKBENCH_MENU_PANEL_KEY
from core.build_info import BUILD_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_v208_build_identity():
    assert BUILD_VERSION.startswith("v225.")

def test_title_bar_uses_real_brand_logo():
    source = (ROOT / "app" / "workbench_renderer.py").read_text(encoding="utf-8")
    assert "workbench-logo-image" in source
    assert "assets\" / \"branding\" / \"gas_ratio_pro_logo.png" in source
    assert _branding_logo_data_uri().startswith("data:image/")


def test_file_and_project_are_interactive_panels():
    source = (ROOT / "app" / "workbench_renderer.py").read_text(encoding="utf-8")
    assert '(i18n("menu.file"), "menu.file")' in source
    assert '(i18n("menu.project"), "menu.project")' in source
    assert WORKBENCH_MENU_PANEL_KEY == "workbench_menu_panel"
    assert "workbench_file_open_project" in source
    assert "workbench_project_open_" in source


def test_documentation_does_not_overlay_second_logo():
    from app import streamlit_app as app

    contract = app._documentation_center_behavior_contract()
    assert contract.logo_overlay_enabled is False
    assert app._documentation_hero_data_uri().startswith("data:image/")

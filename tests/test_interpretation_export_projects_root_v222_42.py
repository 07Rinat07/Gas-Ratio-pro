from pathlib import Path


APP_SOURCE = (Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py").read_text(encoding="utf-8")


def _professional_export_panel_source() -> str:
    start = APP_SOURCE.index("def _render_professional_export_panel(")
    end = APP_SOURCE.index("\ndef ", start + 4)
    return APP_SOURCE[start:end]


def test_professional_export_panel_uses_defined_project_root() -> None:
    panel = _professional_export_panel_source()
    assert "root=LAS_CORRELATION_PROJECTS_ROOT" in panel
    assert "root=PROJECTS_ROOT" not in panel


def test_project_root_constant_is_defined_before_export_panel() -> None:
    definition = APP_SOURCE.index("LAS_CORRELATION_PROJECTS_ROOT =")
    panel = APP_SOURCE.index("def _render_professional_export_panel(")
    assert definition < panel


def test_all_workspace_route_names_are_present_after_bugfix() -> None:
    for route in (
        "nav.dashboard",
        "nav.data",
        "nav.las_workspace",
        "nav.correlation",
        "nav.interpretation",
        "nav.reports",
        "nav.exports",
    ):
        assert route in APP_SOURCE

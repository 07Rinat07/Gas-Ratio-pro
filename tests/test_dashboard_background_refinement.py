from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("docs/archive/legacy_plans/project_plan_v5_legacy.md").read_text(encoding="utf-8")


def test_dashboard_background_refinement_registry_is_present():
    assert "DASHBOARD_BACKGROUND_REFINEMENT" in SOURCE
    assert "dashboard-background-refinement" in SOURCE
    assert 'data-dashboard-background-refinement="center-contained"' in SOURCE


def test_dashboard_background_is_centered_and_reduced():
    assert "clamp(210px, 18vw, 330px) auto" in SOURCE
    assert "center bottom 1.1rem" in SOURCE
    assert "clamp(160px, 14vw, 230px) auto" in SOURCE
    assert "clamp(145px, 13vw, 205px) auto" in SOURCE


def test_sidebar_brand_art_is_not_cropped():
    assert "background-size: 100% 100%, contain" in SOURCE
    assert "background-position: center center, center center" in SOURCE


def test_background_refinement_recorded_in_plan():
    assert "Dashboard UX Refactoring → Background Refinement" in PLAN
    assert "брендовый арт теперь центрирован" in PLAN
    assert "- [x] Refine dashboard background centering and scaling." in PLAN

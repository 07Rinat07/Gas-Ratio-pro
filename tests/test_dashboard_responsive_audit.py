from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("docs/project_plan.md").read_text(encoding="utf-8")


def test_dashboard_responsive_audit_marker_is_present():
    assert 'dashboard-responsive-audit' in SOURCE
    assert 'data-dashboard-responsive-audit="notebook-validated"' in SOURCE


def test_dashboard_has_explicit_notebook_and_desktop_breakpoints():
    for marker in (
        '@media (max-width: 1366px)',
        '@media (max-width: 1440px)',
        '@media (min-width: 1441px) and (max-width: 1600px)',
        '@media (min-width: 1601px)',
    ):
        assert marker in SOURCE


def test_dashboard_prevents_horizontal_overflow_without_deleting_blocks():
    assert 'overflow-x: clip' in SOURCE
    assert 'width: min(100%, 100vw)' in SOURCE
    assert 'max-width: 100%' in SOURCE
    for section_id in (
        'id="dashboard-project-status"',
        'id="dashboard-projects"',
        'id="dashboard-recent-las"',
        'id="dashboard-calculations"',
        'id="dashboard-reports"',
        'id="dashboard-activity"',
        'id="dashboard-favorites"',
    ):
        assert section_id in SOURCE


def test_dashboard_long_text_wraps_inside_cards():
    assert 'overflow-wrap: anywhere' in SOURCE
    assert '.dashboard-3 .dashboard-list-row > div:first-child' in SOURCE


def test_responsive_audit_recorded_in_plan():
    assert '- [x] Run responsive layout audit after each UI stage.' in PLAN
    assert 'Dashboard UX Refactoring → Responsive Layout Audit' in PLAN
    assert '1366×768, 1440×900, 1600×900 и 1920×1080' in PLAN

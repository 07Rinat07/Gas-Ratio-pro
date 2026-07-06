from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("docs/project_plan.md").read_text(encoding="utf-8")


def test_dashboard_3_branch_marker_and_layout_are_present():
    assert 'data-dashboard-branch="Dashboard 3.0"' in SOURCE
    assert 'dashboard-3-branch' in SOURCE
    assert '.dashboard-3 .dashboard-content' in SOURCE
    assert 'grid-template-columns: var(--d3-side) minmax(0, 1fr)' in SOURCE


def test_dashboard_3_restores_useful_information_blocks():
    for marker in (
        'id="dashboard-project-status"',
        'id="dashboard-projects"',
        'id="dashboard-recent-las"',
        'id="dashboard-calculations"',
        'id="dashboard-activity"',
        'id="dashboard-project-health"',
        'id="dashboard-license"',
    ):
        assert marker in SOURCE


def test_dashboard_3_has_laptop_breakpoints_and_centered_background():
    assert '@media (max-width: 1440px)' in SOURCE
    assert '@media (max-width: 1200px)' in SOURCE
    assert 'background-position: center center, center center, center center, center bottom 1.4rem' in SOURCE
    assert 'clamp(230px, 20vw, 360px) auto' in SOURCE


def test_dashboard_3_is_recorded_in_project_plan():
    assert 'Dashboard 3.0' in PLAN
    assert 'восстановлен как полноценная рабочая панель' in PLAN

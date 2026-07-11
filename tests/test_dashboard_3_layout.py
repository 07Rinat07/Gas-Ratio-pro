from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("docs/archive/legacy_plans/project_plan_v5_legacy.md").read_text(encoding="utf-8")


def test_project_workspace_branch_marker_and_layout_are_present():
    assert 'data-dashboard-branch="Project Workspace 1.0"' in SOURCE
    assert 'data-dashboard-workspace="project-workspace-1"' in SOURCE
    assert 'dashboard-3-branch' in SOURCE
    assert '.dashboard-3 .dashboard-content' in SOURCE
    assert 'grid-template-columns: minmax(0, 1fr)' in SOURCE


def test_project_workspace_restores_useful_information_blocks():
    for marker in (
        'id="dashboard-project-status"',
        'id="dashboard-projects"',
        'id="dashboard-recent-las"',
        'id="dashboard-calculations"',
        'id="dashboard-reports"',
        'id="dashboard-activity"',
        'id="dashboard-favorites"',
    ):
        assert marker in SOURCE


def test_project_workspace_has_laptop_breakpoints_and_centered_background():
    assert '@media (max-width: 1440px)' in SOURCE
    assert '@media (max-width: 1200px)' in SOURCE
    assert 'background-position: center center, center center, center center, center bottom 1.1rem' in SOURCE
    assert 'clamp(210px, 18vw, 330px) auto' in SOURCE


def test_project_workspace_is_recorded_in_project_plan():
    assert 'Project Workspace 1.0' in PLAN
    assert 'центральная область больше не повторяет Sidebar' in PLAN

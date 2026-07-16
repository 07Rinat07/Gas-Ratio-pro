from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")


def test_dashboard_information_hierarchy_marker_and_core_sections():
    assert 'data-dashboard-hierarchy="information"' in SOURCE
    assert 'data-dashboard-information-hierarchy="workspace-v1"' in SOURCE
    assert 'id="dashboard-project-status"' in SOURCE
    assert 'id="dashboard-recent-las"' in SOURCE
    assert 'id="dashboard-calculations"' in SOURCE
    assert 'id="dashboard-reports"' in SOURCE
    assert 'id="dashboard-favorites"' in SOURCE
    assert 'i18n("dashboard.section.projects")' in SOURCE
    assert 'i18n("dashboard.section.las")' in SOURCE
    assert 'i18n("dashboard.section.calculations")' in SOURCE
    assert 'i18n("dashboard.section.reports")' in SOURCE
    assert 'i18n("dashboard.section.activity")' in SOURCE
    assert 'i18n("dashboard.section.favorites")' in SOURCE


def test_dashboard_removes_decorative_panels_from_hierarchy():
    assert '.dashboard-information-hierarchy .dashboard-card.news' in SOURCE
    assert '.dashboard-information-hierarchy .dashboard-card.tips' in SOURCE
    assert '.dashboard-information-hierarchy .dashboard-card.preview-card' in SOURCE
    assert 'Новости</h3>' not in SOURCE
    assert 'Полезные советы</h3>' not in SOURCE
    assert 'Быстрый просмотр: последний проект' not in SOURCE


def test_dashboard_hierarchy_grid_uses_productive_workspace_areas():
    assert '"projects projects projects projects las las las las calculations calculations calculations calculations"' in SOURCE
    assert '"reports reports reports reports activity activity activity activity favorites favorites favorites favorites"' in SOURCE
    assert '.dashboard-card.recent-las { grid-area: las; }' in SOURCE
    assert '.dashboard-card.calculations { grid-area: calculations; }' in SOURCE
    assert '.dashboard-3 .dashboard-card.reports { grid-area: reports; }' in SOURCE
    assert '.dashboard-3 .dashboard-card.favorites { grid-area: favorites; }' in SOURCE

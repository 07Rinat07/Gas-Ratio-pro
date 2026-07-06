from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")


def test_dashboard_information_hierarchy_marker_and_core_sections():
    assert 'data-dashboard-hierarchy="information"' in SOURCE
    assert 'data-dashboard-information-hierarchy="v4"' in SOURCE
    assert 'id="dashboard-project-status"' in SOURCE
    assert 'id="dashboard-recent-las"' in SOURCE
    assert 'id="dashboard-calculations"' in SOURCE
    assert 'Последние проекты' in SOURCE
    assert 'Последние LAS' in SOURCE
    assert 'Последние расчеты' in SOURCE
    assert 'Последняя активность' in SOURCE
    assert 'Статус лицензии' in SOURCE


def test_dashboard_removes_decorative_panels_from_hierarchy():
    assert '.dashboard-information-hierarchy .dashboard-card.news' in SOURCE
    assert '.dashboard-information-hierarchy .dashboard-card.tips' in SOURCE
    assert '.dashboard-information-hierarchy .dashboard-card.preview-card' in SOURCE
    assert 'Новости</h3>' not in SOURCE
    assert 'Полезные советы</h3>' not in SOURCE
    assert 'Быстрый просмотр: последний проект' not in SOURCE


def test_dashboard_hierarchy_grid_uses_productive_areas():
    assert '"status projects activity"' in SOURCE
    assert '"las quick calculations"' in SOURCE
    assert '"license license license"' in SOURCE
    assert '.dashboard-card.recent-las { grid-area: las; }' in SOURCE
    assert '.dashboard-card.calculations { grid-area: calculations; }' in SOURCE

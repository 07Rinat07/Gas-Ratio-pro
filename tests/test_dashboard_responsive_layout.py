from pathlib import Path


def test_laptop_dashboard_layout_uses_narrow_left_and_centered_background():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "dashboard-grid-optimized" in source
    assert 'data-dashboard-grid="optimized"' in source
    assert "minmax(8.2rem, 0.34fr)" in source
    assert "minmax(0, 1.36fr)" in source
    assert "center bottom" in source
    assert "dashboard-card.welcome p:nth-of-type(n+2)" in source


def test_notebook_dashboard_grid_prevents_horizontal_overflow():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "minmax(7.4rem, 0.30fr)" in source
    assert "minmax(0, 1.70fr)" in source
    assert "grid-template-areas:\n                    \"status projects\"\n                    \"las quick\"\n                    \"calculations activity\"\n                    \"license license\"" in source
    assert ".dashboard-card.news,\n            .dashboard-card.tips,\n            .dashboard-card.preview-card,\n            .dashboard-card.welcome { display: none; }" in source


def test_dashboard_cards_have_compact_laptop_metrics_and_actions():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "dashboard-metrics { grid-template-columns: repeat(2, minmax(0, 1fr))" in source
    assert "dashboard-actions { grid-template-columns: repeat(auto-fit, minmax(7.2rem, 1fr))" in source
    assert "dashboard-action-card { min-height: 3.45rem; padding: 0.46rem; }" in source
    assert ".dashboard-list-row { display: grid; grid-template-columns: minmax(0, 1fr) auto" in source
    assert "overflow: hidden" in source


def test_simplified_navigation_compacts_on_laptop():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "simplified-dashboard-navigation .app-nav-description { display: none; }" in source
    assert "Открыть: {label}" not in source
    assert "minmax(7.2rem, 1fr)" in source

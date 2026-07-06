from pathlib import Path


def test_laptop_dashboard_layout_uses_narrow_left_and_centered_background():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "minmax(11rem, 0.46fr)" in source
    assert "minmax(0, 1.22fr)" in source
    assert "center bottom" in source
    assert "dashboard-card.welcome p:nth-of-type(n+2)" in source


def test_dashboard_cards_have_compact_laptop_metrics_and_actions():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "dashboard-metrics { grid-template-columns: repeat(2, minmax(0, 1fr))" in source
    assert "dashboard-actions { grid-template-columns: repeat(3, minmax(0, 1fr))" in source
    assert "overflow: hidden" in source

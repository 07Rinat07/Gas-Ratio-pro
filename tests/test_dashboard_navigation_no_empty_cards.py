from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")


def test_dashboard_navigation_does_not_render_empty_card_wrappers():
    render_start = SOURCE.index("def _render_main_navigation")
    render_end = SOURCE.index("PAGE_LAYOUT_META", render_start)
    render_source = SOURCE[render_start:render_end]

    assert "no-empty-nav-cards" in render_source
    assert "app-nav-card" not in render_source
    assert "active_class" not in render_source
    assert "<div class=\"app-nav-card" not in render_source


def test_dashboard_navigation_keeps_single_button_per_item():
    render_start = SOURCE.index("def _render_main_navigation")
    render_end = SOURCE.index("PAGE_LAYOUT_META", render_start)
    render_source = SOURCE[render_start:render_end]

    assert "st.button(button_label" in render_source
    assert "Открыть:" not in render_source
    assert "app-nav-description" in render_source


def test_dashboard_navigation_css_hides_legacy_empty_cards():
    assert ".simplified-dashboard-navigation.no-empty-nav-cards .app-nav-card { display: none !important; }" in SOURCE
    assert "blank rectangles above navigation buttons" in SOURCE

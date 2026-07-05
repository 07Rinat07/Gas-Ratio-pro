from __future__ import annotations

from pathlib import Path

from projects.repository import ProjectRecord
from app import streamlit_app as app


def _project(project_id: str, name: str, updated_at: str = "2026-01-01T00:00:00Z") -> ProjectRecord:
    return ProjectRecord(id=project_id, name=name, updated_at=updated_at)


def test_dashboard_background_asset_is_embedded() -> None:
    data_uri = app._dashboard_background_data_uri()

    assert data_uri.startswith("data:image/png;base64,")
    assert len(data_uri) > 100


def test_dashboard_recent_projects_limit() -> None:
    projects = (_project("a", "A"), _project("b", "B"), _project("c", "C"), _project("d", "D"))

    recent = app._dashboard_recent_projects(projects, limit=3)

    assert tuple(project.id for project in recent) == ("a", "b", "c")


def test_dashboard_project_statistics_empty_storage(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app, "WELLS_STORAGE_ROOT", tmp_path / "wells")
    monkeypatch.setattr(app, "LAS_CORRELATION_PROJECTS_ROOT", tmp_path / "projects")
    active_project = _project("active", "Active")

    stats = app._dashboard_project_statistics(active_project, (active_project,))

    assert stats == {
        "projects": 1,
        "wells": 0,
        "las_files": 0,
        "calculations": 0,
        "exports": 0,
    }


def test_dashboard_news_items_are_dynamic(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app, "LAS_CORRELATION_PROJECTS_ROOT", tmp_path / "projects")
    active_project = _project("active", "Karakuik Project", updated_at="2026-02-03T04:05:06Z")

    news = app._dashboard_news_items(active_project)

    assert "Активный проект: Karakuik Project" in news
    assert "Проект обновлен: 2026-02-03T04:05:06Z" in news
    assert any(item.startswith("Сохраненных расчетов:") for item in news)


def test_dashboard_activity_empty_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app, "LAS_CORRELATION_PROJECTS_ROOT", tmp_path / "projects")

    activity = app._dashboard_activity_items(_project("active", "Active"))

    assert activity == ("Пока нет проектной активности", "Импортируйте LAS/CSV/XLSX или сохраните расчет")


def test_dashboard_tip_is_not_empty() -> None:
    assert app._dashboard_tip(_project("active", "Active")) in app.DASHBOARD_TIPS


def test_wide_layout_uses_full_available_width() -> None:
    label, max_width, _description = app._layout_profile_summary("wide")

    assert label == "Большой экран"
    assert "100vw" in max_width


def test_dashboard_shell_css_has_modern_application_shell() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert ".dashboard-side-rail { display: none; }" in source
    assert "calc(100vh - 4.2rem)" in source
    assert "background-position: left center" in source
    assert "dashboard-footer" in source
    assert "@media (max-width: 760px)" in source


def test_sidebar_is_compact_for_dashboard_workspace() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert 'section[data-testid="stSidebar"]' in source
    assert "14.6rem" in source
    assert "sidebar_project_search" in source


def test_dashboard_has_large_functional_action_cards() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "Создать / открыть проект" in source
    assert "functional-quick-actions" in source
    assert "dashboard_jump_" in source
    assert "dashboard-action-card" in source


def test_global_background_layer_is_available_for_all_tabs() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "--global-bg-image" in source
    assert "background-attachment: fixed" in source
    assert 'button[role="tab"]' in source


def test_main_navigation_replaces_small_streamlit_tabs() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "ACTIVE_MAIN_TAB_KEY" in source
    assert "_render_main_navigation" in source
    assert "st.tabs(list(APP_TABS))" not in source
    assert "Открыть: Старт" in source


def test_documentation_tab_uses_branded_background() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "docs-hero" in source
    assert "docs-panel" in source
    assert "var(--global-bg-image)" in source


def test_proprietary_license_file_exists() -> None:
    license_text = Path(app.ROOT_DIR / "LICENSE").read_text(encoding="utf-8")

    assert "Proprietary License" in license_text
    assert "Rinat Sarmuldin" in license_text
    assert "ura07srr@gmail.com" in license_text


def test_project_search_results_empty_query_returns_empty() -> None:
    assert app._project_search_results(_project("active", "Active"), "") == ()


def test_dashboard_transparency_is_less_aggressive() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "rgba(3, 7, 18, 0.22)" in source
    assert "rgba(4, 10, 24, 0.24)" in source
    assert "dashboard_project_search" in source


def test_branded_logo_asset_is_embedded() -> None:
    data_uri = app._branding_logo_data_uri()

    assert data_uri.startswith("data:image/png;base64,")
    assert len(data_uri) > 100


def test_responsive_profiles_cover_phone_laptop_and_large_screen() -> None:
    labels = app._layout_profile_options()

    assert "Телефон" in labels
    assert "Ноутбук" in labels
    assert "Большой экран" in labels

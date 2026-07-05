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
    assert "--brand-bg-position: right 3vw bottom 1.2rem" in source
    assert "background-size: 100% 100%, var(--brand-bg-size)" in source
    assert "dashboard-footer" in source
    assert "@media (max-width: 760px)" in source


def test_sidebar_is_modern_project_control_center() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert 'section[data-testid="stSidebar"]' in source
    assert "18.2rem" in source
    assert "sidebar-brand-card" in source
    assert "sidebar_quick_nav_" in source
    assert "sidebar_project_search" in source


def test_sidebar_helpers_report_health_and_recent_empty_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app, "LAS_CORRELATION_PROJECTS_ROOT", tmp_path / "projects")
    project = _project("active", "Active")

    assert app._sidebar_project_health({"las_files": 0, "calculations": 0, "wells": 0}, 0)[0] == "Пустой проект"
    assert app._sidebar_project_health({"las_files": 1, "calculations": 0, "wells": 0}, 1)[0] == "Готов к работе"
    assert app._sidebar_recent_project_items(project)[0]["label"] == "Нет недавних материалов"


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
    assert "docs-hero-banner" in source
    assert "docs-panel" in source
    assert "docs-hero-image" in source
    assert "docs-hero-brand-badge" in source
    assert "_documentation_hero_data_uri" in source


def test_documentation_hero_asset_is_embedded() -> None:
    data_uri = app._documentation_hero_data_uri()

    assert data_uri.startswith("data:image/png;base64,")
    assert len(data_uri) > 100


def test_proprietary_license_file_exists() -> None:
    license_text = Path(app.ROOT_DIR / "LICENSE").read_text(encoding="utf-8")

    assert "Proprietary License" in license_text
    assert "Rinat Sarmuldin" in license_text
    assert "ura07srr@gmail.com" in license_text


def test_project_search_results_empty_query_returns_empty() -> None:
    assert app._project_search_results(_project("active", "Active"), "") == ()


def test_dashboard_transparency_is_less_aggressive() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "rgba(3, 7, 18, 0.04)" in source
    assert "rgba(4, 10, 24, 0.08)" in source
    assert "rgba(5, 10, 22, 0.035)" in source
    assert "dashboard_project_search" in source


def test_brand_background_is_proportionally_scaled_not_cover_cropped() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "--brand-bg-size: clamp(300px, 42vw, 720px) auto" in source
    assert "background-size: var(--brand-bg-size)" in source
    assert "background-repeat: no-repeat, no-repeat" in source
    assert "@media (min-width: 1920px)" in source
    assert "@media (max-width: 900px)" in source


def test_branded_logo_asset_is_embedded() -> None:
    data_uri = app._branding_logo_data_uri()

    assert data_uri.startswith("data:image/png;base64,")
    assert len(data_uri) > 100


def test_responsive_profiles_cover_phone_laptop_and_large_screen() -> None:
    labels = app._layout_profile_options()

    assert "Телефон" in labels
    assert "Ноутбук" in labels
    assert "Большой экран" in labels


def test_dashboard_brand_visibility_layers_are_tuned() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "rgba(3, 7, 18, 0.04)" in source
    assert "rgba(4, 10, 24, 0.08)" in source
    assert "rgba(5, 10, 22, 0.035)" in source
    assert "backdrop-filter: blur(1.4px)" in source


def test_global_command_palette_entries_include_navigation_and_docs(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app, "LAS_CORRELATION_PROJECTS_ROOT", tmp_path / "projects")
    entries = app._command_palette_entries(_project("active", "Active"))

    titles = {entry["title"] for entry in entries}

    assert "LAS-редактор" in titles
    assert "Импорт LAS / CSV / Excel" in titles
    assert "Troubleshooting" in titles


def test_global_command_palette_filter_matches_keywords() -> None:
    entries = (
        {"title": "Импорт LAS / CSV / Excel", "category": "Данные", "target_tab": "Работа с данными", "description": "Загрузка", "keywords": "импорт las csv"},
        {"title": "Инструкции и документация", "category": "Справка", "target_tab": "Инструкции и документация", "description": "Help", "keywords": "docs help"},
    )

    filtered = app._filter_command_palette_entries(entries, "las", limit=4)

    assert len(filtered) == 1
    assert filtered[0]["target_tab"] == "Работа с данными"


def test_global_command_palette_rendering_is_present() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "COMMAND_PALETTE_QUERY_KEY" in source
    assert "_render_global_command_palette(active_project)" in source
    assert "command-palette-shell" in source
    assert "Ctrl+K / поиск по проекту" in source


def test_unified_page_layout_shell_is_available() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "PAGE_LAYOUT_META" in source
    assert "app-page-shell" in source
    assert "app-page-header" in source
    assert "app-page-badge" in source
    assert "_open_page_shell(active_tab)" in source
    assert "Темный workspace" in source


def test_page_layout_meta_has_all_workspace_tabs() -> None:
    for tab_name in app.APP_TABS:
        if tab_name == "Старт":
            continue
        meta = app._page_layout_meta(tab_name)
        assert meta["title"] == tab_name
        assert meta["subtitle"]
        assert meta["badge"]


def test_documentation_center_v2_has_quick_links_toc_faq_and_shortcuts() -> None:
    titles = app._documentation_quick_link_titles()
    toc = app._documentation_table_of_contents()
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "Быстрый старт" in titles
    assert "Диагностика" in titles
    assert any(item["anchor"] == "docs-shortcuts" for item in toc)
    assert any(item["anchor"] == "docs-faq" for item in toc)
    assert "DOCUMENTATION_FAQ" in source
    assert "DOCUMENTATION_SHORTCUTS" in source
    assert "docs-v2-grid" in source
    assert "docs-toc" in source
    assert "Gas Ratio Pro Documentation Center v2" in source


def test_documentation_center_v2_is_documented_in_project_plan() -> None:
    plan = Path(app.ROOT_DIR / "docs" / "project_plan.md").read_text(encoding="utf-8")
    guide = Path(app.ROOT_DIR / "docs" / "user_guide.md").read_text(encoding="utf-8")

    assert "Documentation Center v2" in plan
    assert "Quick Actions Wiring" in plan
    assert "Documentation Center v2" in guide
    assert "горячие клавиши" in guide


def test_dashboard_quick_actions_are_wired_from_single_registry() -> None:
    titles = app._start_action_titles()
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "Создать / открыть проект" in titles
    assert "Импорт LAS / CSV / Excel" in titles
    assert "Настройки интерфейса" in titles
    assert "Лицензия" in titles
    assert "DASHBOARD_LAST_QUICK_ACTION_KEY" in source
    assert "dashboard_quick_action_" in source
    assert "_trigger_quick_action(action)" in source
    assert "help=action[\"tooltip\"]" in source
    assert "quick-action-wired" in source


def test_dashboard_quick_action_registry_targets_real_tabs() -> None:
    valid_tabs = set(app.APP_TABS)

    for action in app.START_ACTIONS:
        assert action["id"]
        assert action["button_label"]
        assert action["tooltip"]
        assert action["target_tab"] in valid_tabs

    assert app._quick_action_by_id("las_editor")["target_tab"] == "LAS-редактор"
    assert app._quick_action_by_id("missing") is None


def test_quick_actions_wiring_is_documented() -> None:
    plan = Path(app.ROOT_DIR / "docs" / "project_plan.md").read_text(encoding="utf-8")
    guide = Path(app.ROOT_DIR / "docs" / "user_guide.md").read_text(encoding="utf-8")

    assert "Quick Actions Wiring" in plan
    assert "dashboard_quick_action_" in plan
    assert "Quick Actions Wiring" in guide
    assert "все кнопки быстрого доступа" in guide


def test_command_palette_search_categories_cover_project_objects() -> None:
    categories = set(app.COMMAND_PALETTE_CATEGORY_ORDER)

    assert "Команды" in categories
    assert "Проекты" in categories
    assert "Скважины" in categories
    assert "LAS" in categories
    assert "Кривые" in categories
    assert "Расчеты" in categories
    assert "Отчеты" in categories
    assert "Документация" in categories
    assert "Недавние" in categories
    assert "Избранное" in categories


def test_command_palette_filter_supports_categories_and_ranking() -> None:
    entries = (
        {"title": "Импорт LAS / CSV / Excel", "category": "Данные", "search_category": "Команды", "target_tab": "Работа с данными", "description": "Загрузка", "keywords": "импорт las csv"},
        {"title": "Well A", "category": "Проект · well", "search_category": "Скважины", "target_tab": "Работа с данными", "description": "active", "keywords": "well скважина"},
        {"title": "Troubleshooting", "category": "Документация", "search_category": "Документация", "target_tab": "Инструкции и документация", "description": "docs/troubleshooting.md", "keywords": "docs help"},
    )

    filtered = app._filter_command_palette_entries(entries, "well", category="Скважины", limit=4)

    assert len(filtered) == 1
    assert filtered[0]["title"] == "Well A"


def test_command_palette_recent_and_favorite_resolution() -> None:
    entries = (
        {"title": "Импорт LAS / CSV / Excel", "category": "Данные", "search_category": "Команды", "target_tab": "Работа с данными", "description": "Загрузка", "keywords": "импорт las csv"},
        {"title": "Troubleshooting", "category": "Документация", "search_category": "Документация", "target_tab": "Инструкции и документация", "description": "docs/troubleshooting.md", "keywords": "docs help"},
    )
    recent_id = app._command_entry_id(entries[1])

    recent = app._filter_command_palette_entries(entries, "", category="Недавние", recent_ids=[recent_id], limit=4)

    assert len(recent) == 1
    assert recent[0]["title"] == "Troubleshooting"


def test_command_palette_search_stage_documented() -> None:
    project_plan = Path("docs/project_plan.md").read_text(encoding="utf-8")
    user_guide = Path("docs/user_guide.md").read_text(encoding="utf-8")

    assert "UI Modernization Track → Command Palette Search" in project_plan
    assert "Недавние" in user_guide
    assert "Избранное" in user_guide


def test_responsive_dashboard_layout_targets_declared() -> None:
    targets = app._responsive_dashboard_target_names()
    media_queries = app._responsive_dashboard_media_queries()

    assert "1366×768 laptop" in targets
    assert "1920×1080 Full HD" in targets
    assert "2560×1440 / 3440×1440 / 3840×2160" in targets
    assert "Mobile" in targets
    assert "@media (max-width: 480px)" in media_queries
    assert "@media (min-width: 2560px)" in media_queries


def test_responsive_dashboard_css_prevents_overflow_and_hides_low_priority_mobile_widgets() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "--responsive-dashboard-columns" in source
    assert "overflow-x: hidden" in source
    assert "repeat(auto-fit, minmax(11.5rem, 1fr))" in source
    assert ".dashboard-card.news, .dashboard-card.tips { display: none; }" in source
    assert ".dashboard-card.preview-card { display: none; }" in source
    assert "@media (min-width: 3440px)" in source
    assert "@media (min-width: 3840px)" in source


def test_background_manager_final_pass_rules_separate_branded_and_engineering_pages() -> None:
    branded_tabs = app._background_manager_branded_tabs()
    workspace_tabs = app._background_manager_workspace_tabs()

    assert "Старт" in branded_tabs
    assert "Инструкции и документация" in branded_tabs
    assert "LAS-редактор" in workspace_tabs
    assert "LAS-корреляция" in workspace_tabs
    assert "Интерпретационные графики" in workspace_tabs
    assert app._background_manager_rule("LAS-редактор")["mode"] == "dark-workspace"
    assert app._background_manager_rule("Инструкции и документация")["mode"] == "documentation"


def test_background_manager_final_pass_css_disables_background_for_engineering_surfaces() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "BACKGROUND_MANAGER_RULES" in source
    assert "BACKGROUND_POSITION_PRESETS" in source
    assert "BACKGROUND_OPACITY_PRESETS" in source
    assert "background-rule-dark-workspace" in source
    assert "background-image: none !important" in source
    assert "#las-editor-workspace" in source
    assert "#correlation-workspace" in source
    assert "#graphs-workspace" in source
    assert "Preserve" not in source or "aspect ratio" in source


def test_background_manager_final_pass_is_documented() -> None:
    plan = Path(app.ROOT_DIR / "docs" / "project_plan.md").read_text(encoding="utf-8")
    guide = Path(app.ROOT_DIR / "docs" / "user_guide.md").read_text(encoding="utf-8")

    assert "Background Manager Final Pass" in plan
    assert "Refine branded background manager" in plan
    assert "Background Manager Final Pass" in guide
    assert "LAS-редактор" in guide


def test_shared_glass_ui_system_tokens_cover_required_components() -> None:
    token_names = app._glass_ui_token_names()
    css_classes = app._glass_ui_css_classes()

    assert "card" in token_names
    assert "panel" in token_names
    assert "hero" in token_names
    assert "sidebar" in token_names
    assert "navbar" in token_names
    assert "modal" in token_names
    assert "tooltip" in token_names
    assert "glass-card" in css_classes
    assert "glass-panel" in css_classes
    assert "glass-hero" in css_classes


def test_shared_glass_ui_system_css_has_transparency_border_shadow_blur_and_contrast() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "--glass-card-bg" in source
    assert "--glass-panel-bg" in source
    assert "--glass-border-token" in source
    assert "--glass-shadow-token" in source
    assert "--glass-blur-token" in source
    assert "--glass-high-contrast-text" in source
    assert "--glass-dark-overlay-control" in source
    assert ".glass-readability-check" in source
    assert ".background-rule-dark-workspace .glass-card" in source


def test_shared_glass_ui_system_is_documented() -> None:
    plan = Path(app.ROOT_DIR / "docs" / "project_plan.md").read_text(encoding="utf-8")
    guide = Path(app.ROOT_DIR / "docs" / "user_guide.md").read_text(encoding="utf-8")

    assert "Glass UI System" in plan
    assert "Add shared glass UI system" in plan
    assert "shared transparency tokens" in plan
    assert "Glass UI System" in guide
    assert "LAS Editor / Graphs / Reports" in guide

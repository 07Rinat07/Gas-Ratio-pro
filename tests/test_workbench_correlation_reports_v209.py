from pathlib import Path

from core.workbench_ui_layout import build_workbench_ui_layout
from core.workbench_navigation import WorkbenchNavigationRouter
from reports.document_model import build_engineering_document


def test_workbench_exposes_correlation_route_in_production_sources() -> None:
    from app.workbench_renderer import workbench_menu_navigation_ids
    from core.workbench_shell import DEFAULT_WORKBENCH_NAVIGATION

    route = WorkbenchNavigationRouter().by_navigation("nav.correlation")
    navigation_ids = {item.id for item in DEFAULT_WORKBENCH_NAVIGATION}

    assert route.workspace == "correlation"
    assert "nav.correlation" in workbench_menu_navigation_ids()
    assert "nav.correlation" in navigation_ids


def test_default_project_tree_contains_correlation_entry() -> None:
    layout = build_workbench_ui_layout({"context": {}, "status": {}, "interaction": {}, "tool": {}, "commands": (), "actions": (), "routes": (), "dock_panes": (), "ui_providers": {}})
    ids = {item['id'] for item in layout.project_tree}
    assert 'tree.correlation' in ids


def test_engineering_document_places_plot_before_tables() -> None:
    source = Path('reports/document_model.py').read_text(encoding='utf-8')
    assert source.index('if include_figures:') < source.index('if tables:')


def test_engineering_report_is_compact_and_reasoning_is_expert_only() -> None:
    source = Path('reports/hydrocarbon_report.py').read_text(encoding='utf-8')
    assert '[:15]' in source
    assert 'if _card_number(card.thickness) > 0.0' in source
    engineering_block = source.split('engineering_tables = (', 1)[1].split('technical_tables = (', 1)[0]
    assert 'interval_card_reasoning_report_table' not in engineering_block

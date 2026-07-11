from pathlib import Path

from core.workbench_ui_layout import build_workbench_ui_layout
from reports.document_model import build_engineering_document


def test_workbench_exposes_correlation_route_in_production_sources() -> None:
    renderer = Path('app/workbench_renderer.py').read_text(encoding='utf-8')
    app = Path('app/streamlit_app.py').read_text(encoding='utf-8')
    assert '("Correlation", "nav.correlation")' in renderer
    assert '"tree.correlation": "nav.correlation"' in renderer
    assert '"nav.correlation": ("las-correlation"' in app
    assert 'multi-well-uploader' in app


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

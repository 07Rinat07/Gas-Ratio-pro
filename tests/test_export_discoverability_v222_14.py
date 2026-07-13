from pathlib import Path

APP_SOURCE = Path('app/streamlit_app.py').read_text(encoding='utf-8')


def test_export_panel_is_prominent_and_expanded() -> None:
    assert '🖨️ ПЕЧАТЬ И ПРОФЕССИОНАЛЬНЫЙ ЭКСПОРТ' in APP_SOURCE
    assert 'expanded=True' in APP_SOURCE
    assert '🖨️ ПОДГОТОВИТЬ ФАЙЛ ДЛЯ ПЕЧАТИ И СКАЧИВАНИЯ' in APP_SOURCE
    assert '⬇️ СКАЧАТЬ ГОТОВЫЙ' in APP_SOURCE


def test_full_well_atlas_scope_is_available() -> None:
    assert 'Вся скважина и все УВ-интервалы' in APP_SOURCE
    assert 'обзорный планшет и детальные страницы' in APP_SOURCE
    assert 'scope={print_mode}' in APP_SOURCE


def test_export_reports_four_stages() -> None:
    for stage in ('Шаг 1 из 4', 'Шаг 2 из 4', 'Шаг 3 из 4', 'Шаг 4 из 4'):
        assert stage in APP_SOURCE
    assert 'st.progress(5' in APP_SOURCE


def test_export_panel_precedes_screen_graph_settings() -> None:
    export_call = APP_SOURCE.index('_render_professional_export_panel(', APP_SOURCE.index('def _render_interpretation_graphs_tab'))
    graph_settings = APP_SOURCE.index('### Настройка экранных графиков', export_call)
    plot_render = APP_SOURCE.index('st.plotly_chart(', graph_settings)
    assert export_call < graph_settings < plot_render

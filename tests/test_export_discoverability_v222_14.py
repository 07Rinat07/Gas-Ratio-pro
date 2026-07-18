from pathlib import Path

APP_SOURCE = Path('app/streamlit_app.py').read_text(encoding='utf-8')
from reports.export_progress import EXPORT_PROGRESS_STAGES


def test_export_panel_is_prominent_and_expanded() -> None:
    from app import streamlit_app as app
    from core.ui_behavior_contracts import PROFESSIONAL_EXPORT_BEHAVIOR

    calls = []

    class FakeStreamlit:
        def markdown(self, *_args, **_kwargs):
            return None

        def popover(self, label, *, help=None):
            calls.append(("popover", label, help))
            return object()

    result = app._print_center_container(FakeStreamlit())

    assert result is not None
    assert calls == [(
        "popover",
        PROFESSIONAL_EXPORT_BEHAVIOR.panel_label,
        PROFESSIONAL_EXPORT_BEHAVIOR.panel_help,
    )]
    assert PROFESSIONAL_EXPORT_BEHAVIOR.primary_action_label
    assert PROFESSIONAL_EXPORT_BEHAVIOR.download_prefix


def test_full_well_atlas_scope_is_available() -> None:
    assert 'Вся скважина и все УВ-интервалы' in APP_SOURCE
    assert 'обзорный планшет и детальные страницы' in APP_SOURCE
    assert 'scope={print_mode}' in APP_SOURCE


def test_export_reports_four_stages() -> None:
    assert tuple(stage.prefix for stage in EXPORT_PROGRESS_STAGES) == (
        'Шаг 1 из 4 — Проверка параметров',
        'Шаг 2 из 4 — Подготовка данных',
        'Шаг 3 из 4 — Формирование документа',
        'Шаг 4 из 4 — Финализация файла',
    )
    assert 'staged_progress_reporter(report)' in APP_SOURCE
    assert 'st.progress(status_view.progress / 100.0' in APP_SOURCE


def test_export_panel_precedes_screen_graph_settings() -> None:
    export_call = APP_SOURCE.index('_render_professional_export_panel(', APP_SOURCE.index('def _render_interpretation_graphs_tab'))
    graph_settings = APP_SOURCE.index('### Настройка экранных графиков', export_call)
    plot_render = APP_SOURCE.index('st.plotly_chart(', graph_settings)
    assert export_call < graph_settings < plot_render

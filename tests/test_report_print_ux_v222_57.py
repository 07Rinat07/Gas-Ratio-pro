from pathlib import Path

from reports.plot_theme import apply_report_plot_theme


class FakeFigure:
    def __init__(self):
        self.layouts = []
        self.traces = []

    def __deepcopy__(self, memo):
        return self

    def update_layout(self, **kwargs):
        self.layouts.append(kwargs)

    def update_traces(self, **kwargs):
        self.traces.append(kwargs)


def test_report_plot_theme_enforces_print_readability():
    figure = FakeFigure()
    themed = apply_report_plot_theme(figure)
    assert themed is figure
    assert any(item.get("template") == "plotly_white" for item in figure.layouts)
    assert any(item.get("font", {}).get("size") == 15 for item in figure.layouts)
    assert any(item.get("legend", {}).get("font", {}).get("size") == 14 for item in figure.layouts)
    assert any(item.get("line", {}).get("width") == 2.2 for item in figure.traces)


def test_report_panel_is_compact_and_action_oriented():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert 'with st.expander("Отчёт и печать", expanded=False)' in source
    assert "Сформировать инженерный отчёт" in source
    assert "После подготовки файла появятся отдельные действия" in source


def test_print_legends_are_not_micro_text():
    pdf = Path("reports/presentation_pdf.py").read_text(encoding="utf-8")
    docx = Path("reports/presentation_docx.py").read_text(encoding="utf-8")
    assert "fontSize=9.5" in pdf
    assert "one-item-per-row" in pdf
    assert "Pt(10)" in docx
    assert "width=2600, height=1700" in pdf
    assert "width=2600, height=1700" in docx


def test_developer_diagnostics_are_collapsed_by_default():
    source = Path("app/workbench_renderer.py").read_text(encoding="utf-8")
    assert 'i18n("diagnostics.show_advanced")' in source
    assert 'value=False' in source
    assert "if show_advanced:" in source

from pathlib import Path
import json

from reports.document_model import DocumentMetadata, DocumentNotice, DocumentSection, DocumentTable, EngineeringDocument
from reports.presentation_export import PresentationExportOptions, export_presentation_pdf_package, safe_export_basename
from reports.presentation_pdf import PresentationPdfOptions, render_engineering_document_pdf


class _DummyMetadata:
    report_profile = "engineering"
    title = "Тестовый отчет"
    subtitle = "Инженерное заключение"
    source_label = "LAS"
    project_label = "Demo"
    depth_label = "1000-1010 м"

    def as_report_rows(self):
        return (("Источник данных", self.source_label), ("Проект", self.project_label), ("Интервал анализа", self.depth_label))


class _DummyModel:
    schema = "gas-ratio-pro/presentation/model/test"
    metadata = _DummyMetadata()

    @property
    def result(self):
        return None

    @property
    def figures(self):
        return ()

    @property
    def engineer_first_tables(self):
        from reports.export_html import HtmlReportTable

        return (HtmlReportTable(title="Интервалы", headers=("От", "До", "Тип"), rows=((1000, 1005, "Газ"),)),)

    @property
    def expert_tables(self):
        return self.engineer_first_tables


def _document() -> EngineeringDocument:
    return EngineeringDocument(
        metadata=DocumentMetadata(
            title="Газовый отчет",
            subtitle="Проверка PDF",
            rows=(("Скважина", "A-1"), ("Интервал", "1000-1005 м")),
            notes=("Каждая интерпретация является инженерной гипотезой.",),
        ),
        sections=(
            DocumentSection(
                title="Интервалы",
                blocks=(
                    DocumentTable(title="Основные интервалы", headers=("От", "До", "Тип"), rows=((1000, 1005, "Газ"),)),
                    DocumentNotice(title="Ограничения", text="Требуется проверка по ГИС."),
                ),
            ),
        ),
    )


def test_render_engineering_document_pdf_returns_pdf_bytes() -> None:
    result = render_engineering_document_pdf(_document(), options=PresentationPdfOptions(include_figures=False))

    assert result.content.startswith(b"%PDF")
    assert result.profile == "engineering"
    assert result.table_titles == ("Основные интервалы",)


def test_pdf_renderer_sanitizes_page_options() -> None:
    result = render_engineering_document_pdf(
        _document(),
        options=PresentationPdfOptions(paper_size="bad", orientation="bad", margin_mm=999),
    )

    assert result.content.startswith(b"%PDF")


def test_export_presentation_pdf_package_writes_manifest(tmp_path: Path) -> None:
    result = export_presentation_pdf_package(
        _DummyModel(),
        options=PresentationExportOptions(output_dir=tmp_path, base_name="../Demo Report", include_figures=False),
    )

    assert result.pdf_path.exists()
    assert result.pdf_path.read_bytes().startswith(b"%PDF")
    assert result.manifest_path.exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "gas-ratio-pro/presentation/pdf-export/v1"
    assert manifest["pdf_file"] == result.pdf_path.name
    assert "/" not in result.pdf_path.name
    assert ".." not in result.pdf_path.name


def test_pdf_export_reuses_safe_basename() -> None:
    assert safe_export_basename("../well/report") == "well_report"

class _CanvasProbe:
    def __init__(self) -> None:
        self.page_number = 3
        self.strings: list[str] = []

    def __getattr__(self, name):
        if name in {"saveState", "restoreState", "setAuthor", "setTitle", "setSubject", "setKeywords", "setStrokeColor", "setLineWidth", "line", "setFillColor", "setFont"}:
            return lambda *args, **kwargs: None
        if name in {"drawString", "drawCentredString", "drawRightString"}:
            return lambda *args, **kwargs: self.strings.append(str(args[-1]))
        raise AttributeError(name)

    def getPageNumber(self) -> int:
        return self.page_number


class _DocProbe:
    leftMargin = 36
    rightMargin = 36


def test_pdf_page_decorator_draws_controlled_document_identity() -> None:
    from reports.presentation_pdf import _build_page_decorator

    canvas = _CanvasProbe()
    callback = _build_page_decorator(
        options=PresentationPdfOptions(
            document_code="GRP-WELL-A1",
            footer_text="Approved engineering output",
            classification="INTERNAL",
        ),
        document_title="Well A-1 Gas Ratio Report",
        page_size=(595.0, 842.0),
        regular_font="Helvetica",
        bold_font="Helvetica-Bold",
    )

    callback(canvas, _DocProbe())

    assert "Well A-1 Gas Ratio Report" in canvas.strings
    assert "GRP-WELL-A1" in canvas.strings
    assert "Approved engineering output" in canvas.strings
    assert "INTERNAL" in canvas.strings
    assert "Page 3" in canvas.strings


def test_pdf_page_chrome_can_be_disabled() -> None:
    result = render_engineering_document_pdf(
        _document(),
        options=PresentationPdfOptions(include_figures=False, show_page_chrome=False),
    )

    assert result.content.startswith(b"%PDF")

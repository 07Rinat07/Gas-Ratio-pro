from pathlib import Path
import json
from zipfile import ZipFile

from reports.document_model import DocumentMetadata, DocumentNotice, DocumentSection, DocumentTable, EngineeringDocument
from reports.presentation_docx import PresentationDocxOptions, render_engineering_document_docx
from reports.presentation_export import PresentationExportOptions, export_presentation_docx_package, safe_export_basename


class _DummyMetadata:
    report_profile = "engineering"
    title = "Тестовый DOCX отчет"
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
            subtitle="Проверка DOCX",
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


def test_render_engineering_document_docx_returns_office_package() -> None:
    result = render_engineering_document_docx(_document(), options=PresentationDocxOptions(include_figures=False))

    assert result.content.startswith(b"PK")
    assert result.profile == "engineering"
    assert result.table_titles == ("Основные интервалы",)
    with ZipFile(__import__("io").BytesIO(result.content)) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")
    assert "Газовый отчет" in document_xml
    assert "Основные интервалы" in document_xml


def test_docx_renderer_sanitizes_page_options() -> None:
    result = render_engineering_document_docx(
        _document(),
        options=PresentationDocxOptions(paper_size="bad", orientation="bad", margin_mm=999),
    )

    assert result.content.startswith(b"PK")


def test_export_presentation_docx_package_writes_manifest(tmp_path: Path) -> None:
    result = export_presentation_docx_package(
        _DummyModel(),
        options=PresentationExportOptions(output_dir=tmp_path, base_name="../Demo DOCX", include_figures=False),
    )

    assert result.docx_path.exists()
    assert result.docx_path.read_bytes().startswith(b"PK")
    assert result.manifest_path.exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "gas-ratio-pro/presentation/docx-export/v1"
    assert manifest["docx_file"] == result.docx_path.name
    assert "/" not in result.docx_path.name
    assert ".." not in result.docx_path.name


def test_docx_export_reuses_safe_basename() -> None:
    assert safe_export_basename("../well/docx") == "well_docx"

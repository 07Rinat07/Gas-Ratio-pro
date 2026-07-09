from __future__ import annotations

from pathlib import Path

from reports.document_model import DocumentMetadata, DocumentNotice, DocumentSection, DocumentTable, EngineeringDocument
from reports.presentation_pdf import PresentationPdfOptions, _font_candidates, _register_fonts, render_engineering_document_pdf


def test_pdf_font_candidates_support_common_desktop_platforms(monkeypatch) -> None:
    custom_regular = Path("C:/custom/NotoSans-Regular.ttf")
    custom_bold = Path("C:/custom/NotoSans-Bold.ttf")
    monkeypatch.setenv("GAS_RATIO_PRO_PDF_FONT", str(custom_regular))
    monkeypatch.setenv("GAS_RATIO_PRO_PDF_FONT_BOLD", str(custom_bold))

    candidates = _font_candidates()

    assert candidates[0] == (custom_regular, custom_bold)
    candidate_text = "\n".join(str(path) for pair in candidates for path in pair)
    assert "C:/Windows/Fonts/arial.ttf" in candidate_text
    assert "DejaVuSans.ttf" in candidate_text
    assert "NotoSans-Regular.ttf" in candidate_text


def test_pdf_renderer_uses_unicode_font_not_builtin_helvetica() -> None:
    regular, bold = _register_fonts()

    assert regular != "Helvetica"
    assert bold != "Helvetica-Bold"


def test_pdf_renderer_accepts_russian_kazakh_english_text() -> None:
    document = EngineeringDocument(
        metadata=DocumentMetadata(
            title="Gas Ratio Pro — көптілді есеп / многоязычный отчет",
            subtitle="Русский, қазақша and English text smoke test",
            rows=(
                ("Скважина", "Ұңғыма A-1"),
                ("Интервал", "1000–1010 м"),
            ),
            notes=("Әр интерпретация түсінікті, түсіндірілетін және қайталанатын болуы керек.",),
        ),
        sections=(
            DocumentSection(
                title="Интервалы / Аралықтар",
                blocks=(
                    DocumentTable(
                        title="Основные интервалы",
                        headers=("От", "До", "Тип"),
                        rows=((1000, 1005, "Газ / Газ / Gas"),),
                    ),
                    DocumentNotice(title="Ескерту", text="Қазақ, русский and English glyphs must render in PDF."),
                ),
            ),
        ),
    )

    result = render_engineering_document_pdf(document, options=PresentationPdfOptions(include_figures=False))

    assert result.content.startswith(b"%PDF")
    assert len(result.content) > 10_000

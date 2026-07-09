from __future__ import annotations

from pathlib import Path


def test_presentation_export_does_not_eagerly_import_pdf_or_docx_backends() -> None:
    source = Path("reports/presentation_export.py").read_text(encoding="utf-8")

    top_level = source.split("def export_presentation_html_package", maxsplit=1)[0]

    assert "from reports.presentation_pdf import" not in top_level
    assert "from reports.presentation_docx import" not in top_level
    assert "from docx import" not in top_level
    assert "from reportlab" not in top_level


def test_requirements_include_professional_export_dependencies() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert "reportlab" in requirements
    assert "python-docx" in requirements

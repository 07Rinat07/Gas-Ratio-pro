from __future__ import annotations

import pytest

from reports.export_static import (
    StaticExportOptions,
    StaticExportUnavailableError,
    export_plotly_static_bytes,
    validate_static_export_format,
)


def test_validate_static_export_format_accepts_supported_formats():
    assert validate_static_export_format("PNG") == "png"
    assert validate_static_export_format("pdf") == "pdf"
    assert validate_static_export_format(" svg ") == "svg"


def test_validate_static_export_format_rejects_unknown_format():
    with pytest.raises(ValueError, match="не поддерживается"):
        validate_static_export_format("docx")


def test_export_plotly_static_bytes_reports_missing_kaleido(monkeypatch):
    class FigureStub:
        def to_image(self, **kwargs):
            raise ValueError("Image export using the kaleido engine requires the kaleido package")

    with pytest.raises(StaticExportUnavailableError, match="kaleido"):
        export_plotly_static_bytes(FigureStub(), StaticExportOptions(format="png"))


def test_export_plotly_static_bytes_passes_normalized_options():
    captured = {}

    class FigureStub:
        def to_image(self, **kwargs):
            captured.update(kwargs)
            return b"image"

    data = export_plotly_static_bytes(
        FigureStub(),
        StaticExportOptions(format="png", width=100, height=200, scale=0.1),
    )

    assert data == b"image"
    assert captured == {
        "format": "png",
        "width": 320,
        "height": 320,
        "scale": 0.5,
    }


def test_export_native_composite_svg_png_pdf():
    from app.visualization_v3.composite_engine import CompositeLogResult

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" '
        'viewBox="0 0 400 300"><rect width="400" height="300" fill="white"/>'
        '<text x="20" y="40" font-size="24">TGAS</text></svg>'
    )
    result = CompositeLogResult(
        svg=svg,
        width=400,
        height=300,
        depth_start=1000,
        depth_stop=1100,
        rendered_tracks=("tgas",),
    )

    svg_bytes = export_plotly_static_bytes(result, StaticExportOptions(format="svg"))
    assert svg_bytes.startswith(b"<svg")

    png_bytes = export_plotly_static_bytes(
        result, StaticExportOptions(format="png", width=1200, height=900, scale=1)
    )
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    pdf_bytes = export_plotly_static_bytes(result, StaticExportOptions(format="pdf"))
    assert pdf_bytes.startswith(b"%PDF")

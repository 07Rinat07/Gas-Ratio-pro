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

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from palettes.plot_engine import prepare_figure_for_export


StaticExportFormat = Literal["png", "pdf", "svg"]
SUPPORTED_STATIC_EXPORT_FORMATS: tuple[StaticExportFormat, ...] = ("png", "pdf", "svg")


class StaticExportUnavailableError(RuntimeError):
    """Raised when Plotly static export engine is not available."""


@dataclass(frozen=True)
class StaticExportOptions:
    format: StaticExportFormat
    width: int = 1400
    height: int = 900
    scale: float = 2.0


def validate_static_export_format(format_name: str) -> StaticExportFormat:
    normalized = str(format_name).strip().lower()
    if normalized not in SUPPORTED_STATIC_EXPORT_FORMATS:
        supported = ", ".join(SUPPORTED_STATIC_EXPORT_FORMATS)
        raise ValueError(f"Формат `{format_name}` не поддерживается. Доступно: {supported}.")
    return normalized  # type: ignore[return-value]


def _export_composite_svg_bytes(figure, options: StaticExportOptions) -> bytes:
    """Export the native CompositeLogResult without routing through Plotly/Kaleido."""
    svg_text = getattr(figure, "svg", None)
    if not isinstance(svg_text, str) or not svg_text.strip():
        raise TypeError("Composite SVG payload is empty")

    export_format = validate_static_export_format(options.format)
    if export_format == "svg":
        return svg_text.encode("utf-8")

    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise StaticExportUnavailableError(
            "Для PNG/PDF экспорта инженерного планшета нужен пакет PyMuPDF."
        ) from exc

    source = fitz.open(stream=svg_text.encode("utf-8"), filetype="svg")
    try:
        if source.page_count < 1:
            raise ValueError("SVG document has no pages")
        page = source.load_page(0)
        if export_format == "pdf":
            pdf_bytes = source.convert_to_pdf()
            target = fitz.open(stream=pdf_bytes, filetype="pdf")
            try:
                return target.tobytes(garbage=4, deflate=True)
            finally:
                target.close()

        target_width = max(640, int(options.width))
        target_height = max(640, int(options.height))
        sx = target_width / max(1.0, float(page.rect.width))
        sy = target_height / max(1.0, float(page.rect.height))
        scale = max(0.5, min(sx, sy) * max(0.5, float(options.scale)))
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return pixmap.tobytes("png")
    finally:
        source.close()


def export_plotly_static_bytes(figure, options: StaticExportOptions) -> bytes:
    export_format = validate_static_export_format(options.format)

    # CompositeLogResult is a native SVG document, not a Plotly Figure.
    # Export it directly so PNG/SVG/PDF do not call a non-existent ``to_image`` method.
    if hasattr(figure, "svg"):
        return _export_composite_svg_bytes(figure, options)

    try:
        export_figure = prepare_figure_for_export(
            figure, width=max(320, int(options.width)), height=max(320, int(options.height))
        )
        return export_figure.to_image(
            format=export_format,
            width=max(320, int(options.width)),
            height=max(320, int(options.height)),
            scale=max(0.5, float(options.scale)),
        )
    except (ImportError, ValueError) as exc:
        message = str(exc).lower()
        if "kaleido" in message or "image export" in message:
            raise StaticExportUnavailableError(
                "Для PNG/PDF/SVG экспорта Plotly нужен пакет kaleido. "
                "Установите зависимости из requirements.txt и перезапустите приложение."
            ) from exc
        raise

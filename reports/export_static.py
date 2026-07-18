from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from palettes.plot_engine import prepare_figure_for_export


StaticExportFormat = Literal["png", "pdf", "svg"]
SUPPORTED_STATIC_EXPORT_FORMATS: tuple[StaticExportFormat, ...] = ("png", "pdf", "svg")


class StaticExportUnavailableError(RuntimeError):
    """Raised when the supported Plotly static export engine is unavailable."""


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


def export_plotly_static_bytes(figure, options: StaticExportOptions) -> bytes:
    """Export a genuine Plotly figure through Kaleido.

    Native CompositeLog SVG objects were previously exported through an
    independent first-page static branch.  That branch is retired: engineering
    visualizations must use ``VisualizationPageAwarePackage`` and the parity-
    gated delivery adapter instead.
    """

    export_format = validate_static_export_format(options.format)
    if hasattr(figure, "svg") and not hasattr(figure, "to_image"):
        raise StaticExportUnavailableError(
            "Legacy CompositeLog static export отключён. Используйте Professional Print Center "
            "и page-aware SVG/PNG/PDF пакет."
        )

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

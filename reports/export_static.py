from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


def export_plotly_static_bytes(figure, options: StaticExportOptions) -> bytes:
    export_format = validate_static_export_format(options.format)
    try:
        return figure.to_image(
            format=export_format,
            width=max(320, int(options.width)),
            height=max(320, int(options.height)),
            scale=max(0.5, float(options.scale)),
        )
    except (ImportError, ValueError) as exc:
        message = str(exc).lower()
        if "kaleido" in message or "image export" in message:
            raise StaticExportUnavailableError(
                "Для PNG/PDF/SVG экспорта нужен пакет kaleido. "
                "Установите зависимости из requirements.txt и перезапустите приложение."
            ) from exc
        raise

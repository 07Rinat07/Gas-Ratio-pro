from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from reports.presentation_export import PresentationExportOptions, safe_export_basename

ReportProfile = Literal["engineering", "expert"]
ExportFormat = Literal["html", "pdf", "docx", "bundle"]


@dataclass(frozen=True)
class ReportProfileOption:
    """UI-facing report profile description.

    The Streamlit layer should show these labels instead of hardcoding profile
    text.  This keeps UI wording, renderer behaviour and tests aligned.
    """

    id: ReportProfile
    label: str
    description: str
    include_technical_appendix: bool


@dataclass(frozen=True)
class ExportFormatOption:
    """UI-facing export format description."""

    id: ExportFormat
    label: str
    extension: str
    mime_type: str
    description: str


@dataclass(frozen=True)
class PresentationExportUiState:
    """Normalized state passed from UI controls to the export layer.

    This object intentionally contains no Streamlit dependency.  UI code can
    build it from selectboxes, toggles and text inputs, while tests can validate
    export behaviour without launching the browser app.
    """

    profile: ReportProfile
    export_format: ExportFormat
    include_figures: bool
    include_technical_appendix: bool
    base_name: str
    output_dir: Path


_REPORT_PROFILES: tuple[ReportProfileOption, ...] = (
    ReportProfileOption(
        id="engineering",
        label="Инженерный отчет",
        description="Краткое заключение, интервалы, уверенность, рекомендации и ограничения без технического мусора.",
        include_technical_appendix=False,
    ),
    ReportProfileOption(
        id="expert",
        label="Экспертный отчет",
        description="Инженерный отчет плюс технические таблицы, диагностика и расчетные приложения.",
        include_technical_appendix=True,
    ),
)

_EXPORT_FORMATS: tuple[ExportFormatOption, ...] = (
    ExportFormatOption(
        id="html",
        label="HTML",
        extension="html",
        mime_type="text/html",
        description="Быстрый просмотр и печать через браузер.",
    ),
    ExportFormatOption(
        id="pdf",
        label="PDF",
        extension="pdf",
        mime_type="application/pdf",
        description="Печатный инженерный отчет.",
    ),
    ExportFormatOption(
        id="docx",
        label="DOCX",
        extension="docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        description="Редактируемый отчет для организации.",
    ),
    ExportFormatOption(
        id="bundle",
        label="HTML + PDF + DOCX",
        extension="zip",
        mime_type="application/zip",
        description="Единый пакет всех форматов из одного PresentationModel.",
    ),
)


def report_profile_options() -> tuple[ReportProfileOption, ...]:
    """Return stable report profiles for UI selectors."""

    return _REPORT_PROFILES


def export_format_options() -> tuple[ExportFormatOption, ...]:
    """Return stable export formats for UI selectors."""

    return _EXPORT_FORMATS


def normalize_report_profile(value: str | None) -> ReportProfile:
    """Normalize user input to a supported report profile."""

    normalized = str(value or "").strip().lower()
    if normalized in {"expert", "экспертный", "expert_report"}:
        return "expert"
    return "engineering"


def normalize_export_format(value: str | None) -> ExportFormat:
    """Normalize user input to a supported export format."""

    normalized = str(value or "").strip().lower()
    allowed = {option.id for option in _EXPORT_FORMATS}
    if normalized in allowed:
        return normalized  # type: ignore[return-value]
    if normalized in {"all", "zip", "package", "пакет"}:
        return "bundle"
    return "html"


def profile_by_id(profile: str | None) -> ReportProfileOption:
    """Return profile metadata by id with engineering as safe default."""

    profile_id = normalize_report_profile(profile)
    return next(option for option in _REPORT_PROFILES if option.id == profile_id)


def export_format_by_id(export_format: str | None) -> ExportFormatOption:
    """Return export format metadata by id with HTML as safe default."""

    format_id = normalize_export_format(export_format)
    return next(option for option in _EXPORT_FORMATS if option.id == format_id)


def build_report_base_name(*parts: str, fallback: str = "gas-ratio-professional-report") -> str:
    """Build a safe report basename from project/well/source labels."""

    raw = "_".join(str(part).strip() for part in parts if str(part).strip())
    return safe_export_basename(raw, fallback=fallback)


def build_presentation_export_ui_state(
    *,
    profile: str | None,
    export_format: str | None,
    output_dir: str | Path,
    base_name_parts: Iterable[str] = (),
    include_figures: bool = True,
) -> PresentationExportUiState:
    """Convert UI control values into a renderer-neutral export state."""

    profile_option = profile_by_id(profile)
    format_option = export_format_by_id(export_format)
    base_name = build_report_base_name(*tuple(base_name_parts))
    return PresentationExportUiState(
        profile=profile_option.id,
        export_format=format_option.id,
        include_figures=bool(include_figures),
        include_technical_appendix=profile_option.include_technical_appendix,
        base_name=base_name,
        output_dir=Path(output_dir),
    )


def export_options_from_ui_state(state: PresentationExportUiState) -> PresentationExportOptions:
    """Create existing PresentationExportOptions from normalized UI state."""

    return PresentationExportOptions(
        output_dir=state.output_dir,
        base_name=state.base_name,
        include_figures=state.include_figures,
        include_technical_appendix=state.include_technical_appendix,
        overwrite=True,
    )

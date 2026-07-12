from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from reports.presentation_export import PresentationExportOptions, safe_export_basename

ReportProfile = Literal["engineering", "expert"]
ExportFormat = Literal["pdf", "docx", "bundle"]


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
        id="pdf",
        label="PDF",
        extension="pdf",
        mime_type="application/pdf",
        description="Готовый печатный инженерный отчет.",
    ),
    ExportFormatOption(
        id="docx",
        label="DOCX",
        extension="docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        description="Редактируемый отчет для согласования и передачи заказчику.",
    ),
    ExportFormatOption(
        id="bundle",
        label="PDF + DOCX",
        extension="zip",
        mime_type="application/zip",
        description="Пакет PDF и DOCX из одного PresentationModel.",
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
    return "pdf"


def profile_by_id(profile: str | None) -> ReportProfileOption:
    """Return profile metadata by id with engineering as safe default."""

    profile_id = normalize_report_profile(profile)
    return next(option for option in _REPORT_PROFILES if option.id == profile_id)


def export_format_by_id(export_format: str | None) -> ExportFormatOption:
    """Return export format metadata by id with PDF as safe default."""

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

# v35: renderer-neutral UI export execution
from dataclasses import dataclass as _dataclass
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED

from reports.presentation_export import (
    export_presentation_docx_package,
    export_presentation_pdf_package,
)
from reports.presentation_model import PresentationModel


@_dataclass(frozen=True)
class PresentationUiExportArtifact:
    """Download-ready export artifact for Streamlit or another UI shell.

    The UI should not know how PDF, DOCX or bundle reports are rendered.
    It passes a PresentationModel plus normalized UI state and receives bytes,
    a safe file name and the correct MIME type.
    """

    content: bytes
    file_name: str
    mime_type: str
    export_format: ExportFormat
    profile: ReportProfile
    manifest_names: tuple[str, ...] = ()


def _read_single_export(path: Path) -> bytes:
    return path.read_bytes()


def build_ui_export_artifact(
    model: PresentationModel,
    state: PresentationExportUiState,
) -> PresentationUiExportArtifact:
    """Render a UI-selected report export into download-ready bytes.

    This is the handoff point between Modern UI and Presentation Layer.  It is
    intentionally renderer-neutral: Streamlit does not branch into PDF/DOCX
    internals and does not duplicate report content logic.
    """

    options = export_options_from_ui_state(state)
    format_option = export_format_by_id(state.export_format)

    if state.export_format == "pdf":
        result = export_presentation_pdf_package(model, options=options)
        return PresentationUiExportArtifact(
            content=_read_single_export(result.pdf_path),
            file_name=result.pdf_path.name,
            mime_type=format_option.mime_type,
            export_format=state.export_format,
            profile=state.profile,
            manifest_names=(result.manifest_path.name,),
        )

    if state.export_format == "docx":
        result = export_presentation_docx_package(model, options=options)
        return PresentationUiExportArtifact(
            content=_read_single_export(result.docx_path),
            file_name=result.docx_path.name,
            mime_type=format_option.mime_type,
            export_format=state.export_format,
            profile=state.profile,
            manifest_names=(result.manifest_path.name,),
        )

    with TemporaryDirectory(prefix="gas_ratio_presentation_bundle_") as temp_dir:
        temp_state = PresentationExportUiState(
            profile=state.profile,
            export_format=state.export_format,
            include_figures=state.include_figures,
            include_technical_appendix=state.include_technical_appendix,
            base_name=state.base_name,
            output_dir=Path(temp_dir),
        )
        temp_options = export_options_from_ui_state(temp_state)
        pdf_result = export_presentation_pdf_package(model, options=temp_options)
        docx_result = export_presentation_docx_package(model, options=temp_options)
        zip_path = Path(temp_dir) / f"{safe_export_basename(state.base_name)}.zip"
        bundle_files = (
            pdf_result.pdf_path,
            pdf_result.manifest_path,
            docx_result.docx_path,
            docx_result.manifest_path,
        )
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            for path in bundle_files:
                archive.write(path, arcname=path.name)
        return PresentationUiExportArtifact(
            content=zip_path.read_bytes(),
            file_name=zip_path.name,
            mime_type=format_option.mime_type,
            export_format=state.export_format,
            profile=state.profile,
            manifest_names=(
                pdf_result.manifest_path.name,
                docx_result.manifest_path.name,
            ),
        )

from __future__ import annotations

"""Renderer-neutral state machine for the Professional Export Wizard.

The module deliberately contains no Streamlit dependency.  A desktop, web or
CLI shell can render the same steps and use the same validation rules.  The
wizard does not build engineering calculations; it only validates export
intent before handing a prepared PresentationModel to the presentation layer.
"""

from dataclasses import dataclass, replace
from enum import IntEnum
from pathlib import Path
from typing import Iterable

from reports.presentation_ui import (
    ExportFormat,
    PresentationExportUiState,
    ReportProfile,
    build_presentation_export_ui_state,
    export_format_by_id,
    profile_by_id,
)


class ExportWizardStep(IntEnum):
    SOURCE = 1
    CONTENT = 2
    FORMAT = 3
    DESTINATION = 4
    REVIEW = 5


@dataclass(frozen=True)
class ExportWizardIssue:
    code: str
    message: str
    field: str
    blocking: bool = True


@dataclass(frozen=True)
class ExportWizardCapabilities:
    """Formats implemented by the professional report renderer."""

    report_formats: tuple[ExportFormat, ...] = ("pdf", "docx", "bundle")

    def supports(self, export_format: str) -> bool:
        return export_format in self.report_formats


@dataclass(frozen=True)
class ExportWizardState:
    step: ExportWizardStep = ExportWizardStep.SOURCE
    source_label: str = ""
    project_label: str = ""
    profile: ReportProfile = "engineering"
    export_format: ExportFormat = "pdf"
    include_figures: bool = True
    output_dir: Path = Path("exports")
    base_name_parts: tuple[str, ...] = ()

    def with_step(self, step: ExportWizardStep | int) -> "ExportWizardState":
        return replace(self, step=ExportWizardStep(step))

    def next_step(self) -> "ExportWizardState":
        return self.with_step(min(int(self.step) + 1, int(ExportWizardStep.REVIEW)))

    def previous_step(self) -> "ExportWizardState":
        return self.with_step(max(int(self.step) - 1, int(ExportWizardStep.SOURCE)))




@dataclass(frozen=True)
class ExportWizardStepView:
    """Renderer-neutral presentation state for one wizard step."""

    step: ExportWizardStep
    label: str
    description: str
    active: bool
    completed: bool
    available: bool

    @property
    def number(self) -> int:
        return int(self.step)


@dataclass(frozen=True)
class ExportWizardReview:
    """Final, human-readable review assembled before binary rendering."""

    source_label: str
    project_label: str
    profile_label: str
    format_label: str
    destination: str
    file_name: str
    include_figures: bool
    ready: bool
    issues: tuple[ExportWizardIssue, ...]
    steps: tuple[ExportWizardStepView, ...]


_STEP_COPY: tuple[tuple[ExportWizardStep, str, str], ...] = (
    (ExportWizardStep.SOURCE, "Источник", "Проект и инженерные данные"),
    (ExportWizardStep.CONTENT, "Состав", "Режим, шаблон и разделы"),
    (ExportWizardStep.FORMAT, "Формат", "PDF, DOCX или пакет"),
    (ExportWizardStep.DESTINATION, "Назначение", "Имя и каталог файла"),
    (ExportWizardStep.REVIEW, "Проверка", "Итог перед формированием"),
)


@dataclass(frozen=True)
class ExportWizardPreflight:
    state: ExportWizardState
    issues: tuple[ExportWizardIssue, ...]
    ui_state: PresentationExportUiState | None

    @property
    def ready(self) -> bool:
        return not any(issue.blocking for issue in self.issues) and self.ui_state is not None


def _clean_parts(parts: Iterable[str]) -> tuple[str, ...]:
    return tuple(text for value in parts if (text := str(value or "").strip()))


def validate_export_wizard(
    state: ExportWizardState,
    *,
    capabilities: ExportWizardCapabilities | None = None,
) -> ExportWizardPreflight:
    """Validate the complete export intent and build the normalized UI state.

    Validation is deterministic and side-effect free.  In particular, it does
    not create output directories or render files, which makes it safe to run
    after every UI control change.
    """

    capabilities = capabilities or ExportWizardCapabilities()
    issues: list[ExportWizardIssue] = []

    if not str(state.source_label or "").strip():
        issues.append(ExportWizardIssue("source.required", "Не выбран источник инженерных данных.", "source_label"))

    format_option = export_format_by_id(state.export_format)
    if not capabilities.supports(format_option.id):
        issues.append(
            ExportWizardIssue(
                "format.unsupported_for_report",
                f"Формат {format_option.label} не поддерживается конструктором профессионального отчета.",
                "export_format",
            )
        )

    output_dir = Path(state.output_dir)
    if output_dir.exists() and not output_dir.is_dir():
        issues.append(ExportWizardIssue("destination.not_directory", "Путь экспорта указывает на файл, а не на каталог.", "output_dir"))

    name_parts = _clean_parts(state.base_name_parts) or _clean_parts((state.project_label, state.source_label))
    ui_state = build_presentation_export_ui_state(
        profile=state.profile,
        export_format=state.export_format,
        output_dir=output_dir,
        base_name_parts=name_parts,
        include_figures=state.include_figures,
    )

    if not ui_state.base_name:
        issues.append(ExportWizardIssue("name.required", "Не удалось сформировать имя файла отчета.", "base_name_parts"))

    return ExportWizardPreflight(state=state, issues=tuple(issues), ui_state=ui_state)


def require_export_ready(
    state: ExportWizardState,
    *,
    capabilities: ExportWizardCapabilities | None = None,
) -> PresentationExportUiState:
    """Return normalized state or raise one actionable validation error."""

    result = validate_export_wizard(state, capabilities=capabilities)
    if not result.ready:
        details = "; ".join(issue.message for issue in result.issues if issue.blocking)
        raise ValueError(f"Export wizard is not ready: {details}")
    assert result.ui_state is not None
    return result.ui_state

def build_export_wizard_steps(
    state: ExportWizardState,
    *,
    capabilities: ExportWizardCapabilities | None = None,
) -> tuple[ExportWizardStepView, ...]:
    """Build deterministic step navigation without Streamlit dependencies."""

    capabilities = capabilities or ExportWizardCapabilities()
    source_complete = bool(str(state.source_label or "").strip())
    content_complete = bool(str(state.profile or "").strip())
    format_complete = capabilities.supports(export_format_by_id(state.export_format).id)
    output_dir = Path(state.output_dir)
    destination_complete = not (output_dir.exists() and not output_dir.is_dir())
    completion = {
        ExportWizardStep.SOURCE: source_complete,
        ExportWizardStep.CONTENT: content_complete,
        ExportWizardStep.FORMAT: format_complete,
        ExportWizardStep.DESTINATION: destination_complete,
        ExportWizardStep.REVIEW: source_complete and content_complete and format_complete and destination_complete,
    }

    rows: list[ExportWizardStepView] = []
    prior_complete = True
    for step, label, description in _STEP_COPY:
        available = step is ExportWizardStep.SOURCE or prior_complete
        rows.append(
            ExportWizardStepView(
                step=step,
                label=label,
                description=description,
                active=step is state.step,
                completed=completion[step],
                available=available,
            )
        )
        prior_complete = prior_complete and completion[step]
    return tuple(rows)


def build_export_wizard_review(
    state: ExportWizardState,
    *,
    capabilities: ExportWizardCapabilities | None = None,
) -> ExportWizardReview:
    """Return the final review screen model used by UI shells and tests."""

    preflight = validate_export_wizard(state, capabilities=capabilities)
    profile = profile_by_id(state.profile)
    export_format = export_format_by_id(state.export_format)
    ui_state = preflight.ui_state
    file_name = ""
    if ui_state is not None:
        file_name = f"{ui_state.base_name}.{export_format.extension}"
    return ExportWizardReview(
        source_label=str(state.source_label or "").strip(),
        project_label=str(state.project_label or "").strip(),
        profile_label=profile.label,
        format_label=export_format.label,
        destination=str(Path(state.output_dir)),
        file_name=file_name,
        include_figures=bool(state.include_figures),
        ready=preflight.ready,
        issues=preflight.issues,
        steps=build_export_wizard_steps(state, capabilities=capabilities),
    )


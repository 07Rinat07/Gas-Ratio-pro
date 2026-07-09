from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from reports.document_model import EngineeringDocument, build_engineering_document
from reports.presentation_docx import PresentationDocxOptions, build_presentation_docx_report
from reports.presentation_html import PresentationHtmlOptions, build_presentation_html_report
from reports.presentation_model import PresentationModel
from reports.presentation_pdf import PresentationPdfOptions, build_presentation_pdf_report


PRESENTATION_LAYER_FREEZE_VERSION = "1.0"
PRESENTATION_MODEL_SCHEMA = "gas-ratio-pro/presentation/model/v1"
DOCUMENT_MODEL_SCHEMA = "gas-ratio-pro/document/model/v1"
HTML_PROFILE_SCHEMA = "gas-ratio-pro/presentation/html/v1"
PDF_PROFILE_SCHEMA = "gas-ratio-pro/presentation/pdf/v1"
DOCX_PROFILE_SCHEMA = "gas-ratio-pro/presentation/docx/v1"


@dataclass(frozen=True)
class PresentationFreezeCheck:
    """Single Presentation Layer freeze gate check.

    The check is intentionally small and serializable so it can be shown in the
    UI, written into manifests, or used by tests without coupling to pytest.
    """

    code: str
    title: str
    passed: bool
    details: str = ""


@dataclass(frozen=True)
class PresentationFreezeStatus:
    """Result of the Presentation Layer v1 freeze gate."""

    version: str
    frozen: bool
    checks: tuple[PresentationFreezeCheck, ...]
    presentation_schema: str
    document_schema: str

    @property
    def failed_checks(self) -> tuple[PresentationFreezeCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)

    def require_frozen(self) -> None:
        """Raise a deterministic error when the freeze gate is not satisfied."""

        if self.frozen:
            return
        failed = ", ".join(check.code for check in self.failed_checks) or "unknown"
        raise RuntimeError(f"Presentation Layer freeze gate failed: {failed}")


def _check(code: str, title: str, passed: bool, details: str = "") -> PresentationFreezeCheck:
    return PresentationFreezeCheck(code=code, title=title, passed=bool(passed), details=details)


def _same(values: Iterable[object]) -> bool:
    unique = set(values)
    return len(unique) == 1


def build_presentation_freeze_status(
    model: PresentationModel,
    *,
    include_figures: bool = True,
    include_technical_appendix: bool | None = None,
) -> PresentationFreezeStatus:
    """Run the Presentation Layer v1 audit/freeze gate.

    This function does not run hydrocarbon calculations and does not reinterpret
    intervals. It verifies that the frozen reporting stack has one source of
    presentation truth: ``PresentationModel -> EngineeringDocument -> renderers``.
    """

    include_technical = (
        model.metadata.report_profile == "expert"
        if include_technical_appendix is None
        else bool(include_technical_appendix)
    )
    document: EngineeringDocument = build_engineering_document(
        model,
        include_figures=include_figures,
        include_technical_appendix=include_technical,
    )

    html = build_presentation_html_report(
        model,
        options=PresentationHtmlOptions(
            include_figures=include_figures,
            include_technical_appendix=include_technical,
            page_title=model.metadata.title,
        ),
    )
    pdf = build_presentation_pdf_report(
        model,
        options=PresentationPdfOptions(
            include_figures=include_figures,
            include_technical_appendix=include_technical,
            title=model.metadata.title,
        ),
    )
    docx = build_presentation_docx_report(
        model,
        options=PresentationDocxOptions(
            include_figures=include_figures,
            include_technical_appendix=include_technical,
            title=model.metadata.title,
        ),
    )

    checks = (
        _check(
            "presentation_schema_v1",
            "PresentationModel schema is frozen",
            model.schema == PRESENTATION_MODEL_SCHEMA,
            model.schema,
        ),
        _check(
            "document_schema_v1",
            "EngineeringDocument schema is frozen",
            document.schema == DOCUMENT_MODEL_SCHEMA,
            document.schema,
        ),
        _check(
            "document_single_source",
            "Document table and plot composition matches renderers",
            document.table_titles == html.table_titles == pdf.table_titles == docx.table_titles
            and document.plot_count == html.figure_count == pdf.figure_count == docx.figure_count,
            f"tables={document.table_titles}; plots={document.plot_count}",
        ),
        _check(
            "renderer_profile_consistency",
            "HTML/PDF/DOCX profiles are identical",
            _same((html.profile, pdf.profile, docx.profile)) and html.profile == document.metadata.profile,
            f"html={html.profile}; pdf={pdf.profile}; docx={docx.profile}; document={document.metadata.profile}",
        ),
        _check(
            "engineering_profile_default",
            "Engineering profile remains engineer-first",
            include_technical or document.metadata.profile == "engineering",
            document.metadata.profile,
        ),
        _check(
            "renderer_schemas_v1",
            "Renderer result schemas are frozen where applicable",
            pdf.schema == PDF_PROFILE_SCHEMA and docx.schema == DOCX_PROFILE_SCHEMA,
            f"pdf={pdf.schema}; docx={docx.schema}",
        ),
    )
    frozen = all(check.passed for check in checks)
    return PresentationFreezeStatus(
        version=PRESENTATION_LAYER_FREEZE_VERSION,
        frozen=frozen,
        checks=checks,
        presentation_schema=model.schema,
        document_schema=document.schema,
    )


__all__ = [
    "DOCUMENT_MODEL_SCHEMA",
    "DOCX_PROFILE_SCHEMA",
    "HTML_PROFILE_SCHEMA",
    "PDF_PROFILE_SCHEMA",
    "PRESENTATION_LAYER_FREEZE_VERSION",
    "PRESENTATION_MODEL_SCHEMA",
    "PresentationFreezeCheck",
    "PresentationFreezeStatus",
    "build_presentation_freeze_status",
]

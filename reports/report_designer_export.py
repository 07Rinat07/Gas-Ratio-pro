from __future__ import annotations

"""Download-ready exports produced from a Professional Report Designer design."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from reports.presentation_docx import render_engineering_document_docx
from reports.presentation_model import PresentationModel
from reports.presentation_pdf import render_engineering_document_pdf
from reports.presentation_ui import ExportFormat, export_format_by_id
from reports.report_designer import ReportDesign, require_designed_report
from reports.presentation_export import safe_export_basename


@dataclass(frozen=True)
class DesignedReportArtifact:
    content: bytes
    file_name: str
    mime_type: str
    export_format: ExportFormat
    template_id: str
    manifest_names: tuple[str, ...] = ()


def build_designed_report_artifact(
    model: PresentationModel,
    *,
    design: ReportDesign,
    export_format: str,
    base_name: str,
) -> DesignedReportArtifact:
    """Render PDF, DOCX or a synchronized bundle from one designed document."""

    normalized_format = export_format_by_id(export_format)
    if normalized_format.id not in {"pdf", "docx", "bundle"}:
        raise ValueError(
            f"Export format {normalized_format.id!r} is not supported by Report Designer; "
            "use the visualization or table exporter."
        )

    result = require_designed_report(model, design)
    assert result.document is not None
    assert result.pdf_options is not None
    assert result.docx_options is not None
    safe_name = safe_export_basename(base_name, fallback="gas-ratio-professional-report")

    if normalized_format.id == "pdf":
        rendered = render_engineering_document_pdf(result.document, options=result.pdf_options)
        return DesignedReportArtifact(
            content=rendered.content,
            file_name=f"{safe_name}.pdf",
            mime_type=normalized_format.mime_type,
            export_format="pdf",
            template_id=design.template_id,
        )

    if normalized_format.id == "docx":
        rendered = render_engineering_document_docx(result.document, options=result.docx_options)
        return DesignedReportArtifact(
            content=rendered.content,
            file_name=f"{safe_name}.docx",
            mime_type=normalized_format.mime_type,
            export_format="docx",
            template_id=design.template_id,
        )

    pdf = render_engineering_document_pdf(result.document, options=result.pdf_options)
    docx = render_engineering_document_docx(result.document, options=result.docx_options)
    pdf_name = f"{safe_name}.pdf"
    docx_name = f"{safe_name}.docx"
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(pdf_name, pdf.content)
        archive.writestr(docx_name, docx.content)
    return DesignedReportArtifact(
        content=buffer.getvalue(),
        file_name=f"{safe_name}.zip",
        mime_type=normalized_format.mime_type,
        export_format="bundle",
        template_id=design.template_id,
        manifest_names=(pdf_name, docx_name),
    )


__all__ = ["DesignedReportArtifact", "build_designed_report_artifact"]

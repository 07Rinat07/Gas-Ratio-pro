from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Literal

from reports.presentation_html import PresentationHtmlOptions, build_presentation_html_report
from reports.presentation_model import PresentationModel


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


PresentationExportKind = Literal["html", "pdf", "docx", "bundle"]


@dataclass(frozen=True)
class PresentationUnifiedExportResult:
    """Unified result returned by the renderer-neutral export facade.

    The result exposes the common audit fields for every export mode and keeps
    format-specific paths in one dictionary. UI/controllers can depend on this
    stable object instead of branching over individual renderer return classes.
    """

    kind: str
    files: dict[str, Path]
    manifest_path: Path
    profile: str
    table_titles: tuple[str, ...]
    figure_count: int

    def primary_path(self) -> Path:
        """Return the main user-facing file for single-format exports.

        Bundle exports do not have one primary artifact, therefore the bundle
        manifest is returned as the auditable entry point.
        """

        for key in ("html", "pdf", "docx"):
            if key in self.files:
                return self.files[key]
        return self.manifest_path


@dataclass(frozen=True)
class PresentationExportOptions:
    """Options for writing a printable presentation export package.

    This exporter is intentionally renderer-neutral. It writes the current
    professional HTML report and a small manifest that records which profile,
    sections and figures were exported. Future PDF/DOCX exporters can use the
    same PresentationModel without rebuilding engineering content.
    """

    output_dir: str | Path
    base_name: str = "gas-ratio-professional-report"
    include_figures: bool = True
    include_technical_appendix: bool = False
    overwrite: bool = True


@dataclass(frozen=True)
class PresentationExportResult:
    """Files created by the presentation export layer."""

    html_path: Path
    manifest_path: Path
    profile: str
    table_titles: tuple[str, ...]
    figure_count: int


@dataclass(frozen=True)
class PresentationDocxExportResult:
    """DOCX file created by the presentation export layer."""

    docx_path: Path
    manifest_path: Path
    profile: str
    table_titles: tuple[str, ...]
    figure_count: int


@dataclass(frozen=True)
class PresentationPdfExportResult:
    """PDF file created by the presentation export layer."""

    pdf_path: Path
    manifest_path: Path
    profile: str
    table_titles: tuple[str, ...]
    figure_count: int


@dataclass(frozen=True)
class PresentationBundleExportResult:
    """Multi-format export created from one PresentationModel.

    The bundle exporter is the consistency gate for Professional Reporting.
    It writes HTML, PDF and DOCX from the same source model and records one
    bundle manifest so engineering content can be audited across formats.
    """

    html_path: Path
    pdf_path: Path
    docx_path: Path
    manifest_path: Path
    profile: str
    table_titles: tuple[str, ...]
    figure_count: int


def safe_export_basename(value: str, *, fallback: str = "gas-ratio-professional-report") -> str:
    """Return a filesystem-safe export basename without directory traversal.

    User-entered well names or project labels may contain spaces, slashes or
    local-language punctuation. Export paths must be deterministic and safe, so
    this helper collapses unsupported characters to underscores and strips path
    separators.
    """

    text = str(value or "").strip()
    if not text:
        text = fallback
    text = text.replace("\\", "_").replace("/", "_")
    text = _SAFE_NAME_RE.sub("_", text).strip("._-")
    return text or fallback


def _write_bytes(path: Path, content: bytes, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Export file already exists: {path}")
    path.write_bytes(content)


def _metadata_manifest(model: PresentationModel) -> dict[str, str]:
    return {
        "title": model.metadata.title,
        "subtitle": model.metadata.subtitle,
        "source_label": model.metadata.source_label,
        "project_label": model.metadata.project_label,
        "depth_label": model.metadata.depth_label,
        "report_profile": model.metadata.report_profile,
    }


def _export_manifest(
    *,
    schema: str,
    model: PresentationModel,
    profile: str,
    table_titles: tuple[str, ...],
    figure_count: int,
    files: dict[str, str],
    renderer_schema: dict[str, str] | None = None,
    consistency: dict[str, bool] | None = None,
) -> dict[str, object]:
    """Build a normalized manifest for HTML, PDF, DOCX and bundle exports."""

    manifest: dict[str, object] = {
        "schema": schema,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "profile": profile,
        "files": files,
        "table_titles": list(table_titles),
        "figure_count": figure_count,
        "presentation_schema": model.schema,
        "metadata": _metadata_manifest(model),
    }
    if renderer_schema:
        manifest["renderer_schema"] = renderer_schema
    if consistency:
        manifest["consistency"] = consistency
    return manifest


def export_presentation_html_package(
    model: PresentationModel,
    *,
    options: PresentationExportOptions,
) -> PresentationExportResult:
    """Write a professional HTML report plus a reproducible export manifest.

    The function does not run interval detection or interpretation. It consumes
    the already-built PresentationModel and records enough metadata to audit what
    exactly was exported for a given report profile.
    """

    output_dir = Path(options.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = safe_export_basename(options.base_name)

    rendered = build_presentation_html_report(
        model,
        options=PresentationHtmlOptions(
            include_figures=options.include_figures,
            include_technical_appendix=options.include_technical_appendix,
            page_title=model.metadata.title,
        ),
    )

    html_path = output_dir / f"{base_name}.html"
    manifest_path = output_dir / f"{base_name}.manifest.json"
    _write_bytes(html_path, rendered.content, overwrite=options.overwrite)

    manifest = _export_manifest(
        schema="gas-ratio-pro/presentation/export/v1",
        model=model,
        profile=rendered.profile,
        table_titles=rendered.table_titles,
        figure_count=rendered.figure_count,
        files={"html": html_path.name},
    )
    manifest["html_file"] = html_path.name  # Backward-compatible manifest field.
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    _write_bytes(manifest_path, manifest_bytes, overwrite=options.overwrite)

    return PresentationExportResult(
        html_path=html_path,
        manifest_path=manifest_path,
        profile=rendered.profile,
        table_titles=rendered.table_titles,
        figure_count=rendered.figure_count,
    )


def export_presentation_docx_package(
    model: PresentationModel,
    *,
    options: PresentationExportOptions,
    docx_options: object | None = None,
) -> PresentationDocxExportResult:
    """Write a professional DOCX report plus a reproducible export manifest.

    DOCX support is imported lazily so the Streamlit application can start
    even on environments where the optional ``python-docx`` package is not
    installed yet. The user only needs the dependency when exporting DOCX.
    """

    from reports.presentation_docx import PresentationDocxOptions, build_presentation_docx_report, ensure_docx_available

    ensure_docx_available()

    output_dir = Path(options.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = safe_export_basename(options.base_name)

    rendered = build_presentation_docx_report(
        model,
        options=docx_options
        or PresentationDocxOptions(
            include_figures=options.include_figures,
            include_technical_appendix=options.include_technical_appendix,
            title=model.metadata.title,
        ),
    )

    docx_path = output_dir / f"{base_name}.docx"
    manifest_path = output_dir / f"{base_name}.docx.manifest.json"
    _write_bytes(docx_path, rendered.content, overwrite=options.overwrite)

    manifest = _export_manifest(
        schema="gas-ratio-pro/presentation/docx-export/v1",
        model=model,
        profile=rendered.profile,
        table_titles=rendered.table_titles,
        figure_count=rendered.figure_count,
        files={"docx": docx_path.name},
        renderer_schema={"docx": rendered.schema},
    )
    manifest["docx_file"] = docx_path.name  # Backward-compatible manifest field.
    manifest["docx_schema"] = rendered.schema
    _write_bytes(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"), overwrite=options.overwrite)

    return PresentationDocxExportResult(
        docx_path=docx_path,
        manifest_path=manifest_path,
        profile=rendered.profile,
        table_titles=rendered.table_titles,
        figure_count=rendered.figure_count,
    )


def export_presentation_pdf_package(
    model: PresentationModel,
    *,
    options: PresentationExportOptions,
    pdf_options: object | None = None,
) -> PresentationPdfExportResult:
    """Write a professional PDF report plus a reproducible export manifest.

    PDF support is imported lazily so reportlab is required only when the user
    actually exports PDF or bundle reports.
    """

    from reports.presentation_pdf import PresentationPdfOptions, build_presentation_pdf_report

    output_dir = Path(options.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = safe_export_basename(options.base_name)

    rendered = build_presentation_pdf_report(
        model,
        options=pdf_options
        or PresentationPdfOptions(
            include_figures=options.include_figures,
            include_technical_appendix=options.include_technical_appendix,
            title=model.metadata.title,
        ),
    )

    pdf_path = output_dir / f"{base_name}.pdf"
    manifest_path = output_dir / f"{base_name}.pdf.manifest.json"
    _write_bytes(pdf_path, rendered.content, overwrite=options.overwrite)

    manifest = _export_manifest(
        schema="gas-ratio-pro/presentation/pdf-export/v1",
        model=model,
        profile=rendered.profile,
        table_titles=rendered.table_titles,
        figure_count=rendered.figure_count,
        files={"pdf": pdf_path.name},
        renderer_schema={"pdf": rendered.schema},
    )
    manifest["pdf_file"] = pdf_path.name  # Backward-compatible manifest field.
    manifest["pdf_schema"] = rendered.schema
    _write_bytes(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"), overwrite=options.overwrite)

    return PresentationPdfExportResult(
        pdf_path=pdf_path,
        manifest_path=manifest_path,
        profile=rendered.profile,
        table_titles=rendered.table_titles,
        figure_count=rendered.figure_count,
    )


def export_presentation_bundle_package(
    model: PresentationModel,
    *,
    options: PresentationExportOptions,
    pdf_options: object | None = None,
    docx_options: object | None = None,
) -> PresentationBundleExportResult:
    """Write HTML, PDF and DOCX reports from the same PresentationModel.

    This function is intentionally a thin orchestration layer. It does not
    rebuild interpretation content and it does not call calculation engines.
    All formats are rendered from the same PresentationModel/EngineeringDocument
    chain, which prevents the engineering report, printable PDF and DOCX copy
    from diverging.
    """

    output_dir = Path(options.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = safe_export_basename(options.base_name)

    html_result = export_presentation_html_package(model, options=options)
    pdf_result = export_presentation_pdf_package(
        model,
        options=options,
        pdf_options=pdf_options,
    )
    docx_result = export_presentation_docx_package(
        model,
        options=options,
        docx_options=docx_options,
    )

    profile_set = {html_result.profile, pdf_result.profile, docx_result.profile}
    if len(profile_set) != 1:
        raise ValueError(f"Presentation export profiles diverged: {sorted(profile_set)}")

    title_set = {html_result.table_titles, pdf_result.table_titles, docx_result.table_titles}
    if len(title_set) != 1:
        raise ValueError("Presentation export table composition diverged between formats")

    figure_set = {html_result.figure_count, pdf_result.figure_count, docx_result.figure_count}
    if len(figure_set) != 1:
        raise ValueError("Presentation export figure count diverged between formats")

    bundle_manifest_path = output_dir / f"{base_name}.bundle.manifest.json"
    manifest = _export_manifest(
        schema="gas-ratio-pro/presentation/bundle-export/v1",
        model=model,
        profile=html_result.profile,
        table_titles=html_result.table_titles,
        figure_count=html_result.figure_count,
        files={
            "html": html_result.html_path.name,
            "pdf": pdf_result.pdf_path.name,
            "docx": docx_result.docx_path.name,
            "html_manifest": html_result.manifest_path.name,
            "pdf_manifest": pdf_result.manifest_path.name,
            "docx_manifest": docx_result.manifest_path.name,
        },
        consistency={
            "same_profile": True,
            "same_table_titles": True,
            "same_figure_count": True,
            "single_source_model": True,
        },
    )
    _write_bytes(
        bundle_manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        overwrite=options.overwrite,
    )

    return PresentationBundleExportResult(
        html_path=html_result.html_path,
        pdf_path=pdf_result.pdf_path,
        docx_path=docx_result.docx_path,
        manifest_path=bundle_manifest_path,
        profile=html_result.profile,
        table_titles=html_result.table_titles,
        figure_count=html_result.figure_count,
    )


def export_presentation_package(
    model: PresentationModel,
    *,
    kind: PresentationExportKind,
    options: PresentationExportOptions,
    pdf_options: object | None = None,
    docx_options: object | None = None,
) -> PresentationUnifiedExportResult:
    """Export a presentation report through one stable facade.

    Controllers and UI code should call this function instead of selecting
    renderer-specific functions directly. The facade preserves lazy imports and
    still returns a normalized audit result for HTML, PDF, DOCX or bundle mode.
    """

    normalized_kind = str(kind or "").strip().lower()
    if normalized_kind == "html":
        result = export_presentation_html_package(model, options=options)
        return PresentationUnifiedExportResult(
            kind="html",
            files={"html": result.html_path},
            manifest_path=result.manifest_path,
            profile=result.profile,
            table_titles=result.table_titles,
            figure_count=result.figure_count,
        )
    if normalized_kind == "pdf":
        result = export_presentation_pdf_package(model, options=options, pdf_options=pdf_options)
        return PresentationUnifiedExportResult(
            kind="pdf",
            files={"pdf": result.pdf_path},
            manifest_path=result.manifest_path,
            profile=result.profile,
            table_titles=result.table_titles,
            figure_count=result.figure_count,
        )
    if normalized_kind == "docx":
        result = export_presentation_docx_package(model, options=options, docx_options=docx_options)
        return PresentationUnifiedExportResult(
            kind="docx",
            files={"docx": result.docx_path},
            manifest_path=result.manifest_path,
            profile=result.profile,
            table_titles=result.table_titles,
            figure_count=result.figure_count,
        )
    if normalized_kind == "bundle":
        result = export_presentation_bundle_package(
            model,
            options=options,
            pdf_options=pdf_options,
            docx_options=docx_options,
        )
        return PresentationUnifiedExportResult(
            kind="bundle",
            files={"html": result.html_path, "pdf": result.pdf_path, "docx": result.docx_path},
            manifest_path=result.manifest_path,
            profile=result.profile,
            table_titles=result.table_titles,
            figure_count=result.figure_count,
        )
    raise ValueError(f"Unsupported presentation export kind: {kind!r}")


__all__ = [
    "PresentationExportOptions",
    "PresentationExportKind",
    "PresentationExportResult",
    "PresentationUnifiedExportResult",
    "PresentationDocxExportResult",
    "PresentationPdfExportResult",
    "PresentationBundleExportResult",
    "export_presentation_bundle_package",
    "export_presentation_docx_package",
    "export_presentation_html_package",
    "export_presentation_package",
    "export_presentation_pdf_package",
    "safe_export_basename",
]

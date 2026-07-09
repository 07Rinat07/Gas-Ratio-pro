from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re

from reports.presentation_html import PresentationHtmlOptions, build_presentation_html_report
from reports.presentation_model import PresentationModel


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


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

    manifest = {
        "schema": "gas-ratio-pro/presentation/export/v1",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "profile": rendered.profile,
        "html_file": html_path.name,
        "table_titles": list(rendered.table_titles),
        "figure_count": rendered.figure_count,
        "presentation_schema": model.schema,
        "metadata": {
            "title": model.metadata.title,
            "subtitle": model.metadata.subtitle,
            "source_label": model.metadata.source_label,
            "project_label": model.metadata.project_label,
            "depth_label": model.metadata.depth_label,
            "report_profile": model.metadata.report_profile,
        },
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    _write_bytes(manifest_path, manifest_bytes, overwrite=options.overwrite)

    return PresentationExportResult(
        html_path=html_path,
        manifest_path=manifest_path,
        profile=rendered.profile,
        table_titles=rendered.table_titles,
        figure_count=rendered.figure_count,
    )


__all__ = [
    "PresentationExportOptions",
    "PresentationExportResult",
    "export_presentation_html_package",
    "safe_export_basename",
]

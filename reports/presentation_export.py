from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
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
class PresentationBundleValidationResult:
    """Audit result for a generated multi-format presentation bundle.

    Release QA needs a deterministic check that all files referenced by the
    bundle manifest exist, have non-empty payloads and keep the declared
    cross-format consistency flags. The validator reads only the export
    artifacts; it never rebuilds engineering calculations or presentation
    models.
    """

    manifest_path: Path
    ok: bool
    files_checked: tuple[Path, ...]
    missing_files: tuple[str, ...]
    empty_files: tuple[str, ...]
    consistency: dict[str, bool]
    validation_report_path: Path | None = None

    @property
    def issue_count(self) -> int:
        """Return the number of concrete file-level validation issues."""

        return len(self.missing_files) + len(self.empty_files)


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


def _visualization_manifest(model: PresentationModel) -> dict[str, object]:
    """Return export-audit metadata for prepared visualization previews.

    Export manifests must describe whether renderer-ready visualization previews
    travelled with the report contract.  The function only inspects the
    already-prepared PresentationModel previews and never rebuilds LAS tracks,
    sampled curves or interval overlays.
    """

    raw_previews = getattr(model, "visualization_previews", ()) or ()
    previews = [dict(preview or {}) for preview in raw_previews]
    formats = sorted({str(preview.get("format") or "").strip() for preview in previews if str(preview.get("format") or "").strip()})
    return {
        "preview_count": len(previews),
        "export_ready": bool(previews) and all(bool(preview.get("export_ready")) for preview in previews),
        "formats": formats,
        "contains_raw_dataframe": any(bool(preview.get("contains_raw_dataframe")) for preview in previews),
        "total_tracks": sum(int(preview.get("track_count") or 0) for preview in previews),
        "total_curves": sum(int(preview.get("curve_count") or 0) for preview in previews),
        "total_overlays": sum(int(preview.get("overlay_count") or 0) for preview in previews),
    }




def _visualization_preview_assets(model: PresentationModel, *, base_name: str) -> dict[str, str]:
    """Write stable SVG visualization assets for report bundles.

    The bundle manifest must point every report format to one shared
    Visualization Engine output instead of letting HTML, PDF and DOCX invent
    their own copies.  Only lightweight SVG previews are exported; raw LAS
    dataframes and sampled point payloads remain inside service-layer contracts.
    """

    assets: dict[str, str] = {}
    for index, preview in enumerate(getattr(model, "visualization_previews", ()) or (), start=1):
        data = dict(preview or {})
        if str(data.get("format") or "").lower() != "svg":
            continue
        svg = str(data.get("svg") or "").strip()
        if not svg.startswith("<svg"):
            continue
        key = f"visualization_preview_{index}"
        assets[key] = f"assets/{base_name}-{key}.svg"
    return assets


def _write_visualization_preview_assets(model: PresentationModel, *, output_dir: Path, base_name: str, overwrite: bool) -> dict[str, str]:
    """Persist visualization SVG previews as auditable bundle assets."""

    asset_paths = _visualization_preview_assets(model, base_name=base_name)
    if not asset_paths:
        return {}
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    previews = tuple(getattr(model, "visualization_previews", ()) or ())
    for index, preview in enumerate(previews, start=1):
        key = f"visualization_preview_{index}"
        relative_name = asset_paths.get(key)
        if not relative_name:
            continue
        svg = str(dict(preview or {}).get("svg") or "").strip()
        _write_bytes(output_dir / relative_name, svg.encode("utf-8"), overwrite=overwrite)
    return asset_paths




def _asset_digest(path: Path) -> str:
    """Return a stable sha256 digest for an exported bundle asset."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_visualization_asset_index(
    *,
    output_dir: Path,
    assets: dict[str, str],
    model: PresentationModel,
) -> dict[str, object]:
    """Build a machine-readable index for visualization bundle assets.

    The bundle manifest records where visualization assets are, while the asset
    index gives external tools a compact, filesystem-verifiable catalogue with
    size, digest and renderer metadata.  It reads only already written assets
    and already prepared preview contracts; no plotting or LAS calculations are
    executed here.
    """

    previews = tuple(getattr(model, "visualization_previews", ()) or ())
    entries: list[dict[str, object]] = []
    total_size = 0
    for index, preview in enumerate(previews, start=1):
        key = f"visualization_preview_{index}"
        relative_name = assets.get(key)
        if not relative_name:
            continue
        path = output_dir / relative_name
        data = dict(preview or {})
        size = path.stat().st_size if path.exists() else 0
        total_size += size
        entries.append(
            {
                "id": key,
                "role": "visualization_preview",
                "format": str(data.get("format") or "svg"),
                "path": relative_name,
                "size_bytes": size,
                "sha256": _asset_digest(path) if path.exists() else "",
                "export_ready": bool(data.get("export_ready")),
                "track_count": int(data.get("track_count") or 0),
                "curve_count": int(data.get("curve_count") or 0),
                "overlay_count": int(data.get("overlay_count") or 0),
                "contains_raw_dataframe": bool(data.get("contains_raw_dataframe")),
            }
        )

    return {
        "schema": "gas-ratio-pro/presentation/visualization-assets/v1",
        "asset_count": len(entries),
        "total_size_bytes": total_size,
        "formats": sorted({str(entry["format"]) for entry in entries}),
        "all_export_ready": bool(entries) and all(bool(entry["export_ready"]) for entry in entries),
        "contains_raw_dataframe": any(bool(entry["contains_raw_dataframe"]) for entry in entries),
        "assets": entries,
    }


def _write_visualization_asset_index(
    *,
    output_dir: Path,
    base_name: str,
    assets: dict[str, str],
    model: PresentationModel,
    overwrite: bool,
) -> str:
    """Persist the visualization asset index and return its relative path."""

    if not assets:
        return ""
    index = _build_visualization_asset_index(output_dir=output_dir, assets=assets, model=model)
    relative_name = f"assets/{base_name}-visualization-assets.index.json"
    index_path = output_dir / relative_name
    index_path.parent.mkdir(parents=True, exist_ok=True)
    _write_bytes(index_path, json.dumps(index, ensure_ascii=False, indent=2).encode("utf-8"), overwrite=overwrite)
    return relative_name


def _with_visualization_assets(manifest: dict[str, object], assets: dict[str, str], *, asset_index: str = "") -> dict[str, object]:
    """Attach shared visualization asset references to an export manifest."""

    if not assets:
        return manifest
    files = manifest.setdefault("files", {})
    if isinstance(files, dict):
        files.update(assets)
    visualization = manifest.setdefault("visualization", {})
    if isinstance(visualization, dict):
        visualization["asset_count"] = len(assets)
        visualization["asset_format"] = "svg"
        visualization["assets"] = dict(assets)
        visualization["single_shared_asset_source"] = True
        if asset_index:
            files["visualization_asset_index"] = asset_index
            visualization["asset_index"] = asset_index
            visualization["asset_index_schema"] = "gas-ratio-pro/presentation/visualization-assets/v1"
    return manifest


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
        "visualization": _visualization_manifest(model),
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
            # Engineering reports contain wide ranking/passport tables and are
            # materially more readable on landscape A4.  Client reports remain
            # compact portrait documents.
            orientation="landscape" if model.metadata.report_profile == "engineering" else "portrait",
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

    visualization_preview_count = int(_visualization_manifest(model)["preview_count"])
    visualization_assets = _write_visualization_preview_assets(
        model,
        output_dir=output_dir,
        base_name=base_name,
        overwrite=options.overwrite,
    )

    visualization_asset_index = _write_visualization_asset_index(
        output_dir=output_dir,
        base_name=base_name,
        assets=visualization_assets,
        model=model,
        overwrite=options.overwrite,
    )

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
            **visualization_assets,
            **({"visualization_asset_index": visualization_asset_index} if visualization_asset_index else {}),
        },
        consistency={
            "same_profile": True,
            "same_table_titles": True,
            "same_figure_count": True,
            "same_visualization_preview_count": True,
            "same_visualization_asset_count": len(visualization_assets) == visualization_preview_count,
            "single_visualization_asset_source": True,
            "visualization_asset_index_ready": bool(visualization_assets) == bool(visualization_asset_index),
            "single_source_model": True,
        },
    )
    _with_visualization_assets(manifest, visualization_assets, asset_index=visualization_asset_index)
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




def build_presentation_bundle_validation_report(result: PresentationBundleValidationResult) -> dict[str, object]:
    """Return a machine-readable validation report for a bundle audit.

    The report is designed for CI and external QA tools.  It mirrors the
    filesystem-only validation result in JSON-safe primitives and adds an
    explicit status, issue list and checked-file catalogue so callers do not
    have to parse console output or Python dataclasses.
    """

    issues: list[dict[str, str]] = []
    for name in result.missing_files:
        issues.append({"severity": "error", "kind": "missing_file", "target": str(name)})
    for name in result.empty_files:
        issues.append({"severity": "error", "kind": "empty_file", "target": str(name)})
    failed_consistency = sorted(key for key, value in result.consistency.items() if value is not True)
    for key in failed_consistency:
        issues.append({"severity": "error", "kind": "failed_consistency", "target": key})

    files = []
    for path in result.files_checked:
        files.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )

    return {
        "schema": "gas-ratio-pro/presentation/bundle-validation/v1",
        "status": "ok" if result.ok else "failed",
        "ok": result.ok,
        "manifest": str(result.manifest_path),
        "files_checked": files,
        "file_count": len(files),
        "missing_files": list(result.missing_files),
        "empty_files": list(result.empty_files),
        "consistency": dict(result.consistency),
        "failed_consistency": failed_consistency,
        "issue_count": len(issues),
        "issues": issues,
    }


def write_presentation_bundle_validation_report(
    result: PresentationBundleValidationResult,
    *,
    report_path: str | Path | None = None,
    overwrite: bool = True,
) -> Path:
    """Write a JSON validation report beside a bundle manifest.

    The default filename is derived from the manifest name and is stable across
    local QA, CI and release packaging.  This keeps release evidence inside the
    export directory without re-running any presentation calculations.
    """

    path = Path(report_path) if report_path is not None else result.manifest_path.with_suffix(".validation.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_presentation_bundle_validation_report(result)
    _write_bytes(path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), overwrite=overwrite)
    return path

def validate_presentation_bundle_export(manifest_path: str | Path) -> PresentationBundleValidationResult:
    """Validate an already written presentation bundle manifest.

    The bundle manifest is the release-audit entry point for professional
    reports. This function confirms that every referenced artifact is present,
    non-empty and that the consistency flags created by the bundle exporter are
    still true. It is intentionally filesystem-only so it can run in CI, smoke
    scripts and operator checks without loading LAS data again.
    """

    manifest = Path(manifest_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    base_dir = manifest.parent
    files = payload.get("files", {})
    if not isinstance(files, dict):
        files = {}

    required_keys = ("html", "pdf", "docx", "html_manifest", "pdf_manifest", "docx_manifest")
    visualization_assets = payload.get("visualization", {}).get("assets", {}) if isinstance(payload.get("visualization"), dict) else {}
    if not isinstance(visualization_assets, dict):
        visualization_assets = {}
    checked: list[Path] = []
    missing: list[str] = []
    empty: list[str] = []

    asset_index_key = "visualization_asset_index" if files.get("visualization_asset_index") else ""

    for key in required_keys + tuple(str(key) for key in visualization_assets.keys()) + ((asset_index_key,) if asset_index_key else ()): 
        name = files.get(key)
        if not isinstance(name, str) or not name.strip():
            missing.append(key)
            continue
        path = base_dir / name
        checked.append(path)
        if not path.exists():
            missing.append(name)
            continue
        if path.stat().st_size <= 0:
            empty.append(name)

    raw_consistency = payload.get("consistency", {})
    consistency = {str(key): bool(value) for key, value in raw_consistency.items()} if isinstance(raw_consistency, dict) else {}
    required_consistency = (
        "same_profile",
        "same_table_titles",
        "same_figure_count",
        "same_visualization_preview_count",
        "single_source_model",
    )
    consistency_ok = all(consistency.get(key) is True for key in required_consistency)
    ok = not missing and not empty and consistency_ok

    return PresentationBundleValidationResult(
        manifest_path=manifest,
        ok=ok,
        files_checked=tuple(checked),
        missing_files=tuple(missing),
        empty_files=tuple(empty),
        consistency=consistency,
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
    "PresentationBundleValidationResult",
    "build_presentation_bundle_validation_report",
    "export_presentation_bundle_package",
    "export_presentation_docx_package",
    "export_presentation_html_package",
    "export_presentation_package",
    "export_presentation_pdf_package",
    "safe_export_basename",
    "validate_presentation_bundle_export",
    "write_presentation_bundle_validation_report",
]

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

import pandas as pd

from las_editor.las_creator import LasCreationSpec, build_las_text
from las_editor.las_safe_export import (
    LasExportIssue,
    LasSafeExportManifest,
    build_las_export_manifest,
    export_issue_table_rows,
    export_las_document_safely,
    export_las_text_safely,
    export_manifest_table,
)
from las_editor.las_validator import LasValidationFinding
from reports.export_csv import export_csv_bytes
from reports.export_las import export_las_bytes
from reports.export_xlsx import export_xlsx_bytes

LAS_EXPORT_CENTER_SCHEMA = "gas-ratio-pro.las-export-center.v1"
LAS_EXPORT_CENTER_STORAGE_KEY = "las_export_center"
SUPPORTED_EXPORT_FORMATS = ("las", "csv", "xlsx")
ExportFormat = Literal["las", "csv", "xlsx"]


@dataclass(frozen=True)
class ExportCenterRequest:
    """Renderer-independent export request for LAS Workspace 2.0.

    The request is intentionally explicit: UI code prepares this object, while
    backend code validates the destination, renders a preview manifest and only
    writes files through safe exporter methods.
    """

    target_path: str | Path
    export_format: ExportFormat = "las"
    source_path: str | Path | None = None
    allow_overwrite: bool = False
    create_parent: bool = True
    well_name: str = "WELL"
    depth_column: str | None = None
    null_value: float = -999.25
    curve_units: dict[str, str] = field(default_factory=dict)
    well_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExportCenterResult:
    """Unified result for Export Center preview/write operations."""

    schema: str
    status: str
    export_format: str
    target_path: str
    manifest: LasSafeExportManifest
    issues: tuple[LasExportIssue, ...] = ()
    table_rows: tuple[dict[str, Any], ...] = ()
    markdown_report: str = ""
    bytes_count: int = 0

    @property
    def is_ready(self) -> bool:
        return self.status == "ready" and self.manifest.is_ready

    @property
    def is_exported(self) -> bool:
        return self.status == "exported" and self.manifest.is_ready


def normalize_export_format(value: str) -> ExportFormat:
    normalized = str(value or "las").strip().lower().lstrip(".")
    if normalized not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format: {value!r}")
    return normalized  # type: ignore[return-value]


def normalize_export_path(path: str | Path, export_format: str) -> Path:
    raw = str(path or "").strip()
    if not raw:
        raise ValueError("Export path is required.")
    fmt = normalize_export_format(export_format)
    target = Path(raw).expanduser()
    expected_suffix = f".{fmt}"
    if target.suffix.lower() != expected_suffix:
        target = target.with_suffix(expected_suffix)
    return target


def _render_tabular_bytes(dataframe: pd.DataFrame, request: ExportCenterRequest) -> bytes:
    fmt = normalize_export_format(request.export_format)
    if fmt == "csv":
        return export_csv_bytes(dataframe)
    if fmt == "xlsx":
        return export_xlsx_bytes(dataframe)
    return export_las_bytes(
        dataframe,
        well_name=request.well_name,
        depth_column=request.depth_column,
        null_value=request.null_value,
        curve_units=request.curve_units,
        well_metadata=request.well_metadata,
    )


def _manifest_from_bytes(
    payload: bytes,
    request: ExportCenterRequest,
    dataframe: pd.DataFrame | None,
    validation_findings: Iterable[LasValidationFinding],
) -> LasSafeExportManifest:
    target = normalize_export_path(request.target_path, request.export_format)
    pseudo_text = payload.decode("utf-8", errors="replace") if normalize_export_format(request.export_format) != "xlsx" else ""
    manifest = build_las_export_manifest(
        pseudo_text,
        target,
        source_path=request.source_path,
        allow_overwrite=request.allow_overwrite,
        dataframe=dataframe,
        validation_findings=validation_findings,
    )
    return LasSafeExportManifest(
        schema=manifest.schema,
        status=manifest.status,
        created_at=manifest.created_at,
        target_path=manifest.target_path,
        source_path=manifest.source_path,
        bytes_count=len(payload),
        line_count=manifest.line_count,
        curve_count=manifest.curve_count,
        row_count=manifest.row_count,
        overwrite_allowed=manifest.overwrite_allowed,
        issues=manifest.issues,
        validation_summary=manifest.validation_summary,
    )


def build_export_center_preview(
    dataframe: pd.DataFrame,
    request: ExportCenterRequest,
    *,
    las_text: str | None = None,
    validation_findings: Iterable[LasValidationFinding] = (),
) -> ExportCenterResult:
    """Build a no-write Export Center preview for UI confirmation."""

    fmt = normalize_export_format(request.export_format)
    target = normalize_export_path(request.target_path, fmt)
    if fmt == "las" and las_text is not None:
        manifest = build_las_export_manifest(
            las_text,
            target,
            source_path=request.source_path,
            allow_overwrite=request.allow_overwrite,
            dataframe=dataframe,
            validation_findings=validation_findings,
        )
        bytes_count = manifest.bytes_count
    else:
        payload = _render_tabular_bytes(dataframe, request)
        manifest = _manifest_from_bytes(payload, request, dataframe, validation_findings)
        bytes_count = len(payload)

    status = "ready" if manifest.is_ready else "blocked"
    rows = tuple(export_manifest_table(manifest)) + tuple(export_issue_table_rows(manifest.issues))
    return ExportCenterResult(
        schema=LAS_EXPORT_CENTER_SCHEMA,
        status=status,
        export_format=fmt,
        target_path=str(target),
        manifest=manifest,
        issues=manifest.issues,
        table_rows=rows,
        markdown_report=render_export_center_report(manifest, export_format=fmt),
        bytes_count=bytes_count,
    )


def export_dataframe_from_center(
    dataframe: pd.DataFrame,
    request: ExportCenterRequest,
    *,
    las_text: str | None = None,
    validation_findings: Iterable[LasValidationFinding] = (),
) -> ExportCenterResult:
    """Validate and export a DataFrame through Export Center.

    LAS exports are delegated to the safe LAS exporter. CSV/XLSX exports reuse
    the same destination safety rules and therefore also block source overwrite.
    """

    preview = build_export_center_preview(dataframe, request, las_text=las_text, validation_findings=validation_findings)
    if not preview.is_ready:
        return preview

    target = Path(preview.target_path)
    if request.create_parent:
        target.parent.mkdir(parents=True, exist_ok=True)

    fmt = normalize_export_format(request.export_format)
    if fmt == "las" and las_text is not None:
        manifest = export_las_text_safely(
            las_text,
            target,
            source_path=request.source_path,
            allow_overwrite=request.allow_overwrite,
            create_parent=request.create_parent,
            dataframe=dataframe,
            validation_findings=validation_findings,
        )
        bytes_count = manifest.bytes_count
    else:
        payload = _render_tabular_bytes(dataframe, request)
        target.write_bytes(payload)
        manifest = _manifest_from_bytes(payload, request, dataframe, validation_findings)
        bytes_count = len(payload)

    return ExportCenterResult(
        schema=LAS_EXPORT_CENTER_SCHEMA,
        status="exported" if manifest.is_ready else "blocked",
        export_format=fmt,
        target_path=str(target),
        manifest=manifest,
        issues=manifest.issues,
        table_rows=tuple(export_manifest_table(manifest)) + tuple(export_issue_table_rows(manifest.issues)),
        markdown_report=render_export_center_report(manifest, export_format=fmt),
        bytes_count=bytes_count,
    )


def export_las_spec_from_center(
    spec: LasCreationSpec,
    request: ExportCenterRequest,
    *,
    dataframe: pd.DataFrame | None = None,
) -> ExportCenterResult:
    """Export a LAS creation spec through Export Center."""

    fmt = normalize_export_format(request.export_format)
    if fmt == "las":
        target = normalize_export_path(request.target_path, fmt)
        manifest = export_las_document_safely(
            spec,
            target,
            dataframe=dataframe,
            source_path=request.source_path,
            allow_overwrite=request.allow_overwrite,
            create_parent=request.create_parent,
        )
        return ExportCenterResult(
            schema=LAS_EXPORT_CENTER_SCHEMA,
            status="exported" if manifest.is_ready else "blocked",
            export_format=fmt,
            target_path=manifest.target_path,
            manifest=manifest,
            issues=manifest.issues,
            table_rows=tuple(export_manifest_table(manifest)) + tuple(export_issue_table_rows(manifest.issues)),
            markdown_report=render_export_center_report(manifest, export_format=fmt),
            bytes_count=manifest.bytes_count,
        )

    df = dataframe.copy() if dataframe is not None else pd.DataFrame()
    return export_dataframe_from_center(df, request, las_text=build_las_text(spec, df) if not df.empty else None)


def render_export_center_report(manifest: LasSafeExportManifest, *, export_format: str) -> str:
    lines = [
        "# LAS Export Center",
        "",
        f"Status: {manifest.status}",
        f"Format: {normalize_export_format(export_format).upper()}",
        f"Target: {manifest.target_path}",
        f"Rows: {manifest.row_count}",
        f"Curves: {manifest.curve_count}",
        f"Bytes: {manifest.bytes_count}",
        "",
        "## Issues",
    ]
    if not manifest.issues:
        lines.append("No export blocking issues.")
    for issue in manifest.issues:
        lines.append(f"- [{issue.severity.upper()}] {issue.code}: {issue.message}")
        if issue.recommendation:
            lines.append(f"  Recommendation: {issue.recommendation}")
    return "\n".join(lines)


class LASExportCenter:
    """Backend service for A.10 Export Center."""

    def preview(
        self,
        dataframe: pd.DataFrame,
        request: ExportCenterRequest,
        *,
        las_text: str | None = None,
        validation_findings: Iterable[LasValidationFinding] = (),
    ) -> ExportCenterResult:
        return build_export_center_preview(dataframe, request, las_text=las_text, validation_findings=validation_findings)

    def export_dataframe(
        self,
        dataframe: pd.DataFrame,
        request: ExportCenterRequest,
        *,
        las_text: str | None = None,
        validation_findings: Iterable[LasValidationFinding] = (),
    ) -> ExportCenterResult:
        return export_dataframe_from_center(dataframe, request, las_text=las_text, validation_findings=validation_findings)

    def export_las_spec(
        self,
        spec: LasCreationSpec,
        request: ExportCenterRequest,
        *,
        dataframe: pd.DataFrame | None = None,
    ) -> ExportCenterResult:
        return export_las_spec_from_center(spec, request, dataframe=dataframe)

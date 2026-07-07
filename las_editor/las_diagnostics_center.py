"""LAS Diagnostics Center for Roadmap v4 Phase A.8.

The diagnostics center is a read-only orchestration layer. It aggregates
validator, quality-control and depth-order findings into one normalized report
for UI tables, exports and the operation journal. It never mutates the source
LAS working table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from las_editor.depth_repair import analyze_depth_order
from las_editor.header_editor import LasHeaderCard
from las_editor.las_quality_control import CurveQualityProfile, run_las_quality_control
from las_editor.las_validator import validate_las_workspace
from las_editor.las_creator import DEFAULT_NULL_VALUE

LAS_DIAGNOSTICS_CENTER_SCHEMA = "gas-ratio-pro/las-diagnostics-center/v1"
LAS_DIAGNOSTICS_CENTER_STORAGE_KEY = "las_diagnostics_center"


@dataclass(frozen=True)
class LasDiagnosticFinding:
    """One normalized finding shown by Diagnostics Center."""

    severity: str
    code: str
    message: str
    source: str
    section: str = ""
    curve: str = ""
    row: int | None = None
    recommendation: str = ""
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class LasDiagnosticsReport:
    """Aggregated read-only diagnostics report for a LAS workspace."""

    schema: str
    generated_at: str
    status: str
    findings: tuple[LasDiagnosticFinding, ...]
    summary: Mapping[str, Any]
    diagnostics: tuple[str, ...]
    manifest: Mapping[str, Any]

    @property
    def error_count(self) -> int:
        return int(self.summary.get("errors", 0))

    @property
    def warning_count(self) -> int:
        return int(self.summary.get("warnings", 0))

    @property
    def info_count(self) -> int:
        return int(self.summary.get("info", 0))

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _summary(findings: Sequence[LasDiagnosticFinding], *, row_count: int, curve_count: int, sources: Sequence[str]) -> dict[str, Any]:
    by_severity: dict[str, int] = {}
    by_source: dict[str, int] = {}
    by_code: dict[str, int] = {}
    for item in findings:
        by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
        by_source[item.source] = by_source.get(item.source, 0) + 1
        by_code[item.code] = by_code.get(item.code, 0) + 1

    errors = by_severity.get("error", 0)
    warnings = by_severity.get("warning", 0)
    return {
        "status": "failed" if errors else ("warning" if warnings else "passed"),
        "errors": errors,
        "warnings": warnings,
        "info": by_severity.get("info", 0),
        "finding_count": len(findings),
        "row_count": int(row_count),
        "curve_count": int(curve_count),
        "sources": list(sources),
        "by_severity": by_severity,
        "by_source": by_source,
        "by_code": by_code,
    }


def _manifest(report: LasDiagnosticsReport | None, findings: Sequence[LasDiagnosticFinding], summary: Mapping[str, Any], diagnostics: Sequence[str]) -> dict[str, Any]:
    return {
        "schema": LAS_DIAGNOSTICS_CENTER_SCHEMA,
        "generated_at": _timestamp_utc() if report is None else report.generated_at,
        "status": summary.get("status", "passed"),
        "summary": dict(summary),
        "diagnostics": list(diagnostics),
        "findings": [
            {
                "severity": item.severity,
                "code": item.code,
                "message": item.message,
                "source": item.source,
                "section": item.section,
                "curve": item.curve,
                "row": item.row,
                "recommendation": item.recommendation,
                "details": dict(item.details or {}),
            }
            for item in findings
        ],
    }


def run_las_diagnostics_center(
    ascii_data: pd.DataFrame,
    *,
    cards: Iterable[LasHeaderCard | Mapping[str, Any]] | None = None,
    sections: Iterable[str] | None = None,
    las_text: str | None = None,
    depth_curve: str | None = None,
    expected_step: float | None = None,
    null_value: float = DEFAULT_NULL_VALUE,
    profiles: Iterable[CurveQualityProfile] | None = None,
    units: Mapping[str, str] | None = None,
    include_validation: bool = True,
    include_quality_control: bool = True,
    include_depth_order: bool = True,
) -> LasDiagnosticsReport:
    """Run all enabled LAS diagnostics in read-only mode.

    The input DataFrame is never modified. Callers can safely run this before
    repair/export and then decide whether to open Depth Repair, Validator or
    ASCII Spreadsheet for manual correction.
    """

    source_df = ascii_data.copy(deep=True)
    findings: list[LasDiagnosticFinding] = []
    sources: list[str] = []

    if include_validation and cards is not None:
        sources.append("validator")
        validation = validate_las_workspace(
            cards=cards,
            ascii_data=source_df,
            sections=sections,
            las_text=las_text,
            null_value=null_value,
        )
        for item in validation.findings:
            findings.append(
                LasDiagnosticFinding(
                    item.severity,
                    item.code,
                    item.message,
                    "validator",
                    section=item.section,
                    curve=item.mnemonic or item.column,
                    row=item.row,
                    recommendation=item.recommendation,
                )
            )

    if include_quality_control:
        sources.append("quality_control")
        quality = run_las_quality_control(
            source_df,
            depth_curve=depth_curve,
            expected_step=expected_step,
            null_value=null_value,
            profiles=profiles,
            units=units,
        )
        for item in quality.issues:
            findings.append(
                LasDiagnosticFinding(
                    item.severity,
                    item.code,
                    item.message,
                    "quality_control",
                    curve=item.curve,
                    row=item.row,
                    details=item.details,
                )
            )

    if include_depth_order:
        sources.append("depth_repair")
        depth_plan = analyze_depth_order(source_df, depth_curve=depth_curve)
        for item in depth_plan.issues:
            recommendation = "Open Depth Repair Center and repair row order on a working copy." if item.code == "DEPTH_DECREASES" else "Review depth values before automatic repair."
            findings.append(
                LasDiagnosticFinding(
                    item.severity,
                    item.code,
                    item.message,
                    "depth_repair",
                    curve=item.depth_curve,
                    row=item.row_index,
                    recommendation=recommendation,
                    details=item.details,
                )
            )

    generated_at = _timestamp_utc()
    summary = _summary(findings, row_count=len(source_df), curve_count=len(source_df.columns), sources=tuple(sources))
    diagnostics = (
        "LAS Diagnostics Center completed in read-only mode.",
        "Source LAS/DataFrame was copied before diagnostics and was not mutated.",
        "Use specialized workspaces for corrections: Validator, Data Cleanup, Depth Repair or Export Center.",
    )
    manifest = {
        "schema": LAS_DIAGNOSTICS_CENTER_SCHEMA,
        "generated_at": generated_at,
        "status": summary["status"],
        "summary": dict(summary),
        "diagnostics": list(diagnostics),
        "findings": [
            {
                "severity": item.severity,
                "code": item.code,
                "message": item.message,
                "source": item.source,
                "section": item.section,
                "curve": item.curve,
                "row": item.row,
                "recommendation": item.recommendation,
                "details": dict(item.details or {}),
            }
            for item in findings
        ],
    }
    return LasDiagnosticsReport(
        schema=LAS_DIAGNOSTICS_CENTER_SCHEMA,
        generated_at=generated_at,
        status=str(summary["status"]),
        findings=tuple(findings),
        summary=summary,
        diagnostics=diagnostics,
        manifest=manifest,
    )


def diagnostics_finding_table_rows(findings: Iterable[LasDiagnosticFinding]) -> tuple[dict[str, Any], ...]:
    """Convert diagnostics findings to Streamlit/export-ready rows."""

    return tuple(
        {
            "severity": item.severity,
            "source": item.source,
            "code": item.code,
            "section": item.section,
            "curve": item.curve,
            "row": item.row,
            "message": item.message,
            "recommendation": item.recommendation,
            "details": dict(item.details or {}),
        }
        for item in findings
    )


def render_diagnostics_report(report: LasDiagnosticsReport) -> str:
    """Render a compact Markdown report for Diagnostics Center."""

    lines = [
        "# LAS Diagnostics Center Report",
        "",
        f"Status: {report.status}",
        f"Generated at: {report.generated_at}",
        f"Rows: {report.summary.get('row_count', 0)}",
        f"Curves: {report.summary.get('curve_count', 0)}",
        f"Errors: {report.error_count}",
        f"Warnings: {report.warning_count}",
        f"Info: {report.info_count}",
        "",
        "## Diagnostics",
        "",
    ]
    lines.extend(f"- {item}" for item in report.diagnostics)
    lines.extend(["", "## Findings", ""])
    if not report.findings:
        lines.append("No diagnostics findings.")
    for index, item in enumerate(report.findings, start=1):
        location = ", ".join(part for part in (item.section, item.curve, f"row={item.row}" if item.row is not None else "") if part)
        lines.append(f"{index}. [{item.severity.upper()}] {item.source}.{item.code}: {item.message}" + (f" ({location})" if location else ""))
        if item.recommendation:
            lines.append(f"   Recommendation: {item.recommendation}")
    return "\n".join(lines).strip() + "\n"

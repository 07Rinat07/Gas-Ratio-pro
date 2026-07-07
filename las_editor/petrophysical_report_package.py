from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

PETROPHYSICAL_REPORT_PACKAGE_SCHEMA = "gas-ratio-pro/petrophysical-report-package/v1"
PETROPHYSICAL_REPORT_PACKAGE_STORAGE_KEY = "petrophysical_report_package"


@dataclass(frozen=True)
class ReportPackageIssue:
    """One issue detected while assembling a petrophysical report package."""

    severity: str
    code: str
    message: str
    section: str = ""
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ReportPackageSection:
    """Normalized report section ready for Report Studio or Markdown export."""

    section_id: str
    title: str
    status: str
    summary: str
    row_count: int = 0
    metrics: Mapping[str, Any] | None = None
    table_rows: tuple[Mapping[str, Any], ...] = ()
    source_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class PetrophysicalReportPackage:
    """Complete evidence-backed petrophysical report package."""

    schema: str
    generated_at: str
    well_name: str
    package_title: str
    sections: tuple[ReportPackageSection, ...]
    issues: tuple[ReportPackageIssue, ...] = ()
    source_references: tuple[str, ...] = ()
    manifest: Mapping[str, Any] | None = None


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _round_value(value: Any, digits: int = 6) -> Any:
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, dict):
        return {key: _round_value(item, digits) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round_value(item, digits) for item in value]
    return value


def _collect_source_references(*objects: Any, extra: Sequence[str] | None = None) -> tuple[str, ...]:
    refs: list[str] = []
    for obj in objects:
        for ref in getattr(obj, "source_references", ()) or ():
            ref_text = str(ref)
            if ref_text and ref_text not in refs:
                refs.append(ref_text)
    for ref in extra or ():
        ref_text = str(ref)
        if ref_text and ref_text not in refs:
            refs.append(ref_text)
    return tuple(refs)


def _issue_rows(issues: Sequence[Any]) -> tuple[Mapping[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for issue in issues:
        if hasattr(issue, "__dataclass_fields__"):
            rows.append({key: _round_value(value) for key, value in asdict(issue).items()})
        elif isinstance(issue, Mapping):
            rows.append({str(key): _round_value(value) for key, value in issue.items()})
        else:
            rows.append({"message": str(issue)})
    return tuple(rows)


def _metric_from_intervals(intervals: Sequence[Any], field: str) -> float:
    total = 0.0
    for interval in intervals:
        value = getattr(interval, field, 0.0)
        try:
            total += float(value or 0.0)
        except (TypeError, ValueError):
            continue
    return total


def _average_from_intervals(intervals: Sequence[Any], field: str) -> float | None:
    values: list[float] = []
    for interval in intervals:
        value = getattr(interval, field, None)
        try:
            if value is not None:
                values.append(float(value))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return sum(values) / len(values)


def build_petrophysical_section(result: Any | None) -> ReportPackageSection:
    """Build section from Petrophysical Workspace result."""

    if result is None:
        return ReportPackageSection("petrophysics", "Петрофизические расчеты", "missing", "Петрофизические расчеты не переданы.")
    intervals = tuple(getattr(result, "intervals", ()) or ())
    issues = tuple(getattr(result, "issues", ()) or ())
    metrics = {
        "interval_count": len(intervals),
        "avg_vsh": _average_from_intervals(intervals, "average_vsh"),
        "avg_phie": _average_from_intervals(intervals, "average_phie"),
        "avg_sw": _average_from_intervals(intervals, "average_sw"),
        "errors": sum(1 for issue in issues if getattr(issue, "severity", "") == "error"),
        "warnings": sum(1 for issue in issues if getattr(issue, "severity", "") == "warning"),
    }
    status = "ok" if metrics["errors"] == 0 else "attention"
    summary = f"Интервалов: {len(intervals)}; ошибок: {metrics['errors']}; предупреждений: {metrics['warnings']}."
    rows = tuple(asdict(item) if hasattr(item, "__dataclass_fields__") else dict(item) for item in intervals)
    return ReportPackageSection("petrophysics", "Петрофизические расчеты", status, summary, len(rows), _round_value(metrics), rows, tuple(getattr(result, "source_references", ()) or ()))


def build_saturation_section(result: Any | None) -> ReportPackageSection:
    """Build section from Advanced Saturation Models result."""

    if result is None:
        return ReportPackageSection("saturation_models", "Модели насыщенности", "missing", "Результаты моделей насыщенности не переданы.")
    comparisons = tuple(getattr(result, "comparisons", ()) or ())
    issues = tuple(getattr(result, "issues", ()) or ())
    metrics = {
        "comparison_count": len(comparisons),
        "avg_model_spread": _average_from_intervals(comparisons, "model_spread"),
        "errors": sum(1 for issue in issues if getattr(issue, "severity", "") == "error"),
        "warnings": sum(1 for issue in issues if getattr(issue, "severity", "") == "warning"),
    }
    status = "ok" if metrics["errors"] == 0 else "attention"
    summary = f"Сравнений моделей: {len(comparisons)}; среднее расхождение моделей: {metrics['avg_model_spread']}."
    rows = tuple(asdict(item) if hasattr(item, "__dataclass_fields__") else dict(item) for item in comparisons)
    return ReportPackageSection("saturation_models", "Модели насыщенности", status, summary, len(rows), _round_value(metrics), rows, tuple(getattr(result, "source_references", ()) or ()))


def build_crossplot_section(result: Any | None) -> ReportPackageSection:
    """Build section from Petrophysical Crossplot Workspace result."""

    if result is None:
        return ReportPackageSection("crossplots", "Петрофизические кроссплоты", "missing", "Кроссплоты не переданы.")
    specs = tuple(getattr(result, "specs", ()) or ())
    clusters = tuple(getattr(result, "clusters", ()) or ())
    trends = tuple(getattr(result, "trends", ()) or ())
    metrics = {"plot_count": len(specs), "cluster_count": len(clusters), "trend_count": len(trends)}
    summary = f"Графиков: {len(specs)}; кластеров: {len(clusters)}; трендов: {len(trends)}."
    rows = tuple(asdict(item) if hasattr(item, "__dataclass_fields__") else dict(item) for item in specs)
    return ReportPackageSection("crossplots", "Петрофизические кроссплоты", "ok", summary, len(rows), metrics, rows, tuple(getattr(result, "source_references", ()) or ()))


def build_intervals_section(result: Any | None) -> ReportPackageSection:
    """Build section from Well Interval Manager result."""

    if result is None:
        return ReportPackageSection("intervals", "Интервалы и pay-зоны", "missing", "Интервалы не переданы.")
    intervals = tuple(getattr(result, "intervals", ()) or ())
    metrics = {
        "interval_count": len(intervals),
        "gross_thickness": _metric_from_intervals(intervals, "gross_thickness"),
        "net_thickness": _metric_from_intervals(intervals, "net_thickness"),
        "pay_thickness": _metric_from_intervals(intervals, "pay_thickness"),
    }
    summary = f"Интервалов: {len(intervals)}; pay thickness: {round(metrics['pay_thickness'], 4)}."
    rows = tuple(asdict(item) if hasattr(item, "__dataclass_fields__") else dict(item) for item in intervals)
    return ReportPackageSection("intervals", "Интервалы и pay-зоны", "ok", summary, len(rows), _round_value(metrics), rows, tuple(getattr(result, "source_references", ()) or ()))


def build_volumes_section(result: Any | None) -> ReportPackageSection:
    """Build section from Reservoir Property Calculator result."""

    if result is None:
        return ReportPackageSection("reservoir_volumes", "Объемные показатели коллектора", "missing", "Объемные расчеты не переданы.")
    intervals = tuple(getattr(result, "intervals", ()) or ())
    issues = tuple(getattr(result, "issues", ()) or ())
    metrics = {
        "interval_count": len(intervals),
        "total_brv_m3": _metric_from_intervals(intervals, "bulk_rock_volume_m3"),
        "total_pv_m3": _metric_from_intervals(intervals, "pore_volume_m3"),
        "total_hcpv_m3": _metric_from_intervals(intervals, "hydrocarbon_pore_volume_m3"),
        "total_ooip_sm3": _metric_from_intervals(intervals, "ooip_sm3"),
        "total_ogip_sm3": _metric_from_intervals(intervals, "ogip_sm3"),
        "errors": sum(1 for issue in issues if getattr(issue, "severity", "") == "error"),
    }
    status = "ok" if metrics["errors"] == 0 else "attention"
    summary = f"HCPV: {round(metrics['total_hcpv_m3'], 4)} м3; OOIP: {round(metrics['total_ooip_sm3'], 4)}; OGIP: {round(metrics['total_ogip_sm3'], 4)}."
    rows = tuple(asdict(item) if hasattr(item, "__dataclass_fields__") else dict(item) for item in intervals)
    return ReportPackageSection("reservoir_volumes", "Объемные показатели коллектора", status, summary, len(rows), _round_value(metrics), rows, tuple(getattr(result, "source_references", ()) or ()))


def validate_report_package(sections: Sequence[ReportPackageSection]) -> tuple[ReportPackageIssue, ...]:
    """Validate a package before handing it to Report Studio."""

    issues: list[ReportPackageIssue] = []
    seen: set[str] = set()
    for section in sections:
        if section.section_id in seen:
            issues.append(ReportPackageIssue("error", "duplicate_section", f"Duplicate report section `{section.section_id}`.", section.section_id))
        seen.add(section.section_id)
        if section.status == "missing":
            issues.append(ReportPackageIssue("warning", "missing_section_data", f"Section `{section.title}` has no source data.", section.section_id))
        if section.status == "attention":
            issues.append(ReportPackageIssue("warning", "section_requires_attention", f"Section `{section.title}` contains warnings or errors.", section.section_id))
    return tuple(issues)


def build_petrophysical_report_package(
    *,
    well_name: str = "Unknown well",
    package_title: str = "Petrophysical Interpretation Report Package",
    petrophysical_result: Any | None = None,
    saturation_result: Any | None = None,
    crossplot_result: Any | None = None,
    interval_result: Any | None = None,
    reservoir_property_result: Any | None = None,
    source_references: Sequence[str] | None = None,
) -> PetrophysicalReportPackage:
    """Assemble a normalized package from LAS Platform interpretation outputs."""

    sections = (
        build_petrophysical_section(petrophysical_result),
        build_saturation_section(saturation_result),
        build_crossplot_section(crossplot_result),
        build_intervals_section(interval_result),
        build_volumes_section(reservoir_property_result),
    )
    refs = _collect_source_references(petrophysical_result, saturation_result, crossplot_result, interval_result, reservoir_property_result, extra=source_references)
    issues = validate_report_package(sections)
    package = PetrophysicalReportPackage(
        schema=PETROPHYSICAL_REPORT_PACKAGE_SCHEMA,
        generated_at=_timestamp_utc(),
        well_name=well_name,
        package_title=package_title,
        sections=sections,
        issues=issues,
        source_references=refs,
        manifest={},
    )
    manifest = build_petrophysical_report_manifest(package)
    return PetrophysicalReportPackage(package.schema, package.generated_at, package.well_name, package.package_title, package.sections, package.issues, package.source_references, manifest)


def report_section_table_rows(sections: Sequence[ReportPackageSection]) -> list[dict[str, Any]]:
    """Convert report sections to UI-ready table rows."""

    rows: list[dict[str, Any]] = []
    for section in sections:
        rows.append(
            {
                "section_id": section.section_id,
                "title": section.title,
                "status": section.status,
                "summary": section.summary,
                "row_count": section.row_count,
                "source_count": len(section.source_references),
            }
        )
    return rows


def report_issue_table_rows(issues: Sequence[ReportPackageIssue]) -> list[dict[str, Any]]:
    """Convert package issues to UI-ready rows."""

    return [{key: _round_value(value) for key, value in asdict(issue).items()} for issue in issues]


def build_petrophysical_report_manifest(package: PetrophysicalReportPackage) -> dict[str, Any]:
    """Build deterministic manifest for report reproducibility."""

    return {
        "schema": package.schema,
        "generated_at": package.generated_at,
        "well_name": package.well_name,
        "package_title": package.package_title,
        "section_count": len(package.sections),
        "sections": [
            {
                "section_id": section.section_id,
                "title": section.title,
                "status": section.status,
                "row_count": section.row_count,
                "metrics": _round_value(dict(section.metrics or {})),
                "source_references": list(section.source_references),
            }
            for section in package.sections
        ],
        "issue_count": len(package.issues),
        "issues": [asdict(issue) for issue in package.issues],
        "source_references": list(package.source_references),
    }


def render_petrophysical_report_markdown(package: PetrophysicalReportPackage) -> str:
    """Render a compact engineer-readable Markdown report package."""

    lines = [
        "# Petrophysical Report Package",
        "",
        f"Well: **{package.well_name}**",
        f"Package: **{package.package_title}**",
        f"Generated at: `{package.generated_at}`",
        "",
        "## Sections",
        "",
    ]
    for section in package.sections:
        lines.extend(
            [
                f"### {section.title}",
                "",
                f"Status: `{section.status}`",
                f"Summary: {section.summary}",
                f"Rows: {section.row_count}",
            ]
        )
        if section.metrics:
            lines.append("Metrics:")
            for key, value in section.metrics.items():
                lines.append(f"- {key}: {_round_value(value)}")
        if section.source_references:
            lines.append("Sources:")
            for ref in section.source_references:
                lines.append(f"- {ref}")
        lines.append("")

    if package.issues:
        lines.extend(["## Package Issues", ""])
        for issue in package.issues:
            lines.append(f"- **{issue.severity}** `{issue.code}` ({issue.section}): {issue.message}")
        lines.append("")

    if package.source_references:
        lines.extend(["## Evidence Sources", ""])
        for ref in package.source_references:
            lines.append(f"- {ref}")
    return "\n".join(lines).rstrip() + "\n"

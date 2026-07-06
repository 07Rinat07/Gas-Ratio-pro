from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from projects.report_studio import (
    REPORT_EXPORT_FORMATS,
    ReportSection,
    build_report_export_jobs_table,
    build_report_export_manifest,
    build_report_output_prefix,
    build_report_sections_table,
    build_report_template_table,
    create_report_export_job,
    create_report_template,
    list_report_export_jobs,
    list_report_templates,
    normalize_report_formats,
    normalize_report_sections,
    summarize_report_studio,
)


def test_create_report_template_and_tables(tmp_path: Path) -> None:
    template = create_report_template(
        tmp_path,
        "demo_project",
        "Monthly engineering report",
        orientation="landscape",
        formats=["pdf", "html", "xlsx"],
        sections=[
            ReportSection(id="summary", title="Summary", section_type="summary", order=20),
            {"id": "plots", "title": "Plots", "section_type": "plot", "order": 10},
        ],
    )

    templates = list_report_templates(tmp_path, "demo_project")
    assert len(templates) == 1
    assert templates[0].id == template.id
    assert templates[0].sections[0].id == "plots"

    table = build_report_template_table(templates)
    assert isinstance(table, pd.DataFrame)
    assert table.loc[0, "Форматы"] == "pdf, html, xlsx"

    sections_table = build_report_sections_table(template.sections)
    assert list(sections_table["ID"]) == ["plots", "summary"]


def test_report_export_job_and_manifest(tmp_path: Path) -> None:
    template = create_report_template(tmp_path, "p1", "Reservoir summary", formats=["pdf", "html"])
    job = create_report_export_job(tmp_path, "p1", "Reservoir summary export", template.id, well_id="Well A", formats=["pdf", "docx"])

    jobs = list_report_export_jobs(tmp_path, "p1")
    assert len(jobs) == 1
    assert jobs[0].template_id == template.id
    assert jobs[0].output_prefix.startswith("well-a_")

    manifest = build_report_export_manifest(template, job)
    assert manifest["page"] == {"size": "A4", "orientation": "portrait"}
    assert manifest["formats"] == ["pdf", "docx"]
    assert manifest["outputs"] == [f"{job.output_prefix}.pdf", f"{job.output_prefix}.docx"]
    assert len(manifest["sections"]) >= 1

    jobs_table = build_report_export_jobs_table(jobs)
    assert jobs_table.loc[0, "Статус"] == "queued"


def test_validation_and_summary(tmp_path: Path) -> None:
    assert "pdf" in REPORT_EXPORT_FORMATS
    assert normalize_report_formats(["pdf", "pdf", "html"]) == ("pdf", "html")
    with pytest.raises(ValueError):
        normalize_report_formats(["exe"])
    with pytest.raises(ValueError):
        normalize_report_sections([{"title": "Bad", "section_type": "unknown"}])

    template = create_report_template(tmp_path, "p2", "Daily report")
    create_report_export_job(tmp_path, "p2", "Daily export", template.id, formats=["html"])
    summary = summarize_report_studio(tmp_path, "p2")
    assert summary.templates == 1
    assert summary.export_jobs == 1
    assert summary.sections == len(template.sections)

    prefix = build_report_output_prefix("My Report", well_id="Well 42")
    assert prefix.startswith("well-42_my-report_")

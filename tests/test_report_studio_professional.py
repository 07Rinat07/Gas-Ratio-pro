from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from projects.report_studio import (
    REPORT_CONTENT_BLOCK_TYPES,
    REPORT_JOB_STATUSES,
    ReportContentBlock,
    build_report_blocks_table,
    build_report_package_table,
    build_report_render_manifest,
    build_report_render_preview,
    build_report_validation_table,
    create_report_export_job,
    create_report_package,
    create_report_template,
    list_report_packages,
    normalize_report_blocks,
    render_report_html,
    update_report_export_job_status,
    validate_report_package,
)


def test_report_package_blocks_preview_and_html(tmp_path: Path) -> None:
    template = create_report_template(
        tmp_path,
        "demo_project",
        "Professional report",
        sections=[
            {"id": "summary", "title": "Summary", "section_type": "summary", "order": 10},
            {"id": "plots", "title": "Plots", "section_type": "plot", "order": 20},
        ],
    )
    package = create_report_package(
        tmp_path,
        "demo_project",
        "Daily professional package",
        template.id,
        well_id="Well A",
        blocks=[
            ReportContentBlock(id="intro", section_id="summary", title="Intro", content="Engineering summary", order=10),
            {"id": "plot-1", "section_id": "plots", "block_type": "plot", "title": "Gas ratio plot", "source_id": "plot-template-1", "order": 20},
        ],
        variables={"author": "Engineer"},
    )

    assert len(list_report_packages(tmp_path, "demo_project")) == 1
    assert package.blocks[0].id == "intro"
    assert validate_report_package(template, package) == ()

    preview = build_report_render_preview(template, package)
    assert preview.sections == 2
    assert preview.blocks == 2
    assert preview.estimated_pages >= 1
    assert preview.table_of_contents[0]["section_id"] == "summary"

    html = render_report_html(template, package)
    assert "Daily professional package" in html
    assert "Engineering summary" in html
    assert "Gas ratio plot" in html


def test_report_package_validation_and_tables(tmp_path: Path) -> None:
    template = create_report_template(tmp_path, "p1", "Validation template")
    package = create_report_package(
        tmp_path,
        "p1",
        "Invalid package",
        template.id,
        blocks=[
            {"id": "bad", "section_id": "missing", "block_type": "table", "title": "No source"},
            {"id": "empty", "section_id": "summary", "block_type": "paragraph", "title": "Empty"},
        ],
    )

    issues = validate_report_package(template, package)
    codes = {issue.code for issue in issues}
    assert "unknown_section" in codes
    assert "missing_source" in codes
    assert "empty_paragraph" in codes

    issues_table = build_report_validation_table(issues)
    assert isinstance(issues_table, pd.DataFrame)
    assert set(issues_table["Код"]) == codes

    packages_table = build_report_package_table([package])
    assert packages_table.loc[0, "Блоков"] == 2

    blocks_table = build_report_blocks_table(package.blocks)
    assert list(blocks_table["ID"]) == ["bad", "empty"]


def test_render_manifest_and_job_status(tmp_path: Path) -> None:
    template = create_report_template(tmp_path, "p2", "Export template", formats=["pdf", "html"])
    package = create_report_package(
        tmp_path,
        "p2",
        "Export package",
        template.id,
        blocks=[{"id": "summary", "section_id": "summary", "content": "Ready"}],
    )
    job = create_report_export_job(tmp_path, "p2", "Export job", template.id, formats=["pdf"])
    manifest = build_report_render_manifest(template, package, job)

    assert manifest["package_id"] == package.id
    assert manifest["formats"] == ["pdf"]
    assert manifest["validation"] == []
    assert manifest["preview"]["blocks"] == 1

    completed = update_report_export_job_status(tmp_path, "p2", job.id, "completed")
    assert completed.status == "completed"
    with pytest.raises(ValueError):
        update_report_export_job_status(tmp_path, "p2", job.id, "unknown")


def test_normalize_report_blocks_validation() -> None:
    assert "paragraph" in REPORT_CONTENT_BLOCK_TYPES
    assert "completed" in REPORT_JOB_STATUSES
    blocks = normalize_report_blocks([
        {"id": "b2", "section_id": "summary", "content": "Second", "order": 20},
        {"id": "b1", "section_id": "summary", "content": "First", "order": 10},
    ])
    assert [block.id for block in blocks] == ["b1", "b2"]
    with pytest.raises(ValueError):
        normalize_report_blocks([{"id": "bad", "section_id": "summary", "block_type": "video"}])

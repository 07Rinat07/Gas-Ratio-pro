from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest

from reports.report_designer import ReportDesign
from reports.report_designer_export import build_designed_report_artifact


class _Metadata:
    title = "Source title"
    subtitle = "Source subtitle"
    source_label = "Well-A"
    project_label = "Project-A"
    depth_label = "1000-1100 m"
    report_profile = "engineering"

    def as_report_rows(self):
        return (("Проект", self.project_label), ("Источник", self.source_label))


class _Model:
    metadata = _Metadata()
    figures = ()
    visualization_previews = ()
    engineer_first_tables = ()
    expert_tables = ()


def test_designed_pdf_uses_requested_name_and_real_pdf_bytes():
    artifact = build_designed_report_artifact(
        _Model(),
        design=ReportDesign(template_id="minimal", title="Minimal report"),
        export_format="pdf",
        base_name="Well A / final",
    )
    assert artifact.file_name.endswith(".pdf")
    assert artifact.content.startswith(b"%PDF")
    assert artifact.template_id == "minimal"


def test_designed_bundle_contains_pdf_and_docx_from_same_basename():
    artifact = build_designed_report_artifact(
        _Model(),
        design=ReportDesign(template_id="engineering"),
        export_format="bundle",
        base_name="Well-A-report",
    )
    with ZipFile(BytesIO(artifact.content)) as archive:
        names = sorted(archive.namelist())
    assert names == ["Well-A-report.docx", "Well-A-report.pdf"]


def test_designer_export_rejects_visualization_channel():
    with pytest.raises(ValueError, match="not supported by Report Designer"):
        build_designed_report_artifact(
            _Model(),
            design=ReportDesign(),
            export_format="png",
            base_name="report",
        )

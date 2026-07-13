from __future__ import annotations

import pytest

from reports.report_designer import ReportDesign
from reports.report_designer_export import build_designed_report_artifact


class _Metadata:
    title = "Cancellation test"
    subtitle = ""
    source_label = "well.las"
    project_label = "Project"
    depth_label = "1000-1100 m"
    report_profile = "engineering"

    def as_report_rows(self):
        return (("Проект", self.project_label),)


class _Model:
    metadata = _Metadata()
    figures = ()
    visualization_previews = ()
    engineer_first_tables = ()
    expert_tables = ()


def test_designed_pdf_reports_monotonic_progress() -> None:
    progress: list[tuple[int, str]] = []
    artifact = build_designed_report_artifact(
        _Model(),
        design=ReportDesign(template_id="minimal", title="Progress report"),
        export_format="pdf",
        base_name="progress-report",
        on_progress=lambda value, message: progress.append((value, message)),
    )

    values = [value for value, _ in progress]
    assert artifact.content.startswith(b"%PDF")
    assert values
    assert values == sorted(values)
    assert values[0] == 5
    assert values[-1] == 98
    assert any("PDF" in message for _, message in progress)


def test_designed_report_honours_cooperative_cancellation() -> None:
    checks = {"count": 0}

    def check_cancelled() -> None:
        checks["count"] += 1
        if checks["count"] >= 4:
            raise RuntimeError("cancelled-for-test")

    with pytest.raises(RuntimeError, match="cancelled-for-test"):
        build_designed_report_artifact(
            _Model(),
            design=ReportDesign(template_id="engineering"),
            export_format="docx",
            base_name="cancelled-report",
            check_cancelled=check_cancelled,
        )

    assert checks["count"] >= 4

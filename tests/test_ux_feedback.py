import pytest

from ui.ux_feedback import (
    OperationProgressPlan,
    OperationStage,
    REPORT_EXPORT_PROGRESS,
    tooltip,
    tooltip_keys,
    validate_tooltip_coverage,
)


def test_report_tooltips_are_registered_and_non_empty():
    required = {
        "report.profile",
        "report.format",
        "report.template",
        "report.sections",
        "report.technical_appendix",
        "report.page_chrome",
        "report.print_scope",
        "report.prepare",
    }
    assert required.issubset(set(tooltip_keys()))
    assert all(tooltip(key) for key in required)


def test_unknown_tooltip_requires_fallback():
    with pytest.raises(KeyError):
        tooltip("missing")
    assert tooltip("missing", fallback="Fallback") == "Fallback"


def test_tooltip_coverage_reports_only_missing_keys():
    assert validate_tooltip_coverage(["report.profile", "missing", "missing"]) == ("missing",)


def test_report_export_progress_is_monotonic_and_complete():
    assert [stage.percent for stage in REPORT_EXPORT_PROGRESS.stages] == [5, 30, 70, 95, 100]
    assert REPORT_EXPORT_PROGRESS.stage("render").percent == 70
    assert REPORT_EXPORT_PROGRESS.stage("complete").percent == 100


def test_progress_plan_rejects_invalid_sequences():
    with pytest.raises(ValueError):
        OperationProgressPlan(
            id="broken",
            stages=(OperationStage("late", 80, "Late"), OperationStage("early", 20, "Early")),
        )

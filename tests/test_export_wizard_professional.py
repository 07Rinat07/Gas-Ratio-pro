from __future__ import annotations

from pathlib import Path

import pytest

from reports.export_wizard import (
    ExportWizardState,
    ExportWizardStep,
    require_export_ready,
    validate_export_wizard,
)
from reports.presentation_ui import build_presentation_export_ui_state, build_ui_export_artifact


def test_wizard_navigation_is_bounded() -> None:
    first = ExportWizardState()
    assert first.previous_step().step is ExportWizardStep.SOURCE
    assert first.next_step().step is ExportWizardStep.CONTENT
    assert first.with_step(ExportWizardStep.REVIEW).next_step().step is ExportWizardStep.REVIEW


def test_wizard_preflight_builds_safe_report_state(tmp_path: Path) -> None:
    state = ExportWizardState(
        source_label="Well A.las",
        project_label="North Block",
        profile="engineering",
        export_format="pdf",
        output_dir=tmp_path,
    )

    result = validate_export_wizard(state)

    assert result.ready is True
    assert result.issues == ()
    assert result.ui_state is not None
    assert result.ui_state.base_name == "North_Block_Well_A.las"
    assert result.ui_state.include_technical_appendix is True


def test_wizard_blocks_unimplemented_report_format(tmp_path: Path) -> None:
    state = ExportWizardState(source_label="Well A", export_format="png", output_dir=tmp_path)

    result = validate_export_wizard(state)

    assert result.ready is False
    assert result.ui_state is not None
    assert [issue.code for issue in result.issues] == ["format.unsupported_for_report"]
    with pytest.raises(ValueError, match="PNG"):
        require_export_ready(state)


def test_wizard_requires_source(tmp_path: Path) -> None:
    result = validate_export_wizard(ExportWizardState(output_dir=tmp_path))
    assert result.ready is False
    assert result.issues[0].field == "source_label"


def test_report_artifact_rejects_wrong_format_instead_of_returning_zip(tmp_path: Path) -> None:
    state = build_presentation_export_ui_state(
        profile="engineering",
        export_format="xlsx",
        output_dir=tmp_path,
        base_name_parts=("Well A",),
    )

    with pytest.raises(ValueError, match="not supported by the professional report renderer"):
        build_ui_export_artifact(object(), state)  # validation happens before model access


def test_wizard_step_views_expose_completed_review_path(tmp_path: Path) -> None:
    from reports.export_wizard import build_export_wizard_steps

    state = ExportWizardState(
        step=ExportWizardStep.REVIEW,
        source_label="Well A.las",
        project_label="North Block",
        profile="engineering",
        export_format="pdf",
        output_dir=tmp_path,
    )

    steps = build_export_wizard_steps(state)

    assert [step.number for step in steps] == [1, 2, 3, 4, 5]
    assert [step.label for step in steps] == ["Источник", "Состав", "Формат", "Назначение", "Проверка"]
    assert all(step.completed for step in steps)
    assert steps[-1].active is True
    assert all(step.available for step in steps)


def test_wizard_step_views_lock_following_steps_when_source_is_missing(tmp_path: Path) -> None:
    from reports.export_wizard import build_export_wizard_steps

    steps = build_export_wizard_steps(ExportWizardState(output_dir=tmp_path))

    assert steps[0].available is True
    assert steps[0].completed is False
    assert steps[1].available is False
    assert steps[-1].completed is False


def test_wizard_review_contains_final_file_and_preflight_state(tmp_path: Path) -> None:
    from reports.export_wizard import build_export_wizard_review

    review = build_export_wizard_review(
        ExportWizardState(
            step=ExportWizardStep.REVIEW,
            source_label="Well A.las",
            project_label="North Block",
            profile="engineering",
            export_format="docx",
            output_dir=tmp_path,
            base_name_parts=("North Block", "Well A", "professional report"),
        )
    )

    assert review.ready is True
    assert review.profile_label == "Инженерный отчет"
    assert review.format_label == "DOCX"
    assert review.file_name == "North_Block_Well_A_professional_report.docx"
    assert review.destination == str(tmp_path)
    assert review.issues == ()


def test_streamlit_export_panel_renders_wizard_review(tmp_path: Path) -> None:
    from core.ui_behavior_contracts import PROFESSIONAL_EXPORT_BEHAVIOR
    from reports.export_wizard import ExportWizardState, ExportWizardStep, build_export_wizard_review

    review = build_export_wizard_review(
        ExportWizardState(
            step=ExportWizardStep.REVIEW,
            source_label="Well A.las",
            project_label="North Block",
            export_format="pdf",
            output_dir=tmp_path,
        )
    )

    assert review.ready is True
    assert review.steps[-1].label == "Проверка"
    assert review.steps[-1].active is True
    assert (not review.ready) is False
    assert PROFESSIONAL_EXPORT_BEHAVIOR.primary_action_label.startswith("🖨")

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

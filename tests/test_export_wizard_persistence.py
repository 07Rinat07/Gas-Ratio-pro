from pathlib import Path
import json

import pytest

from reports.export_wizard import ExportWizardState, ExportWizardStep
from reports.export_wizard_persistence import (
    EXPORT_WIZARD_DRAFT_SCHEMA,
    ExportWizardDraft,
    ExportWizardDraftRepository,
)


def _draft(tmp_path: Path) -> ExportWizardDraft:
    return ExportWizardDraft(
        project_id="project/alpha",
        wizard=ExportWizardState(
            step=ExportWizardStep.CONTENT,
            source_label="Well A.las",
            project_label="North Block",
            profile="engineering",
            export_format="docx",
            output_dir=tmp_path / "exports",
            base_name_parts=("North Block", "Well A"),
        ),
        report_mode_id="standard",
        template_id="corporate",
        report_title="North Block Report",
        sections=("results", "plots", "unknown"),
        include_technical_appendix=False,
        show_page_chrome=True,
        print_mode="Выбрать отдельно",
        depth_top=2200.0,
        depth_bottom=2100.0,
    )


def test_project_scoped_draft_round_trip_is_atomic_and_normalized(tmp_path: Path) -> None:
    repository = ExportWizardDraftRepository(tmp_path / "drafts")
    path = repository.save(_draft(tmp_path))

    assert path.name == "export_wizard_draft.json"
    assert path.parent.name == "project_alpha"
    assert not path.with_suffix(".json.tmp").exists()

    restored = repository.load("project/alpha")
    assert restored is not None
    assert restored.wizard.step is ExportWizardStep.CONTENT
    assert restored.wizard.export_format == "docx"
    assert restored.sections == ("results", "plots")
    assert restored.depth_top == 2100.0
    assert restored.depth_bottom == 2200.0
    assert restored.updated_at


def test_draft_json_contains_schema_and_no_engineering_payload(tmp_path: Path) -> None:
    repository = ExportWizardDraftRepository(tmp_path)
    path = repository.save(_draft(tmp_path))
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema"] == EXPORT_WIZARD_DRAFT_SCHEMA
    assert "dataframe" not in path.read_text(encoding="utf-8").lower()
    assert "rendered" not in payload


def test_missing_draft_returns_none_and_delete_is_idempotent(tmp_path: Path) -> None:
    repository = ExportWizardDraftRepository(tmp_path)
    assert repository.load("missing") is None
    assert repository.delete("missing") is False
    repository.save(ExportWizardDraft(project_id="missing", wizard=ExportWizardState()))
    assert repository.delete("missing") is True
    assert repository.load("missing") is None


def test_invalid_schema_is_rejected(tmp_path: Path) -> None:
    repository = ExportWizardDraftRepository(tmp_path)
    path = repository.path_for("alpha")
    path.parent.mkdir(parents=True)
    path.write_text('{"schema":"legacy"}', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        repository.load("alpha")


def test_cross_project_payload_is_rejected(tmp_path: Path) -> None:
    repository = ExportWizardDraftRepository(tmp_path)
    path = repository.save(ExportWizardDraft(project_id="alpha", wizard=ExportWizardState()))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["project_id"] = "beta"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="another project"):
        repository.load("alpha")


def test_streamlit_panel_restores_and_saves_project_draft() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "ExportWizardDraftRepository(ROOT_DIR / \"data\" / \"projects\")" in source
    assert "draft_repository.load(str(active_project.id))" in source
    assert "draft_repository.save(" in source
    assert "export_wizard_draft_restored_" in source

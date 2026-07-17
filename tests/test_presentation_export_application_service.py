from pathlib import Path

import pytest

from reports.export_history import ExportHistoryEntry
from reports.export_wizard import ExportWizardState
from reports.export_wizard_persistence import ExportWizardDraft
from services.presentation_export_application_service import PresentationExportApplicationService


def test_service_persists_project_draft_and_history(tmp_path: Path) -> None:
    service = PresentationExportApplicationService(root=tmp_path, project_id="demo")
    draft = ExportWizardDraft(project_id="demo", wizard=ExportWizardState())

    service.save_draft(draft)
    loaded = service.load_draft()

    assert loaded is not None
    assert loaded.project_id == "demo"

    entry = ExportHistoryEntry(
        project_id="demo",
        file_name="report.pdf",
        format_id="pdf",
        format_label="PDF",
        profile_id="engineering",
        depth_top=1000.0,
        depth_bottom=1100.0,
        size_bytes=128,
        request_signature="signature",
    )
    service.record_history(entry)

    history = service.load_history()
    assert len(history) == 1
    assert history[0].project_id == "demo"
    assert history[0].file_name == "report.pdf"
    assert history[0].request_signature == "signature"
    assert service.clear_history() is True
    assert service.delete_draft() is True


def test_service_rejects_cross_project_writes(tmp_path: Path) -> None:
    service = PresentationExportApplicationService(root=tmp_path, project_id="demo")

    with pytest.raises(ValueError, match="another project"):
        service.save_draft(ExportWizardDraft(project_id="other", wizard=ExportWizardState()))


def test_service_reports_project_scoped_health(tmp_path: Path) -> None:
    service = PresentationExportApplicationService(root=tmp_path, project_id="demo")

    health = service.health()

    assert health["project_id"] == "demo"
    assert health["preview_storage_status"] == "empty"
    assert health["preview_storage_schema"] == 2
    assert health["preview_storage_migration_required"] is False
    assert health["preview_storage_quarantine_count"] == 0

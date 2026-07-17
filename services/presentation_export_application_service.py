"""Project-scoped application service for presentation export persistence.

The service is the UI-facing boundary for export drafts, export history and
report-preview metadata. Repository construction and storage paths remain
inside the application layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from reports.export_history import ExportHistoryEntry, ExportHistoryRepository
from reports.export_wizard_persistence import ExportWizardDraft, ExportWizardDraftRepository
from reports.report_preview_persistence import (
    ReportPreviewCountsLoadResult,
    ReportPreviewCountsRepository,
    ReportPreviewCountsStorageHealth,
)


class PresentationExportApplicationService:
    """Coordinate all project-scoped persistence used by the export workspace."""

    def __init__(self, *, root: Path | str, project_id: str) -> None:
        clean_project_id = str(project_id or "").strip()
        if not clean_project_id:
            raise ValueError("project_id is required")
        self._root = Path(root)
        self._project_id = clean_project_id
        self._drafts = ExportWizardDraftRepository(self._root)
        self._history = ExportHistoryRepository(self._root)
        self._preview_counts = ReportPreviewCountsRepository(self._root)

    @property
    def project_id(self) -> str:
        return self._project_id

    def load_draft(self) -> ExportWizardDraft | None:
        return self._drafts.load(self._project_id)

    def save_draft(self, draft: ExportWizardDraft) -> Path:
        self._require_project(draft.project_id)
        return self._drafts.save(draft)

    def delete_draft(self) -> bool:
        return self._drafts.delete(self._project_id)

    def load_preview_counts(self) -> ReportPreviewCountsLoadResult:
        return self._preview_counts.load_with_recovery(self._project_id)

    def save_preview_counts(self, payload: Mapping[str, Any]) -> Path:
        return self._preview_counts.save(self._project_id, payload)

    def preview_storage_health(self) -> ReportPreviewCountsStorageHealth:
        return self._preview_counts.storage_health(self._project_id)

    def delete_preview_counts(self, *, include_quarantine: bool = False) -> bool:
        return self._preview_counts.delete(
            self._project_id,
            include_quarantine=include_quarantine,
        )

    def load_history(self) -> tuple[ExportHistoryEntry, ...]:
        return self._history.load(self._project_id)

    def record_history(self, entry: ExportHistoryEntry) -> Path:
        self._require_project(entry.project_id)
        return self._history.record(entry)

    def clear_history(self) -> bool:
        return self._history.clear(self._project_id)

    def health(self) -> dict[str, object]:
        preview = self.preview_storage_health()
        return {
            "service": type(self).__name__,
            "project_id": self._project_id,
            "root": str(self._root.resolve()),
            "preview_storage_status": preview.status,
            "preview_storage_schema": preview.current_schema,
            "preview_storage_migration_required": preview.migration_required,
            "preview_storage_quarantine_count": preview.quarantine_count,
        }

    def _require_project(self, project_id: str) -> None:
        if str(project_id or "").strip() != self._project_id:
            raise ValueError("application service cannot persist data for another project")

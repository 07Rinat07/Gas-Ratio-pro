"""Application-service facade for multi-well interpretation correlation.

UI modules use this facade instead of constructing repositories directly.  The
existing domain/repository classes remain unchanged and can be migrated behind
this boundary incrementally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, MutableMapping

from core.repository_io import RepositoryIOMetrics
from projects.interpretation_correlation import (
    CorrelationWorkspace,
    CorrelationWorkspaceRepository,
    CorrelationWorkspaceService,
    PublishedInterpretationInput,
    discover_published_interpretations,
)
from projects.interpretation_correlation_commands import CorrelationWorkspaceCommandService
from projects.interpretation_correlation_suggestions import (
    CorrelationSuggestionAcceptanceJournal,
    CorrelationSuggestionProfileRepository,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id


class InterpretationCorrelationApplicationService:
    """Project-scoped use cases for correlation workspace management."""

    def __init__(
        self,
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        io_metrics: RepositoryIOMetrics | None = None,
    ) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)
        self.io_metrics = io_metrics
        self._repository = CorrelationWorkspaceRepository(
            root=self.root,
            project_id=self.project_id,
            io_metrics=io_metrics,
        )
        self._suggestion_profiles: CorrelationSuggestionProfileRepository | None = None
        self._acceptance_journals: dict[str, CorrelationSuggestionAcceptanceJournal] = {}

    def list_published_inputs(self) -> tuple[PublishedInterpretationInput, ...]:
        return discover_published_interpretations(root=self.root, project_id=self.project_id)

    def list_workspaces(self) -> tuple[CorrelationWorkspace, ...]:
        return self._repository.list()

    def create_workspace(
        self,
        *,
        name: str,
        description: str = "",
        wells: tuple[str, ...] = (),
    ) -> CorrelationWorkspace:
        return self._repository.create(name=name, description=description, wells=wells)

    def get_workspace(self, workspace_id: str) -> CorrelationWorkspace:
        return self._repository.get(workspace_id)

    def delete_workspace(self, workspace_id: str) -> bool:
        return self._repository.delete(workspace_id)

    def workspace_service(self, workspace_id: str) -> CorrelationWorkspaceService:
        return CorrelationWorkspaceService(
            root=self.root,
            project_id=self.project_id,
            workspace_id=workspace_id,
            io_metrics=self.io_metrics,
        )

    def command_service(
        self,
        state: MutableMapping[str, Any],
        workspace_id: str,
    ) -> CorrelationWorkspaceCommandService:
        return CorrelationWorkspaceCommandService(
            state,
            root=self.root,
            project_id=self.project_id,
            workspace_id=workspace_id,
            io_metrics=self.io_metrics,
        )


    def _profile_store(self) -> CorrelationSuggestionProfileRepository:
        if self._suggestion_profiles is None:
            self._suggestion_profiles = CorrelationSuggestionProfileRepository(
                root=self.root, project_id=self.project_id, io_metrics=self.io_metrics
            )
        return self._suggestion_profiles

    def list_suggestion_profiles(self) -> tuple[dict[str, Any], ...]:
        """Return saved calibration profiles without exposing persistence objects."""
        return tuple(self._profile_store().list())

    def save_suggestion_profile(self, *, name: str, settings: Any) -> dict[str, Any]:
        """Create or replace one named suggestion-calibration profile."""
        return self._profile_store().save(name=name, settings=settings)

    def delete_suggestion_profile(self, profile_id: str) -> bool:
        """Delete a saved calibration profile by identifier."""
        return self._profile_store().delete(profile_id)

    def _acceptance_journal(self, workspace_id: str) -> CorrelationSuggestionAcceptanceJournal:
        clean_workspace_id = str(workspace_id).strip()
        if not clean_workspace_id:
            raise ValueError("Workspace id must not be empty.")
        if clean_workspace_id not in self._acceptance_journals:
            self._acceptance_journals[clean_workspace_id] = CorrelationSuggestionAcceptanceJournal(
                root=self.root,
                project_id=self.project_id,
                workspace_id=clean_workspace_id,
                io_metrics=self.io_metrics,
            )
        return self._acceptance_journals[clean_workspace_id]

    def record_suggestion_acceptance(
        self,
        *,
        workspace_id: str,
        preview: Any,
        accepted_ids: Any,
        added_tie_ids: Any,
    ) -> dict[str, Any]:
        """Persist one accepted suggestion batch through the application boundary."""
        return self._acceptance_journal(workspace_id).append(
            preview=preview, accepted_ids=accepted_ids, added_tie_ids=added_tie_ids
        )

    def list_suggestion_acceptances(self, *, workspace_id: str) -> tuple[dict[str, Any], ...]:
        """Return the acceptance history for one correlation workspace."""
        return tuple(self._acceptance_journal(workspace_id).list())

    def health(self) -> dict[str, Any]:
        """Return a compact serializable health description for diagnostics."""

        directory = self._repository.directory
        return {
            "service": type(self).__name__,
            "project_id": self.project_id,
            "root": str(self.root),
            "repository_directory_exists": directory.exists(),
            "suggestion_profiles_initialized": self._suggestion_profiles is not None,
            "acceptance_journal_scopes": len(self._acceptance_journals),
        }

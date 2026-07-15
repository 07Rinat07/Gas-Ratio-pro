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


    def suggestion_profile_repository(self) -> CorrelationSuggestionProfileRepository:
        return CorrelationSuggestionProfileRepository(
            root=self.root, project_id=self.project_id, io_metrics=self.io_metrics
        )

    def suggestion_acceptance_journal(
        self, workspace_id: str
    ) -> CorrelationSuggestionAcceptanceJournal:
        return CorrelationSuggestionAcceptanceJournal(
            root=self.root,
            project_id=self.project_id,
            workspace_id=workspace_id,
            io_metrics=self.io_metrics,
        )

    def health(self) -> dict[str, Any]:
        """Return a compact serializable health description for diagnostics."""

        directory = self._repository.directory
        return {
            "service": type(self).__name__,
            "project_id": self.project_id,
            "root": str(self.root),
            "repository_directory_exists": directory.exists(),
        }

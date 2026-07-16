"""Project-scoped application boundary for storage index maintenance.

The Streamlit UI must not construct :class:`core.storage_lifecycle.IndexManager`
directly.  This service owns the infrastructure facade and exposes only the
use cases required by Project Database and destructive storage workflows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.storage_lifecycle import IndexManager, IndexSyncResult


class ProjectStorageApplicationService:
    """Coordinate project index and file-version synchronization."""

    def __init__(self, *, root: Path | str, project_id: str) -> None:
        clean_project_id = str(project_id).strip()
        if not clean_project_id:
            raise ValueError("Project id must not be empty.")
        self._root = Path(root).resolve()
        self._project_id = clean_project_id
        self._index_manager: IndexManager | None = None

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def root(self) -> Path:
        return self._root

    def _manager(self) -> IndexManager:
        if self._index_manager is None:
            self._index_manager = IndexManager(self._root)
        return self._index_manager

    def sync_storage(self) -> IndexSyncResult:
        """Rebuild the project index and synchronize file-version metadata."""
        return self._manager().sync_project_storage(self._project_id)

    def rebuild_index(self) -> IndexSyncResult:
        """Explicitly rebuild the project index from the filesystem."""
        return self._manager().rebuild_project_index(self._project_id)

    def validate_index(self) -> IndexSyncResult:
        """Validate the persisted index without changing project storage."""
        return self._manager().validate_project_index(self._project_id)

    def sync_after_delete(self) -> IndexSyncResult:
        """Synchronize index metadata after a successful destructive action."""
        return self._manager().sync_after_delete(self._project_id)

    def health_snapshot(self) -> dict[str, Any]:
        """Return lightweight lifecycle diagnostics without exposing infrastructure."""
        return {
            "service": type(self).__name__,
            "project_id": self._project_id,
            "root": str(self._root),
            "index_manager_initialized": self._index_manager is not None,
        }

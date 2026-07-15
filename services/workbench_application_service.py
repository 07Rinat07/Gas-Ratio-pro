"""Session-scoped application boundary for Modern Workbench coordination.

The facade owns lightweight Workbench coordination services and exposes
explicit use cases to Streamlit adapters.  UI modules therefore do not create
stateful coordination services ad hoc on every rerun.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, MutableMapping

from core.workbench_bulk_actions import WorkbenchBulkActionService, bulk_actions_for
from core.workbench_context import WorkbenchSelection, WorkbenchSelectionService
from core.workbench_entry_points import WorkbenchEntryPointService, WorkbenchEntryResult
from core.workbench_property_actions import WorkbenchPropertyActionService


class WorkbenchApplicationService:
    """Coordinate Workbench entry, selection and queued UI actions."""

    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        projects_root: str | Path,
        sessions_dir: str | Path = "data/sessions",
    ) -> None:
        self._state = state
        self._projects_root = Path(projects_root)
        self._sessions_dir = Path(sessions_dir)
        self._bulk = WorkbenchBulkActionService(state)
        self._selection = WorkbenchSelectionService(state)
        self._properties = WorkbenchPropertyActionService(state)
        self._entry: WorkbenchEntryPointService | None = None

    def _entry_service(self) -> WorkbenchEntryPointService:
        if self._entry is None:
            self._entry = WorkbenchEntryPointService(
                self._state,
                projects_root=self._projects_root,
                sessions_dir=self._sessions_dir,
            )
        return self._entry

    def project_entries(self) -> list[dict[str, Any]]:
        return self._entry_service().project_entries()

    def open_project(self, project_id: str) -> WorkbenchEntryResult:
        return self._entry_service().open_project(project_id)

    def restore_recent_session(self, session_path: str | Path | None = None) -> WorkbenchEntryResult:
        return self._entry_service().restore_recent_session(session_path)

    def bulk_actions(self, target: str) -> tuple[dict[str, Any], ...]:
        return bulk_actions_for(target)

    def set_bulk_selection(self, *, key: str, target: str, object_ids, metadata=None) -> None:
        self._bulk.set_selection(key=key, target=target, object_ids=object_ids, metadata=metadata)

    def request_bulk_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._bulk.request(payload)

    def consume_bulk_action(self) -> dict[str, Any] | None:
        return self._bulk.consume()

    def set_bulk_result(self, **kwargs: Any) -> None:
        self._bulk.set_result(**kwargs)

    def bulk_result(self) -> dict[str, Any] | None:
        return self._bulk.result()

    def select(self, target: str, object_id: str, metadata: dict[str, Any] | None = None) -> WorkbenchSelection:
        return self._selection.select(target, object_id, metadata)

    def clear_selection(self, reason: str = "selection_cleared") -> WorkbenchSelection:
        return self._selection.clear(reason)

    def consume_property_action(self) -> dict[str, Any] | None:
        return self._properties.consume()

    def set_property_result(self, **kwargs: Any) -> None:
        self._properties.set_result(**kwargs)

    def health_snapshot(self) -> dict[str, Any]:
        return {
            "service": type(self).__name__,
            "projects_root": str(self._projects_root.resolve()),
            "sessions_dir": str(self._sessions_dir.resolve()),
            "entry_initialized": self._entry is not None,
            "selection_empty": self._selection.current().is_empty(),
            "has_bulk_result": self._bulk.result() is not None,
            "has_property_result": self._properties.result() is not None,
        }

"""Project-scoped application boundary for background report export jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, MutableMapping

from projects.repository import DEFAULT_PROJECTS_ROOT
from reports.background_export import (
    BackgroundExportManager,
    ExportJobSnapshot,
    ExportWork,
)


class BackgroundExportApplicationService:
    """Own the background executor and enforce one project context.

    Only metadata snapshots are stored in the supplied application state.
    Futures, cancellation tokens and completed result objects remain process-local
    inside :class:`BackgroundExportManager`.
    """

    def __init__(
        self,
        state: MutableMapping[str, Any] | None = None,
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        max_workers: int = 1,
    ) -> None:
        clean_project_id = str(project_id).strip()
        if not clean_project_id:
            raise ValueError("project_id must not be empty")
        self._root = Path(root).resolve()
        self._project_id = clean_project_id
        self._metadata_key = f"background_export_metadata_{clean_project_id}"
        metadata_state = state if state is not None else {}
        self._metadata_state = metadata_state
        metadata = metadata_state.get(self._metadata_key)
        if not isinstance(metadata, dict):
            metadata = {}
            metadata_state[self._metadata_key] = metadata
        self._manager = BackgroundExportManager(metadata, max_workers=max_workers)

    @property
    def project_id(self) -> str:
        return self._project_id

    def submit(
        self,
        *,
        request_signature: str,
        work: ExportWork,
        retry_of_job_id: str = "",
        retry_reason: str = "",
        export_format: str = "",
    ) -> ExportJobSnapshot:
        return self._manager.submit(
            project_id=self._project_id,
            request_signature=request_signature,
            work=work,
            retry_of_job_id=retry_of_job_id,
            retry_reason=retry_reason,
            export_format=export_format,
        )

    def list(self) -> list[ExportJobSnapshot]:
        return self._manager.list(project_id=self._project_id)

    def cancel(self, job_id: str) -> ExportJobSnapshot:
        return self._assert_owned(self._manager.cancel(job_id))

    def dismiss(self, job_id: str) -> None:
        self._assert_owned_job(job_id)
        self._manager.dismiss(job_id)

    def dismiss_terminal(self, *, preserve_available_results: bool = False) -> int:
        return self._manager.dismiss_terminal(
            project_id=self._project_id,
            preserve_available_results=preserve_available_results,
        )

    def result_available(self, job_id: str) -> bool:
        self._assert_owned_job(job_id)
        return self._manager.result_available(job_id)

    def pop_result(self, job_id: str) -> Any:
        try:
            self._assert_owned_job(job_id)
        except KeyError:
            if self._foreign_job_exists(job_id):
                raise ValueError("Background export job belongs to another project")
            raise
        return self._manager.pop_result(job_id)

    def health_snapshot(self) -> dict[str, Any]:
        jobs = self.list()
        return {
            "project_id": self._project_id,
            "root": str(self._root),
            "jobs": len(jobs),
            "running": sum(1 for item in jobs if not item.terminal),
            "terminal": sum(1 for item in jobs if item.terminal),
            "available_results": sum(
                1 for item in jobs if self._manager.result_available(item.id)
            ),
            "metadata_key": self._metadata_key,
        }

    def _assert_owned_job(self, job_id: str) -> ExportJobSnapshot:
        clean_job_id = str(job_id).strip()
        if not clean_job_id:
            raise ValueError("job_id must not be empty")
        for snapshot in self.list():
            if snapshot.id == clean_job_id:
                return snapshot

        raise KeyError(f"Unknown export job for project {self._project_id}: {clean_job_id}")


    def _foreign_job_exists(self, job_id: str) -> bool:
        clean_job_id = str(job_id).strip()
        for key, project_metadata in self._metadata_state.items():
            if key == self._metadata_key or not key.startswith("background_export_metadata_"):
                continue
            if not isinstance(project_metadata, MutableMapping):
                continue
            jobs = project_metadata.get(BackgroundExportManager.STATE_KEY)
            if not isinstance(jobs, MutableMapping):
                continue
            payload = jobs.get(clean_job_id)
            if isinstance(payload, MutableMapping):
                snapshot = ExportJobSnapshot.from_dict(payload)
                return snapshot.project_id != self._project_id
        return False

    def _assert_owned(self, snapshot: ExportJobSnapshot) -> ExportJobSnapshot:
        if snapshot.project_id != self._project_id:
            raise ValueError("Background export job belongs to another project")
        return snapshot

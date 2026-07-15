"""Project-scoped application boundary for background report exports."""

from __future__ import annotations

from typing import Any, Callable, MutableMapping

from reports.background_export import BackgroundExportManager, ExportJobSnapshot


class BackgroundExportApplicationService:
    """Own the background export manager for one project.

    Session state stores only recoverable metadata. The executor, futures,
    cancellation events and binary results remain process-local inside the
    runtime-managed application service.
    """

    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        project_id: str,
        max_workers: int = 1,
    ) -> None:
        clean_project_id = str(project_id).strip()
        if not clean_project_id:
            raise ValueError("project_id must not be empty")
        self._project_id = clean_project_id
        self._manager = BackgroundExportManager(state, max_workers=max_workers)

    @property
    def project_id(self) -> str:
        return self._project_id

    def submit(
        self,
        *,
        request_signature: str,
        work: Callable[..., Any],
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

    def list(self) -> tuple[ExportJobSnapshot, ...]:
        return self._manager.list(project_id=self._project_id)

    def _owned_snapshot(self, job_id: str) -> ExportJobSnapshot:
        snapshot = self._manager.snapshot(job_id)
        if snapshot.project_id != self._project_id:
            raise ValueError("Export job belongs to another project")
        return snapshot

    def cancel(self, job_id: str) -> ExportJobSnapshot:
        self._owned_snapshot(job_id)
        return self._manager.cancel(job_id)

    def result_available(self, job_id: str) -> bool:
        self._owned_snapshot(job_id)
        return self._manager.result_available(job_id)

    def pop_result(self, job_id: str) -> Any:
        self._owned_snapshot(job_id)
        return self._manager.pop_result(job_id)

    def dismiss(self, job_id: str) -> None:
        self._owned_snapshot(job_id)
        self._manager.dismiss(job_id)

    def dismiss_terminal(self, *, preserve_available_results: bool = True) -> int:
        return self._manager.dismiss_terminal(
            project_id=self._project_id,
            preserve_available_results=preserve_available_results,
        )

    def health_snapshot(self) -> dict[str, Any]:
        jobs = self.list()
        return {
            "project_id": self._project_id,
            "jobs": len(jobs),
            "active_jobs": sum(1 for item in jobs if not item.terminal),
            "available_results": sum(
                1 for item in jobs if self._manager.result_available(item.id)
            ),
        }

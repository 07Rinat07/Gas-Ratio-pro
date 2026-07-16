"""Project-scoped runtime boundary for controlled presentation export.

Heavy presentation models and rendered binary artifacts are retained only in
process-local service state.  Streamlit session state stores neither DataFrame-
derived presentation models nor export bytes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from reports.export_controller import ExportArtifact, ExportController, ExportRequest


class PresentationExportRuntimeApplicationService:
    """Own and coordinate the bounded export controller cache for one project."""

    def __init__(self, *, root: Path | str, project_id: str) -> None:
        clean_project_id = str(project_id or "").strip()
        if not clean_project_id:
            raise ValueError("Project id must not be empty.")
        self._root = Path(root).resolve()
        self._project_id = clean_project_id
        self._runtime_state: dict[str, Any] = {}
        self._controller: ExportController | None = None

    @property
    def project_id(self) -> str:
        return self._project_id

    def _export_controller(self) -> ExportController:
        if self._controller is None:
            self._controller = ExportController(self._runtime_state)
        return self._controller

    def prepare(
        self,
        request: ExportRequest,
        *,
        frame: Any,
        build_model: Callable[[Any, ExportRequest], Any],
        render_artifact: Callable[[Any, Any, ExportRequest], ExportArtifact],
        on_progress: Callable[[int, str], None] | None = None,
        check_cancelled: Callable[[], None] | None = None,
    ) -> tuple[ExportArtifact, dict[str, float | bool]]:
        if str(request.project_id or "").strip() != self._project_id:
            raise ValueError("export request belongs to another project")
        return self._export_controller().prepare(
            request,
            frame=frame,
            build_model=build_model,
            render_artifact=render_artifact,
            on_progress=on_progress,
            check_cancelled=check_cancelled,
        )

    def clear_cache(self) -> None:
        if self._controller is not None:
            self._controller.clear_project_cache(self._project_id)

    def health_snapshot(self) -> dict[str, object]:
        metrics = (
            self._controller.cache_metrics()
            if self._controller is not None
            else {
                "model_entries": 0,
                "artifact_entries": 0,
                "artifact_bytes": 0,
                "artifact_max_bytes": ExportController.ARTIFACT_CACHE_MAX_BYTES,
            }
        )
        return {
            "service": type(self).__name__,
            "project_id": self._project_id,
            "root": str(self._root),
            "controller_initialized": self._controller is not None,
            **metrics,
        }

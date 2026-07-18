"""Project-scoped runtime boundary for controlled presentation export.

Heavy presentation models and rendered binary artifacts are retained only in
process-local service state. Streamlit session state stores neither DataFrame-
derived presentation models nor export bytes. Stage 5.1 also enforces
petrophysical report authorization immediately before the export controller.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from reports.export_controller import ExportArtifact, ExportController, ExportRequest
from services.petrophysical_report_authorization_application_service import (
    PetrophysicalReportAuthorizationApplicationService,
)


class PresentationExportRuntimeApplicationService:
    """Own bounded export caches and the final-report authorization boundary."""

    def __init__(
        self,
        *,
        root: Path | str,
        project_id: str,
        application_root: Path | str | None = None,
        report_authorization_service: PetrophysicalReportAuthorizationApplicationService | None = None,
    ) -> None:
        clean_project_id = str(project_id or "").strip()
        if not clean_project_id:
            raise ValueError("Project id must not be empty.")
        self._root = Path(root).resolve()
        self._application_root = Path(application_root).resolve() if application_root else Path(__file__).resolve().parents[1]
        self._project_id = clean_project_id
        self._runtime_state: dict[str, Any] = {}
        self._controller: ExportController | None = None
        self._report_authorization = report_authorization_service

    @property
    def project_id(self) -> str:
        return self._project_id

    def _export_controller(self) -> ExportController:
        if self._controller is None:
            self._controller = ExportController(self._runtime_state)
        return self._controller

    def _authorization_service(self) -> PetrophysicalReportAuthorizationApplicationService:
        if self._report_authorization is None:
            self._report_authorization = PetrophysicalReportAuthorizationApplicationService(root=self._application_root)
        return self._report_authorization

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

        authorization = None
        if request.require_final_report_authorization:
            if on_progress is not None:
                on_progress(1, "Проверка допуска петрофизических методов к финальному отчёту.")
            authorization = self._authorization_service().authorize(
                request.petrophysical_method_ids,
                final_report=True,
            )
            authorization.assert_authorized()

        artifact, metrics = self._export_controller().prepare(
            request,
            frame=frame,
            build_model=build_model,
            render_artifact=render_artifact,
            on_progress=on_progress,
            check_cancelled=check_cancelled,
        )
        enriched_metrics: dict[str, float | bool] = dict(metrics)
        enriched_metrics["petrophysical_authorization_checked"] = authorization is not None
        enriched_metrics["petrophysical_authorized"] = bool(authorization and authorization.passed)
        if authorization is not None:
            artifact = replace(
                artifact,
                authorization_id=authorization.authorization_id,
                authorization_gate_ids=(authorization.validation_gate_id, authorization.calibration_gate_id),
            )
        return artifact, enriched_metrics

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
            "application_root": str(self._application_root),
            "controller_initialized": self._controller is not None,
            "report_authorization_initialized": self._report_authorization is not None,
            **metrics,
        }

"""Lazy application-service container backed by the runtime registry.

The container keeps UI code away from repository construction.  It stores only
live service objects in :class:`RuntimeServiceRegistry`; application/session
state remains free of repositories, locks and other non-serializable objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, MutableMapping, TypeVar

from core.repository_io import RepositoryIOMetrics
from core.runtime_service_registry import RuntimeServiceRegistry, runtime_service_registry

T = TypeVar("T")
_CONTAINER_KEY = "application_service_container"


@dataclass(frozen=True, slots=True)
class ApplicationServiceDescriptor:
    """Serializable description of one lazily created application service."""

    key: str
    service_name: str
    project_id: str
    type_name: str


class ApplicationServiceContainer:
    """Create and reuse project-scoped application services lazily."""

    def __init__(
        self,
        registry: RuntimeServiceRegistry,
        state: MutableMapping[str, Any] | None = None,
    ) -> None:
        self._registry = registry
        self._state = state if state is not None else {}
        self._descriptors: dict[str, ApplicationServiceDescriptor] = {}

    @staticmethod
    def _service_key(service_name: str, project_id: str, root: Path | str) -> str:
        clean_name = str(service_name).strip()
        clean_project = str(project_id).strip()
        if not clean_name or not clean_project:
            raise ValueError("Service name and project id must not be empty.")
        root_key = str(Path(root).resolve())
        return f"application::{clean_name}::{clean_project}::{root_key}"

    def ensure_project_service(
        self,
        *,
        service_name: str,
        project_id: str,
        root: Path | str,
        factory: Callable[[], T],
        expected_type: type[T],
    ) -> T:
        key = self._service_key(service_name, project_id, root)
        service = self._registry.ensure(
            key,
            factory,
            expected_type=expected_type,
            scope="project",
        )
        self._descriptors[key] = ApplicationServiceDescriptor(
            key=key,
            service_name=str(service_name),
            project_id=str(project_id),
            type_name=type(service).__name__,
        )
        return service



    def ensure_session_service(
        self,
        *,
        service_name: str,
        factory: Callable[[], T],
        expected_type: type[T],
        instance_key: str = "",
    ) -> T:
        """Create/reuse a session-scoped application service."""
        clean_name = str(service_name).strip()
        if not clean_name:
            raise ValueError("Service name must not be empty.")
        suffix = str(instance_key).strip()
        key = f"application::{clean_name}::__session__" + (f"::{suffix}" if suffix else "")
        service = self._registry.ensure(
            key, factory, expected_type=expected_type, scope="session"
        )
        self._descriptors[key] = ApplicationServiceDescriptor(
            key=key, service_name=clean_name, project_id="__session__",
            type_name=type(service).__name__,
        )
        return service

    def workbench_runtime(self):
        """Return the session-scoped Modern Workbench runtime boundary."""
        from services.workbench_runtime_application_service import (
            WorkbenchRuntimeApplicationService,
        )

        return self.ensure_session_service(
            service_name="workbench_runtime",
            factory=lambda: WorkbenchRuntimeApplicationService(registry=self._registry),
            expected_type=WorkbenchRuntimeApplicationService,
        )

    def workbench(self, *, projects_root: Path | str, sessions_dir: Path | str = "data/sessions"):
        from services.workbench_application_service import WorkbenchApplicationService
        return self.ensure_session_service(
            service_name="workbench",
            factory=lambda: WorkbenchApplicationService(
                self._state, projects_root=projects_root, sessions_dir=sessions_dir
            ),
            expected_type=WorkbenchApplicationService,
            instance_key=f"{Path(projects_root).resolve()}::{Path(sessions_dir).resolve()}",
        )

    def ensure_workspace_service(
        self,
        *,
        service_name: str,
        root: Path | str,
        factory: Callable[[], T],
        expected_type: type[T],
    ) -> T:
        """Create/reuse a workspace-scoped service without serializing it in session state."""
        key = self._service_key(service_name, "__workspace__", root)
        service = self._registry.ensure(
            key, factory, expected_type=expected_type, scope="workspace"
        )
        self._descriptors[key] = ApplicationServiceDescriptor(
            key=key, service_name=str(service_name), project_id="__workspace__",
            type_name=type(service).__name__,
        )
        return service

    def project_manager(self, *, root: Path | str, default_project_id: str):
        from services.project_manager_service import ProjectManagerService
        return self.ensure_workspace_service(
            service_name="project_manager", root=root,
            factory=lambda: ProjectManagerService(root, default_project_id),
            expected_type=ProjectManagerService,
        )

    def export_manager(self, *, root: Path | str):
        from services.export_manager_service import ExportManagerService
        return self.ensure_workspace_service(
            service_name="export_manager", root=root,
            factory=lambda: ExportManagerService(root), expected_type=ExportManagerService,
        )

    def well_manager(self, *, root: Path | str):
        from services.well_manager_service import WellManagerService
        return self.ensure_workspace_service(
            service_name="well_manager", root=root,
            factory=lambda: WellManagerService(root), expected_type=WellManagerService,
        )

    def dataset_manager(self, *, root: Path | str):
        from services.dataset_manager_service import DatasetManagerService
        return self.ensure_workspace_service(
            service_name="dataset_manager", root=root,
            factory=lambda: DatasetManagerService(root), expected_type=DatasetManagerService,
        )

    def user_locale_preferences(self, *, path: Path | str):
        """Return the session-scoped persistent locale preference boundary."""
        from services.user_locale_preference_service import UserLocalePreferenceService

        return self.ensure_session_service(
            service_name="user_locale_preferences",
            factory=lambda: UserLocalePreferenceService(path),
            expected_type=UserLocalePreferenceService,
            instance_key=str(Path(path).resolve()),
        )

    def localization(
        self,
        *,
        catalogs_dir: Path | str,
        language: str = "ru",
    ):
        """Return the session-scoped localization boundary.

        The service is keyed by catalog directory; the active language remains
        mutable inside the service and is never encoded into the registry key.
        """
        from services.localization_application_service import (
            LocalizationApplicationService,
        )

        return self.ensure_session_service(
            service_name="localization",
            factory=lambda: LocalizationApplicationService(
                catalogs_dir=catalogs_dir, language=language
            ),
            expected_type=LocalizationApplicationService,
            instance_key=str(Path(catalogs_dir).resolve()),
        )

    def cache_metrics_registry(self):
        """Return the single session-scoped cache telemetry registry."""
        from core.cache_metrics import CacheMetricsRegistry

        return self._registry.ensure(
            "cache_metrics_registry",
            CacheMetricsRegistry,
            expected_type=CacheMetricsRegistry,
            scope="session",
        )

    def temporary_files(self, *, allowed_roots: tuple[Path | str, ...] | None = None):
        """Return the session-scoped lifecycle boundary for temporary files."""
        from services.temporary_file_application_service import TemporaryFileApplicationService

        roots = tuple(allowed_roots or ())
        instance_key = "|".join(str(Path(root).resolve()) for root in roots) or "system-temp"
        return self.ensure_session_service(
            service_name="temporary_files",
            factory=lambda: TemporaryFileApplicationService(allowed_roots=roots or None),
            expected_type=TemporaryFileApplicationService,
            instance_key=instance_key,
        )

    def data_platform(self, *, root: Path | str):
        """Return the workspace-scoped industry data-platform boundary."""
        from services.data_platform_application_service import DataPlatformApplicationService

        return self.ensure_workspace_service(
            service_name="data_platform",
            root=root,
            factory=lambda: DataPlatformApplicationService(root),
            expected_type=DataPlatformApplicationService,
        )

    def petrophysical_validation(self, *, root: Path | str):
        """Return the workspace-scoped Stage 5 validation-gate boundary."""
        from services.petrophysical_validation_application_service import (
            PetrophysicalValidationApplicationService,
        )

        return self.ensure_workspace_service(
            service_name="petrophysical_validation",
            root=root,
            factory=lambda: PetrophysicalValidationApplicationService(root=root),
            expected_type=PetrophysicalValidationApplicationService,
        )

    def petrophysical_calibration(self, *, root: Path | str):
        """Return the workspace-scoped Stage 5.1 field-calibration boundary."""
        from services.petrophysical_calibration_application_service import (
            PetrophysicalCalibrationApplicationService,
        )

        validation = self.petrophysical_validation(root=root)
        return self.ensure_workspace_service(
            service_name="petrophysical_calibration",
            root=root,
            factory=lambda: PetrophysicalCalibrationApplicationService(
                root=root,
                validation_service=validation,
            ),
            expected_type=PetrophysicalCalibrationApplicationService,
        )

    def petrophysical_report_authorization(self, *, root: Path | str):
        """Return the final-report authorization boundary."""
        from services.petrophysical_report_authorization_application_service import (
            PetrophysicalReportAuthorizationApplicationService,
        )

        validation = self.petrophysical_validation(root=root)
        calibration = self.petrophysical_calibration(root=root)
        return self.ensure_workspace_service(
            service_name="petrophysical_report_authorization",
            root=root,
            factory=lambda: PetrophysicalReportAuthorizationApplicationService(
                root=root,
                validation_service=validation,
                calibration_service=calibration,
            ),
            expected_type=PetrophysicalReportAuthorizationApplicationService,
        )


    def operator_calibration_packages(
        self,
        *,
        projects_root: Path | str,
        application_root: Path | str,
        project_id: str,
    ):
        """Return the project-scoped Stage 5.2 operator calibration boundary."""
        from services.operator_calibration_package_application_service import (
            OperatorCalibrationPackageApplicationService,
        )

        validation = self.petrophysical_validation(root=application_root)
        baseline_calibration = self.petrophysical_calibration(root=application_root)
        baseline_authorization = self.petrophysical_report_authorization(root=application_root)
        return self.ensure_project_service(
            service_name="operator_calibration_packages",
            project_id=project_id,
            root=projects_root,
            factory=lambda: OperatorCalibrationPackageApplicationService(
                projects_root=projects_root,
                application_root=application_root,
                project_id=project_id,
                validation_service=validation,
                baseline_calibration_service=baseline_calibration,
                baseline_authorization_service=baseline_authorization,
            ),
            expected_type=OperatorCalibrationPackageApplicationService,
        )

    def runtime_diagnostics(self, *, root: Path | str):
        # Local import keeps diagnostics infrastructure behind a lazy boundary.
        from services.runtime_diagnostics_application_service import (
            RuntimeDiagnosticsApplicationService,
        )

        return self.ensure_workspace_service(
            service_name="runtime_diagnostics",
            root=root,
            factory=lambda: RuntimeDiagnosticsApplicationService(
                root=root, registry=self._registry
            ),
            expected_type=RuntimeDiagnosticsApplicationService,
        )

    def correlation(
        self,
        *,
        project_id: str,
        root: Path | str,
        io_metrics: RepositoryIOMetrics | None = None,
    ):
        # Local import keeps correlation dependencies behind the lazy boundary.
        from services.interpretation_correlation_application_service import (
            InterpretationCorrelationApplicationService,
        )

        effective_metrics = io_metrics
        if effective_metrics is None:
            from services.runtime_diagnostics_application_service import (
                RuntimeDiagnosticsApplicationService,
            )

            # Resolve the shared collector through the diagnostics application
            # boundary without eagerly registering a workspace service descriptor.
            effective_metrics = RuntimeDiagnosticsApplicationService(
                root=root, registry=self._registry
            ).repository_metrics()

        return self.ensure_project_service(
            service_name="interpretation_correlation",
            project_id=project_id,
            root=root,
            factory=lambda: InterpretationCorrelationApplicationService(
                root=root,
                project_id=project_id,
                io_metrics=effective_metrics,
            ),
            expected_type=InterpretationCorrelationApplicationService,
        )

    def project_storage(
        self,
        *,
        project_id: str,
        root: Path | str,
    ):
        """Return the lazy project-scoped storage maintenance boundary."""
        from services.project_storage_application_service import (
            ProjectStorageApplicationService,
        )

        return self.ensure_project_service(
            service_name="project_storage",
            project_id=project_id,
            root=root,
            factory=lambda: ProjectStorageApplicationService(
                root=root,
                project_id=project_id,
            ),
            expected_type=ProjectStorageApplicationService,
        )

    def background_export(
        self,
        *,
        project_id: str,
        root: Path | str,
        max_workers: int = 1,
        metadata_state: MutableMapping[str, Any] | None = None,
    ):
        """Return the project-scoped background export execution boundary.

        ``metadata_state`` is a compatibility injection point for tests and
        non-Streamlit hosts. Production callers normally rely on the container
        state. Only compact job metadata is stored in either mapping.
        """
        from services.background_export_application_service import (
            BackgroundExportApplicationService,
        )

        return self.ensure_project_service(
            service_name="background_export",
            project_id=project_id,
            root=root,
            factory=lambda: BackgroundExportApplicationService(
                root=root,
                project_id=project_id,
                state=metadata_state if metadata_state is not None else self._state,
                max_workers=max_workers,
            ),
            expected_type=BackgroundExportApplicationService,
        )

    def presentation_export_runtime(
        self,
        *,
        project_id: str,
        root: Path | str,
    ):
        from services.presentation_export_runtime_application_service import (
            PresentationExportRuntimeApplicationService,
        )

        return self.ensure_project_service(
            service_name="presentation_export_runtime",
            project_id=project_id,
            root=root,
            factory=lambda: PresentationExportRuntimeApplicationService(
                root=root,
                project_id=project_id,
                application_root=Path(__file__).resolve().parents[1],
                report_authorization_service=self.petrophysical_report_authorization(
                    root=Path(__file__).resolve().parents[1]
                ),
                operator_calibration_service=self.operator_calibration_packages(
                    projects_root=root,
                    application_root=Path(__file__).resolve().parents[1],
                    project_id=project_id,
                ),
            ),
            expected_type=PresentationExportRuntimeApplicationService,
        )

    def presentation_export(
        self,
        *,
        project_id: str,
        root: Path | str,
    ):
        # Local import preserves lazy loading of report persistence dependencies.
        from services.presentation_export_application_service import (
            PresentationExportApplicationService,
        )

        return self.ensure_project_service(
            service_name="presentation_export",
            project_id=project_id,
            root=root,
            factory=lambda: PresentationExportApplicationService(
                root=root,
                project_id=project_id,
            ),
            expected_type=PresentationExportApplicationService,
        )

    def las_workspace(
        self,
        *,
        project_id: str,
        root: Path | str,
    ):
        # Local import keeps LAS storage infrastructure behind the lazy boundary.
        from services.las_workspace_application_service import (
            LasWorkspaceApplicationService,
        )

        return self.ensure_project_service(
            service_name="las_workspace",
            project_id=project_id,
            root=root,
            factory=lambda: LasWorkspaceApplicationService(
                root=root,
                project_id=project_id,
            ),
            expected_type=LasWorkspaceApplicationService,
        )


    def pdf_preview(
        self,
        *,
        project_id: str,
        root: Path | str,
        metrics_registry=None,
    ):
        # Local import keeps heavy PDF preview runtime dependencies lazy.
        from services.pdf_preview_application_service import (
            PdfPreviewApplicationService,
        )

        effective_metrics = metrics_registry or self.cache_metrics_registry()
        return self.ensure_project_service(
            service_name="pdf_preview",
            project_id=project_id,
            root=root,
            factory=lambda: PdfPreviewApplicationService(
                root=root,
                project_id=project_id,
                metrics_registry=effective_metrics,
            ),
            expected_type=PdfPreviewApplicationService,
        )

    def correlation_presentation(
        self,
        *,
        project_id: str,
        root: Path | str,
        metrics_registry=None,
    ):
        from services.correlation_presentation_application_service import (
            CorrelationPresentationApplicationService,
        )

        effective_metrics = metrics_registry or self.cache_metrics_registry()
        return self.ensure_project_service(
            service_name="correlation_presentation",
            project_id=project_id,
            root=root,
            factory=lambda: CorrelationPresentationApplicationService(
                root=root,
                project_id=project_id,
                metrics_registry=effective_metrics,
            ),
            expected_type=CorrelationPresentationApplicationService,
        )

    def interpretation_presentation(
        self,
        *,
        project_id: str,
        root: Path | str,
        metrics_registry=None,
    ):
        from services.interpretation_presentation_application_service import (
            InterpretationPresentationApplicationService,
        )

        effective_metrics = metrics_registry or self.cache_metrics_registry()
        return self.ensure_project_service(
            service_name="interpretation_presentation",
            project_id=project_id,
            root=root,
            factory=lambda: InterpretationPresentationApplicationService(
                root=root,
                project_id=project_id,
                metrics_registry=effective_metrics,
            ),
            expected_type=InterpretationPresentationApplicationService,
        )

    def interpretation_workspace(
        self,
        *,
        project_id: str,
        root: Path | str,
    ):
        # Local import preserves lazy loading of interpretation persistence.
        from services.interpretation_workspace_application_service import (
            InterpretationWorkspaceApplicationService,
        )

        return self.ensure_project_service(
            service_name="interpretation_workspace",
            project_id=project_id,
            root=root,
            factory=lambda: InterpretationWorkspaceApplicationService(
                root=root,
                project_id=project_id,
            ),
            expected_type=InterpretationWorkspaceApplicationService,
        )

    def descriptors(self) -> tuple[ApplicationServiceDescriptor, ...]:
        active_keys = {item.key for item in self._registry.descriptors()}
        stale = tuple(key for key in self._descriptors if key not in active_keys)
        for key in stale:
            self._descriptors.pop(key, None)
        return tuple(self._descriptors[key] for key in sorted(self._descriptors))

    def quality_control(self, *, root: Path | str | None = None):
        """Return the lazy QC boundary; pass root to enable artifact persistence."""
        from services.qc_application_service import QCApplicationService
        if root is None:
            return self.ensure_session_service(
                service_name="quality_control",
                factory=QCApplicationService,
                expected_type=QCApplicationService,
            )
        return self.ensure_workspace_service(
            service_name="quality_control",
            root=root,
            factory=lambda: QCApplicationService(root),
            expected_type=QCApplicationService,
        )

    def snapshot(self) -> dict[str, Any]:
        descriptors = self.descriptors()
        return {
            "active": len(descriptors),
            "services": [
                {
                    "key": item.key,
                    "service_name": item.service_name,
                    "project_id": item.project_id,
                    "type_name": item.type_name,
                }
                for item in descriptors
            ],
        }


def application_service_container(state: MutableMapping[str, Any]) -> ApplicationServiceContainer:
    """Return the session container without placing services in serializable state."""

    registry = runtime_service_registry(state)
    return registry.ensure(
        _CONTAINER_KEY,
        lambda: ApplicationServiceContainer(registry, state),
        expected_type=ApplicationServiceContainer,
        scope="session",
    )

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

    def __init__(self, registry: RuntimeServiceRegistry) -> None:
        self._registry = registry
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

        return self.ensure_project_service(
            service_name="interpretation_correlation",
            project_id=project_id,
            root=root,
            factory=lambda: InterpretationCorrelationApplicationService(
                root=root,
                project_id=project_id,
                io_metrics=io_metrics,
            ),
            expected_type=InterpretationCorrelationApplicationService,
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

        return self.ensure_project_service(
            service_name="pdf_preview",
            project_id=project_id,
            root=root,
            factory=lambda: PdfPreviewApplicationService(
                root=root,
                project_id=project_id,
                metrics_registry=metrics_registry,
            ),
            expected_type=PdfPreviewApplicationService,
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
        lambda: ApplicationServiceContainer(registry),
        expected_type=ApplicationServiceContainer,
        scope="session",
    )

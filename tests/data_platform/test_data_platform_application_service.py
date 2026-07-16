import json

import pytest

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from services.data_platform_application_service import DataPlatformApplicationService


def test_register_source_file_creates_artifact_and_manifest(tmp_path):
    projects = tmp_path / "projects"
    source = tmp_path / "well.las"
    source.write_text("~Version\nVERS. 2.0", encoding="utf-8")
    service = DataPlatformApplicationService(projects)

    manifest = service.register_source_file(
        project_id="project-a",
        well_id="well-1",
        source=source,
        actor="Rinat",
        metadata={"curve_count": 3},
    )

    assert manifest.format_id == "las"
    assert manifest.provenance.operation == "import"
    assert manifest.provenance.actor == "Rinat"
    assert (projects / "project-a" / "artifacts" / manifest.artifact_path).exists()
    assert service.manifests.load("project-a", manifest.dataset_id) == manifest
    json.dumps(service.snapshot("project-a"), ensure_ascii=False)


def test_register_rejects_export_only_format(tmp_path):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"%PDF")
    service = DataPlatformApplicationService(tmp_path / "projects")
    with pytest.raises(ValueError, match="does not support import"):
        service.register_source_file(project_id="project-a", source=source)


def test_container_reuses_workspace_data_platform_service(tmp_path):
    container = ApplicationServiceContainer(RuntimeServiceRegistry(), {})
    first = container.data_platform(root=tmp_path / "projects")
    second = container.data_platform(root=tmp_path / "projects")
    assert first is second

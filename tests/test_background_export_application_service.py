from pathlib import Path
from time import sleep

import pytest

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from reports.background_export import ExportJobStatus
from services.background_export_application_service import BackgroundExportApplicationService


def _wait(service: BackgroundExportApplicationService, job_id: str):
    for _ in range(100):
        jobs = {item.id: item for item in service.list()}
        snapshot = jobs[job_id]
        if snapshot.terminal:
            return snapshot
        sleep(0.01)
    raise AssertionError("background export did not finish")


def test_service_owns_project_context_and_process_local_result(tmp_path: Path) -> None:
    state = {}
    service = BackgroundExportApplicationService(
        root=tmp_path, project_id="project-a", state=state
    )

    job = service.submit(
        request_signature="sig-1",
        export_format="pdf",
        work=lambda report, check: b"artifact",
    )
    completed = _wait(service, job.id)

    assert completed.project_id == "project-a"
    assert completed.status is ExportJobStatus.COMPLETED
    assert service.result_available(job.id)
    assert service.pop_result(job.id) == b"artifact"
    assert not service.result_available(job.id)
    assert "background_export_metadata_project-a" in state
    assert all(not key.startswith("background_export_manager") for key in state)


def test_service_rejects_foreign_or_unknown_jobs(tmp_path: Path) -> None:
    state = {}
    first = BackgroundExportApplicationService(root=tmp_path, project_id="a", state=state)
    second = BackgroundExportApplicationService(root=tmp_path, project_id="b", state=state)
    job = first.submit(request_signature="sig", work=lambda report, check: b"x")
    _wait(first, job.id)

    with pytest.raises(KeyError):
        second.result_available(job.id)
    with pytest.raises(KeyError):
        second.dismiss(job.id)


def test_container_reuses_service_per_project_and_isolates_projects(tmp_path: Path) -> None:
    state = {}
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry, state)

    first = container.background_export(project_id="a", root=tmp_path)
    same = container.background_export(project_id="a", root=tmp_path)
    other = container.background_export(project_id="b", root=tmp_path)

    assert first is same
    assert first is not other
    assert first.project_id == "a"
    assert other.project_id == "b"


def test_health_snapshot_is_lightweight(tmp_path: Path) -> None:
    service = BackgroundExportApplicationService(root=tmp_path, project_id="a", state={})
    snapshot = service.health_snapshot()

    assert snapshot["project_id"] == "a"
    assert snapshot["jobs"] == 0
    assert "manager" not in snapshot
    assert "executor" not in snapshot

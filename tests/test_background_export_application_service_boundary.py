from __future__ import annotations

import ast
import time
from pathlib import Path

import pytest

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from reports.background_export import ExportJobStatus
from services.background_export_application_service import BackgroundExportApplicationService


def _wait(service: BackgroundExportApplicationService, job_id: str, timeout: float = 2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = next(job for job in service.list() if job.id == job_id)
        if item.terminal:
            return item
        time.sleep(0.01)
    raise AssertionError("background export did not finish")


def test_service_is_project_scoped_and_reused(tmp_path):
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry, {})
    state = {}

    first = container.background_export(
        project_id="p1", root=tmp_path, metadata_state=state
    )
    second = container.background_export(
        project_id="p1", root=tmp_path, metadata_state=state
    )
    other = container.background_export(
        project_id="p2", root=tmp_path, metadata_state={}
    )

    assert first is second
    assert first is not other


def test_service_submits_and_hands_off_result():
    service = BackgroundExportApplicationService({}, project_id="p1")

    job = service.submit(
        request_signature="sig",
        export_format="pdf",
        work=lambda report, check: b"artifact",
    )
    completed = _wait(service, job.id)

    assert completed.status is ExportJobStatus.COMPLETED
    assert service.result_available(job.id)
    assert service.pop_result(job.id) == b"artifact"


def test_service_rejects_foreign_job_access():
    shared_state = {}
    first = BackgroundExportApplicationService(shared_state, project_id="p1")
    second = BackgroundExportApplicationService(shared_state, project_id="p2")
    job = first.submit(request_signature="sig", work=lambda report, check: b"x")
    _wait(first, job.id)

    with pytest.raises(ValueError, match="another project"):
        second.pop_result(job.id)


def test_streamlit_ui_does_not_construct_background_manager_directly():
    path = Path("app/streamlit_app.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "reports.background_export"
        for alias in node.names
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "BackgroundExportManager" not in imported
    assert "BackgroundExportManager" not in calls
    assert ".background_export(" in path.read_text(encoding="utf-8")

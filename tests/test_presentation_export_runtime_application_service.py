from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from reports.export_controller import ExportRequest
from services.presentation_export_runtime_application_service import PresentationExportRuntimeApplicationService


def _request(project_id: str) -> ExportRequest:
    return ExportRequest(
        project_id=project_id, project_name="P", source_label="S",
        profile_id="engineering", format_id="pdf", format_label="PDF",
        extension="pdf", mime_type="application/pdf", depth_top=1.0,
        depth_bottom=2.0, source_signature="sig", calculation_revision=1,
        presentation_revision=1, figure_height=1000, context_signature="ctx",
    )


def test_service_is_lazy_and_project_scoped(tmp_path: Path) -> None:
    service = PresentationExportRuntimeApplicationService(root=tmp_path, project_id="a")
    assert service.health_snapshot()["controller_initialized"] is False
    with pytest.raises(ValueError, match="another project"):
        service.prepare(_request("b"), frame=None, build_model=lambda *_: None, render_artifact=lambda *_: None)
    assert service.health_snapshot()["controller_initialized"] is False


def test_container_reuses_runtime_service_and_isolates_projects(tmp_path: Path) -> None:
    container = ApplicationServiceContainer(RuntimeServiceRegistry(), {})
    first = container.presentation_export_runtime(project_id="a", root=tmp_path)
    again = container.presentation_export_runtime(project_id="a", root=tmp_path)
    other = container.presentation_export_runtime(project_id="b", root=tmp_path)
    assert first is again
    assert first is not other


def test_streamlit_does_not_construct_export_controller_or_store_controller_cache() -> None:
    path = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "ExportController" not in imports
    assert "ExportController" not in calls
    assert "background_export_controller_cache_" not in source
    assert ".presentation_export_runtime(" in source

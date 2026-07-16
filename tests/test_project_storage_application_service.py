from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from services.project_storage_application_service import ProjectStorageApplicationService


def test_project_storage_service_is_lazy_and_project_scoped(tmp_path: Path) -> None:
    service = ProjectStorageApplicationService(root=tmp_path, project_id="project-a")

    assert service.health_snapshot()["index_manager_initialized"] is False
    assert service.project_id == "project-a"
    assert service.root == tmp_path.resolve()

    # Validation initializes infrastructure only when a storage use case is invoked.
    result = service.validate_index()

    assert result.project_id == "project-a"
    assert service.health_snapshot()["index_manager_initialized"] is True


def test_project_storage_service_rejects_empty_project_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Project id"):
        ProjectStorageApplicationService(root=tmp_path, project_id="  ")


def test_container_reuses_service_and_isolates_projects(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry, {})

    first = container.project_storage(project_id="a", root=tmp_path)
    again = container.project_storage(project_id="a", root=tmp_path)
    other = container.project_storage(project_id="b", root=tmp_path)

    assert first is again
    assert first is not other
    assert {item.service_name for item in container.descriptors()} == {"project_storage"}


def test_streamlit_ui_does_not_construct_index_manager_directly() -> None:
    source_path = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_names: set[str] = set()
    constructed_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            constructed_names.add(node.func.id)

    assert "IndexManager" not in imported_names
    assert "IndexManager" not in constructed_names
    assert "project_storage(" in source_path.read_text(encoding="utf-8")

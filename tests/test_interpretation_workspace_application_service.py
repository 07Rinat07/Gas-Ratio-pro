from __future__ import annotations

from pathlib import Path

import pytest

from services.interpretation_workspace_application_service import InterpretationWorkspaceApplicationService


def test_service_lazily_reuses_context_operations(tmp_path: Path) -> None:
    service = InterpretationWorkspaceApplicationService(root=tmp_path, project_id="project-a")

    assert service.health_snapshot()["catalog_scopes"] == 0
    first = service.catalog(well_id="well-a")
    second = service.catalog(well_id="well-a")

    assert first is second
    assert service.interval_types() is service.interval_types()
    assert service.filter_presets(well_id="well-a", interpretation_id="default") is service.filter_presets(
        well_id="well-a", interpretation_id="default"
    )
    assert service.revisions(well_id="well-a", interpretation_id="default") is service.revisions(
        well_id="well-a", interpretation_id="default"
    )
    snapshot = service.health_snapshot()
    assert snapshot["catalog_scopes"] == 1
    assert snapshot["preset_scopes"] == 1
    assert snapshot["revision_scopes"] == 1
    assert snapshot["interval_types_initialized"] is True


def test_service_catalog_operations_are_project_scoped(tmp_path: Path) -> None:
    service = InterpretationWorkspaceApplicationService(root=tmp_path, project_id="project-a")
    catalog = service.catalog(well_id="well-a")

    initial = catalog.list()
    created = catalog.create(name="Working interpretation", description="test")

    assert len(initial) == 1
    assert catalog.get(created.id).name == "Working interpretation"
    assert (tmp_path / "project-a" / "wells" / "well-a" / "interpretations" / created.id).is_dir()


def test_gateway_does_not_expose_repository_state(tmp_path: Path) -> None:
    service = InterpretationWorkspaceApplicationService(root=tmp_path, project_id="project-a")
    gateway = service.catalog(well_id="well-a")

    with pytest.raises(AttributeError):
        _ = gateway.root
    with pytest.raises(AttributeError):
        _ = gateway._load_items

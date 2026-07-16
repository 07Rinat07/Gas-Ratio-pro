from __future__ import annotations

from pathlib import Path

import pytest

from services.interpretation_workspace_application_service import InterpretationWorkspaceApplicationService


def test_service_lazily_reuses_context_operations(tmp_path: Path) -> None:
    service = InterpretationWorkspaceApplicationService(root=tmp_path, project_id="project-a")

    assert service.health_snapshot()["catalog_scopes"] == 0
    first = service.list_interpretations(well_id="well-a")
    second = service.list_interpretations(well_id="well-a")

    assert first == second
    assert service.list_interval_types() == service.list_interval_types()
    assert service.filter_preset_use_cases(well_id="well-a", interpretation_id="default") is service.filter_preset_use_cases(
        well_id="well-a", interpretation_id="default"
    )
    assert service.revision_use_cases(well_id="well-a", interpretation_id="default") is service.revision_use_cases(
        well_id="well-a", interpretation_id="default"
    )
    snapshot = service.health_snapshot()
    assert snapshot["catalog_scopes"] == 1
    assert snapshot["preset_scopes"] == 1
    assert snapshot["revision_scopes"] == 1
    assert snapshot["interval_types_initialized"] is True


def test_service_catalog_operations_are_project_scoped(tmp_path: Path) -> None:
    service = InterpretationWorkspaceApplicationService(root=tmp_path, project_id="project-a")
    initial = service.list_interpretations(well_id="well-a")
    created = service.create_interpretation(
        well_id="well-a", name="Working interpretation", description="test"
    )

    assert len(initial) == 1
    assert service.get_interpretation(created.id, well_id="well-a").name == "Working interpretation"
    assert (tmp_path / "project-a" / "wells" / "well-a" / "interpretations" / created.id).is_dir()


def test_service_does_not_expose_repository_gateways(tmp_path: Path) -> None:
    service = InterpretationWorkspaceApplicationService(root=tmp_path, project_id="project-a")

    assert not hasattr(service, "catalog")
    assert not hasattr(service, "interval_types")
    assert not hasattr(service, "filter_presets")
    assert not hasattr(service, "revisions")


def test_service_owns_interval_coordination_lifecycle(tmp_path: Path) -> None:
    service = InterpretationWorkspaceApplicationService(root=tmp_path, project_id="project-a")
    state: dict[str, object] = {}

    manager = service.interval_manager(
        state=state, well_id="well-a", interpretation_id="default"
    )
    assert manager is service.interval_manager(
        state=state, well_id="well-a", interpretation_id="default"
    )
    assert service.interval_properties(
        state=state, well_id="well-a", interpretation_id="default"
    ) is service.interval_properties(
        state=state, well_id="well-a", interpretation_id="default"
    )
    assert service.interval_batch(
        state=state, well_id="well-a", interpretation_id="default"
    ) is service.interval_batch(
        state=state, well_id="well-a", interpretation_id="default"
    )

    snapshot = service.health_snapshot()
    assert snapshot["manager_scopes"] == 1
    assert snapshot["properties_scopes"] == 1
    assert snapshot["batch_scopes"] == 1


def test_interval_manager_lifecycle_is_isolated_by_state_and_context(tmp_path: Path) -> None:
    service = InterpretationWorkspaceApplicationService(root=tmp_path, project_id="project-a")
    first_state: dict[str, object] = {}
    second_state: dict[str, object] = {}

    first = service.interval_manager(
        state=first_state, well_id="well-a", interpretation_id="default"
    )
    other_state = service.interval_manager(
        state=second_state, well_id="well-a", interpretation_id="default"
    )
    other_well = service.interval_manager(
        state=first_state, well_id="well-b", interpretation_id="default"
    )

    assert first is not other_state
    assert first is not other_well

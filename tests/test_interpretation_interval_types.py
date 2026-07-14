from pathlib import Path

import pytest

from projects.interpretation_interval_types import InterpretationIntervalTypeRepository


def test_repository_returns_defaults_without_creating_file(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")

    items = repository.list()

    assert {item.id for item in items} >= {"undefined", "reservoir", "pay", "gas", "oil", "water"}
    assert not (tmp_path / "project" / "interpretation_interval_types.json").exists()


def test_repository_upserts_and_persists_custom_type(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")

    created = repository.upsert(type_id="tight gas", name="Плотный газ", color="#123abc", description="Test")
    loaded = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project").get(created.id)

    assert created.id == "tight_gas"
    assert created.color == "#123ABC"
    assert loaded == created


def test_repository_updates_existing_type_without_changing_created_at(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    first = repository.upsert(type_id="custom", name="Первый", color="#112233")

    updated = repository.upsert(type_id="custom", name="Второй", color="#445566")

    assert updated.name == "Второй"
    assert updated.created_at == first.created_at


def test_repository_deletes_type_and_is_project_scoped(tmp_path: Path) -> None:
    first = InterpretationIntervalTypeRepository(root=tmp_path, project_id="first")
    second = InterpretationIntervalTypeRepository(root=tmp_path, project_id="second")
    first.upsert(type_id="custom", name="Custom", color="#112233")

    assert first.delete("custom") is True
    assert first.delete("custom") is False
    assert second.get("custom") is None


def test_repository_validates_color(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")

    with pytest.raises(ValueError, match="HEX"):
        repository.upsert(type_id="bad", name="Bad", color="red")

from projects.interpretation_intervals import create_interpretation_interval


def test_repository_reports_project_wide_type_usage(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="custom", name="Custom", color="#112233")
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        interpretation_id="default",
        label="A",
        top=100,
        base=110,
        interval_type="custom",
    )
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-b",
        interpretation_id="secondary",
        label="B",
        top=200,
        base=210,
        interval_type="custom",
    )

    usage = repository.usage("custom")

    assert usage.interval_count == 2
    assert usage.well_count == 2
    assert usage.interpretation_count == 2
    assert usage.in_use is True


def test_repository_refuses_to_delete_type_used_by_intervals(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="custom", name="Custom", color="#112233")
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        label="A",
        top=100,
        base=110,
        interval_type="custom",
    )

    with pytest.raises(ValueError, match="используется"):
        repository.delete("custom")

    assert repository.get("custom") is not None

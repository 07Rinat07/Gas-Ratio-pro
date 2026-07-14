from __future__ import annotations

import json
from pathlib import Path

import pytest

from projects.interpretation_catalog import InterpretationCatalogRepository
from projects.interpretation_intervals import create_interpretation_interval, load_interpretation_intervals


def repo(tmp_path: Path) -> InterpretationCatalogRepository:
    return InterpretationCatalogRepository(root=tmp_path, project_id="project", well_id="well")


def test_catalog_discovers_default_and_manages_metadata(tmp_path: Path) -> None:
    catalog = repo(tmp_path)
    assert catalog.list()[0].id == "default"

    created = catalog.create(name="Версия геолога", description="Ручная проверка")
    assert created.id == "interpretation"
    updated = catalog.update(created.id, name="Версия геолога 2", description="Обновлено")
    assert updated.name == "Версия геолога 2"
    assert catalog.get(created.id).description == "Обновлено"


def test_duplicate_copies_intervals_and_rewrites_scope(tmp_path: Path) -> None:
    catalog = repo(tmp_path)
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well",
        interpretation_id="default",
        label="A",
        top=100,
        base=110,
    )
    duplicate = catalog.duplicate("default", name="Сценарий B")

    copied = load_interpretation_intervals(
        root=tmp_path, project_id="project", well_id="well", interpretation_id=duplicate.id
    )
    assert copied.interpretation_id == duplicate.id
    assert [item.label for item in copied.intervals] == ["A"]
    payload = json.loads(
        (tmp_path / "project" / "wells" / "well" / "interpretations" / duplicate.id / "intervals.json").read_text(encoding="utf-8")
    )
    assert payload["interpretation_id"] == duplicate.id


def test_delete_is_reversible_and_last_interpretation_is_protected(tmp_path: Path) -> None:
    catalog = repo(tmp_path)
    second = catalog.create(name="Second")
    deleted = catalog.delete(second.id)
    assert all(item.id != second.id for item in catalog.list())
    assert catalog.list_deleted()[0].trash_id == deleted.trash_id

    restored = catalog.restore(deleted.trash_id)
    assert restored.id == second.id
    assert catalog.get(second.id).name == "Second"

    catalog.delete(second.id)
    with pytest.raises(ValueError, match="единственную"):
        catalog.delete("default")


def test_duplicate_rejects_existing_target_id(tmp_path: Path) -> None:
    catalog = repo(tmp_path)
    catalog.create(name="Existing", interpretation_id="existing")
    with pytest.raises(ValueError, match="уже существует"):
        catalog.duplicate("default", name="Copy", target_id="existing")

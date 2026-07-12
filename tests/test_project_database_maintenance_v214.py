from __future__ import annotations

from pathlib import Path

import pytest

from projects.project_index import (
    load_project_file_index,
    load_project_file_versions,
    load_project_uuid_registry,
)
from projects.repository import create_project
from services.project_manager_service import ProjectManagerService


def _project_with_files(root: Path):
    project = create_project(root=root, name="Database maintenance")
    project_dir = root / project.id
    (project_dir / "datasets" / "csv" / "a").mkdir(parents=True)
    (project_dir / "datasets" / "csv" / "b").mkdir(parents=True)
    (project_dir / "datasets" / "csv" / "a" / "gas.csv").write_text("depth,c1\n1,10\n", encoding="utf-8")
    (project_dir / "datasets" / "csv" / "b" / "gas-copy.csv").write_text("depth,c1\n1,10\n", encoding="utf-8")
    return project


def test_project_database_metadata_reset_preserves_user_files(tmp_path: Path) -> None:
    project = _project_with_files(tmp_path)
    service = ProjectManagerService(tmp_path)
    service.index_manager.sync_project_storage(project.id)

    source = tmp_path / project.id / "datasets" / "csv" / "a" / "gas.csv"
    result = service.reset_project_database_metadata(project.id)

    assert source.exists()
    assert result.operation == "reset"
    assert result.indexed_files >= 2
    assert load_project_file_index(tmp_path, project.id)
    assert load_project_file_versions(tmp_path, project.id)
    assert load_project_uuid_registry(tmp_path, project.id)
    assert result.backup_id


def test_project_database_compaction_keeps_one_version_per_asset(tmp_path: Path) -> None:
    project = _project_with_files(tmp_path)
    service = ProjectManagerService(tmp_path)
    service.index_manager.sync_project_storage(project.id)
    source = tmp_path / project.id / "datasets" / "csv" / "a" / "gas.csv"
    source.write_text("depth,c1\n1,11\n", encoding="utf-8")
    service.index_manager.sync_project_storage(project.id)
    assert any(asset.version_count > 1 for asset in load_project_file_versions(tmp_path, project.id))

    result = service.compact_project_database_metadata(project.id)

    assets = load_project_file_versions(tmp_path, project.id)
    assert result.operation == "compact"
    assert assets
    assert all(asset.version_count == 1 for asset in assets)
    assert source.exists()


def test_exact_duplicate_delete_requires_checksum_group_and_creates_backup(tmp_path: Path) -> None:
    project = _project_with_files(tmp_path)
    service = ProjectManagerService(tmp_path)
    service.index_manager.sync_project_storage(project.id)
    duplicate = "datasets/csv/b/gas-copy.csv"

    result = service.delete_exact_duplicate_file(project.id, duplicate)

    assert result.operation == "delete-duplicate"
    assert result.deleted_path == duplicate
    assert not (tmp_path / project.id / duplicate).exists()
    assert (tmp_path / project.id / "datasets/csv/a/gas.csv").exists()
    assert result.backup_id
    assert all(entry.relative_path != duplicate for entry in load_project_file_index(tmp_path, project.id))


def test_non_duplicate_file_cannot_be_deleted_by_duplicate_operation(tmp_path: Path) -> None:
    project = _project_with_files(tmp_path)
    unique = tmp_path / project.id / "datasets" / "csv" / "unique.csv"
    unique.write_text("depth,c1\n2,20\n", encoding="utf-8")
    service = ProjectManagerService(tmp_path)
    service.index_manager.sync_project_storage(project.id)

    with pytest.raises(ValueError, match="SHA-256"):
        service.delete_exact_duplicate_file(project.id, "datasets/csv/unique.csv")

    assert unique.exists()

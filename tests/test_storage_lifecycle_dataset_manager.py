from __future__ import annotations

from pathlib import Path

from core.storage_lifecycle import DeleteEngine, ResourceManager
from projects.datasets import list_project_mud_log_records, save_project_mud_log_dataset
from services.dataset_manager_service import DatasetManagerService


def test_resource_manager_releases_path_resources(tmp_path: Path) -> None:
    manager = ResourceManager()
    released: list[str] = []
    source = tmp_path / "dataset" / "source.xlsx"
    source.parent.mkdir()
    source.write_bytes(b"placeholder")

    manager.register_file(source, owner="Dataset Preview", release_callback=lambda: released.append("file"))
    manager.register_dataframe("df:source", owner="Dataset Preview", path=source, release_callback=lambda: released.append("df"))

    assert manager.diagnostics().total == 2
    assert manager.release_path(source.parent) == 2
    assert sorted(released) == ["df", "file"]
    assert manager.diagnostics().total == 0


def test_delete_engine_releases_registered_resources_before_delete(tmp_path: Path) -> None:
    manager = ResourceManager()
    engine = DeleteEngine(manager, attempts=1, delay_seconds=0)
    dataset_dir = tmp_path / "dataset"
    source = dataset_dir / "source.xlsx"
    dataset_dir.mkdir()
    source.write_bytes(b"placeholder")
    released: list[str] = []
    manager.register_file(source, owner="Dataset Preview", release_callback=lambda: released.append("released"))

    result = engine.delete_path(dataset_dir)

    assert result.deleted is True
    assert result.released_resources == 1
    assert released == ["released"]
    assert not dataset_dir.exists()


def test_dataset_manager_service_clear_mud_log_section_removes_files_and_manifest(tmp_path: Path) -> None:
    project_id = "demo"
    save_project_mud_log_dataset(
        b"DEPTH,C1\n100,1\n101,2\n",
        root=tmp_path,
        project_id=project_id,
        file_name="mud.csv",
        name="Mud Test",
    )
    records_before = list_project_mud_log_records(tmp_path, project_id, include_archived=True)
    assert len(records_before) == 1

    service = DatasetManagerService(tmp_path)
    section_dir = service.section_dir(project_id, "mud_log")
    assert section_dir.exists()

    summary = service.clear_section(project_id, "mud_log")

    assert summary.requested == 1
    assert summary.deleted == 1
    assert section_dir.exists()
    assert list_project_mud_log_records(tmp_path, project_id, include_archived=True) == ()
    assert not any(path.name.startswith("source") for path in section_dir.rglob("*"))


def test_dataset_manager_service_delete_selected_dataset_updates_manifest(tmp_path: Path) -> None:
    project_id = "demo"
    first = save_project_mud_log_dataset(
        b"DEPTH,C1\n100,1\n",
        root=tmp_path,
        project_id=project_id,
        file_name="first.csv",
        name="First Mud",
    )
    second = save_project_mud_log_dataset(
        b"DEPTH,C1\n101,2\n",
        root=tmp_path,
        project_id=project_id,
        file_name="second.csv",
        name="Second Mud",
    )

    service = DatasetManagerService(tmp_path)
    summary = service.delete_dataset(project_id, "mud_log", first.id)
    remaining = list_project_mud_log_records(tmp_path, project_id, include_archived=True)

    assert summary.deleted == 1
    assert tuple(record.id for record in remaining) == (second.id,)
    assert not service._spec("mud_log").dataset_dir(tmp_path, project_id, first.id).exists()

from core.storage_lifecycle import IndexManager
from projects.project_index import load_project_file_index, save_project_file_index


def test_index_manager_rebuilds_index_after_dataset_delete(tmp_path: Path) -> None:
    project_id = "demo"
    record = save_project_mud_log_dataset(
        b"DEPTH,C1\n100,1\n",
        root=tmp_path,
        project_id=project_id,
        file_name="mud.csv",
        name="Mud Index Test",
    )
    save_project_file_index(tmp_path, project_id)
    before_paths = {entry.relative_path for entry in load_project_file_index(tmp_path, project_id)}
    assert any(record.id in path for path in before_paths)

    service = DatasetManagerService(tmp_path)
    summary = service.delete_dataset(project_id, "mud_log", record.id)

    after_paths = {entry.relative_path for entry in load_project_file_index(tmp_path, project_id)}
    assert summary.index_entries == len(after_paths)
    assert not any(record.id in path for path in after_paths)


def test_index_manager_rebuild_project_index_removes_stale_entries(tmp_path: Path) -> None:
    project_id = "demo"
    project_dir = tmp_path / project_id
    data_file = project_dir / "datasets" / "mud_log" / "source.xlsx"
    data_file.parent.mkdir(parents=True)
    data_file.write_bytes(b"content")
    save_project_file_index(tmp_path, project_id)
    assert load_project_file_index(tmp_path, project_id)

    data_file.unlink()
    result = IndexManager(tmp_path).rebuild_project_index(project_id)

    assert result.entries_count == 0
    assert load_project_file_index(tmp_path, project_id) == ()

from core.storage_lifecycle import CacheManager, FileHandleManager


def test_cache_manager_clears_path_bound_entries(tmp_path: Path) -> None:
    cache = CacheManager()
    released: list[str] = []
    dataset_dir = tmp_path / "dataset"
    source = dataset_dir / "source.xlsx"
    dataset_dir.mkdir()
    source.write_bytes(b"placeholder")

    cache.register("preview:source", owner="Dataset Preview", path=source, release_callback=lambda: released.append("cache"))

    assert len(cache.diagnostics()) == 1
    assert cache.clear_path(dataset_dir) == 1
    assert released == ["cache"]
    assert cache.diagnostics() == ()


def test_file_handle_manager_delegates_release_to_resource_manager(tmp_path: Path) -> None:
    resource_manager = ResourceManager()
    handles = FileHandleManager(resource_manager)
    released: list[str] = []
    source = tmp_path / "dataset" / "source.xlsx"
    source.parent.mkdir()
    source.write_bytes(b"placeholder")

    handles.register_file(source, owner="Dataset Preview", release_callback=lambda: released.append("handle"))

    assert len(handles.diagnostics()) == 1
    assert handles.release_path(source.parent) == 1
    assert released == ["handle"]
    assert handles.diagnostics() == ()


def test_dataset_manager_service_releases_file_handles_and_cache_before_delete(tmp_path: Path) -> None:
    project_id = "demo"
    record = save_project_mud_log_dataset(
        b"DEPTH,C1\n100,1\n",
        root=tmp_path,
        project_id=project_id,
        file_name="mud.csv",
        name="Mud Lifecycle Test",
    )
    service = DatasetManagerService(tmp_path)
    dataset_path = service._spec("mud_log").dataset_dir(tmp_path, project_id, record.id)
    source_path = dataset_path / "source.csv"
    released: list[str] = []

    service.file_handle_manager.register_file(source_path, owner="Dataset Preview", release_callback=lambda: released.append("file"))
    service.cache_manager.register("preview:mud", owner="Dataset Preview", path=source_path, release_callback=lambda: released.append("cache"))

    summary = service.delete_dataset(project_id, "mud_log", record.id)

    assert summary.deleted == 1
    assert sorted(released) == ["cache", "file"]
    assert service.diagnostics()["file_handles"] == ()
    assert service.diagnostics()["cache_entries"] == ()

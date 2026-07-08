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

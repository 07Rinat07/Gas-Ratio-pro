from pathlib import Path

from projects.datasets import save_project_csv_dataset
from services.dataset_manager_service import DatasetManagerService


def test_dataset_manager_service_deletes_csv_dataset(tmp_path: Path) -> None:
    project_id = "demo-project"
    record = save_project_csv_dataset(
        b"DEPTH,GR\n1000,80\n1001,82\n",
        root=tmp_path,
        project_id=project_id,
        file_name="mud.csv",
        name="Mud CSV",
    )

    service = DatasetManagerService(tmp_path)
    assert len(service.list_datasets(project_id, kind="csv")) == 1

    result = service.delete_dataset(project_id, "csv", record.id)

    assert result.deleted is True
    assert service.list_datasets(project_id, kind="csv") == ()
    assert not (tmp_path / project_id / "datasets" / "csv" / record.id).exists()


def test_dataset_manager_service_clear_section_and_all(tmp_path: Path) -> None:
    project_id = "demo-project"
    save_project_csv_dataset(b"DEPTH,GR\n1000,80\n", root=tmp_path, project_id=project_id, file_name="a.csv", name="A")
    save_project_csv_dataset(b"DEPTH,GR\n1001,81\n", root=tmp_path, project_id=project_id, file_name="b.csv", name="B")

    service = DatasetManagerService(tmp_path)
    section_result = service.clear_section(project_id, "csv")

    assert section_result.deleted_count == 2
    assert service.summarize(project_id).total == 0

    save_project_csv_dataset(b"DEPTH,GR\n1002,82\n", root=tmp_path, project_id=project_id, file_name="c.csv", name="C")
    all_result = service.clear_all(project_id)

    assert all_result.deleted_count == 1
    assert service.list_datasets(project_id) == ()

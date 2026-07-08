from __future__ import annotations

from services.dataset_manager_service import DatasetManagerService
from services.las_manager_service import LasManagerService
from projects.repository import create_project


def test_las_manager_delete_uses_storage_lifecycle_and_updates_index(tmp_path):
    project = create_project(tmp_path, name="LAS lifecycle")
    service = LasManagerService(tmp_path)
    saved = service.save_file(
        project_id=project.id,
        data=b"~Version\n VERS. 2.0\n~Well\n STRT.M 1\n STOP.M 1\n STEP.M 1\n NULL. -999.25\n~Curve\n DEPT.M : Depth\n GR.API : Gamma\n~Ascii\n1 80\n",
        file_name="demo.las",
        well_name="Demo",
    )

    result = service.delete_file(project.id, saved.record.id)

    assert result.deleted is True
    assert service.list_files(project.id, include_archived=True) == ()
    assert not (tmp_path / project.id / "wells" / saved.record.id).exists()
    assert result.index_entries_count >= 0


def test_dataset_manager_las_section_routes_to_las_service(tmp_path):
    project = create_project(tmp_path, name="Dataset LAS lifecycle")
    las_service = LasManagerService(tmp_path)
    saved = las_service.save_file(
        project_id=project.id,
        data=b"~Version\n VERS. 2.0\n~Well\n STRT.M 1\n STOP.M 1\n STEP.M 1\n NULL. -999.25\n~Curve\n DEPT.M : Depth\n GR.API : Gamma\n~Ascii\n1 80\n",
        file_name="demo.las",
        well_name="Demo",
    )
    dataset_service = DatasetManagerService(tmp_path)

    summary = dataset_service.delete_dataset(project.id, "las", saved.record.id)

    assert summary.deleted == 1
    assert summary.section == "las"
    assert las_service.list_files(project.id, include_archived=True) == ()

from pathlib import Path

import pandas as pd
import pytest

from projects.repository import DEFAULT_PROJECT_ID, create_project, delete_project, load_project
from wells.repository import delete_well, delete_well_version, list_wells, save_well_version


def test_delete_well_version_removes_only_selected_version(tmp_path: Path):
    df = pd.DataFrame({"DEPT": [1.0, 1.2], "GR": [10, 20]})
    record = save_well_version(df, root=tmp_path, well_name="Well A", version_label="v1", depth_column="DEPT")
    record = save_well_version(df, root=tmp_path, well_id=record.id, well_name="Well A", version_label="v2", depth_column="DEPT")

    first_version_id = record.versions[0].id
    assert delete_well_version(tmp_path, record.id, first_version_id) is True

    records = list_wells(tmp_path)
    assert len(records) == 1
    assert len(records[0].versions) == 1
    assert records[0].versions[0].id != first_version_id


def test_delete_last_well_version_removes_well(tmp_path: Path):
    df = pd.DataFrame({"DEPT": [1.0], "GR": [10]})
    record = save_well_version(df, root=tmp_path, well_name="Well B", version_label="v1", depth_column="DEPT")

    assert delete_well_version(tmp_path, record.id, record.versions[0].id) is True
    assert list_wells(tmp_path) == ()


def test_delete_well_removes_manifest_and_files(tmp_path: Path):
    df = pd.DataFrame({"DEPT": [1.0], "GR": [10]})
    record = save_well_version(df, root=tmp_path, well_name="Well C", version_label="v1", depth_column="DEPT")

    assert delete_well(tmp_path, record.id) is True
    assert not (tmp_path / record.id).exists()


def test_delete_project_removes_project_directory(tmp_path: Path):
    project = create_project(tmp_path, name="Delete Me")
    assert (tmp_path / project.id).exists()

    assert delete_project(tmp_path, project.id) is True
    assert not (tmp_path / project.id).exists()


def test_delete_project_protects_default(tmp_path: Path):
    with pytest.raises(ValueError):
        delete_project(tmp_path, DEFAULT_PROJECT_ID)

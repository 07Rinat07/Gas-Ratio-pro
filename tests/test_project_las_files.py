from __future__ import annotations

import pytest

from projects import list_project_las_files, read_project_las_file_bytes, save_project_las_file


LAS_BYTES = b"~Version\nVERS. 2.0\n~Curve\nDEPT.M : Depth\nGR.API : Gamma\n~ASCII\n1000 45\n"


def test_project_las_file_roundtrip(tmp_path):
    record = save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.las",
        well_name="Well A",
    )

    records = list_project_las_files(tmp_path, "demo")

    assert len(records) == 1
    assert records[0].id == record.id
    assert records[0].name == "Well A"
    assert records[0].original_file_name == "Well A.las"
    assert read_project_las_file_bytes(tmp_path, "demo", record.id) == LAS_BYTES
    assert (tmp_path / "demo" / "wells" / record.id / "source.las").exists()


def test_project_las_file_uses_unique_ids(tmp_path):
    first = save_project_las_file(LAS_BYTES, root=tmp_path, project_id="demo", file_name="well.las")
    second = save_project_las_file(LAS_BYTES, root=tmp_path, project_id="demo", file_name="well.las")

    assert first.id != second.id
    assert {record.id for record in list_project_las_files(tmp_path, "demo")} == {first.id, second.id}


def test_project_las_file_rejects_unsafe_project_id(tmp_path):
    with pytest.raises(ValueError, match="Некорректный идентификатор проекта"):
        save_project_las_file(LAS_BYTES, root=tmp_path, project_id="../bad", file_name="well.las")

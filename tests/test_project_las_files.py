from __future__ import annotations

import pytest

from projects import (
    list_project_las_files,
    list_project_las_wells,
    read_project_las_file_bytes,
    save_project_las_file,
)


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
    assert records[0].well_id == "well-a"
    assert records[0].version_label == "Исходный LAS"
    assert records[0].original_file_name == "Well A.las"
    assert read_project_las_file_bytes(tmp_path, "demo", record.id) == LAS_BYTES
    assert (tmp_path / "demo" / "wells" / record.id / "source.las").exists()


def test_project_las_file_uses_unique_ids_and_groups_versions_by_well(tmp_path):
    first = save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="well.las",
        well_name="Well A",
        version_label="raw 1",
    )
    second = save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="well.las",
        well_name="Well A",
        version_label="raw 2",
    )

    records = list_project_las_files(tmp_path, "demo")
    well_cards = list_project_las_wells(tmp_path, "demo")

    assert first.id != second.id
    assert first.well_id == second.well_id == "well-a"
    assert {record.id for record in records} == {first.id, second.id}
    assert len(well_cards) == 1
    assert well_cards[0].id == "well-a"
    assert well_cards[0].name == "Well A"
    assert {version.version_label for version in well_cards[0].versions} == {"raw 1", "raw 2"}


def test_project_las_file_rejects_unsafe_project_id(tmp_path):
    with pytest.raises(ValueError, match="Некорректный идентификатор проекта"):
        save_project_las_file(LAS_BYTES, root=tmp_path, project_id="../bad", file_name="well.las")

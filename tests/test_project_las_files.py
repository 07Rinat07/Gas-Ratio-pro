from __future__ import annotations

import hashlib
import json
from io import BytesIO
from zipfile import ZipFile

import pytest

from projects import (
    export_project_las_files_zip,
    list_project_las_files,
    list_project_las_wells,
    read_project_las_file_bytes,
    read_project_las_file_dataframe,
    save_project_las_file,
    set_project_las_file_archived,
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
    assert records[0].archived_at == ""
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


def test_project_las_file_archive_hides_version_without_deleting_source(tmp_path):
    first = save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="well-a-raw.las",
        well_name="Well A",
        version_label="raw",
    )
    second = save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="well-a-fixed.las",
        well_name="Well A",
        version_label="fixed",
    )

    archived = set_project_las_file_archived(tmp_path, "demo", first.id, archived=True)

    active_records = list_project_las_files(tmp_path, "demo")
    all_records = list_project_las_files(tmp_path, "demo", include_archived=True)
    active_cards = list_project_las_wells(tmp_path, "demo")
    all_cards = list_project_las_wells(tmp_path, "demo", include_archived=True)

    assert archived.archived_at
    assert {record.id for record in active_records} == {second.id}
    assert {record.id for record in all_records} == {first.id, second.id}
    assert [version.id for version in active_cards[0].versions] == [second.id]
    assert {version.id for version in all_cards[0].versions} == {first.id, second.id}
    assert read_project_las_file_bytes(tmp_path, "demo", first.id) == LAS_BYTES

    restored = set_project_las_file_archived(tmp_path, "demo", first.id, archived=False)

    assert restored.archived_at == ""
    assert {record.id for record in list_project_las_files(tmp_path, "demo")} == {first.id, second.id}


def test_project_las_file_rejects_unsafe_project_id(tmp_path):
    with pytest.raises(ValueError, match="Некорректный идентификатор проекта"):
        save_project_las_file(LAS_BYTES, root=tmp_path, project_id="../bad", file_name="well.las")


def test_project_las_file_dataframe_and_zip_export(tmp_path):
    record = save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.las",
        well_name="Well A",
        version_label="raw",
    )

    dataframe = read_project_las_file_dataframe(tmp_path, "demo", record.id)
    zip_bytes = export_project_las_files_zip(tmp_path, "demo", [record.id])

    assert list(dataframe.columns) == ["DEPT", "GR"]
    assert dataframe.loc[0, "DEPT"] == 1000.0
    with ZipFile(BytesIO(zip_bytes)) as archive:
        names = archive.namelist()
        assert any(name.endswith(".las") for name in names)
        assert any(name.endswith(".csv") for name in names)
        assert any(name.endswith(".xlsx") for name in names)
        assert "manifest.json" in names
        assert "README.txt" in names
        csv_name = next(name for name in names if name.endswith(".csv"))
        assert "DEPT" in archive.read(csv_name).decode("utf-8-sig")
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert manifest["project_id"] == "demo"
        assert manifest["formats"] == ["las", "xlsx", "csv"]
        assert manifest["las_files"][0]["id"] == record.id
        assert manifest["las_files"][0]["well_name"] == "Well A"
        exported_files = manifest["las_files"][0]["exported_files"]
        las_export = next(item for item in exported_files if item["format"] == "las")
        assert las_export["name"].endswith(".las")
        assert las_export["size_bytes"] == len(archive.read(las_export["name"]))
        assert las_export["sha256"] == hashlib.sha256(archive.read(las_export["name"])).hexdigest()


def test_project_las_zip_export_validates_selection_and_formats(tmp_path):
    record = save_project_las_file(LAS_BYTES, root=tmp_path, project_id="demo", file_name="well.las")

    with pytest.raises(ValueError, match="Не выбраны"):
        export_project_las_files_zip(tmp_path, "demo", [])

    with pytest.raises(ValueError, match="Неподдерживаемый формат"):
        export_project_las_files_zip(tmp_path, "demo", [record.id], formats=("pdf",))



def test_project_las_file_persists_editor_metadata(tmp_path):
    record = save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A prepared.las",
        well_name="Well A",
        version_label="prepared",
        metadata={"source": "las_editor", "edit_log": [{"action": "Batch operation"}]},
    )

    loaded = list_project_las_files(tmp_path, "demo")[0]

    assert loaded.id == record.id
    assert loaded.metadata["source"] == "las_editor"
    assert loaded.metadata["edit_log"][0]["action"] == "Batch operation"

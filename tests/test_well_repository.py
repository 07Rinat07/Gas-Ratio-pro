from __future__ import annotations

import pandas as pd

from wells.repository import list_wells, load_well_record, read_well_file_bytes, save_well_version


def test_save_well_version_creates_manifest_and_exports(tmp_path):
    df = pd.DataFrame({"DEPT": [1000.0, 1000.2], "C1": [80, 90]})

    record = save_well_version(
        df,
        root=tmp_path,
        well_name="Demo Well",
        area="Area 1",
        status="checked",
        comment="Prepared from LAS editor",
        version_label="step 0.2",
        depth_column="DEPT",
        metadata={"target_step": "0.2"},
    )

    loaded = load_well_record(tmp_path, record.id)
    records = list_wells(tmp_path)
    latest_version = loaded.versions[-1]

    assert loaded.name == "Demo Well"
    assert loaded.area == "Area 1"
    assert loaded.status == "checked"
    assert latest_version.label == "step 0.2"
    assert latest_version.metadata["target_step"] == "0.2"
    assert records[0].id == loaded.id
    assert read_well_file_bytes(tmp_path, loaded.id, latest_version.id, "csv").startswith(b"\xef\xbb\xbf")
    assert b"~ASCII" in read_well_file_bytes(tmp_path, loaded.id, latest_version.id, "las")


def test_save_well_version_appends_to_existing_well(tmp_path):
    df = pd.DataFrame({"DEPT": [1000.0], "C1": [80]})
    first = save_well_version(df, root=tmp_path, well_name="Demo")

    second = save_well_version(
        df,
        root=tmp_path,
        well_id=first.id,
        well_name="Demo",
        version_label="manual edit",
    )

    assert first.id == second.id
    assert len(second.versions) == 2

def test_save_well_version_uses_unique_version_ids(tmp_path):
    df = pd.DataFrame({"DEPT": [1000.0], "C1": [80]})
    first = save_well_version(df, root=tmp_path, well_name="Demo", version_label="same label")
    second = save_well_version(df, root=tmp_path, well_id=first.id, version_label="same label")

    version_ids = [version.id for version in second.versions]

    assert len(version_ids) == len(set(version_ids))

from wells.repository import delete_well_record, delete_well_version


def test_delete_well_version_removes_files_and_manifest_entry(tmp_path):
    df = pd.DataFrame({"DEPT": [1000.0], "C1": [80]})
    first = save_well_version(df, root=tmp_path, well_name="Demo", version_label="v1")
    second = save_well_version(df, root=tmp_path, well_id=first.id, version_label="v2")
    version_id = second.versions[0].id

    updated = delete_well_version(tmp_path, second.id, version_id)

    assert [version.id for version in updated.versions] == [second.versions[1].id]
    assert not (tmp_path / second.id / "versions" / version_id).exists()


def test_delete_well_record_removes_directory(tmp_path):
    df = pd.DataFrame({"DEPT": [1000.0], "C1": [80]})
    record = save_well_version(df, root=tmp_path, well_name="Demo")

    assert delete_well_record(tmp_path, record.id) is True
    assert not (tmp_path / record.id).exists()


def test_load_and_read_well_from_legacy_escaped_directory(tmp_path):
    df = pd.DataFrame({"DEPT": [1000.0], "C1": [80]})
    record = save_well_version(df, root=tmp_path, well_name="ГК,ННК,Дср", version_label="v1", depth_column="DEPT")
    original_dir = tmp_path / record.id
    legacy_dir = tmp_path / "20260703-#U0433#U043a-#U043d#U043d#U043a-#U0434#U0441#U0440"
    original_dir.rename(legacy_dir)

    loaded = load_well_record(tmp_path, record.id)
    csv_bytes = read_well_file_bytes(tmp_path, record.id, record.versions[0].id, "csv")

    assert loaded.id == record.id
    assert csv_bytes.startswith(b"\xef\xbb\xbf")

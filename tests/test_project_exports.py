from __future__ import annotations

import pytest

from projects import list_project_exports, read_project_export_file_bytes, save_project_export


def test_project_export_roundtrip_saves_file_and_manifest(tmp_path):
    data = b"<html><body>report</body></html>"

    record = save_project_export(
        data,
        root=tmp_path,
        project_id="demo",
        label="Depth report",
        file_name="depth report.html",
        mime_type="text/html",
        kind="interpretation_html",
        source="Well A",
        metadata={"rows": 3},
    )

    records = list_project_exports(tmp_path, "demo")

    assert len(records) == 1
    assert records[0].id == record.id
    assert records[0].file_name == "depth_report.html"
    assert records[0].mime_type == "text/html"
    assert records[0].metadata == {"rows": 3}
    assert read_project_export_file_bytes(tmp_path, "demo", record.id) == data
    assert (tmp_path / "demo" / "exports" / record.id / "depth_report.html").exists()


def test_project_export_uses_unique_ids_and_lists_newest_first(tmp_path):
    first = save_project_export(b"one", root=tmp_path, project_id="demo", label="same", file_name="a.csv")
    second = save_project_export(b"two", root=tmp_path, project_id="demo", label="same", file_name="a.csv")
    records = list_project_exports(tmp_path, "demo")

    assert first.id != second.id
    assert records[0].id == second.id
    assert {record.id for record in records} == {first.id, second.id}


def test_project_export_validates_data_and_project_id(tmp_path):
    with pytest.raises(ValueError, match="Нет данных экспорта"):
        save_project_export(b"", root=tmp_path, project_id="demo")

    with pytest.raises(ValueError, match="Некорректный идентификатор проекта"):
        save_project_export(b"data", root=tmp_path, project_id="../bad")


def test_project_export_read_rejects_unknown_record(tmp_path):
    with pytest.raises(FileNotFoundError, match="Project export not found"):
        read_project_export_file_bytes(tmp_path, "demo", "missing")

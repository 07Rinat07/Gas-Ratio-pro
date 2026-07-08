from __future__ import annotations

from services.las_manager_service import LasManagerService


SIMPLE_LAS = b"""~Version Information\nVERS. 2.0 : CWLS LOG ASCII STANDARD - VERSION 2.0\nWRAP. NO : ONE LINE PER DEPTH STEP\n~Well Information\nSTRT.M 1000.0 : START DEPTH\nSTOP.M 1000.5 : STOP DEPTH\nSTEP.M 0.5 : STEP\nNULL. -999.25 : NULL VALUE\nWELL. Demo : WELL\n~Curve Information\nDEPT.M : DEPTH\nGR.API : Gamma Ray\n~ASCII\n1000.0 80\n1000.5 82\n"""


def test_las_manager_service_saves_lists_and_deletes_file(tmp_path):
    service = LasManagerService(tmp_path)

    result = service.save_file(
        project_id="demo",
        data=SIMPLE_LAS,
        file_name="demo.las",
        well_name="Demo Well",
        version_label="raw",
    )

    records = service.list_files("demo")
    assert len(records) == 1
    assert records[0].id == result.record.id
    assert service.read_bytes("demo", result.record.id) == SIMPLE_LAS

    delete_result = service.delete_file("demo", result.record.id)
    assert delete_result.deleted is True
    assert service.list_files("demo") == ()


def test_las_manager_service_archives_restores_and_clears(tmp_path):
    service = LasManagerService(tmp_path)
    first = service.save_file(project_id="demo", data=SIMPLE_LAS, file_name="a.las", well_name="A").record
    second = service.save_file(project_id="demo", data=SIMPLE_LAS, file_name="b.las", well_name="B").record

    archive_result = service.archive_file("demo", first.id)
    assert archive_result.archived is True
    assert {record.id for record in service.list_files("demo")} == {second.id}
    assert {record.id for record in service.list_files("demo", include_archived=True)} == {first.id, second.id}

    restore_result = service.restore_file("demo", first.id)
    assert restore_result.archived is False
    assert {record.id for record in service.list_files("demo")} == {first.id, second.id}

    clear_result = service.clear_files("demo")
    assert clear_result.deleted_count == 2
    assert service.list_files("demo", include_archived=True) == ()

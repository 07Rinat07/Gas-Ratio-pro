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


def test_las_manager_service_delete_releases_resources_and_updates_index(tmp_path):
    from core.storage_lifecycle import CacheManager, DeleteEngine, FileHandleManager, IndexManager, ResourceManager
    from projects.project_index import validate_project_file_index

    resource_manager = ResourceManager()
    cache_manager = CacheManager()
    file_handle_manager = FileHandleManager(resource_manager)
    delete_engine = DeleteEngine(
        resource_manager,
        cache_manager=cache_manager,
        file_handle_manager=file_handle_manager,
        attempts=1,
    )
    service = LasManagerService(
        tmp_path,
        resource_manager=resource_manager,
        cache_manager=cache_manager,
        file_handle_manager=file_handle_manager,
        delete_engine=delete_engine,
        index_manager=IndexManager(tmp_path),
    )

    record = service.save_file(project_id="demo", data=SIMPLE_LAS, file_name="demo.las", well_name="Demo").record
    las_dir = service.las_dir("demo", record.id)
    service.register_las_file("demo", record.id, owner="test-preview")
    service.register_las_cache("las-preview-cache", owner="test-preview", path=las_dir)

    assert resource_manager.diagnostics().total == 1
    assert len(cache_manager.diagnostics()) == 1

    result = service.delete_file("demo", record.id)

    assert result.deleted is True
    assert result.released_resources >= 1
    assert resource_manager.diagnostics().total == 0
    assert cache_manager.diagnostics() == ()
    assert not las_dir.exists()
    assert service.list_files("demo", include_archived=True) == ()
    assert all(record.id not in entry.relative_path for entry in validate_project_file_index(tmp_path, "demo"))


def test_las_manager_service_compatibility_aliases(tmp_path):
    service = LasManagerService(tmp_path)
    record = service.create(project_id="demo", data=SIMPLE_LAS, file_name="demo.las", well_name="Demo").record

    assert service.list("demo")
    assert service.list_las_files("demo")
    assert service.list_las_wells("demo")
    assert service.export_formats

    archive_result = service.archive("demo", record.id)
    assert archive_result.archived is True
    restore_result = service.restore("demo", record.id)
    assert restore_result.archived is False

    delete_result = service.remove_file("demo", record.id)
    assert delete_result.deleted is True

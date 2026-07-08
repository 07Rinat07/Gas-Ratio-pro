from __future__ import annotations

from core.storage_lifecycle import CacheManager, DeleteEngine, FileHandleManager, IndexManager, ResourceManager
from services.export_manager_service import ExportManagerService


def _service(tmp_path):
    resources = ResourceManager()
    cache = CacheManager()
    files = FileHandleManager(resources)
    delete_engine = DeleteEngine(resources, cache_manager=cache, file_handle_manager=files, attempts=2, delay_seconds=0)
    return ExportManagerService(
        tmp_path,
        delete_engine=delete_engine,
        index_manager=IndexManager(tmp_path),
        resource_manager=resources,
        cache_manager=cache,
        file_handle_manager=files,
    ), resources, cache, files


def test_export_manager_service_saves_reads_and_deletes_export(tmp_path):
    service, _resources, _cache, _files = _service(tmp_path)

    saved = service.save_export(
        project_id="demo",
        data=b"payload",
        label="Demo",
        file_name="demo.txt",
        mime_type="text/plain",
        kind="text",
        source="test",
        metadata={"a": 1},
    )

    assert service.count_exports("demo") == 1
    assert service.read_export_bytes("demo", saved.record.id) == b"payload"

    deleted = service.delete_export("demo", saved.record.id)

    assert deleted.deleted is True
    assert service.list_exports("demo") == ()


def test_export_manager_service_clears_all_exports(tmp_path):
    service, _resources, _cache, _files = _service(tmp_path)
    service.save_export(project_id="demo", data=b"one", label="One", file_name="one.txt", mime_type="text/plain", kind="text")
    service.save_export(project_id="demo", data=b"two", label="Two", file_name="two.txt", mime_type="text/plain", kind="text")

    result = service.clear_exports("demo")

    assert result.removed_count == 2
    assert service.count_exports("demo") == 0


def test_export_manager_service_releases_resources_and_cache_before_delete(tmp_path):
    service, resources, cache, files = _service(tmp_path)
    saved = service.save_export(
        project_id="demo",
        data=b"payload",
        label="Demo",
        file_name="demo.txt",
        mime_type="text/plain",
        kind="text",
    )
    export_file = tmp_path / "demo" / "exports" / saved.record.id / "demo.txt"
    files.register_file(export_file, owner="test-preview", resource_id="export-preview-file")
    resources.register_dataframe("export-preview-df", owner="test-preview", path=export_file)
    cache.register("export-preview-cache", owner="test-preview", path=export_file)

    result = service.delete_export("demo", saved.record.id)

    assert result.deleted is True
    assert resources.diagnostics().total == 0
    assert cache.diagnostics() == ()
    assert not export_file.exists()


def test_export_manager_service_compatibility_aliases(tmp_path):
    service, _resources, _cache, _files = _service(tmp_path)
    saved = service.save_export(
        project_id="demo",
        data=b"payload",
        label="Demo",
        file_name="demo.txt",
        mime_type="text/plain",
        kind="text",
    )

    assert service.count("demo") == 1
    assert service.list("demo")[0].id == saved.record.id
    assert service.read_bytes("demo", saved.record.id) == b"payload"
    assert service.refresh("demo")[0].id == saved.record.id
    assert service.delete("demo", saved.record.id).deleted is True

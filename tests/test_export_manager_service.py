from __future__ import annotations

from services.export_manager_service import ExportManagerService


def test_export_manager_service_saves_reads_and_deletes_export(tmp_path):
    service = ExportManagerService(tmp_path)

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
    service = ExportManagerService(tmp_path)
    service.save_export(project_id="demo", data=b"one", label="One", file_name="one.txt", mime_type="text/plain", kind="text")
    service.save_export(project_id="demo", data=b"two", label="Two", file_name="two.txt", mime_type="text/plain", kind="text")

    result = service.clear_exports("demo")

    assert result.removed_count == 2
    assert service.count_exports("demo") == 0

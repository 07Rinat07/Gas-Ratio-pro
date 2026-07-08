from __future__ import annotations

from pathlib import Path

from core.storage_lifecycle import DeleteEngine, ResourceManager


def test_delete_engine_deletes_directory_and_releases_registered_resource(tmp_path: Path) -> None:
    resource_manager = ResourceManager()
    target = tmp_path / "dataset"
    target.mkdir()
    source = target / "source.xlsx"
    source.write_bytes(b"fake-xlsx")
    resource_manager.register("preview:source", source, owner="Dataset Preview")

    result = DeleteEngine(resource_manager=resource_manager, retries=1).delete_path(target)

    assert result.deleted is True
    assert target.exists() is False
    assert len(result.released_resources) == 1
    assert resource_manager.diagnostics() == ()

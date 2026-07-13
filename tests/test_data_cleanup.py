from pathlib import Path

import pytest

from core.data_cleanup import DataCleanupService


def test_cleanup_removes_disposable_data_and_preserves_projects(tmp_path: Path):
    data_root = tmp_path / "data"
    (data_root / "cache").mkdir(parents=True)
    (data_root / "cache" / "old.bin").write_bytes(b"1234")
    (data_root / "temp").mkdir()
    (data_root / "temp" / "work.tmp").write_bytes(b"12")
    (data_root / "projects" / "demo").mkdir(parents=True)
    project_file = data_root / "projects" / "demo" / "project.json"
    project_file.write_text("{}", encoding="utf-8")

    result = DataCleanupService(data_root).cleanup()

    assert result.freed_bytes == 6
    assert not (data_root / "cache").exists()
    assert not (data_root / "temp").exists()
    assert project_file.exists()


def test_cleanup_dry_run_does_not_delete(tmp_path: Path):
    data_root = tmp_path / "data"
    target = data_root / "exports"
    target.mkdir(parents=True)
    (target / "report.pdf").write_bytes(b"abc")

    result = DataCleanupService(data_root).cleanup(dry_run=True)

    assert result.dry_run is True
    assert result.freed_bytes == 0
    assert target.exists()
    assert result.items[0].bytes == 3
    assert result.items[0].removed is False


def test_cleanup_rejects_paths_outside_data_root(tmp_path: Path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(ValueError):
        DataCleanupService(data_root).cleanup(extra_paths=(outside,))
